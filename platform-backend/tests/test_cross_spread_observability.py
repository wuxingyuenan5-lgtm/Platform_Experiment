from __future__ import annotations

from app.cross_spread_live_read_client import CrossSpreadLiveReadError
from app.cross_spread_observability_service import get_cross_spread_observability


def _risk(account_id: str) -> dict[str, object]:
    return {
        "source": "bybit_live" if "crypto" in account_id else "mt5_live",
        "accountId": account_id,
        "currency": "USD",
        "equity": "1000",
        "availableBalance": "900",
        "asOf": "2026-07-25T00:00:00Z",
        "dataQualityState": "complete",
    }


def _history_page(account_id: str) -> dict[str, object]:
    return {
        "source": "runtime",
        "accountId": account_id,
        "items": [],
        "nextCursor": None,
        "startTime": "2026-07-24T00:00:00Z",
        "endTime": "2026-07-25T00:00:00Z",
        "asOf": "2026-07-25T00:00:00Z",
        "dataQualityState": "complete",
    }


def test_observability_aggregates_complete_read_only_sections(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.cross_spread_observability_service.runtime.get_account_risk",
        _risk,
    )
    monkeypatch.setattr(
        "app.cross_spread_observability_service.runtime.list_position_rows",
        lambda account_id: [],
    )
    monkeypatch.setattr(
        "app.cross_spread_observability_service.runtime.query_order_history",
        lambda **kwargs: _history_page(kwargs["account_id"]),
    )
    monkeypatch.setattr(
        "app.cross_spread_observability_service.runtime.query_fill_history",
        lambda **kwargs: _history_page(kwargs["account_id"]),
    )

    result = get_cross_spread_observability(history_hours=24, limit=20)

    assert result.status == "complete"
    assert result.bybit.status == "complete"
    assert result.mt5.status == "complete"
    assert result.bybit.account_risk is not None
    assert result.bybit.section_states["recentOrders"] == "complete"
    assert result.warnings == []


def test_observability_marks_failed_section_without_faking_zero(monkeypatch) -> None:
    def risk(account_id: str) -> dict[str, object]:
        if "mt5" in account_id:
            raise CrossSpreadLiveReadError("MT5 account_info unavailable")
        return _risk(account_id)

    monkeypatch.setattr(
        "app.cross_spread_observability_service.runtime.get_account_risk",
        risk,
    )
    monkeypatch.setattr(
        "app.cross_spread_observability_service.runtime.list_position_rows",
        lambda account_id: [],
    )
    monkeypatch.setattr(
        "app.cross_spread_observability_service.runtime.query_order_history",
        lambda **kwargs: _history_page(kwargs["account_id"]),
    )
    monkeypatch.setattr(
        "app.cross_spread_observability_service.runtime.query_fill_history",
        lambda **kwargs: _history_page(kwargs["account_id"]),
    )

    result = get_cross_spread_observability(history_hours=24, limit=20)

    assert result.status == "partial"
    assert result.mt5.status == "partial"
    assert result.mt5.account_risk is None
    assert result.mt5.section_states["accountRisk"] == "unavailable"
    assert any("MT5 accountRisk" in warning for warning in result.warnings)
