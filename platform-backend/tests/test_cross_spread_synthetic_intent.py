from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi import HTTPException

import app.cross_spread_synthetic_service as synthetic_service
from app.cross_spread_exit_schemas import (
    CrossSpreadExitPlanResponse,
    CrossSpreadMarketOpenRequest,
    ExitPlanStatus,
)
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

NOW = datetime(2026, 7, 25, tzinfo=UTC)


def batch_response(batch_id: str, *, direction: str) -> ExecutionBatchResponse:
    return ExecutionBatchResponse(
        batchId=batch_id,
        idempotencyKey=f"key:{batch_id}",
        strategyInstanceId="strategy_cross_venue_spread_instance_default",
        accountId="account_crypto_test",
        strategyKey="cross_venue_spread",
        direction=direction,
        status="hedged",
        requiresManualIntervention=False,
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
) -> CrossSpreadExitPlanResponse:
    return CrossSpreadExitPlanResponse(
        planId="plan-1",
        strategyInstanceId="strategy_cross_venue_spread_instance_default",
        openBatchId="open-batch-1",
        closeBatchId=None,
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

    def fake_submit(request):
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
    )
    take_profit_result = synthetic_service._close_claimed_plan(
        take_profit_plan,
        execution_mode="market",
    )

    assert [request.action for request, _kwargs in submitted] == [
        "CLOSE_LONG",
        "CLOSE_LONG",
    ]
    assert manual_result.order_intent is not None
    assert take_profit_result.order_intent is not None
    assert manual_result.order_intent.trigger_reason == "MANUAL"
    assert take_profit_result.order_intent.trigger_reason == "TAKE_PROFIT"
    assert manual_result.order_intent.action == "CLOSE_LONG_SPREAD"
    assert take_profit_result.order_intent.action == "CLOSE_LONG_SPREAD"


def test_limit_intent_fails_closed_before_any_market_submission(monkeypatch) -> None:
    monkeypatch.setattr(
        synthetic_service,
        "submit_cross_spread_market_command",
        lambda *_args, **_kwargs: pytest.fail(
            "Limit intent must not submit a Market command"
        ),
    )

    with pytest.raises(HTTPException) as exc_info:
        synthetic_service.open_cross_spread_market(
            CrossSpreadMarketOpenRequest(
                direction="LONG_SPREAD",
                quantityOz="1",
                takeProfitSpread="0",
                stopLossSpread="-3",
                executionMode="limit",
            )
        )

    assert exc_info.value.status_code == 422
    assert "not implemented" in str(exc_info.value.detail)
