"""Sole research SQL/manifest owner. Compression is outside SQLite transactions."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

from app.config import get_settings
from app.database_connection import connection, read_only_connection
from app.strategy_research_series import METHOD, QUALITY, Deriver, stable_hash

SCHEMA = "strategy-research.parquet.v1"
_CAPTURE_STATUS_CACHE: tuple[str, float, dict] | None = None
_CAPTURE_STATUS_LOCK = threading.Lock()
_CAPTURE_STATUS_TTL_SECONDS = 30.0


def invalidate_capture_status_cache():
    global _CAPTURE_STATUS_CACHE
    with _CAPTURE_STATUS_LOCK:
        _CAPTURE_STATUS_CACHE = None


def root_path():
    return Path(get_settings().strategy_research_path).resolve()


def now():
    return datetime.now(UTC).isoformat()


def checkpoint():
    with connection() as db:
        row = db.execute("SELECT * FROM research_strategy_capture WHERE id=1").fetchone()
    return dict(row) if row else {"cursor": None, "state_json": "null", "status_json": "{}"}


def assert_sqlite_safe(db):
    # Upstream fixes: 3.51.3, 3.50.7, 3.44.6 (do not infer all intervening releases safe).
    version = sqlite3.sqlite_version_info
    fixed = (
        version >= (3, 51, 3)
        or ((3, 50, 7) <= version < (3, 51, 0))
        or ((3, 44, 6) <= version < (3, 45, 0))
    )
    if db.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal" and not fixed:
        raise RuntimeError("SQLite WAL-reset fix required before research ingest")
    if db.execute("PRAGMA synchronous").fetchone()[0] < 2:
        raise RuntimeError("research requires existing FULL-or-stronger durability")


def publish(batch):
    import pyarrow as pa
    import pyarrow.parquet as pq

    events = batch["events"]
    if not events:
        return None
    if batch["schemaVersion"] != "market-events.v1":
        raise ValueError("unsupported market batch schema")
    before = checkpoint()
    if before["cursor"] != batch["after"]:
        with connection() as db:
            prior = db.execute(
                "SELECT part_id FROM research_strategy_parts WHERE end_cursor=?",
                (batch["nextCursor"],),
            ).fetchone()
        if prior:
            return prior[0]
        raise ValueError("market cursor conflict")
    if not batch["nextCursor"] or batch["after"] == batch["nextCursor"]:
        raise ValueError("batch did not advance")
    deriver = Deriver(json.loads(before["state_json"]))
    derived = []
    ids = set()
    for event in events:
        if event["eventId"] in ids:
            raise ValueError("duplicate event within batch")
        ids.add(event["eventId"])
        derived.extend(deriver.consume(event))
    # Deterministic filename and payload allow replay after rename-before-commit crash.
    part_id = stable_hash(
        {
            "from": batch["after"],
            "to": batch["nextCursor"],
            "schema": SCHEMA,
            "method": METHOD,
            "quality": QUALITY,
        }
    )
    folder = root_path()
    folder.mkdir(parents=True, exist_ok=True)
    final = folder / (part_id + ".parquet")
    temp = folder / (part_id + ".pending")
    rows = [
        {
            "layer": "raw",
            "kind": e["kind"],
            "pair": "",
            "scope": e["quoteScope"],
            "received_at": e["runtimeReceivedAt"],
            "event_json": json.dumps(e, sort_keys=True),
        }
        for e in events
    ]
    rows += [
        {
            "layer": "derived",
            "kind": e["kind"],
            "pair": e.get("pairId", ""),
            "scope": e.get("quoteScope", "public"),
            "received_at": e.get("receivedAt", ""),
            "event_json": json.dumps(e, sort_keys=True),
        }
        for e in derived
    ]
    schema = pa.schema(
        [
            (name, pa.string())
            for name in ("layer", "kind", "pair", "scope", "received_at", "event_json")
        ],
        metadata={
            b"schema": SCHEMA.encode(),
            b"numbers": b"lossless decimal-text",
            b"times": b"UTC ISO8601; native ns/ms integer-text",
        },
    )
    table = pa.Table.from_pylist(rows, schema=schema)
    if shutil.disk_usage(folder).free < get_settings().strategy_research_min_free_bytes:
        raise OSError("archive disk budget exhausted")
    pq.write_table(table, temp, compression="zstd")
    with temp.open("r+b") as f:
        os.fsync(f.fileno())
    payload_hash = stable_hash(rows)
    if final.exists():
        existing = pq.read_table(final).to_pylist()
        if stable_hash(existing) != payload_hash:
            raise ValueError("orphan shard content conflict")
        # Keep evidence; replacing with identical durable content is safe and bounded.
    os.replace(temp, final)
    checksum = hashlib.sha256(final.read_bytes()).hexdigest()
    pq.read_metadata(final)  # footer validation before publication
    with connection() as db:
        assert_sqlite_safe(db)
        # Keep the connection-level 30s wait.  A-share close publishing and
        # the serving projection are bounded writers on the same SQLite file;
        # a 250ms override made normal overlap look like a failed ingest.
        db.execute("PRAGMA busy_timeout=30000")
        current = db.execute("SELECT cursor FROM research_strategy_capture WHERE id=1").fetchone()
        if (current[0] if current else None) != batch["after"]:
            raise ValueError("concurrent research publisher")
        db.execute(
            """INSERT INTO research_strategy_parts
            (part_id,start_cursor,end_cursor,path,checksum,row_count,first_at,last_at,published_at)
            VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                part_id,
                batch["after"],
                batch["nextCursor"],
                final.name,
                checksum,
                len(rows),
                min((e["runtimeReceivedAt"] for e in events), key=datetime.fromisoformat),
                max((e["runtimeReceivedAt"] for e in events), key=datetime.fromisoformat),
                now(),
            ),
        )
        db.execute(
            """INSERT INTO research_strategy_capture(id,cursor,state_json,status_json)
            VALUES(1,?,?,?) ON CONFLICT(id) DO UPDATE SET cursor=excluded.cursor,
            state_json=excluded.state_json,status_json=excluded.status_json""",
            (batch["nextCursor"], json.dumps(deriver.state), json.dumps(batch.get("capture", {}))),
        )
    invalidate_capture_status_cache()
    return part_id


def parts():
    with read_only_connection() as db:
        rows = db.execute("SELECT * FROM research_strategy_parts ORDER BY rowid").fetchall()
    return [dict(row) for row in rows]


def read_rows(
    *,
    pair=None,
    layer="derived",
    kind=None,
    start=None,
    end=None,
    part_ids=None,
    max_rows=200000,
    symbol=None,
    source_start_ms=None,
    source_end_ms=None,
):
    import pyarrow.parquet as pq

    out = []
    for part in parts():
        if part_ids is not None and part["part_id"] not in part_ids:
            continue
        if start and datetime.fromisoformat(part["last_at"]) < datetime.fromisoformat(start):
            continue
        if end and datetime.fromisoformat(part["first_at"]) > datetime.fromisoformat(end):
            continue
        path = root_path() / part["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != part["checksum"]:
            raise ValueError("published shard checksum mismatch")
        filters = [("layer", "=", layer)]
        if pair:
            filters.append(("pair", "=", pair))
        if kind:
            filters.append(("kind", "=", kind))
        table = pq.read_table(path, filters=filters, columns=["event_json", "received_at"])
        for row in table.to_pylist():
            if (
                start and datetime.fromisoformat(row["received_at"]) < datetime.fromisoformat(start)
            ) or (end and datetime.fromisoformat(row["received_at"]) > datetime.fromisoformat(end)):
                continue
            event = json.loads(row["event_json"])
            if symbol and event.get("symbol") != symbol:
                continue
            # Historical source windows are distinct from archive receipt windows.
            source = event.get("closeTimeMs", event.get("sourceTimeMs"))
            if source_start_ms is not None and (source is None or int(source) < source_start_ms):
                continue
            if source_end_ms is not None and (source is None or int(source) > source_end_ms):
                continue
            out.append(event)
            if len(out) > max_rows:
                raise ValueError("research scan budget exceeded; narrow the window")
    return out


def capture_status():
    global _CAPTURE_STATUS_CACHE
    cache_path = str(get_settings().database_path)
    now_monotonic = time.monotonic()
    with _CAPTURE_STATUS_LOCK:
        if (
            _CAPTURE_STATUS_CACHE is not None
            and _CAPTURE_STATUS_CACHE[0] == cache_path
            and now_monotonic - _CAPTURE_STATUS_CACHE[1] < _CAPTURE_STATUS_TTL_SECONDS
        ):
            return dict(_CAPTURE_STATUS_CACHE[2])
    entries = parts()
    checkpoint_row = checkpoint()
    folder = root_path()
    size = sum((folder / p["path"]).stat().st_size for p in entries)
    elapsed = (
        (
            datetime.fromisoformat(entries[-1]["last_at"])
            - datetime.fromisoformat(entries[0]["first_at"])
        ).total_seconds()
        if entries
        else 0
    )
    free = shutil.disk_usage(folder if folder.exists() else folder.parent).free
    per_day = str(int(size / elapsed * 86400)) if elapsed > 0 else None
    result = {
        "runtime": json.loads(checkpoint_row["status_json"]),
        "publishedThrough": entries[-1]["last_at"] if entries else None,
        "historyStart": entries[0]["first_at"] if entries else None,
        "parts": len(entries),
        "bytes": str(size),
        "diskFreeBytes": str(free),
        "projectedBytesPerDay": per_day,
        "projectionWindowSeconds": str(elapsed),
        "capacityProjectionIsMeasuredWindowOnly": True,
        "dataVersion": stable_hash([p["checksum"] for p in entries]),
        "cursor": checkpoint_row["cursor"],
        "sqliteVersion": sqlite3.sqlite_version,
        "backup": "not_verified",
        "theoreticalTradingDuration": None,
        "calendarCoverage": "unverified",
    }
    with _CAPTURE_STATUS_LOCK:
        _CAPTURE_STATUS_CACHE = (cache_path, time.monotonic(), result)
    return dict(result)


def capture_metadata():
    """Return the small manifest subset needed by ordinary HTTP envelopes.

    Full ``capture_status`` also stats every archived Parquet file to report
    byte totals. That is appropriate for the explicit status endpoint but made
    every chart read perform thousands of Windows file-stat calls. Ordinary
    reads only need publication bounds and the manifest version.
    """
    with read_only_connection() as db:
        rows = db.execute(
            "SELECT first_at,last_at,checksum FROM research_strategy_parts ORDER BY rowid"
        ).fetchall()
        checkpoint_row = db.execute(
            "SELECT cursor,status_json FROM research_strategy_capture WHERE id=1"
        ).fetchone()
    checksums = [row["checksum"] for row in rows]
    return {
        "runtime": json.loads(checkpoint_row["status_json"]) if checkpoint_row else {},
        "publishedThrough": rows[-1]["last_at"] if rows else None,
        "historyStart": rows[0]["first_at"] if rows else None,
        "parts": len(rows),
        "dataVersion": stable_hash(checksums),
        "cursor": checkpoint_row["cursor"] if checkpoint_row else None,
    }


def enqueue_experiment(user_id, params):
    cutoff = params["cutoff"]
    frozen = [
        p
        for p in parts()
        if datetime.fromisoformat(p["first_at"]) <= datetime.fromisoformat(cutoff)
    ]
    identity = {
        "user": user_id,
        "parameters": params,
        "parts": [p["part_id"] for p in frozen],
        "method": "experiment.v1",
    }
    run_id = stable_hash(identity)
    with connection() as db:
        db.execute(
            """INSERT OR IGNORE INTO research_strategy_experiments
            (run_id,user_id,parameters_json,parts_json,status,created_at)
            VALUES(?,?,?,?,'queued',?)""",
            (run_id, user_id, json.dumps(params), json.dumps(identity["parts"]), now()),
        )
    return get_experiment(run_id, user_id)


def get_experiment(run_id, user_id):
    with connection() as db:
        row = db.execute(
            "SELECT * FROM research_strategy_experiments WHERE run_id=? AND user_id=?",
            (run_id, user_id),
        ).fetchone()
    if row is None:
        return None
    result = dict(row)
    for key in ("parameters_json", "parts_json", "result_json"):
        result[key.removesuffix("_json")] = json.loads(result.pop(key) or "null")
    if isinstance(result.get("result"), dict) and "artifact" in result["result"]:
        import pyarrow.parquet as pq

        ref = result["result"]["artifact"]
        path = root_path() / ref["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != ref["checksum"]:
            raise ValueError("experiment artifact checksum mismatch")
        result["result"] = json.loads(
            pq.read_table(path, columns=["result_json"]).column(0)[0].as_py()
        )
    return result


def experiment_cancelled(run_id):
    with connection() as db:
        row = db.execute(
            "SELECT status FROM research_strategy_experiments WHERE run_id=?", (run_id,)
        ).fetchone()
    return row is None or row[0] == "cancelled"


def next_experiment():
    with connection() as db:
        row = db.execute(
            "SELECT * FROM research_strategy_experiments WHERE status='queued' "
            "ORDER BY created_at LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        changed = db.execute(
            "UPDATE research_strategy_experiments SET status='running' "
            "WHERE run_id=? AND status='queued'",
            (row["run_id"],),
        ).rowcount
    return dict(row) if changed else None


def finish_experiment(run_id, result=None, error=None):
    if result is not None:
        import pyarrow as pa
        import pyarrow.parquet as pq

        folder = root_path()
        folder.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(folder).free < get_settings().strategy_research_min_free_bytes:
            raise OSError("experiment archive disk budget exhausted")
        final = folder / ("experiment-" + run_id + ".parquet")
        temp = final.with_suffix(".pending")
        pq.write_table(pa.table({"result_json": [json.dumps(result)]}), temp, compression="zstd")
        with temp.open("r+b") as f:
            os.fsync(f.fileno())
        pq.read_metadata(temp)
        os.replace(temp, final)
        result = {
            "summary": result["summary"],
            "artifact": {
                "path": final.name,
                "checksum": hashlib.sha256(final.read_bytes()).hexdigest(),
            },
        }
    with connection() as db:
        db.execute(
            "UPDATE research_strategy_experiments SET status=?,result_json=?,error=? "
            "WHERE run_id=? AND status='running'",
            ("failed" if error else "completed", json.dumps(result), error, run_id),
        )


def cancel_experiment(run_id, user_id):
    with connection() as db:
        db.execute(
            "UPDATE research_strategy_experiments SET status='cancelled' "
            "WHERE run_id=? AND user_id=? AND status IN ('queued','running')",
            (run_id, user_id),
        )


def recover_experiments():
    with connection() as db:
        db.execute(
            "UPDATE research_strategy_experiments SET status='queued' WHERE status='running'"
        )


def save_draft(user_id, payload):
    key = stable_hash({"owner": user_id, "payload": payload})
    with connection() as db:
        db.execute(
            "INSERT OR IGNORE INTO research_strategy_drafts(id,user_id,payload_json,created_at)"
            " VALUES(?,?,?,?)",
            (key, user_id, json.dumps(payload), now()),
        )
    return {
        "id": key,
        "parameters": payload,
        "executionAuthorized": False,
        "requires": ["identity", "fresh_quotes", "quantity_matching", "risk_checks"],
    }


def backup(destination: Path):
    """Online DB snapshot first, then exactly its sealed manifests; no active spool copy."""
    destination.mkdir(parents=True, exist_ok=False)
    with connection() as source:
        target = sqlite3.connect(destination / "platform.db")
        source.backup(target)
        exists = target.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='research_strategy_parts'"
        ).fetchone()
        manifest = []
        if exists:
            cur = target.execute("SELECT * FROM research_strategy_parts")
            manifest = [
                dict(zip([x[0] for x in cur.description], row, strict=True))
                for row in cur.fetchall()
            ]
        if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("backup integrity check failed")
        if exists:
            for row in target.execute(
                "SELECT result_json FROM research_strategy_experiments "
                "WHERE result_json IS NOT NULL"
            ):
                result = json.loads(row[0])
                if isinstance(result, dict) and result.get("artifact"):
                    manifest.append(result["artifact"])
        target.close()
    for part in manifest:
        source = root_path() / part["path"]
        target_path = destination / part["path"]
        shutil.copy2(source, target_path)
        if hashlib.sha256(target_path.read_bytes()).hexdigest() != part["checksum"]:
            raise ValueError("backup shard checksum mismatch")
    (destination / "manifest.json").write_text(json.dumps(manifest))
    return {"parts": len(manifest), "integrity": "ok"}


def get_draft(user_id, draft_id):
    with connection() as db:
        row = db.execute(
            "SELECT payload_json FROM research_strategy_drafts WHERE id=? AND user_id=?",
            (draft_id, user_id),
        ).fetchone()
    return json.loads(row[0]) if row else None


def verify_backup(destination: Path):
    """Verify the complete frozen catalog, including every experiment artifact."""
    destination = destination.resolve()
    db = sqlite3.connect((destination / "platform.db").as_uri() + "?mode=ro", uri=True)
    try:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Backup integrity failed")
        expected = {}
        exists = db.execute(
            "SELECT 1 FROM sqlite_master WHERE name='research_strategy_parts'"
        ).fetchone()
        if exists:
            expected.update(db.execute("SELECT path,checksum FROM research_strategy_parts"))
            for row in db.execute(
                "SELECT result_json FROM research_strategy_experiments "
                "WHERE result_json IS NOT NULL"
            ):
                result = json.loads(row[0])
                if isinstance(result, dict) and result.get("artifact"):
                    ref = result["artifact"]
                    expected[ref["path"]] = ref["checksum"]
        manifest = json.loads((destination / "manifest.json").read_text())
        actual = {part["path"]: part["checksum"] for part in manifest}
        if len(actual) != len(manifest) or expected != actual:
            raise ValueError("Backup catalog differs from its manifest")
        for name, checksum in actual.items():
            file = (destination / name).resolve()
            if (
                file.parent != destination
                or hashlib.sha256(file.read_bytes()).hexdigest() != checksum
            ):
                raise ValueError("Backup manifest/checksum failed")
        return {"status": "verified", "parts": len(actual), "restore": "isolated_read_only"}
    finally:
        db.close()
