from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException

import app.cross_spread_exit_routes as exit_routes
import app.cross_spread_synthetic_service as synthetic_service
from app.cross_spread_exit_schemas import (
    CrossSpreadExitPlanResponse,
    CrossSpreadMarketCloseRequest,
    CrossSpreadMarketOpenRequest,
)
from app.cross_spread_limit_policy import CrossSpreadFokPrice
from app.schema_migrations import PLATFORM_MIGRATIONS, apply_migrations

NOW = datetime(2026, 7, 26, tzinfo=UTC)


def triggered_plan(
    trigger_reason: str,
    *,
    take_profit_execution_mode: str = "market",
    stop_loss_execution_mode: str = "market",
    triggered_at: datetime = NOW,
) -> CrossSpreadExitPlanResponse:
    return CrossSpreadExitPlanResponse(
        planId="plan-mode-1",
        strategyInstanceId="strategy_cross_venue_spread_instance_default",
        openBatchId="open-batch-mode-1",
        closeBatchId=None,
        direction="LONG_SPREAD",
        quantityOz="1",
        mt5PositionId="998877",
        entrySpread="-2",
        takeProfitSpread="0",
        stopLossSpread="-3",
        takeProfitExecutionMode=take_profit_execution_mode,
        stopLossExecutionMode=stop_loss_execution_mode,
        status="triggered",
        triggerReason=trigger_reason,
        triggerSpread="-0.2",
        createdAt=NOW,
        updatedAt=triggered_at,
        triggeredAt=triggered_at,
        closedAt=None,
    )


def pricing() -> CrossSpreadFokPrice:
    return CrossSpreadFokPrice(
        direction="SELL_BYBIT_BUY_MT5",
        limit_spread=Decimal("-0.2"),
        executable_spread=Decimal("-0.1"),
        mt5_reference_price=Decimal("2501.1"),
        hedge_reserve=Decimal("0"),
        bybit_tick_size=Decimal("0.1"),
        raw_bybit_limit_price=Decimal("2500.9"),
        bybit_limit_price=Decimal("2500.9"),
        currently_executable=True,
    )


def test_migration_defaults_existing_exit_plans_to_market_market() -> None:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    apply_migrations(db, PLATFORM_MIGRATIONS[:2])
    db.execute(
        """
        INSERT INTO cross_spread_exit_plans (
            id, strategy_instance_id, open_batch_id, close_batch_id, direction,
            quantity_oz, mt5_position_id, entry_spread, take_profit_spread,
            stop_loss_spread, status, trigger_reason, trigger_spread,
            created_at, updated_at, triggered_at, closed_at
        ) VALUES (
            'plan-existing', 'strategy-existing', 'batch-existing', NULL,
            'LONG_SPREAD', '1', '12345', '-2', '0', '-3', 'active',
            NULL, NULL, ?, ?, NULL, NULL
        )
        """,
        (NOW.isoformat(), NOW.isoformat()),
    )

    apply_migrations(db, PLATFORM_MIGRATIONS[:3])

    row = db.execute(
        """
        SELECT take_profit_execution_mode, stop_loss_execution_mode
        FROM cross_spread_exit_plans
        WHERE id = 'plan-existing'
        """
    ).fetchone()
    assert row["take_profit_execution_mode"] == "market"
    assert row["stop_loss_execution_mode"] == "market"


def test_open_request_defaults_exit_execution_modes_to_market() -> None:
    request = CrossSpreadMarketOpenRequest(
        direction="LONG_SPREAD",
        quantityOz="1",
        takeProfitSpread="0",
        stopLossSpread="-3",
    )

    assert request.take_profit_execution_mode == "market"
    assert request.stop_loss_execution_mode == "market"


@pytest.mark.parametrize(
    ("route_name", "service_name", "request_model"),
    [
        (
            "open_market_lifecycle",
            "open_cross_spread_market",
            CrossSpreadMarketOpenRequest(
                direction="LONG_SPREAD",
                quantityOz="1",
                takeProfitSpread="0",
                stopLossSpread="-3",
                executionMode="limit",
                limitSpread="-1",
                limitStrategy="post_only_chase",
            ),
        ),
        (
            "close_market_lifecycle",
            "close_cross_spread_market",
            CrossSpreadMarketCloseRequest(
                executionMode="limit",
                limitSpread="-1",
                limitStrategy="post_only_chase",
            ),
        ),
    ],
)
def test_lifecycle_routes_delegate_to_limit_capable_service(
    monkeypatch,
    route_name: str,
    service_name: str,
    request_model,
) -> None:
    captured = {}
    marker = object()

    def fake_service(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return marker

    monkeypatch.setattr(exit_routes, service_name, fake_service)

    if route_name == "open_market_lifecycle":
        result = exit_routes.open_market_lifecycle(request_model)
    else:
        result = exit_routes.close_market_lifecycle("plan-1", request_model)

    assert result is marker
    if route_name == "open_market_lifecycle":
        assert captured["args"] == (request_model,)
    else:
        assert captured["args"] == ("plan-1",)
        assert captured["kwargs"] == {
            "execution_mode": "limit",
            "limit_spread": request_model.limit_spread,
            "limit_strategy": "post_only_chase",
        }


def test_manual_close_passes_limit_template_to_close_execution(
    monkeypatch,
) -> None:
    plan = triggered_plan("manual")
    pricing_result = pricing()
    captured = {}

    monkeypatch.setattr(synthetic_service, "get_exit_plan", lambda _plan_id: plan)
    monkeypatch.setattr(
        synthetic_service,
        "_prepare_limit_execution",
        lambda intent, limit_spread: (
            captured.update(
                intent=intent,
                limit_spread=limit_spread,
            )
            or pricing_result
        ),
    )
    monkeypatch.setattr(
        synthetic_service,
        "claim_exit_plan",
        lambda *_args, **_kwargs: plan,
    )
    monkeypatch.setattr(
        synthetic_service,
        "_close_claimed_plan",
        lambda claimed, **kwargs: (
            captured.update(claimed=claimed, close_kwargs=kwargs) or "closed"
        ),
    )

    result = synthetic_service.close_cross_spread_market(
        "plan-mode-1",
        execution_mode="limit",
        limit_spread=Decimal("-0.2"),
        limit_strategy="post_only_chase",
    )

    assert result == "closed"
    assert captured["limit_spread"] == Decimal("-0.2")
    assert captured["close_kwargs"] == {
        "execution_mode": "limit",
        "limit_strategy": "post_only_chase",
        "limit_execution": pricing_result,
    }


def test_take_profit_limit_uses_claimed_trigger_spread(monkeypatch) -> None:
    plan = triggered_plan("take_profit", take_profit_execution_mode="limit")
    captured = {}

    def fake_prepare(intent, limit_spread):
        captured["execution_type"] = intent.execution_type
        captured["limit_spread"] = limit_spread
        return pricing()

    def fake_close(
        claimed_plan,
        *,
        execution_mode,
        limit_strategy,
        limit_execution,
    ):
        captured["plan"] = claimed_plan
        captured["execution_mode"] = execution_mode
        captured["limit_strategy"] = limit_strategy
        captured["limit_execution"] = limit_execution
        return "closed"

    monkeypatch.setattr(synthetic_service, "_prepare_limit_execution", fake_prepare)
    monkeypatch.setattr(synthetic_service, "_close_claimed_plan", fake_close)

    result = synthetic_service._close_claimed_plan_for_trigger(plan)

    assert result == "closed"
    assert captured["execution_type"] == "LIMIT"
    assert captured["limit_spread"] == Decimal("-0.2")
    assert captured["execution_mode"] == "limit"
    assert captured["limit_strategy"] == "fok"
    assert captured["limit_execution"] == pricing()


def test_stop_loss_market_uses_same_close_action_without_limit(monkeypatch) -> None:
    plan = triggered_plan("stop_loss", stop_loss_execution_mode="market")
    captured = {}

    def fake_prepare(intent, limit_spread):
        captured["execution_type"] = intent.execution_type
        captured["limit_spread"] = limit_spread
        return None

    def fake_close(
        claimed_plan,
        *,
        execution_mode,
        limit_strategy,
        limit_execution,
    ):
        captured["plan"] = claimed_plan
        captured["execution_mode"] = execution_mode
        captured["limit_strategy"] = limit_strategy
        captured["limit_execution"] = limit_execution
        return "closed"

    monkeypatch.setattr(synthetic_service, "_prepare_limit_execution", fake_prepare)
    monkeypatch.setattr(synthetic_service, "_close_claimed_plan", fake_close)

    result = synthetic_service._close_claimed_plan_for_trigger(plan)

    assert result == "closed"
    assert captured["execution_type"] == "MARKET"
    assert captured["limit_spread"] is None
    assert captured["execution_mode"] == "market"
    assert captured["limit_strategy"] == "fok"
    assert captured["limit_execution"] is None


def test_automatic_limit_preparation_failure_releases_claim(monkeypatch) -> None:
    plan = triggered_plan("take_profit", take_profit_execution_mode="limit")
    released = []
    monkeypatch.setattr(
        synthetic_service,
        "_prepare_limit_execution",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            HTTPException(status_code=409, detail="quote moved")
        ),
    )
    monkeypatch.setattr(
        synthetic_service,
        "release_exit_plan_claim",
        lambda plan_id: released.append(plan_id),
    )

    with pytest.raises(HTTPException, match="quote moved"):
        synthetic_service._close_claimed_plan_for_trigger(plan)

    assert released == ["plan-mode-1"]


def test_fok_exit_idempotency_changes_with_each_claim_time() -> None:
    first = triggered_plan(
        "take_profit",
        take_profit_execution_mode="limit",
        triggered_at=NOW,
    )
    second = triggered_plan(
        "take_profit",
        take_profit_execution_mode="limit",
        triggered_at=NOW + timedelta(seconds=1),
    )

    first_key = synthetic_service._fok_exit_idempotency_key(first)
    second_key = synthetic_service._fok_exit_idempotency_key(second)

    assert first_key != second_key
    assert first_key.startswith("cross-spread-fok-exit:plan-mode-1:")
