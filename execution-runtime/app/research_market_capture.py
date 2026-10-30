"""Lifecycle-owned public capture; fixed MT5 account reads use the existing Worker."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import monotonic
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from app.cross_spread_schedule import resolve_mt5_session_state
from app.market_spool import MarketSpool
from app.research_clock import quote_time_quality
from app.research_minute import MinuteHistory


class ResearchCapture:
    def __init__(self, settings, gateway):
        self.settings, self.gateway = settings, gateway
        self.spool = None
        self.stop_event = threading.Event()
        self.threads = []
        self.error = None
        self.source_health = {}
        self.bybit_clock = None
        self.mt5_clock = None
        self._bybit_last_received: dict[str, float] = {}
        self._sample_lock = threading.Lock()
        self._sampled_at: dict[str, float] = {}
        self._research_tickers: dict[str, dict] = {}
        self._mt5_sample_bucket = -1
        self.minute_history = MinuteHistory()
        self._mt5_minute_seen = set()

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
            self._minutes,
            self._mt5,
            self._rates,
            self._scan,
            self._clock,
            self._mt5_clock,
            self._prices,
            self._mt5_history,
        ):
            t = threading.Thread(target=target, name="research-" + target.__name__, daemon=True)
            t.start()
            self.threads.append(t)

    def _minutes(self):
        while not self.stop_event.wait(1):
            spool = self.spool
            if spool and not spool.error:
                emit = spool.capture
                self.minute_history.flush(
                    int(datetime.now(UTC).timestamp() * 1000),
                    lambda row, emit=emit: emit(
                        row["kind"],
                        row["entity"],
                        "fixed_account_worker"
                        if row["entity"] in {"mt5:XAUUSD", "cross-gold"}
                        else "public",
                        row,
                        source_layer="observed_minute_aggregate",
                        quality=row["quality"],
                    ),
                )

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
        topic = payload.get("topic", "")
        if kind == "bybit_message" and topic:
            with self._sample_lock:
                now = monotonic()
                bucket = int(datetime.now(UTC).timestamp()) // 60
                if topic.startswith("tickers."):
                    previous = self._research_tickers.get(stream, {})
                    ticker = {} if payload.get("type") == "snapshot" else dict(previous)
                    ticker.update(payload.get("data", {}))
                    self._research_tickers[stream] = ticker
                    payload = dict(
                        payload,
                        type="snapshot",
                        data={
                            k: v
                            for k, v in ticker.items()
                            if k in {"symbol", "fundingRate", "markPrice", "nextFundingTime"}
                        },
                        samplingIntervalMs=60000,
                    )
                    kwargs["source_layer"] = "sampled_funding_indication_1m"
                elif topic.startswith("orderbook.1.") and payload.get("type") == "snapshot":
                    data = payload.get("data", {})
                    bids, asks = data.get("b", []), data.get("a", [])
                    if not bids or not asks:
                        self._quality(":".join(stream.split(":")[:2]), scope, "empty_top_quote")
                        return False
                    payload = {
                        "symbol": topic.rsplit(".", 1)[-1],
                        "category": stream.split(":")[1],
                        "bid": bids[0][0],
                        "ask": asks[0][0],
                        "bidSize": bids[0][1],
                        "askSize": asks[0][1],
                        "samplingIntervalMs": 60000,
                        "sampling": "first_observed_per_utc_minute",
                    }
                    self.minute_history.observe(
                        f"bybit:{payload['category']}:{payload['symbol']}",
                        int(datetime.now(UTC).timestamp() * 1000),
                        kwargs.get("source_ms"),
                        payload["bid"],
                        payload["ask"],
                        quote_time_quality(self.bybit_clock, kwargs.get("source_ms")),
                    )
                    kind = "quote_sample"
                    kwargs["source_layer"] = "sampled_top_quote_1m"
                else:
                    # Never persist an unexpected depth/delta as a complete sampled quote.
                    self._quality(
                        ":".join(stream.split(":")[:2]), scope, "unsupported_research_feed"
                    )
                    return False
                # Shared UTC minute boundaries align the independently observed legs.
                # Native and receive timestamps remain the actual observation times.
                if self._sampled_at.get(stream) == bucket:
                    self._bybit_last_received[":".join(stream.split(":")[:2])] = now
                    return False
                self._sampled_at[stream] = bucket
        accepted = self.spool.capture(
            kind, stream, scope, payload, source_clock=self.bybit_clock, **kwargs
        )
        if accepted:
            self.source_health[stream] = {
                "status": "received" if kind in {"bybit_message", "quote_sample"} else "gap",
                "lastReceivedAt": datetime.now(UTC).isoformat(),
                "sourceTimeMs": str(kwargs["source_ms"])
                if kwargs.get("source_ms") is not None
                else None,
                "reason": payload.get("reason") if kind == "quality" else None,
            }
        if accepted and kind in {"bybit_message", "quote_sample"}:
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

    def _mt5_clock(self):
        from app.research_clock import Mt5ObservedClock, conservative_utc_now

        calibration = Mt5ObservedClock()
        account = self.settings.mt5_primary_account_id
        if not account or account not in self.settings.mt5_accounts:
            return
        while not self.stop_event.is_set():
            try:
                if self.settings.live_write_enabled:
                    self.stop_event.wait(2)
                    continue
                quote = self.gateway.get_market_quote(account_id=account, symbol="XAUUSD")
                reference = conservative_utc_now(self.bybit_clock)
                if reference is not None and quote.source_as_of is not None:
                    previous_clock = self.mt5_clock
                    self.mt5_clock = calibration.observe(
                        int(quote.source_as_of.timestamp() * 1000),
                        int(reference.timestamp() * 1000),
                        account,
                        quote.symbol,
                    )
                    if self.mt5_clock and self.spool:
                        self.mt5_clock["collectorSessionId"] = self.spool.session
                        if (
                            previous_clock
                            and previous_clock.get("nativeUtcOffsetMs")
                            == self.mt5_clock["nativeUtcOffsetMs"]
                            and "queryOffsetMs" in previous_clock
                        ):
                            self.mt5_clock["queryOffsetMs"] = previous_clock["queryOffsetMs"]
                        if "queryOffsetMs" not in self.mt5_clock:
                            offset = int(self.mt5_clock["nativeUtcOffsetMs"])
                            for query_offset in (0, offset):
                                end = reference + timedelta(milliseconds=query_offset)
                                probe = self.gateway.get_research_ticks(
                                    account_id=account,
                                    symbol="XAUUSD",
                                    start=end - timedelta(seconds=10),
                                    end=end,
                                    historical=True,
                                )
                                if any(
                                    abs(
                                        int(t["time_msc"])
                                        - offset
                                        - int(reference.timestamp() * 1000)
                                    )
                                    < 10000
                                    for t in probe.get("ticks", [])
                                ):
                                    self.mt5_clock["queryOffsetMs"] = query_offset
                                    break
                            self.source_health["mt5:clock_query"] = {
                                "status": "received"
                                if "queryOffsetMs" in self.mt5_clock
                                else "empty_range",
                                "queryOffsetMs": self.mt5_clock.get("queryOffsetMs"),
                                "lastReceivedAt": datetime.now(UTC).isoformat(),
                            }
                    self.source_health["mt5:clock"] = {
                        "status": "interval_measured" if self.mt5_clock else "calibrating",
                        "lastReceivedAt": datetime.now(UTC).isoformat(),
                        "evidence": self.mt5_clock,
                    }
            except Exception as exc:
                self.source_health["mt5:clock"] = {"status": "gap", "reason": type(exc).__name__}
            self.stop_event.wait(2 if self.mt5_clock else 1)

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
            from app.research_clock import live_mt5_clock

            evidence = live_mt5_clock(self.mt5_clock)
            if evidence is None:
                self.source_health["mt5:XAUUSD"] = {"status": "waiting_native_clock"}
                self.stop_event.wait(1)
                continue
            if start is not None and (reference - start).total_seconds() > 5:
                from app.research_price_history import checkpoint

                gap_path = self.spool.root / "mt5-recovery-gap.json"
                old_gap = json.loads(gap_path.read_text()) if gap_path.exists() else {}
                history_path = self.spool.root / "mt5-history-cursor.json"
                history_state = (
                    json.loads(history_path.read_text()) if history_path.exists() else {}
                )
                pending = old_gap.get("target", "") > history_state.get("target", "")
                gap_start = (
                    min(start.isoformat(), old_gap.get("start", start.isoformat()))
                    if pending
                    else start.isoformat()
                )
                checkpoint(
                    gap_path,
                    {"account": account, "start": gap_start, "target": reference.isoformat()},
                )
                self._quality("mt5:recovery", scope, "live_cursor_backlog_queued_for_history")
                self.source_health["mt5:recovery"] = {
                    "status": "backfilling",
                    "start": gap_start,
                    "target": reference.isoformat(),
                    "lastReadAt": datetime.now(UTC).isoformat(),
                }
                start = None
            if start is None:
                start = reference - timedelta(seconds=1)
            end = min(reference, start + timedelta(seconds=10))
            if end <= start:
                self.stop_event.wait(self.settings.research_mt5_poll_seconds)
                continue
            try:
                batch = self.gateway.get_research_ticks(
                    account_id=account,
                    symbol="XAUUSD",
                    start=start + timedelta(milliseconds=int(evidence.get("queryOffsetMs", 0))),
                    end=end + timedelta(milliseconds=int(evidence.get("queryOffsetMs", 0))),
                    historical=True,
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
                    "clock": "observed_utc_consistent",
                    "clockEvidence": evidence,
                }
                self.source_health["mt5:XAUUSD"] = dict(self.source_health["mt5"])
                if batch.get("ticks"):
                    self.source_health["mt5:clock_query"] = {
                        "status": "received",
                        "queryOffsetMs": evidence.get("queryOffsetMs", 0),
                        "lastReceivedAt": received,
                    }
                mode = "backfill" if (reference - start).total_seconds() > 2 else "realtime"
                batch.update(
                    {
                        "account": account,
                        "start": start.isoformat(),
                        "end": end.isoformat(),
                        "queryClockVersion": "bybit-clock-interval.v1",
                        "timeConversionVersion": evidence["methodVersion"],
                        "nativeUtcOffsetMs": evidence["nativeUtcOffsetMs"],
                        "nativeClockEvidence": evidence,
                    }
                )
                new_seen = set()
                for tick in batch.get("ticks", []):
                    identity = (tick.get("time_msc"), tick.get("bid"), tick.get("ask"))
                    new_seen.add(identity)
                    if mode != "realtime" or identity in self._mt5_minute_seen:
                        continue
                    self.minute_history.observe(
                        "mt5:XAUUSD",
                        int(datetime.now(UTC).timestamp() * 1000),
                        int(tick["time_msc"]) - int(evidence["nativeUtcOffsetMs"]),
                        tick.get("bid"),
                        tick.get("ask"),
                        quote_time_quality(
                            self.bybit_clock,
                            int(tick["time_msc"]) - int(evidence["nativeUtcOffsetMs"]),
                        ),
                    )
                self._mt5_minute_seen = new_seen
                # The Worker still reads native ticks; only the research archive is sampled.
                batch = sample_ticks(batch, 60000)
                batch["ticks"] = [
                    tick
                    for tick in batch["ticks"]
                    if int(tick["time_msc"]) // 60000 > self._mt5_sample_bucket
                ]
                batch["sampling"] = "first_batch_last_native_tick_per_minute"
                accepted = (
                    self.spool.capture(
                        "mt5_batch",
                        "mt5:XAUUSD",
                        scope,
                        batch,
                        mode=mode,
                        source_layer="sampled_tick_1m",
                        received_at=received,
                        source_clock=self.bybit_clock,
                    )
                    if batch["ticks"]
                    else 0
                )
                if accepted is False:
                    break
                # Wait for the fsynced batch before checkpointing. Queue ordering is shared.
                while not self.stop_event.is_set() and not self.spool.error:
                    if self.spool.durable_sequence >= accepted:
                        break
                    self.stop_event.wait(0.02)
                if self.spool.error or self.stop_event.is_set():
                    break
                if batch["ticks"]:
                    self._mt5_sample_bucket = int(batch["ticks"][-1]["time_msc"]) // 60000
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
        retry_delay = 2
        while not self.stop_event.is_set() and not self.spool.error:
            delay = 300
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
                # Only the public VIP0 USDT profile is consumed by this research module.
                tiers = []
                for tier in borrow.get("result", {}).get("vipCoinList", []):
                    if tier.get("vipLevel") in ("No VIP", "VIP 0", "0"):
                        tiers.append(
                            dict(
                                tier,
                                list=[
                                    r for r in tier.get("list", []) if r.get("currency") == "USDT"
                                ],
                            )
                        )
                borrow = dict(borrow, result=dict(borrow.get("result", {}), vipCoinList=tiers))
                self.spool.capture(
                    "borrow_rates",
                    "bybit:borrow",
                    "public",
                    borrow,
                    source_layer="public_vip0_usdt_profile",
                )
                self.source_health["bybit:rates"] = {
                    "status": "received",
                    "lastReceivedAt": datetime.now(UTC).isoformat(),
                }
                retry_delay = 2
            except Exception as exc:
                self._quality("bybit:rates", "public", type(exc).__name__)
                delay = retry_delay
                retry_delay = min(30, retry_delay * 2)
            self.stop_event.wait(delay)

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
                gap_path = self.spool.root / "mt5-recovery-gap.json"
                gap = json.loads(gap_path.read_text()) if gap_path.exists() else {}
                if gap.get("account") == account and gap.get("target", "") > state["target"]:
                    state = {**gap, "tickCount": 0}
                    checkpoint(path, state)
                    continue
                self.source_health["history:mt5"] = {"status": "range_scanned", **state}
                self.source_health["mt5:recovery"] = {"status": "range_scanned", **state}
                self.stop_event.wait(5)
                continue
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
                    sample_ticks(batch, 60000),
                    mode="backfill",
                    source_layer="sampled_tick_history_1m",
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
                elif str(exc) == "Research yielded to account operations":
                    self.source_health["history:mt5"] = {
                        "status": "backfilling",
                        **state,
                        "reason": "research_yielded_to_account_operations",
                    }
                    self.stop_event.wait(0.5)
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
                    {
                        "spot": project_scan_fields(spot, {"symbol", "status"}),
                        "linearTickers": project_scan_fields(
                            tickers, {"symbol", "fundingRate", "markPrice", "nextFundingTime"}
                        ),
                    },
                    source_layer="rest_funding_field_projection_60s",
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
            "quoteSamplingIntervalMs": 60000,
            "researchDepth": 1,
            "clockCalibration": {
                "bybit": self.bybit_clock,
                "mt5": self.mt5_clock or "unverified",
                "host": "unchanged",
            },
        }

    def close(self):
        self.stop_event.set()
        for thread in self.threads:
            thread.join(timeout=3)
        if self.spool:
            self.spool.close()


def project_scan_fields(response: dict[str, Any], fields: set[str]) -> dict[str, Any]:
    result = response.get("result", {})
    return dict(
        response,
        result=dict(
            result,
            list=[{k: v for k, v in row.items() if k in fields} for row in result.get("list", [])],
        ),
    )


def sample_ticks(batch: dict[str, Any], interval_ms: int) -> dict[str, Any]:
    """Keep the last native tick per bucket, retaining native count and identity."""
    buckets = {}
    ticks = batch.get("ticks", [])
    for tick in ticks:
        bucket = int(tick["time_msc"]) // interval_ms
        if bucket not in buckets or int(tick["time_msc"]) >= int(buckets[bucket]["time_msc"]):
            buckets[bucket] = tick
    return dict(
        batch,
        ticks=[buckets[k] for k in sorted(buckets)],
        nativeTickCount=len(ticks),
        samplingIntervalMs=interval_ms,
        sampling="last_native_tick_per_bucket",
    )


def create_research_market_router(capture):
    router = APIRouter(tags=["research-market"])

    @router.get("/v1/market-data/xauusd-daily")
    def xauusd_daily(count: int = Query(default=1500, ge=1, le=2000)):
        account = capture.settings.mt5_primary_account_id
        if (
            capture.settings.live_write_enabled
            or not account
            or account not in capture.settings.mt5_accounts
        ):
            raise HTTPException(503, "fixed MT5 research source unavailable or busy")
        try:
            return capture.gateway.get_research_daily_rates(account_id=account, count=count)
        except Exception as exc:
            raise HTTPException(
                503, f"MT5 daily history unavailable: {type(exc).__name__}"
            ) from exc

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

    @router.post("/v1/market-data/archive-ack")
    def archive_ack(receipt: dict, request: Request):
        if request.client is None or request.client.host not in {"127.0.0.1", "::1"}:
            raise HTTPException(403, "archive acknowledgement requires local consumer")
        allowed = Path(__file__).resolve().parents[1] / "data" / "market-spool"
        if capture.spool and capture.spool.root.resolve() != allowed:
            raise HTTPException(409, "automatic reclaim is restricted to the active spool")
        if capture.spool is None:
            raise HTTPException(503, "research capture is not running")
        try:
            return capture.spool.acknowledge(receipt["cursor"], receipt["checksum"])
        except (ValueError, KeyError, TypeError) as exc:
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
