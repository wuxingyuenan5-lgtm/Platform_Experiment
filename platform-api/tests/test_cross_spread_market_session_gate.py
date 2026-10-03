from datetime import UTC, datetime

import pytest
from fastapi import HTTPException

from app import cross_spread
from app.schemas import CrossSpreadSnapshotResponse


def snapshot(*, mt5_open: bool, mt5_close: bool) -> CrossSpreadSnapshotResponse:
    now = datetime.now(UTC).isoformat()
    venue = {
        "status": "available",
        "quote": {"bid": "2500", "ask": "2501", "mid": "2500.5", "currency": "USD"},
        "positions": [],
        "openAllowed": True,
        "closeAllowed": True,
        "quoteSourceAsOf": now,
    }
    return CrossSpreadSnapshotResponse.model_validate(
        {
            "status": "available",
            "executionState": "executable" if mt5_open and mt5_close else "monitor_only",
            "bybit": {**venue, "venue": "bybit", "symbol": "XAUTUSDT"},
            "mt5": {
                **venue,
                "venue": "mt5",
                "symbol": "XAUUSD.s",
                "openAllowed": mt5_open,
                "closeAllowed": mt5_close,
                "executionBlockReason": None if mt5_open and mt5_close else "quote_stale",
            },
            "longSpread": "-1",
            "shortSpread": "-2",
            "metrics": {},
            "asOf": now,
        }
    )


@pytest.mark.parametrize(("is_close", "allowed"), [(False, False), (True, False)])
def test_normal_cross_execution_is_blocked_when_mt5_session_is_closed(
    monkeypatch, is_close: bool, allowed: bool
) -> None:
    monkeypatch.setattr(
        cross_spread,
        "get_cross_spread_snapshot",
        lambda: snapshot(mt5_open=allowed, mt5_close=allowed),
    )
    with pytest.raises(HTTPException) as exc_info:
        cross_spread.assert_cross_spread_market_executable(is_close=is_close)
    assert exc_info.value.status_code == 423
    assert "mt5: quote_stale" in str(exc_info.value.detail)


def test_close_only_session_allows_normal_exit_but_not_new_open(monkeypatch) -> None:
    current = snapshot(mt5_open=False, mt5_close=True)
    monkeypatch.setattr(cross_spread, "get_cross_spread_snapshot", lambda: current)
    assert cross_spread.assert_cross_spread_market_executable(is_close=True) is current
    with pytest.raises(HTTPException):
        cross_spread.assert_cross_spread_market_executable(is_close=False)
