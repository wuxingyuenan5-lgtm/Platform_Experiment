"""Synthetic transport fixtures; no external account or market connection."""

import time

import pytest

from app.market_spool import MarketSpool


def drain(spool, count):
    until = time.monotonic() + 3
    while spool.durable_sequence < count and not spool.error and time.monotonic() < until:
        time.sleep(0.01)
    assert not spool.error


def test_spool_durable_cursor_reopen_and_partial_tail(tmp_path):
    s = MarketSpool(tmp_path, min_free_bytes=0)
    s.start()
    accepted = s.capture("test", "fixture", "public", {"price": "1.000000000000000001"})
    drain(s, accepted)
    first = s.read(limit=1)
    next_batch = s.read(first["nextCursor"])
    assert next_batch["events"][0]["payload"]["price"] == "1.000000000000000001"
    cursor = next_batch["nextCursor"]
    s.close()
    path = next(tmp_path.glob("*.log"))
    with path.open("ab") as f:
        f.write(b'{"incomplete":')
    recovered = MarketSpool(tmp_path, min_free_bytes=0)
    recovered.start()
    assert path.name in recovered.recovery_gaps
    assert recovered.read(cursor)["events"] == [] or all(
        e["kind"] == "quality" for e in recovered.read(cursor)["events"]
    )
    recovered.close()


def test_spool_single_owner_and_bounded_failure(tmp_path):
    s = MarketSpool(tmp_path, min_free_bytes=0, max_bytes=1000)
    s.start()
    other = MarketSpool(tmp_path, min_free_bytes=0)
    with pytest.raises(RuntimeError):
        other.start()
    s.capture("large", "fixture", "public", {"data": "x" * 3000})
    deadline = time.monotonic() + 2
    while not s.error and time.monotonic() < deadline:
        time.sleep(0.01)
    assert "capacity_budget_exhausted" in s.error
    assert s.capture("late", "fixture", "public", {}) is False
    s.close()


def test_cursor_is_bounded_and_checksum_is_verified(tmp_path):
    s = MarketSpool(tmp_path, min_free_bytes=0)
    s.start()
    accepted = s.capture("fixture", "fixture", "public", {})
    drain(s, accepted)
    with pytest.raises(ValueError):
        s.read("../escape:0")
    with pytest.raises(ValueError):
        s.read(limit=5001)
    with pytest.raises(ValueError):
        s.read(next(iter(s.durable)) + ":1")
    s.close()


def test_public_native_callback_precedes_sdk_book_rewrite(monkeypatch):
    from pybit.unified_trading import WebSocket

    from app.bybit_connection import BybitConnections
    from app.config import Settings

    sockets = []

    def construct(self, **kwargs):
        sockets.append(self)

    monkeypatch.setattr(WebSocket, "__init__", construct)
    monkeypatch.setattr(WebSocket, "orderbook_stream", lambda *a, **k: None)
    monkeypatch.setattr(WebSocket, "ticker_stream", lambda *a, **k: None)
    owner = BybitConnections(Settings())
    events = []
    owner.start_research_streams(lambda *a, **k: events.append((a, k)))
    raw = {
        "topic": "orderbook.50.BTCUSDT",
        "type": "delta",
        "ts": 123,
        "data": {"u": 4, "a": [], "b": []},
    }
    sockets[0]._process_normal_message(raw)
    assert events[0][0][3]["type"] == "delta"
    assert events[0][1]["source_layer"] == "native_websocket"
    assert len(sockets) == 2
    owner.start_research_streams(lambda *a, **k: None)
    assert len(sockets) == 2


def test_mt5_range_preserves_every_native_row(monkeypatch):
    from datetime import UTC, datetime, timedelta
    from types import SimpleNamespace

    import numpy as np

    from app import research_mt5_ticks as module

    t = datetime(2026, 9, 19, tzinfo=UTC)
    ticks = np.array(
        [(123, 1.0, 2.0), (123, 1.1, 2.1)], dtype=[("time_msc", "i8"), ("bid", "f8"), ("ask", "f8")]
    )
    calls = []
    mt5 = SimpleNamespace(
        account_info=lambda: SimpleNamespace(login=1, server="fixture", company="fixture"),
        terminal_info=lambda: SimpleNamespace(connected=True),
        COPY_TICKS_ALL=0,
        copy_ticks_range=lambda *a: calls.append(a) or ticks,
        symbol_info=lambda s: SimpleNamespace(digits=2, point=0.01, trade_contract_size=100),
    )
    adapter = SimpleNamespace(
        _assert_account=lambda a: None,
        _connect=lambda: mt5,
        settings=SimpleNamespace(
            mt5_instruments={"XAUUSD.S": "gold"},
            mt5_primary_account_id="fixture",
            live_write_enabled=False,
        ),
    )
    monkeypatch.setattr(
        module, "resolve_mt5_symbol", lambda **kw: SimpleNamespace(symbol="XAUUSD.s")
    )
    from app.mt5_read_coordinator import COORDINATOR

    monkeypatch.setattr(COORDINATOR, "login", lambda **kw: SimpleNamespace(account_id="fixture"))
    result = module.read_ticks(
        adapter, account_id="fixture", symbol="XAUUSD", start=t, end=t + timedelta(seconds=1)
    )
    assert [x["bid"] for x in result["ticks"]] == ["1.0", "1.1"]
    assert calls[0][1] == t and result["symbol"] == "XAUUSD.s"
    assert result["instrumentId"] == "gold"
    assert result["timeQuality"] == "clock_unverified"
    history = module.read_ticks(
        adapter,
        account_id="fixture",
        symbol="XAUUSD",
        start=t,
        end=t + timedelta(seconds=300),
        historical=True,
    )
    assert history["ticks"] == result["ticks"]
    assert calls[-1][2] - calls[-1][1] == timedelta(seconds=300)
    with pytest.raises(Exception, match="bounded interval"):
        module.read_ticks(
            adapter,
            account_id="fixture",
            symbol="XAUUSD",
            start=t,
            end=t + timedelta(seconds=301),
            historical=True,
        )


def test_spool_reboot_keeps_cursor_order_when_wall_clock_reverses(tmp_path, monkeypatch):
    from app import market_spool

    s = MarketSpool(tmp_path, min_free_bytes=0)
    s.start()
    accepted = s.capture("fixture", "fixture", "public", {})
    drain(s, accepted)
    cursor = s.read()["nextCursor"]
    s.close()
    monkeypatch.setattr(market_spool.time, "time_ns", lambda: 1)
    restarted = MarketSpool(tmp_path, min_free_bytes=0)
    restarted.start()
    accepted = restarted.capture("after_restart", "fixture", "public", {})
    drain(restarted, accepted)
    assert restarted.read(cursor)["events"][-1]["kind"] == "after_restart"
    restarted.close()


def test_partial_socket_constructor_failure_cleans_up_before_retry(monkeypatch):
    from pybit.unified_trading import WebSocket

    from app.bybit_connection import BybitConnections
    from app.config import Settings

    opened, closed = [], []

    def construct(self, **kwargs):
        if kwargs["channel_type"] == "spot":
            raise ConnectionError("fixture")
        opened.append(self)

    monkeypatch.setattr(WebSocket, "__init__", construct)
    monkeypatch.setattr(WebSocket, "orderbook_stream", lambda *a, **k: None)
    monkeypatch.setattr(WebSocket, "ticker_stream", lambda *a, **k: None)
    monkeypatch.setattr(WebSocket, "exit", lambda self: closed.append(self))
    owner = BybitConnections(Settings())
    with pytest.raises(ConnectionError):
        owner.start_research_streams(lambda *a, **k: None)
    assert closed == opened and owner._research_sockets == []


def test_capture_health_advances_only_for_accepted_native_events():
    from types import SimpleNamespace

    from app.research_market_capture import ResearchCapture

    capture = ResearchCapture(None, None)
    capture.spool = SimpleNamespace(capture=lambda *a, **k: 1)
    stream = "bybit:linear:orderbook.50.XAUTUSDT"
    capture._capture_bybit("bybit_message", stream, "public", {}, source_ms=123)
    assert capture.source_health[stream]["sourceTimeMs"] == "123"
    before = dict(capture.source_health)
    capture.spool.capture = lambda *a, **k: False
    capture._capture_bybit("quality", stream, "public", {"reason": "disconnected"})
    assert capture.source_health == before


def test_research_clock_rejects_slow_response_and_host_step(monkeypatch):
    from types import SimpleNamespace

    from app import research_clock

    client = SimpleNamespace(get_server_time=lambda: {"retCode": 0, "result": {"timeNano": "500"}})
    wall, mono = iter([1000, 1200]), iter([2000, 2200])
    monkeypatch.setattr(research_clock.time, "time_ns", lambda: next(wall))
    monkeypatch.setattr(research_clock.time, "monotonic_ns", lambda: next(mono))
    result = research_clock.sample_clock(client)
    assert result["offsetLowerNs"] == "-700" and result["offsetUpperNs"] == "-500"
    wall, mono = iter([1000, 2000000000]), iter([2000, 2000000000])
    with pytest.raises(ValueError, match="rtt"):
        research_clock.sample_clock(client)
    wall, mono = iter([1000, 2000000000]), iter([2000, 2200])
    with pytest.raises(ValueError, match="stepped"):
        research_clock.sample_clock(client)


def test_mt5_query_horizon_uses_observed_utc_not_a_fast_host_clock(monkeypatch):
    from datetime import UTC, datetime

    from app import research_clock

    monkeypatch.setattr(research_clock.time, "monotonic_ns", lambda: 2_000_000_000)
    evidence = {
        "localReceivedNs": "10000000000",
        "localMonotonicNs": "1000000000",
        "offsetLowerNs": "-3000000000",
        "driftAllowanceNs": "100000000",
        "maxAgeNs": "120000000000",
    }
    assert research_clock.conservative_utc_now(evidence) == datetime(
        1970, 1, 1, 0, 0, 7, 900000, tzinfo=UTC
    )
    assert research_clock.conservative_utc_now(None) is None
    evidence["maxAgeNs"] = "1"
    assert research_clock.conservative_utc_now(evidence) is None


def test_closed_price_history_resumes_and_waits_for_next_closed_bar(tmp_path):
    from app.research_price_history import INTERVAL_MS, capture_prices

    class Client:
        now = 3000 * INTERVAL_MS
        calls = []

        def get_server_time(self):
            return {"retCode": 0, "result": {"timeNano": str(self.now * 1000000)}}

        def get_kline(self, **kw):
            self.calls.append(kw)
            return {
                "retCode": 0,
                "result": {
                    "list": [
                        [str(t), "1", "2", "1", "2", "1", "2"]
                        for t in range(kw["start"], kw["end"] + 1, INTERVAL_MS)
                    ]
                },
            }

    class Spool:
        root = tmp_path
        error = None
        durable_sequence = 1
        events = []

        def capture(self, *args, **kwargs):
            self.events.append((args, kwargs))
            return 1

    c, s = Client(), Spool()
    # An old overview cursor must not suppress a new fine-resolution bootstrap.
    (tmp_path / "price-linear-BTCUSDT-trade.json").write_text('{"through": 9999999999999}')
    state = capture_prices(c, s, "linear", "BTCUSDT", "trade", days=1)
    assert not state["complete"] and state["totalRows"] == 1000
    assert c.calls[0]["interval"] == "1"
    state = capture_prices(c, s, "linear", "BTCUSDT", "trade", days=1)
    assert state["complete"] and c.calls[-1]["end"] == c.now - INTERVAL_MS
    assert state["totalRows"] == 1440
    assert s.events[0][1]["mode"] == "backfill"
    capture_prices(c, s, "linear", "BTCUSDT", "trade", days=1)
    assert len(c.calls) == 2
    c.now += INTERVAL_MS
    capture_prices(c, s, "linear", "BTCUSDT", "trade", days=1)
    assert c.calls[-1]["start"] == c.calls[-2]["end"] + INTERVAL_MS
    assert len(s.events) == 3


def test_rejected_history_window_is_retained_without_advancing(tmp_path):
    from types import SimpleNamespace

    from app.research_price_history import capture_prices

    events = []

    def capture(*a, **kw):
        events.append((a, kw))
        return 1

    client = SimpleNamespace(
        get_server_time=lambda: {"retCode": 0, "result": {"timeNano": "1000000000000000"}},
        get_kline=lambda **kw: {
            "retCode": 0,
            "result": {"list": [["2000000000000", "1", "2", "1", "2"]]},
        },
    )
    spool = SimpleNamespace(root=tmp_path, error=None, durable_sequence=1, capture=capture)
    with pytest.raises(ValueError, match="outside requested"):
        capture_prices(client, spool, "linear", "BTCUSDT", "trade")
    assert events[0][1]["quality"] == ["source_window_invalid"]
    assert not (tmp_path / "price-linear-BTCUSDT-trade-1m.json").exists()


def test_price_history_expands_backward_when_retention_window_grows(tmp_path):
    import json

    from app.research_price_history import INTERVAL_MS, capture_prices

    class Client:
        now = 3000 * INTERVAL_MS
        calls = []

        def get_server_time(self):
            return {"retCode": 0, "result": {"timeNano": str(self.now * 1000000)}}

        def get_kline(self, **kw):
            self.calls.append(kw)
            return {"retCode": 0, "result": {"list": [[str(kw["start"]), "1", "2", "1", "2"]]}}

    class Spool:
        root = tmp_path
        error = None
        durable_sequence = 1

        def capture(self, *args, **kwargs):
            return 1

    client, spool = Client(), Spool()
    one_day_floor = client.now - 1 * 86400000 + INTERVAL_MS
    (tmp_path / "price-linear-BTCUSDT-trade-1m.json").write_text(
        json.dumps(
            {
                "floor": one_day_floor,
                "through": client.now - INTERVAL_MS,
                "complete": True,
                "totalRows": 10,
            }
        )
    )

    state = capture_prices(client, spool, "linear", "BTCUSDT", "trade", days=2)

    last_closed = client.now - INTERVAL_MS
    assert client.calls[0]["start"] == last_closed - 2 * 86400000 + INTERVAL_MS
    assert state["floor"] == client.calls[0]["start"]
    assert not state["complete"]
