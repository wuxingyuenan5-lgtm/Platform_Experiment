from __future__ import annotations

import asyncio

from fastapi import HTTPException

from app import cross_spread_exit_service as market_helpers
from app.config import get_settings
from app.cross_spread import get_cross_spread_snapshot, submit_cross_spread_market_command
from app.cross_spread_exit_policy import (
    evaluate_exit_threshold,
    select_executable_close_spread,
)
from app.cross_spread_exit_repository import (
    claim_exit_plan,
    get_exit_plan,
    list_exit_plans,
    mark_plan_closed,
    mark_plan_closing,
    mark_plan_manual_intervention,
)
from app.cross_spread_exit_schemas import (
    CrossSpreadCloseResult,
    CrossSpreadExitEvaluationResponse,
    CrossSpreadExitPlanResponse,
    CrossSpreadMarketOpenRequest,
    CrossSpreadOpenResult,
    CrossSpreadOrderIntentResponse,
)
from app.cross_spread_order_intent import (
    SyntheticOrderIntent,
    build_close_intent,
    build_open_intent,
    market_command_action,
)
from app.execution_batches import get_execution_batch
from app.schemas import CrossSpreadMarketCommandRequest


def open_cross_spread_market(request: CrossSpreadMarketOpenRequest) -> CrossSpreadOpenResult:
    intent = build_open_intent(
        request.direction,
        request.execution_mode,
        trigger_reason="MANUAL",
    )
    _require_market_intent(intent)
    market_helpers._assert_acceptance_open_allowed()
    batch = submit_cross_spread_market_command(
        CrossSpreadMarketCommandRequest(
            action=market_command_action(intent),
            quantityOz=request.quantity_oz,
        )
    )
    if batch.status != "hedged":
        handled = market_helpers._handle_definitive_open_failure(batch)
        return CrossSpreadOpenResult(
            executionBatch=handled,
            orderIntent=_intent_response(intent),
            exitPlan=None,
        )

    try:
        plan = market_helpers._create_exit_plan_for_open_batch(
            batch.batch_id,
            direction=request.direction,
            take_profit_spread=request.take_profit_spread,
            stop_loss_spread=request.stop_loss_spread,
        )
    except HTTPException as exc:
        market_helpers.update_batch_status(
            batch.batch_id,
            "manual_intervention",
            failure_reason=f"Exit plan creation failed: {exc.detail}",
            requires_manual_intervention=True,
        )
        return CrossSpreadOpenResult(
            executionBatch=get_execution_batch(batch.batch_id),
            orderIntent=_intent_response(intent),
            exitPlan=None,
        )
    return CrossSpreadOpenResult(
        executionBatch=batch,
        orderIntent=_intent_response(intent),
        exitPlan=plan,
    )


def close_cross_spread_market(
    plan_id: str,
    *,
    execution_mode: str,
) -> CrossSpreadCloseResult:
    intent = build_close_intent(
        get_exit_plan(plan_id).direction,
        execution_mode,
        trigger_reason="MANUAL",
    )
    _require_market_intent(intent)
    claimed = claim_exit_plan(
        plan_id,
        trigger_reason="manual",
        trigger_spread=None,
    )
    if claimed is None:
        current = get_exit_plan(plan_id)
        if current.status == "closed" and current.close_batch_id is not None:
            completed_intent = build_close_intent(
                current.direction,
                execution_mode,
                trigger_reason=current.trigger_reason or "MANUAL",
            )
            return CrossSpreadCloseResult(
                executionBatch=get_execution_batch(current.close_batch_id),
                orderIntent=_intent_response(completed_intent),
                exitPlan=current,
            )
        raise HTTPException(status_code=409, detail="Exit plan is not active")
    return _close_claimed_plan(claimed, execution_mode=execution_mode)


def evaluate_cross_spread_exit_plans() -> CrossSpreadExitEvaluationResponse:
    settings = get_settings()
    if not settings.live_trading_enabled:
        return CrossSpreadExitEvaluationResponse(
            evaluatedCount=0,
            triggeredCount=0,
            skippedReason="Live cross-spread execution is disabled",
        )

    active = list_exit_plans(status="active")
    if not active:
        return CrossSpreadExitEvaluationResponse(
            evaluatedCount=0,
            triggeredCount=0,
            skippedReason=None,
        )

    snapshot = get_cross_spread_snapshot()
    if snapshot.status != "available":
        return CrossSpreadExitEvaluationResponse(
            evaluatedCount=len(active),
            triggeredCount=0,
            skippedReason="Executable cross-spread quotes are unavailable",
        )

    triggered_count = 0
    for plan in active:
        close_spread = select_executable_close_spread(
            plan.direction,
            long_spread=snapshot.long_spread,
            short_spread=snapshot.short_spread,
        )
        if close_spread is None:
            continue
        trigger_reason = evaluate_exit_threshold(
            plan.direction,
            close_spread=close_spread,
            take_profit_spread=plan.take_profit_spread,
            stop_loss_spread=plan.stop_loss_spread,
        )
        if trigger_reason is None:
            continue
        claimed = claim_exit_plan(
            plan.plan_id,
            trigger_reason=trigger_reason,
            trigger_spread=close_spread,
        )
        if claimed is None:
            continue
        triggered_count += 1
        try:
            _close_claimed_plan(claimed, execution_mode="market")
        except Exception:
            mark_plan_manual_intervention(plan.plan_id, close_batch_id=None)

    return CrossSpreadExitEvaluationResponse(
        evaluatedCount=len(active),
        triggeredCount=triggered_count,
        skippedReason=None,
    )


async def run_cross_spread_exit_monitor() -> None:
    settings = get_settings()
    while True:
        try:
            await asyncio.to_thread(evaluate_cross_spread_exit_plans)
        except Exception:
            # A later interval may evaluate other active plans. A claimed plan is
            # never retried because its state no longer matches the atomic claim.
            pass
        await asyncio.sleep(settings.cross_spread_exit_monitor_interval_seconds)


def _close_claimed_plan(
    plan: CrossSpreadExitPlanResponse,
    *,
    execution_mode: str,
) -> CrossSpreadCloseResult:
    intent = build_close_intent(
        plan.direction,
        execution_mode,
        trigger_reason=plan.trigger_reason or "MANUAL",
    )
    _require_market_intent(intent)
    try:
        batch = submit_cross_spread_market_command(
            CrossSpreadMarketCommandRequest(
                action=market_command_action(intent),
                quantityOz=plan.quantity_oz,
            ),
            idempotency_key=f"cross-spread-exit:{plan.plan_id}",
            bybit_reduce_only=True,
            mt5_reduce_only=True,
            mt5_position_id=plan.mt5_position_id,
        )
    except Exception:
        mark_plan_manual_intervention(plan.plan_id, close_batch_id=None)
        raise

    mark_plan_closing(plan.plan_id, batch.batch_id)
    if batch.status == "hedged":
        try:
            market_helpers._verify_flat_positions(
                expected_mt5_position_id=plan.mt5_position_id
            )
        except HTTPException:
            updated = mark_plan_manual_intervention(
                plan.plan_id,
                close_batch_id=batch.batch_id,
            )
        else:
            updated = mark_plan_closed(plan.plan_id, batch.batch_id)
    else:
        updated = mark_plan_manual_intervention(
            plan.plan_id,
            close_batch_id=batch.batch_id,
        )
    return CrossSpreadCloseResult(
        executionBatch=batch,
        orderIntent=_intent_response(intent),
        exitPlan=updated,
    )


def _intent_response(intent: SyntheticOrderIntent) -> CrossSpreadOrderIntentResponse:
    return CrossSpreadOrderIntentResponse(
        action=intent.action,
        executionType=intent.execution_type,
        triggerReason=intent.trigger_reason,
        direction=intent.direction,
        isOpen=intent.is_open,
    )


def _require_market_intent(intent: SyntheticOrderIntent) -> None:
    if intent.execution_type != "MARKET":
        raise HTTPException(
            status_code=422,
            detail="Limit cross-spread execution is designed but not implemented yet",
        )
