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
    AShareBreadthSnapshot,
    AShareDashboardResponse,
    AShareIndexSnapshot,
    AShareTurnoverStock,
    EmotionLadderRow,
    MacroExpectationEvent,
    MacroExpectationResponse,
    ShenwanMembership,
    ShortTermEmotionSnapshot,
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


class _ReadyDashboardProvider(_DashboardProvider):
    async def market_activity(self) -> AShareBreadthSnapshot:
        return AShareBreadthSnapshot(
            up=3200,
            down=1600,
            flat=100,
            limit_up=80,
            real_limit_up=60,
            limit_down=15,
            real_limit_down=10,
            activity_pct=Decimal("65.31"),
            breadth_state="strong",
            speculation_state="active",
            trade_date=date(2026, 7, 29),
        )


class _InvalidDashboardProvider(_ReadyDashboardProvider):
    async def index_snapshots(self) -> Any:
        return {"unexpected": "payload"}


class _SlowDashboardProvider(_ReadyDashboardProvider):
    async def index_snapshots(self) -> list[AShareIndexSnapshot]:
        await asyncio.sleep(0.05)
        return await super().index_snapshots()


class _FailedDashboardProvider:
    def __getattr__(self, name: str) -> Any:
        async def call(*_: Any, **__: Any) -> Any:
            raise RuntimeError(f"{name} unavailable")

        return call


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


def _install_isolated_caches(
    monkeypatch: pytest.MonkeyPatch,
    *,
    now: Any | None = None,
) -> None:
    now_fn = now or (lambda: datetime.now(UTC))
    monkeypatch.setattr(
        service,
        "_DASHBOARD_CACHE",
        LastKnownGoodResearchCache[AShareDashboardResponse](
            ttl=timedelta(minutes=5),
            is_meaningful=lambda value: bool(value.market_detail.data or value.breadth.data),
            now=now_fn,
        ),
    )
    monkeypatch.setattr(
        service,
        "_MEMBERSHIP_CACHE",
        LastKnownGoodResearchCache[list[ShenwanMembership]](
            ttl=timedelta(hours=24),
            is_meaningful=bool,
            now=now_fn,
        ),
    )
    monkeypatch.setattr(
        service,
        "_STOCK_CACHE",
        LastKnownGoodResearchCache[StockSnapshotResponse](
            ttl=timedelta(minutes=15),
            is_meaningful=lambda value: bool(value.modules),
            now=now_fn,
        ),
    )
    monkeypatch.setattr(
        service,
        "_MACRO_CACHE",
        LastKnownGoodResearchCache[MacroExpectationResponse](
            ttl=timedelta(minutes=15),
            is_meaningful=lambda value: bool(value.events.data),
            now=now_fn,
        ),
    )
    monkeypatch.setattr(service, "_DASHBOARD_LOCK", asyncio.Lock())
    monkeypatch.setattr(service, "_MEMBERSHIP_LOCK", asyncio.Lock())
    monkeypatch.setattr(service, "_MACRO_LOCK", asyncio.Lock())
    monkeypatch.setattr(service, "_STOCK_LOCKS", {})


async def _memberships() -> list[ShenwanMembership]:
    return [_membership()]


def test_dashboard_normal_provider_result_is_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_isolated_caches(monkeypatch)
    monkeypatch.setattr(service, "_PROVIDER", _ReadyDashboardProvider())
    monkeypatch.setattr(service, "_memberships", _memberships)

    result = asyncio.run(service.get_a_share_dashboard())

    assert result.market_detail.meta.status == "ready"
    assert result.breadth.meta.status == "ready"
    assert result.shenwan.meta.status == "ready"
    assert result.emotion.meta.status == "ready"
    assert result.market_detail.meta.fetched_at.tzinfo is not None


def test_dashboard_keeps_other_modules_when_one_provider_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_isolated_caches(monkeypatch)
    monkeypatch.setattr(service, "_PROVIDER", _DashboardProvider())
    monkeypatch.setattr(service, "_memberships", _memberships)

    result = asyncio.run(
        service.get_a_share_dashboard(threshold_yuan=Decimal("987654321"))
    )

    assert result.market_detail.meta.status == "ready"
    assert result.breadth.meta.status == "error"
    assert result.shenwan.meta.status == "ready"
    assert result.shenwan.data.sw2_top[0].sw_l2_name == "半导体"
    assert result.emotion.meta.status == "ready"


def test_dashboard_provider_timeout_is_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_isolated_caches(monkeypatch)
    monkeypatch.setattr(service, "_PROVIDER", _SlowDashboardProvider())
    monkeypatch.setattr(service, "_memberships", _memberships)
    monkeypatch.setattr(service, "PROVIDER_TIMEOUT_SECONDS", 0.005)

    result = asyncio.run(service.get_a_share_dashboard())

    assert result.market_detail.meta.status == "error"
    assert result.market_detail.meta.error_code == "provider_timeout"
    assert result.breadth.meta.status == "ready"
    assert result.shenwan.meta.status == "ready"


def test_dashboard_invalid_payload_is_not_marked_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_isolated_caches(monkeypatch)
    monkeypatch.setattr(service, "_PROVIDER", _InvalidDashboardProvider())
    monkeypatch.setattr(service, "_memberships", _memberships)

    result = asyncio.run(service.get_a_share_dashboard())

    assert result.market_detail.meta.status == "error"
    assert result.market_detail.meta.error_code == "provider_invalid_payload"
    assert result.market_detail.data is None
    assert result.breadth.meta.status == "ready"


def test_dashboard_all_provider_failures_are_unavailable_not_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_isolated_caches(monkeypatch)
    monkeypatch.setattr(service, "_PROVIDER", _FailedDashboardProvider())

    async def failed_memberships() -> list[ShenwanMembership]:
        raise RuntimeError("membership unavailable")

    monkeypatch.setattr(service, "_memberships", failed_memberships)

    result = asyncio.run(service.get_a_share_dashboard())

    assert result.market_detail.meta.status == "error"
    assert result.breadth.meta.status == "error"
    assert result.shenwan.meta.status == "error"
    assert result.emotion.meta.status == "error"
    assert all(
        module.data is None
        for module in (result.market_detail, result.breadth, result.shenwan, result.emotion)
    )


def test_dashboard_uses_marked_stale_last_known_good_after_total_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_at = [datetime(2026, 8, 3, 2, 0, tzinfo=UTC)]
    _install_isolated_caches(monkeypatch, now=lambda: observed_at[0])
    monkeypatch.setattr(service, "_PROVIDER", _ReadyDashboardProvider())
    monkeypatch.setattr(service, "_memberships", _memberships)

    first = asyncio.run(service.get_a_share_dashboard())
    assert first.market_detail.meta.status == "ready"

    observed_at[0] += timedelta(minutes=6)
    monkeypatch.setattr(service, "_PROVIDER", _FailedDashboardProvider())

    async def failed_memberships() -> list[ShenwanMembership]:
        raise RuntimeError("membership unavailable")

    monkeypatch.setattr(service, "_memberships", failed_memberships)
    fallback = asyncio.run(service.get_a_share_dashboard())

    assert fallback.generated_at >= first.generated_at
    for module in (
        fallback.market_detail,
        fallback.breadth,
        fallback.shenwan,
        fallback.emotion,
    ):
        assert module.meta.status == "stale"
        assert module.meta.is_stale is True
        assert module.meta.source
        assert module.meta.fetched_at.tzinfo is not None
        assert "上一份有效数据" in (module.meta.message or "")


def test_stock_snapshot_isolates_individual_module_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_isolated_caches(monkeypatch)

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
