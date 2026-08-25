from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

import app.cross_spread_synthetic_service as synthetic_service
from app.cross_spread_exit_schemas import (
    CrossSpreadExitPlanResponse,
    CrossSpreadMarketOpenRequest,
    ExitPlanStatus,
)
from app.cross_spread_limit_policy import CrossSpreadFokPrice
from app.cross_spread_order_intent import (
    LegacyMarketAction,
    SpreadDirection,
    SyntheticAction,
    build_close_intent,
    build_intent,
    build_open_intent,
    market_command_action,
)
from app.execution_schemas import ExecutionBatchResponse
from app.schemas import BatchLegResponse

NOW = datetime(2026, 7, 25, tzinfo=UTC)


def batch_response(
    batch_id: str,
    *,
    direction: str,
    status: str = "hedged",
) -> ExecutionBatchResponse:
    return ExecutionBatchResponse(
        batchId=batch_id,
        idempotencyKey=f"key:{batch_id}",
        strategyInstanceId="strategy_cross_venue_spread_instance_default",
        accountId="account_crypto_test",
        strategyKey="cross_venue_spread",
        direction=direction,
        status=status,
        requiresManualIntervention=status == "manual_intervention",
        failureReason=None,
        legs=[],
        createdAt=NOW,
        updatedAt=NOW,
    )


def exit_plan(
    *,
    direction: SpreadDirection = "LONG_SPREAD",
    trigger_reason: str | None = None,
    status: ExitPlanStatus = "active",
    close_batch_id: str | None = None,
) -> CrossSpreadExitPlanResponse:
    return CrossSpreadExitPlanResponse(
        planId="plan-1",
        strategyInstanceId="strategy_cross_venue_spread_instance_default",
        openBatchId="open-batch-1",
        closeBatchId=close_batch_id,
        direction=direction,
        quantityOz="1",
        mt5PositionId="778899",
        entrySpread="-2",
        takeProfitSpread="0",
        stopLossSpread="-3",
        status=status,
        triggerReason=trigger_reason,
        triggerSpread=None,
        createdAt=NOW,
        updatedAt=NOW,
        triggeredAt=None,
        closedAt=None,
    )


def fok_price() -> CrossSpreadFokPrice:
    return CrossSpreadFokPrice(
        direction="BUY_BYBIT_SELL_MT5",
        limit_spread=Decimal("-0.7"),
        executable_spread=Decimal("-0.8"),
        mt5_reference_price=Decimal("2501"),
        hedge_reserve=Decimal("0"),
        bybit_tick_size=Decimal("0.1"),
        raw_bybit_limit_price=Decimal("2500.3"),
        bybit_limit_price=Decimal("2500.3"),
        currently_executable=True,
    )


@pytest.mark.parametrize(
    ("action", "market_action", "direction", "is_open"),
    [
        ("OPEN_LONG_SPREAD", "OPEN_LONG", "LONG_SPREAD", True),
        ("CLOSE_LONG_SPREAD", "CLOSE_LONG", "LONG_SPREAD", False),
        ("OPEN_SHORT_SPREAD", "OPEN_SHORT", "SHORT_SPREAD", True),
        ("CLOSE_SHORT_SPREAD", "CLOSE_SHORT", "SHORT_SPREAD", False),
    ],
)
def test_all_four_business_actions_map_to_existing_market_commands(
    action: SyntheticAction,
    market_action: LegacyMarketAction,
    direction: SpreadDirection,
    is_open: bool,
) -> None:
    intent = build_intent(
        action,
        execution_type="market",
        trigger_reason="manual",
    )

    assert market_command_action(intent) == market_action
    assert intent.direction == direction
    assert intent.is_open is is_open


def test_open_and_close_factories_keep_action_execution_and_trigger_separate() -> None:
    open_intent = build_open_intent(
        "SHORT_SPREAD",
        "market",
        trigger_reason="strategy",
    )
    close_intent = build_close_intent(
        "SHORT_SPREAD",
        "limit",
        trigger_reason="stop_loss",
    )

    assert open_intent.action == "OPEN_SHORT_SPREAD"
    assert open_intent.execution_type == "MARKET"
    assert open_intent.trigger_reason == "STRATEGY"
    assert close_intent.action == "CLOSE_SHORT_SPREAD"
    assert close_intent.execution_type == "LIMIT"
    assert close_intent.trigger_reason == "STOP_LOSS"


def test_open_action_rejects_exit_only_trigger_reason() -> None:
    with pytest.raises(ValueError, match="cannot use trigger reason"):
        build_open_intent(
            "LONG_SPREAD",
            "market",
            trigger_reason="take_profit",
        )


def test_market_open_uses_normalized_intent_without_changing_legacy_action(
    monkeypatch,
) -> None:
    captured = {}
    plan = exit_plan()
    monkeypatch.setattr(
        synthetic_service.market_helpers,
        "_assert_acceptance_open_allowed",
        lambda: None,
    )
    monkeypatch.setattr(
        synthetic_service.market_helpers,
        "_create_exit_plan_for_open_batch",
        lambda *_args, **_kwargs: plan,
    )
    monkeypatch.setattr(
        synthetic_service,
        "configure_exit_plan_execution_modes",
        lambda *_args, **_kwargs: plan,
    )

    def fake_submit(request, **_kwargs):
        captured["request"] = request
        return batch_response("open-batch-1", direction=request.action)

    monkeypatch.setattr(
        synthetic_service,
        "submit_cross_spread_market_command",
        fake_submit,
    )

    result = synthetic_service.open_cross_spread_market(
        CrossSpreadMarketOpenRequest(
            direction="LONG_SPREAD",
            quantityOz="1",
            takeProfitSpread="0",
            stopLossSpread="-3",
            executionMode="market",
        )
    )

    assert captured["request"].action == "OPEN_LONG"
    assert result.order_intent is not None
    assert result.order_intent.action == "OPEN_LONG_SPREAD"
    assert result.order_intent.execution_type == "MARKET"
    assert result.order_intent.trigger_reason == "MANUAL"
    assert result.limit_execution is None
    assert result.exit_plan == plan


def test_market_open_reuses_existing_batch_by_client_idempotency_key(monkeypatch) -> None:
    plan = exit_plan()
    existing_batch = batch_response("open-batch-1", direction="OPEN_LONG")

    monkeypatch.setattr(
        synthetic_service,
        "find_batch_by_idempotency_key",
        lambda value: "open-batch-1" if value == "client-open-1" else None,
    )
    monkeypatch.setattr(
        synthetic_service,
        "get_execution_batch",
        lambda _batch_id: existing_batch,
    )
    monkeypatch.setattr(
        synthetic_service,
        "find_plan_by_open_batch",
        lambda _batch_id: plan,
    )
    monkeypatch.setattr(
        synthetic_service,
        "configure_exit_plan_execution_modes",
        lambda *_args, **_kwargs: plan,
    )
    monkeypatch.setattr(
        synthetic_service.market_helpers,
        "_assert_acceptance_open_allowed",
        lambda: pytest.fail("idempotent replay must not re-run acceptance gate"),
    )
    monkeypatch.setattr(
        synthetic_service,
        "submit_cross_spread_market_command",
        lambda *_args, **_kwargs: pytest.fail("idempotent replay must not submit again"),
    )

    result = synthetic_service.open_cross_spread_market(
        CrossSpreadMarketOpenRequest(
            idempotencyKey="client-open-1",
            direction="LONG_SPREAD",
            quantityOz="1",
            takeProfitSpread="0",
            stopLossSpread="-3",
            executionMode="market",
        )
    )

    assert result.execution_batch.batch_id == "open-batch-1"
    assert result.exit_plan == plan


def test_manual_close_and_take_profit_close_share_close_action(monkeypatch) -> None:
    submitted = []
    active_plan = exit_plan()
    take_profit_plan = exit_plan(trigger_reason="take_profit", status="triggered")

    def fake_submit(request, **kwargs):
        submitted.append((request, kwargs))
        return batch_response(f"close-batch-{len(submitted)}", direction=request.action)

    monkeypatch.setattr(
        synthetic_service,
        "submit_cross_spread_market_command",
        fake_submit,
    )
    monkeypatch.setattr(
        synthetic_service.market_helpers,
        "_verify_flat_positions",
        lambda **_: None,
    )
    monkeypatch.setattr(synthetic_service, "mark_plan_closing", lambda *_args: None)
    monkeypatch.setattr(
        synthetic_service,
        "mark_plan_closed",
        lambda plan_id, batch_id: exit_plan(status="closed"),
    )
    monkeypatch.setattr(synthetic_service, "get_exit_plan", lambda _plan_id: active_plan)
    monkeypatch.setattr(
        synthetic_service,
        "claim_exit_plan",
        lambda *_args, **_kwargs: exit_plan(
            trigger_reason="manual",
            status="triggered",
        ),
    )

    manual_result = synthetic_service.close_cross_spread_market(
        active_plan.plan_id,
        execution_mode="market",
        idempotency_key="client-close-submit-1",
    )
    take_profit_result = synthetic_service._close_claimed_plan(
        take_profit_plan,
        execution_mode="market",
    )

    assert [request.action for request, _kwargs in submitted] == [
        "CLOSE_LONG",
        "CLOSE_LONG",
    ]
    assert submitted[0][1]["idempotency_key"] == "client-close-submit-1"
    assert manual_result.order_intent is not None
    assert take_profit_result.order_intent is not None
    assert manual_result.order_intent.trigger_reason == "MANUAL"
    assert take_profit_result.order_intent.trigger_reason == "TAKE_PROFIT"
    assert manual_result.order_intent.action == "CLOSE_LONG_SPREAD"
    assert take_profit_result.order_intent.action == "CLOSE_LONG_SPREAD"


def test_manual_close_reuses_existing_close_batch_by_client_idempotency_key(monkeypatch) -> None:
    plan = exit_plan(status="closing", close_batch_id="close-batch-1")
    existing_batch = batch_response("close-batch-1", direction="CLOSE_LONG")
    existing_batch.idempotency_key = "client-close-1"

    monkeypatch.setattr(synthetic_service, "get_exit_plan", lambda _plan_id: plan)
    monkeypatch.setattr(
        synthetic_service,
        "get_execution_batch",
        lambda _batch_id: existing_batch,
    )
    monkeypatch.setattr(
        synthetic_service,
        "claim_exit_plan",
        lambda *_args, **_kwargs: pytest.fail("idempotent replay must not reclaim plan"),
    )

    result = synthetic_service.close_cross_spread_market(
        plan.plan_id,
        execution_mode="market",
        idempotency_key="client-close-1",
    )

    assert result.execution_batch.batch_id == "close-batch-1"
    assert result.exit_plan == plan


def test_manual_close_recovers_a_failed_unsubmitted_exit_batch(monkeypatch) -> None:
    manual_plan = exit_plan(
        status="manual_intervention",
        close_batch_id="failed-close-1",
    )
    recovered_plan = exit_plan(
        trigger_reason="manual",
        status="triggered",
        close_batch_id="failed-close-1",
    )
    failed_batch = batch_response("failed-close-1", direction="CLOSE_LONG", status="failed")
    failed_batch.legs = [
        BatchLegResponse(
            role="bybit_leg",
            accountId="bybit-live-main",
            orderId="platform-order-rejected-before-venue",
            status="rejected",
            failureReason="Runtime environment is not live",
        ),
        BatchLegResponse(
            role="mt5_leg",
            accountId="mt5-live-main",
            orderId=None,
            status="pending",
            failureReason=None,
        ),
    ]
    captured = {}

    monkeypatch.setattr(synthetic_service, "get_exit_plan", lambda _plan_id: manual_plan)
    monkeypatch.setattr(
        synthetic_service,
        "get_execution_batch",
        lambda _batch_id: failed_batch,
    )
    monkeypatch.setattr(
        synthetic_service,
        "reclaim_manual_exit_plan",
        lambda *_args, **_kwargs: recovered_plan,
    )
    monkeypatch.setattr(
        synthetic_service,
        "_close_claimed_plan",
        lambda claimed, **kwargs: captured.update(plan=claimed, kwargs=kwargs) or "closed",
    )

    result = synthetic_service.close_cross_spread_market(
        manual_plan.plan_id,
        execution_mode="market",
    )

    assert result == "closed"
    assert captured["plan"] == recovered_plan
    assert captured["kwargs"]["idempotency_key"] == (
        "cross-spread-exit-recovery:plan-1:failed-close-1"
    )


def test_limit_open_routes_only_to_fok_executor(monkeypatch) -> None:
    captured = {}
    plan = exit_plan()
    pricing = fok_price()
    monkeypatch.setattr(
        synthetic_service.market_helpers,
        "_assert_acceptance_open_allowed",
        lambda: None,
    )
    monkeypatch.setattr(
        synthetic_service,
        "_prepare_limit_execution",
        lambda *_args, **_kwargs: pricing,
    )
    monkeypatch.setattr(
        synthetic_service,
        "submit_cross_spread_market_command",
        lambda *_args, **_kwargs: pytest.fail("Limit must not submit Market"),
    )
    monkeypatch.setattr(
        synthetic_service.market_helpers,
        "_create_exit_plan_for_open_batch",
        lambda *_args, **_kwargs: plan,
    )
    monkeypatch.setattr(
        synthetic_service,
        "configure_exit_plan_execution_modes",
        lambda *_args, **_kwargs: plan,
    )

    def fake_fok(request, **kwargs):
        captured["request"] = request
        captured["kwargs"] = kwargs
        return batch_response("fok-open-1", direction=request.action)

    monkeypatch.setattr(synthetic_service, "submit_cross_spread_fok_command", fake_fok)

    result = synthetic_service.open_cross_spread_market(
        CrossSpreadMarketOpenRequest(
            direction="LONG_SPREAD",
            quantityOz="1",
            takeProfitSpread="0",
            stopLossSpread="-3",
            executionMode="limit",
            limitSpread="-0.7",
        )
    )

    assert captured["request"].action == "OPEN_LONG"
    assert captured["kwargs"]["bybit_limit_price"] == Decimal("2500.3")
    assert result.order_intent is not None
    assert result.order_intent.execution_type == "LIMIT"
    assert result.limit_execution is not None
    assert result.limit_execution.time_in_force == "FOK"


def test_limit_request_requires_explicit_spread() -> None:
    with pytest.raises(ValidationError, match="limitSpread"):
        CrossSpreadMarketOpenRequest(
            direction="LONG_SPREAD",
            quantityOz="1",
            takeProfitSpread="0",
            stopLossSpread="-3",
            executionMode="limit",
        )


def test_market_open_request_allows_missing_take_profit_and_stop_loss() -> None:
    request = CrossSpreadMarketOpenRequest(
        direction="LONG_SPREAD",
        quantityOz="1",
        executionMode="market",
    )

    assert request.take_profit_spread is None
    assert request.stop_loss_spread is None
