from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

import app.research_macro_history as macro_history
import app.research_service as service
from app.research_data_schemas import (
    AShareIndexSnapshot,
    AShareTurnoverStock,
    EmotionLadderRow,
    MacroExpectationEvent,
    ShenwanMembership,
    ShortTermEmotionSnapshot,
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


class _DashboardProvider:
    async def index_snapshots(self) -> list[AShareIndexSnapshot]:
        return [
            AShareIndexSnapshot(
                code="000001",
                name="上证指数",
                source_symbol="sh000001",
                close=Decimal("3500"),
                turnover_yuan=Decimal("100000000000"),
                spark=[Decimal("3490"), Decimal("3500")],
            )
        ]

    async def market_activity(self) -> Any:
        raise RuntimeError("breadth source unavailable")

    async def a_share_spot(self) -> list[AShareTurnoverStock]:
        return [
            AShareTurnoverStock(
                security_code="600001",
                security_name="测试股份",
                turnover_yuan=Decimal("12000000000"),
                return_pct=Decimal("1.2"),
            )
        ]

    async def short_term_emotion(self) -> ShortTermEmotionSnapshot:
        return ShortTermEmotionSnapshot(
            limit_up_count=40,
            broken_board_count=10,
            limit_down_count=3,
            highest_board_count=4,
            consecutive_board_count=8,
            seal_rate_pct=Decimal("80"),
            break_rate_pct=Decimal("20"),
            promotion_rate_pct=Decimal("25"),
            ladder=[EmotionLadderRow(board_count="2板", stock_count=4)],
            leaders=[],
            trade_date=date(2026, 7, 29),
        )


class _StockProvider:
    async def stock_quote(self, code: str) -> dict[str, Any]:
        return {"code": code, "name": "测试股份", "price": Decimal("12.34"), "peTtm": 20}

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


def test_dashboard_keeps_other_modules_when_one_provider_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def memberships() -> list[ShenwanMembership]:
        return [_membership()]

    monkeypatch.setattr(service, "_PROVIDER", _DashboardProvider())
    monkeypatch.setattr(service, "_memberships", memberships)

    result = asyncio.run(
        service.get_a_share_dashboard(threshold_yuan=Decimal("987654321"))
    )

    assert result.market_detail.meta.status == "ready"
    assert result.breadth.meta.status == "error"
    assert result.shenwan.meta.status == "ready"
    assert result.shenwan.data.sw2_top[0].sw_l2_name == "半导体"
    assert result.emotion.meta.status == "ready"


def test_stock_snapshot_isolates_individual_module_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
