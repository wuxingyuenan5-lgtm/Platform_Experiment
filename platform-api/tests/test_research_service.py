from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

import app.research_macro_history as macro_history
import app.research_service as service
from app.research_cache import LastKnownGoodResearchCache
from app.research_data_schemas import (
    MacroExpectationEvent,
    MacroExpectationResponse,
    ShenwanMembership,
    StockSnapshotResponse,
)

pytestmark = pytest.mark.unit


def _membership(code: str = "600001") -> ShenwanMembership:
    return ShenwanMembership(
        security_code=code,
        sw_l1_code="801080",
        sw_l1_name="电子",
        sw_l2_code="801081",
        sw_l2_name="半导体",
        classification_version="test",
        effective_from=date(2026, 1, 1),
    )


class _StockProvider:
    async def stock_quote(self, code: str) -> dict[str, Any]:
        return {
            "code": code,
            "name": "测试股份",
            "price": Decimal("12.34"),
            "peTtm": 20,
        }

    def __getattr__(self, name: str) -> Any:
        async def call(*_: Any, **__: Any) -> Any:
            if name == "stock_reports":
                raise RuntimeError("report source unavailable")
            if name == "stock_forecast":
                return {"forwardPe": Decimal("18"), "analystCount": 3}
            if name == "stock_fund_flow":
                return {"history": [], "mainNet20d": Decimal("0")}
            if name == "stock_dragon_tiger":
                return {"records": [], "seats": {"buy": [], "sell": []}}
            if name == "stock_lockup":
                return {"history": [], "upcoming": []}
            return []

        return call


def _install_stock_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        service,
        "_STOCK_CACHE",
        LastKnownGoodResearchCache[StockSnapshotResponse](
            ttl=timedelta(minutes=15),
            is_meaningful=lambda value: bool(value.modules),
            now=lambda: datetime.now(UTC),
        ),
    )
    monkeypatch.setattr(
        service,
        "_MACRO_CACHE",
        LastKnownGoodResearchCache[MacroExpectationResponse](
            ttl=timedelta(minutes=15),
            is_meaningful=lambda value: bool(value.events.data),
            now=lambda: datetime.now(UTC),
        ),
    )
    monkeypatch.setattr(service, "_STOCK_LOCKS", {})


def test_stock_snapshot_isolates_individual_module_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_stock_cache(monkeypatch)

    async def memberships() -> list[ShenwanMembership]:
        return [_membership("601234")]

    monkeypatch.setattr(service, "_PROVIDER", _StockProvider())
    monkeypatch.setattr(service, "_memberships", memberships)

    result = asyncio.run(service.get_stock_snapshot("601234"))

    assert result.security_name == "测试股份"
    assert result.modules["quoteValuation"].meta.status == "ready"
    assert result.modules["reports"].meta.status == "error"
    assert result.modules["shenwan"].data["swL2Name"] == "半导体"
    assert Decimal("0") < result.completeness_pct < Decimal("100")


def test_macro_history_calculates_seven_day_change(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    store = macro_history.MacroProbabilityHistoryStore(tmp_path / "macro.json")
    observed = [
        datetime(2026, 7, 20, 8, 0, tzinfo=UTC),
        datetime(2026, 7, 29, 8, 0, tzinfo=UTC),
    ]
    monkeypatch.setattr(macro_history, "_now", lambda: observed.pop(0))

    first = MacroExpectationEvent(
        event_id="fed-cut",
        category="monetary_policy",
        title="Fed cut",
        outcome="Yes",
        current_probability_pct=Decimal("40"),
    )
    second = first.model_copy(update={"current_probability_pct": Decimal("55")})

    asyncio.run(store.update([first]))
    updated = asyncio.run(store.update([second]))

    assert updated[0].change_7d_pct_points == Decimal("15")
    assert len(updated[0].history) == 2
