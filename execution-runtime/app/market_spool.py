"""Research-only sequential spool. No order journal or Platform database access."""

from __future__ import annotations

import hashlib
import json
import os
import queue
import shutil
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, separators=(",", ":"), sort_keys=True, allow_nan=False
    ).encode()


class MarketSpool:
    """Only fsynced frames are exported; an incomplete tail is never rewritten."""

    def __init__(
        self,
        root: Path,
        *,
        max_bytes=2_000_000_000,
        min_free_bytes=1_000_000_000,
        queue_size=8192,
        segment_bytes=8_000_000,
    ):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_bytes, self.min_free_bytes = max_bytes, min_free_bytes
        self.segment_bytes = segment_bytes
        self.session = uuid4().hex
        self.sequence = 0
        self.durable_sequence = 0
        self.queue: queue.Queue = queue.Queue(queue_size)
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.error: str | None = None
        self.dropped = 0
        self.durable: dict[str, int] = {}
        self.last_received: str | None = None
        self.last_durable: str | None = None
        self._lease = None
        self._thread = None
        self._file = None
        self._name = ""
        self._bytes = 0
        self.recovery_gaps: list[str] = []

    def start(self):
        self._lease = (self.root / "capture.lock").open("a+b")
        try:
            if os.name == "nt":
                import msvcrt

                self._lease.seek(0)
                if self._lease.read(1) == b"":
                    self._lease.write(b"0")
                    self._lease.flush()
                self._lease.seek(0)
                msvcrt.locking(self._lease.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._lease.close()
            raise RuntimeError("market capture already owns this spool") from None
        logs = sorted(self.root.glob("*.log"))
        # Older segments were fsynced and sealed by the writer before rotation.
        # Re-hashing the entire retained spool on every restart made a 17GB
        # archive block Runtime startup for minutes and left API/Web at 502.
        # Trust sealed segments and validate only the current tail, where an
        # interrupted frame can actually exist.
        for path in logs[:-1]:
            size = path.stat().st_size
            self.durable[path.name] = size
            self._bytes += size
        for path in logs[-1:]:
            valid = 0
            with path.open("rb") as stream:
                for line in stream:
                    try:
                        frame = json.loads(line)
                        if hashlib.sha256(canonical(frame["event"])).hexdigest() != frame["sha256"]:
                            raise ValueError("checksum")
                    except (ValueError, KeyError):
                        self.recovery_gaps.append(path.name)
                        break
                    valid = stream.tell()
            self.durable[path.name] = valid
            self._bytes += valid
        self._thread = threading.Thread(target=self._write, name="market-spool", daemon=True)
        self._thread.start()
        self.capture(
            "quality",
            "runtime",
            "public",
            {"reason": "collector_started", "recoveryGaps": self.recovery_gaps},
            quality=["capture_gap"],
        )

    def capture(
        self,
        kind,
        stream,
        scope,
        payload,
        *,
        mode="realtime",
        source_ms=None,
        quality=None,
        source_layer="native",
        received_at=None,
        source_clock=None,
    ):
        # One clock domain and admission lock across all callbacks, never SQL/SDK calls.
        with self.lock:
            if self.error or self.stop_event.is_set():
                return False
            self.sequence += 1
            now = received_at or datetime.now(UTC).isoformat()
            event = {
                "schemaVersion": "market-events.v1",
                "eventId": f"{self.session}:{self.sequence}",
                "collectorSessionId": self.session,
                "ingestSequence": str(self.sequence),
                "runtimeReceivedAt": now,
                "runtimeMonotonicNs": str(time.monotonic_ns()),
                "sourceEventTimeMs": str(source_ms) if source_ms is not None else None,
                "sourcePublishTimeMs": str(payload.get("ts")) if payload.get("ts") else None,
                "sourcePrecision": "ms" if source_ms is not None else "unknown",
                "kind": kind,
                "stream": stream,
                "quoteScope": scope,
                "payload": payload,
                "ingestionMode": mode,
                "availableAtOriginal": "unknown" if mode == "backfill" else now,
                "sourceLayer": source_layer,
                "sourceClock": source_clock,
                "quality": quality or [],
            }
            try:
                self.queue.put_nowait(event)
            except queue.Full:
                self.dropped += 1
                self.error = "capture_gap:queue_overflow"
                return False
            self.last_received = now
            return self.sequence

    def _rotate(self):
        if self._file:
            self._file.close()
        previous = max((int(name.split("-", 1)[0]) for name in self.durable), default=0)
        self._name = f"{max(time.time_ns(), previous + 1):020d}-{self.session}.log"
        self._file = (self.root / self._name).open("xb")
        with self.lock:
            self.durable[self._name] = 0

    def _write(self):
        try:
            self._rotate()
            while not self.stop_event.is_set() or not self.queue.empty():
                batch = []
                try:
                    batch.append(self.queue.get(timeout=0.2))
                except queue.Empty:
                    continue
                for _ in range(511):
                    try:
                        batch.append(self.queue.get_nowait())
                    except queue.Empty:
                        break
                encoded = []
                persisted = datetime.now(UTC).isoformat()
                for event in batch:
                    event["spoolWriteStartedAt"] = persisted
                    encoded.append(
                        canonical(
                            {"event": event, "sha256": hashlib.sha256(canonical(event)).hexdigest()}
                        )
                        + b"\n"
                    )
                size = sum(map(len, encoded))
                if (
                    self._bytes + size > self.max_bytes
                    or shutil.disk_usage(self.root).free < self.min_free_bytes + size
                ):
                    raise OSError("capacity_budget_exhausted")
                assert self._file is not None
                self._file.writelines(encoded)
                self._file.flush()
                os.fsync(self._file.fileno())
                self._bytes += size
                with self.lock:
                    self.durable[self._name] = self._file.tell()
                    self.last_durable = datetime.now(UTC).isoformat()
                    self.durable_sequence = int(batch[-1]["ingestSequence"])
                if self._file.tell() >= self.segment_bytes:
                    self._rotate()
        except Exception as exc:
            self.error = f"capture_gap:{type(exc).__name__}:{exc}"
        finally:
            if self._file:
                self._file.close()

    def read(self, after: str | None = None, limit=1000):
        if not 1 <= limit <= 5000:
            raise ValueError("limit must be 1..5000")
        with self.lock:
            bounds = sorted(self.durable.items())
        name, offset = "", 0
        if after:
            try:
                name, offset_text = after.rsplit(":", 1)
                offset = int(offset_text)
            except (ValueError, AttributeError):
                raise ValueError("invalid market cursor") from None
            if name not in dict(bounds) or not 0 <= offset <= dict(bounds)[name]:
                raise ValueError("cursor outside replay coverage")
        events, cursor = [], after
        for part, end in bounds:
            if part < name:
                continue
            with (self.root / part).open("rb") as stream:
                stream.seek(offset if part == name else 0)
                if stream.tell() and stream.tell() < end:
                    stream.seek(stream.tell() - 1)
                    if stream.read(1) != b"\n":
                        raise ValueError("cursor is not a frame boundary")
                while stream.tell() < end and len(events) < limit:
                    frame = json.loads(stream.readline())
                    event = frame["event"]
                    if hashlib.sha256(canonical(event)).hexdigest() != frame["sha256"]:
                        raise ValueError("spool checksum mismatch")
                    events.append(event)
                    cursor = f"{part}:{stream.tell()}"
            if len(events) >= limit:
                break
        return {
            "schemaVersion": "market-events.v1",
            "after": after,
            "nextCursor": cursor,
            "events": events,
            "capture": self.status(),
        }

    def status(self):
        return {
            "sessionId": self.session,
            "status": "failed" if self.error else "collecting",
            "lastReceivedAt": self.last_received,
            "lastDurableAt": self.last_durable,
            "error": self.error,
            "dropped": self.dropped,
            "queued": self.queue.qsize(),
            "bytes": str(self._bytes),
            "budgetBytes": str(self.max_bytes),
            "freeBytes": str(shutil.disk_usage(self.root).free),
            "recoveryGaps": self.recovery_gaps,
        }

    def close(self):
        self.stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
            if self._thread.is_alive():
                raise RuntimeError("spool writer did not stop")
        if self._lease:
            self._lease.close()
