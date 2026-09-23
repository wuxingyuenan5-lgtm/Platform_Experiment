from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.cross_spread_market import _execution_capability
from app.mt5_live_adapter import Mt5LiveAdapter


def _adapter() -> Mt5LiveAdapter:
    adapter = object.__new__(Mt5LiveAdapter)
    adapter._tick_freshness = {}
    adapter._tick_identity = {}
    return adapter


def test_tick_freshness_requires_strict_advancement_and_resets_on_rollback():
    adapter = _adapter()
    assert adapter._observe_tick(
        account_id="a", symbol="XAUUSD.S", login="1", server="broker", time_msc=100
    ) is None
    assert adapter._observe_tick(
        account_id="a", symbol="XAUUSD.S", login="1", server="broker", time_msc=100
    ) is None
    advanced = adapter._observe_tick(
        account_id="a", symbol="XAUUSD.S", login="1", server="broker", time_msc=101
    )
    assert advanced is not None
    assert adapter._observe_tick(
        account_id="a", symbol="XAUUSD.S", login="1", server="broker", time_msc=100
    ) is None


def test_disconnect_clears_tick_freshness():
    adapter = _adapter()
    adapter._tick_identity["a"] = ("1", "broker")
    adapter._observe_tick(
        account_id="a", symbol="XAUUSD.S", login="1", server="broker", time_msc=101
    )
    adapter._reset_tick_freshness("a")
    assert adapter._tick_freshness == {}
    assert adapter._tick_identity == {}


def test_identity_change_uses_a_new_tracker_key():
    adapter = _adapter()
    adapter._observe_tick(
        account_id="a", symbol="XAUUSD.S", login="1", server="broker", time_msc=101
    )
    assert adapter._observe_tick(
        account_id="a", symbol="XAUUSD.S", login="2", server="broker", time_msc=101
    ) is None


def _quote(*, advanced_at: datetime | None, source_as_of: datetime | None = None, **permissions):
    payload = {
        "tickFreshnessTracked": True,
        "lastTickAdvanceObservedAt": advanced_at.isoformat() if advanced_at else None,
        "tradeMode": 4,
        "accountTradeAllowed": True,
        "terminalTradeAllowed": True,
        "accountExpertTradeAllowed": True,
        "pythonTradeAllowed": True,
        "symbolVisible": True,
    }
    payload.update(permissions)
    now = datetime.now(UTC)
    return SimpleNamespace(
        source_as_of=source_as_of or now + timedelta(hours=3),
        as_of=now,
        raw_payload=payload,
    )


def test_future_broker_epoch_is_retained_but_new_tick_allows_execution():
    quote = _quote(advanced_at=datetime.now(UTC))
    assert _execution_capability("mt5", quote) == (True, True, None)
    assert quote.source_as_of > datetime.now(UTC)


def test_stagnant_tick_over_30_seconds_blocks():
    quote = _quote(advanced_at=datetime.now(UTC) - timedelta(seconds=31))
    assert _execution_capability("mt5", quote) == (False, False, "quote_stale")


def test_permission_still_blocks_after_fresh_tick():
    quote = _quote(advanced_at=datetime.now(UTC), accountExpertTradeAllowed=False)
    assert _execution_capability("mt5", quote) == (
        False,
        False,
        "mt5_expert_trade_not_allowed",
    )


def test_naive_quote_observation_fails_closed():
    quote = _quote(advanced_at=datetime.now(UTC))
    quote.as_of = datetime.now()
    assert _execution_capability("mt5", quote) == (
        False,
        False,
        "quote_source_time_missing",
    )
