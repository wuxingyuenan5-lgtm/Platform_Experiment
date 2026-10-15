"""Lifecycle-owned public capture; fixed MT5 account reads use the existing Worker."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import monotonic

from fastapi import APIRouter, HTTPException, Query

from app.cross_spread_schedule import resolve_mt5_session_state
from app.market_spool import MarketSpool


class ResearchCapture:
    def __init__(self, settings, gateway):
        self.settings, self.gateway = settings, gateway
        self.spool = None
        self.stop_event = threading.Event()
        self.threads = []
        self.error = None
        self.source_health = {}
        self.bybit_clock = None
        self._bybit_last_received: dict[str, float] = {}

    def start(self):
        if not self.settings.research_capture_enabled:
            return
        if self.gateway.name != "bybit_mt5":
            self.error = "real_market_gateway_required"
            return
        try:
            self.spool = MarketSpool(
                Path(self.settings.research_spool_path),
                max_bytes=self.settings.research_spool_max_bytes,
                min_free_bytes=self.settings.research_min_free_bytes,
            )
            self.spool.start()
        except Exception as exc:
            self.error = str(exc)
            return
        for target in (
            self._bybit,
            self._mt5,
            self._rates,
            self._scan,
            self._clock,
            self._prices,
            self._mt5_history,
        ):
            t = threading.Thread(target=target, name="research-" + target.__name__, daemon=True)
            t.start()
            self.threads.append(t)

    def _quality(self, stream, scope, reason):
        self.source_health[stream] = {
            "status": "gap",
            "reason": reason,
            "at": datetime.now(UTC).isoformat(),
        }
        if self.spool:
            self.spool.capture("quality", stream, scope, {"reason": reason}, quality=["source_gap"])

    def _capture_bybit(self, kind, stream, scope, payload, **kwargs):
        # SDK callbacks execute on socket threads; only accepted raw events advance health.
        assert self.spool
        accepted = self.spool.capture(
            kind, stream, scope, payload, source_clock=self.bybit_clock, **kwargs
        )
        if accepted:
            self.source_health[stream] = {
                "status": "received" if kind == "bybit_message" else "gap",
                "lastReceivedAt": datetime.now(UTC).isoformat(),
                "sourceTimeMs": str(kwargs["source_ms"])
                if kwargs.get("source_ms") is not None
                else None,
                "reason": payload.get("reason") if kind == "quality" else None,
            }
        if accepted and kind == "bybit_message":
            category = ":".join(stream.split(":")[:2])
            self._bybit_last_received[category] = monotonic()
            self.source_health[category] = {
                "status": "receiving",
                "lastReceivedAt": datetime.now(UTC).isoformat(),
            }
        return accepted

    def _clock(self):
        assert self.spool
        account = self.settings.research_bybit_account_id
        while not self.stop_event.is_set() and not self.spool.error:
            delay = 60
            try:
                from app.research_clock import sample_clock

                client = self.gateway.bybit._connections.client(account)
                evidence = sample_clock(client)
                evidence["collectorSessionId"] = self.spool.session
                accepted = self.spool.capture(
                    "clock_calibration",
                    "bybit:clock",
                    "public",
                    evidence,
                    source_layer="rest_clock_interval",
                )
                if accepted:
                    self.bybit_clock = evidence | {"eventId": f"{self.spool.session}:{accepted}"}
                    self.source_health["bybit:clock"] = {
                        "status": "interval_measured",
                        "lastReceivedAt": datetime.now(UTC).isoformat(),
                        **self.bybit_clock,
                    }
            except Exception as exc:
                from app.research_clock import conservative_utc_now

                if conservative_utc_now(self.bybit_clock) is None:
                    reason = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
                    self._quality("bybit:clock", "public", reason)
                    delay = 5
            self.stop_event.wait(delay)

    def _bybit(self):
        assert self.spool
        # Exactly three distinct subscriptions. XAUT linear is shared by consumers.
        owner = self.gateway.bybit._connections
        delay = 2
        last_start = monotonic()
        while not self.stop_event.is_set() and not self.spool.error:
            try:
                now = monotonic()
                stale = [
                    category
                    for category in ("bybit:linear", "bybit:spot")
                    if now - max(last_start, self._bybit_last_received.get(category, 0)) > 120
                ]
                if stale:
                    for category in stale:
                        self._quality(category, "public", "research_stream_stale")
                restarted = owner.start_research_streams(
                    self._capture_bybit, force_reconnect=bool(stale)
                )
                if restarted:
                    last_start = monotonic()
                    self.source_health["bybit"] = {"status": "subscriptions_started"}
                delay = 2
                self.stop_event.wait(15)
            except Exception as exc:
                self._quality("bybit", "public", type(exc).__name__)
                self.stop_event.wait(delay)
                delay = min(30, delay * 2)

    def _mt5(self):
        assert self.spool
        account = self.settings.mt5_primary_account_id
        if not account or account not in self.settings.mt5_accounts:
            self._quality("mt5", "unavailable", "fixed_quote_account_missing")
            return
        scope = "account:" + account
        cursor_path = self.spool.root / "mt5-cursor.json"
        start = None
        if cursor_path.exists():
            state = json.loads(cursor_path.read_text())
            if state.get("account") == account:
                start = datetime.fromisoformat(state["end"]) - timedelta(milliseconds=2)
        while not self.stop_event.is_set() and not self.spool.error:
            if self.settings.live_write_enabled:
                self._quality("mt5", scope, "research_yielded_to_live_write")
                self.stop_event.wait(1)
                continue
            from app.research_clock import conservative_utc_now

            reference = conservative_utc_now(self.bybit_clock)
            if reference is None:
                self.source_health["mt5"] = {
                    "status": "waiting_utc_reference",
                    "clock": "unverified",
                }
                self.source_health["mt5:XAUUSD"] = dict(self.source_health["mt5"])
                self.stop_event.wait(self.settings.research_mt5_poll_seconds)
                continue
            if start is None:
                start = reference - timedelta(seconds=1)
            end = min(reference, start + timedelta(seconds=1))
            if end <= start:
                self.stop_event.wait(self.settings.research_mt5_poll_seconds)
                continue
            try:
                batch = self.gateway.get_research_ticks(
                    account_id=account, symbol="XAUUSD", start=start, end=end
                )
                received = datetime.now(UTC).isoformat()
                session = resolve_mt5_session_state(
                    schedule=self.settings.cross_spread_mt5_trading_schedule,
                    timezone=self.settings.cross_spread_mt5_schedule_timezone,
                    guard_minutes=self.settings.cross_spread_auto_exit_guard_minutes,
                    overrides=self.settings.cross_spread_mt5_session_overrides,
                    now=reference,
                )
                self.source_health["mt5"] = {
                    "status": "received" if batch.get("ticks") else "empty_range",
                    "lastReadAt": received,
                    "marketStatus": session.status,
                    "nativeSymbol": batch.get("symbol"),
                    "instrumentId": batch.get("instrumentId"),
                    "lastRangeTickCount": len(batch.get("ticks", [])),
                    "lastRangeSourceTimeMs": max(
                        (int(x["time_msc"]) for x in batch.get("ticks", [])), default=None
                    ),
                    "clock": "unverified",
                }
                self.source_health["mt5:XAUUSD"] = dict(self.source_health["mt5"])
                mode = "backfill" if (reference - start).total_seconds() > 2 else "realtime"
                batch.update(
                    {
                        "account": account,
                        "start": start.isoformat(),
                        "end": end.isoformat(),
                        "queryClockVersion": "bybit-clock-interval.v1",
                    }
                )
                accepted = self.spool.capture(
                    "mt5_batch",
                    "mt5:XAUUSD",
                    scope,
                    batch,
                    mode=mode,
                    source_layer="native_tick_batch",
                    received_at=received,
                    source_clock=self.bybit_clock,
                )
                if not accepted:
                    break
                # Wait for the fsynced batch before checkpointing. Queue ordering is shared.
                while not self.stop_event.is_set() and not self.spool.error:
                    if self.spool.durable_sequence >= accepted:
                        break
                    self.stop_event.wait(0.02)
                if self.spool.error or self.stop_event.is_set():
                    break
                temp = cursor_path.with_suffix(".tmp")
                with temp.open("w") as f:
                    f.write(json.dumps({"account": account, "end": end.isoformat()}))
                    f.flush()
                    import os

                    os.fsync(f.fileno())
                temp.replace(cursor_path)
                start = end - timedelta(milliseconds=2)
            except Exception as exc:
                reason = (
                    "research_yielded_to_account_operations"
                    if str(exc) == "Research yielded to account operations"
                    else type(exc).__name__
                )
                if reason == "research_yielded_to_account_operations":
                    self.source_health["mt5:XAUUSD"] = {
                        "status": "deferred",
                        "reason": reason,
                        "at": datetime.now(UTC).isoformat(),
                        "lastReadAt": self.source_health.get("mt5", {}).get("lastReadAt"),
                    }
                else:
                    self._quality("mt5:XAUUSD", scope, reason)
                self.stop_event.wait(2)
            self.stop_event.wait(self.settings.research_mt5_poll_seconds)

    def _rates(self):
        assert self.spool
        account = self.settings.research_bybit_account_id
        if not account or account not in self.settings.bybit_accounts:
            self._quality("bybit:rates", "public", "configured_bybit_owner_required")
            return
        while not self.stop_event.is_set() and not self.spool.error:
            try:
                client = self.gateway.bybit._connections.client(account)
                from app.research_rate_history import capture_funding_history

                for symbol in ("XAUTUSDT", "BTCUSDT"):
                    capture_funding_history(
                        client, self.spool, symbol, self.settings.research_funding_history_days
                    )
                # Public VIP tiers; never include private account borrow balances.
                borrow = client.spot_margin_trade_get_vip_margin_data()
                if borrow.get("retCode") != 0:
                    raise ValueError("public borrow profile rejected")
                self.spool.capture(
                    "borrow_rates", "bybit:borrow", "public", borrow, source_layer="rest"
                )
                self.source_health["bybit:rates"] = {
                    "status": "received",
                    "lastReceivedAt": datetime.now(UTC).isoformat(),
                }
            except Exception as exc:
                self._quality("bybit:rates", "public", type(exc).__name__)
            self.stop_event.wait(300)

    def _prices(self):
        from app.research_price_history import (
            DAILY_HISTORY_DAYS,
            DAILY_SPOT_STREAMS,
            STREAMS,
            capture_prices,
        )

        assert self.spool
        while not self.stop_event.is_set() and not self.spool.error:
            complete = True
            streams = [(c, s, p, "D", DAILY_HISTORY_DAYS) for c, s, p in DAILY_SPOT_STREAMS]
            streams += [
                (c, s, p, "1", self.settings.research_price_history_days) for c, s, p in STREAMS
            ]
            for category, symbol, price_type, interval, days in streams:
                if self.stop_event.is_set():
                    return
                key = f"history:{category}:{symbol}:{price_type}" + (
                    ":1d" if interval == "D" else ""
                )
                try:
                    client = self.gateway.bybit._connections.client(
                        self.settings.research_bybit_account_id
                    )
                    state = capture_prices(
                        client,
                        self.spool,
                        category,
                        symbol,
                        price_type,
                        days,
                        interval=interval,
                    )
                    complete = complete and state["complete"]
                    self.source_health[key] = {
                        "status": "up_to_date" if state["complete"] else "backfilling",
                        **state,
                    }
                except Exception as exc:
                    complete = False
                    self._quality(key, "public", type(exc).__name__)
                self.stop_event.wait(0.5)
            self.stop_event.wait(60 if complete else 5)

    def _mt5_history(self):
        from app.research_clock import conservative_utc_now
        from app.research_price_history import checkpoint, durable

        assert self.spool
        account = self.settings.mt5_primary_account_id
        if not account or account not in self.settings.mt5_accounts:
            return
        path = self.spool.root / "mt5-history-cursor.json"
        state = json.loads(path.read_text()) if path.exists() else {}
        if state and state.get("account") != account:
            self._quality("history:mt5", "account:" + account, "history_owner_changed")
            return
        window = 300
        while not self.stop_event.is_set() and not self.spool.error:
            reference = conservative_utc_now(self.bybit_clock)
            if reference is None or self.settings.live_write_enabled:
                self.stop_event.wait(2)
                continue
            if not state:
                state = {
                    "account": account,
                    "start": (reference - timedelta(days=3)).isoformat(),
                    "target": reference.isoformat(),
                    "tickCount": 0,
                }
            start, target = (
                datetime.fromisoformat(state["start"]),
                datetime.fromisoformat(state["target"]),
            )
            if start >= target:
                self.source_health["history:mt5"] = {"status": "range_scanned", **state}
                return
            end = min(start + timedelta(seconds=window), target)
            try:
                batch = self.gateway.get_research_ticks(
                    account_id=account, symbol="XAUUSD", start=start, end=end, historical=True
                )
                batch.update(
                    {"account": account, "start": start.isoformat(), "end": end.isoformat()}
                )
                sequence = self.spool.capture(
                    "mt5_historical_batch",
                    "mt5:XAUUSD:history",
                    "account:" + account,
                    batch,
                    mode="backfill",
                    source_layer="native_tick_history",
                )
                durable(self.spool, sequence)
                state.update(
                    start=end.isoformat(),
                    tickCount=state["tickCount"] + len(batch.get("ticks", [])),
                )
                checkpoint(path, state)
                self.source_health["history:mt5"] = {
                    "status": "backfilling",
                    **state,
                    "clock": "unverified",
                }
                window = min(300, window * 2)
            except Exception as exc:
                if "exceeds research budget" in str(exc) and window > 1:
                    window = max(1, window // 2)
                else:
                    self._quality("history:mt5", "account:" + account, type(exc).__name__)
                    self.stop_event.wait(2)
            self.stop_event.wait(0.5)

    def _scan(self):
        assert self.spool
        account = self.settings.research_bybit_account_id
        if not account or account not in self.settings.bybit_accounts:
            self._quality("bybit:scan", "public", "configured_bybit_owner_required")
            return
        while not self.stop_event.is_set() and not self.spool.error:
            try:
                client = self.gateway.bybit._connections.client(account)
                spot = client.get_instruments_info(category="spot")
                tickers = client.get_tickers(category="linear")
                if spot.get("retCode") != 0 or tickers.get("retCode") != 0:
                    raise ValueError("public scan rejected")
                self.spool.capture(
                    "market_scan",
                    "bybit:scan",
                    "public",
                    {"spot": spot, "linearTickers": tickers},
                    source_layer="rest_scan",
                )
                self.source_health["bybit:scan"] = {
                    "status": "received",
                    "lastReceivedAt": datetime.now(UTC).isoformat(),
                }
            except Exception as exc:
                self._quality("bybit:scan", "public", type(exc).__name__)
            self.stop_event.wait(60)

    def status(self):
        if not self.spool:
            return {"status": "disabled", "error": self.error}
        return self.spool.status() | {
            "error": self.error or self.spool.error,
            "sources": dict(self.source_health),
            "borrowHistory": "not_connected_requires_account_permission",
            "clockCalibration": {
                "bybit": self.bybit_clock,
                "mt5": "unverified",
                "host": "unchanged",
            },
        }

    def close(self):
        self.stop_event.set()
        for thread in self.threads:
            thread.join(timeout=3)
        if self.spool:
            self.spool.close()


def create_research_market_router(capture):
    router = APIRouter(tags=["research-market"])

    @router.get("/v1/market-data/status")
    def status():
        return capture.status()

    @router.get("/v1/market-data/events")
    def events(after: str | None = None, limit: int = Query(default=1000, ge=1, le=5000)):
        if capture.spool is None:
            return {
                "schemaVersion": "market-events.v1",
                "after": after,
                "nextCursor": after,
                "events": [],
                "capture": capture.status(),
            }
        try:
            batch = capture.spool.read(after, limit)
            batch["capture"] = capture.status()
            return batch
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @router.get("/v1/market-data/price-history")
    def price_history(
        symbol: str,
        category: str = "linear",
        priceType: str = "trade",
        startMs: int = Query(..., ge=0),
        endMs: int = Query(..., ge=0),
        limit: int = Query(default=5000, ge=1, le=5000),
    ):
        """Read a bounded closed-candle window through the capture owner.

        This is a read-through for consumers that must not wait behind the
        high-volume event replay.  The runtime still owns the Bybit client;
        the platform persists only its derived read model.
        """
        if category != "linear" or priceType not in {"trade", "mark"}:
            raise HTTPException(400, "only linear trade/mark history is supported")
        symbol = symbol.upper()
        if symbol not in {"BTCUSDT", "XAUTUSDT"} or startMs > endMs:
            raise HTTPException(400, "unsupported price-history window")
        if capture.spool is None:
            raise HTTPException(503, "research capture is not running")
        account = capture.settings.research_bybit_account_id
        try:
            client = capture.gateway.bybit._connections.client(account)
            method = client.get_mark_price_kline if priceType == "mark" else client.get_kline
            rows = []
            cursor = startMs
            while cursor <= endMs and len(rows) < limit:
                response = method(
                    category=category,
                    symbol=symbol,
                    interval="1",
                    start=cursor,
                    end=min(endMs, cursor + 999 * 60_000),
                    limit=min(1000, limit - len(rows)),
                )
                if response.get("retCode") != 0:
                    raise RuntimeError("Bybit closed-candle read rejected")
                page = response.get("result", {}).get("list", [])
                if not page:
                    break
                rows.extend(page)
                newest = max(int(item[0]) for item in page if len(item) >= 5)
                next_cursor = newest + 60_000
                if next_cursor <= cursor:
                    break
                cursor = next_cursor
            return {
                "symbol": symbol,
                "category": category,
                "priceType": priceType,
                "intervalMs": 60_000,
                "rows": rows[:limit],
            }
        except Exception as exc:
            raise HTTPException(503, f"price-history unavailable: {type(exc).__name__}") from exc

    return router
