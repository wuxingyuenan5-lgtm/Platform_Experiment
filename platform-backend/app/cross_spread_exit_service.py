from __future__ import annotations

import asyncio
from decimal import Decimal

from fastapi import HTTPException

from app.config import get_settings
from app.cross_spread import (
    BYBIT_LEG_ROLE,
    MT5_LEG_ROLE,
    STRATEGY_INSTANCE_ID,
    get_cross_spread_snapshot,
    submit_cross_spread_market_command,
)
from app.cross_spread_exit_policy import (
    evaluate_exit_threshold,
    select_executable_close_spread,
)
from app.cross_spread_exit_repository import (
    claim_exit_plan,
    create_exit_plan,
    get_exit_plan,
    list_exit_plans,
    load_batch_fill_summaries,
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
)
from app.execution_batches import get_execution_batch, update_batch_status
from app.schemas import CrossSpreadMarketCommandRequest


def open_cross_spread_market(request: CrossSpreadMarketOpenRequest) -> CrossSpreadOpenResult:
    _require_market_mode(request.execution_mode)
    action = "OPEN_LONG" if request.direction == "LONG_SPREAD" else "OPEN_SHORT"
    batch = submit_cross_spread_market_command(
        CrossSpreadMarketCommandRequest(
            action=action,
            quantityOz=request.quantity_oz,
        )
    )
    if batch.status != "hedged":
        return CrossSpreadOpenResult(executionBatch=batch, exitPlan=None)

    try:
        plan = _create_exit_plan_for_open_batch(
            batch.batch_id,
            direction=request.direction,
            take_profit_spread=request.take_profit_spread,
            stop_loss_spread=request.stop_loss_spread,
        )
    except HTTPException as exc:
        update_batch_status(
            batch.batch_id,
            "manual_intervention",
            failure_reason=f"Exit plan creation failed: {exc.detail}",
            requires_manual_intervention=True,
        )
        return CrossSpreadOpenResult(
            executionBatch=get_execution_batch(batch.batch_id),
            exitPlan=None,
        )
    return CrossSpreadOpenResult(executionBatch=batch, exitPlan=plan)


def close_cross_spread_market(
    plan_id: str,
    *,
    execution_mode: str,
) -> CrossSpreadCloseResult:
    _require_market_mode(execution_mode)
    claimed = claim_exit_plan(
        plan_id,
        trigger_reason="manual",
        trigger_spread=None,
    )
    if claimed is None:
        current = get_exit_plan(plan_id)
        if current.status == "closed" and current.close_batch_id is not None:
            return CrossSpreadCloseResult(
                executionBatch=get_execution_batch(current.close_batch_id),
                exitPlan=current,
            )
        raise HTTPException(status_code=409, detail="Exit plan is not active")
    return _close_claimed_plan(claimed)


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
            _close_claimed_plan(claimed)
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
            # The next interval may evaluate other active plans, but a claimed plan is never retried.
            pass
        await asyncio.sleep(settings.cross_spread_exit_monitor_interval_seconds)


def _create_exit_plan_for_open_batch(
    batch_id: str,
    *,
    direction: str,
    take_profit_spread: Decimal,
    stop_loss_spread: Decimal,
) -> CrossSpreadExitPlanResponse:
    summaries = load_batch_fill_summaries(batch_id)
    bybit = summaries.get(BYBIT_LEG_ROLE)
    mt5 = summaries.get(MT5_LEG_ROLE)
    if bybit is None or mt5 is None:
        raise HTTPException(status_code=409, detail="Hedged batch fill evidence is incomplete")

    snapshot = get_cross_spread_snapshot()
    if snapshot.mt5.status != "available":
        raise HTTPException(status_code=409, detail="MT5 positions are unavailable after open")
    expected_mt5_side = "sell" if direction == "LONG_SPREAD" else "buy"
    candidates = [
        position
        for position in snapshot.mt5.positions
        if position.side == expected_mt5_side
        and position.external_id is not None
        and abs(position.quantity) >= mt5.quantity
    ]
    if len(candidates) != 1:
        raise HTTPException(
            status_code=409,
            detail="MT5 open position cannot be mapped to exactly one Position Ticket",
        )

    return create_exit_plan(
        strategy_instance_id=STRATEGY_INSTANCE_ID,
        open_batch_id=batch_id,
        direction=direction,
        quantity_oz=bybit.quantity,
        mt5_position_id=str(candidates[0].external_id),
        entry_spread=bybit.average_price - mt5.average_price,
        take_profit_spread=take_profit_spread,
        stop_loss_spread=stop_loss_spread,
    )


def _close_claimed_plan(plan: CrossSpreadExitPlanResponse) -> CrossSpreadCloseResult:
    action = "CLOSE_LONG" if plan.direction == "LONG_SPREAD" else "CLOSE_SHORT"
    try:
        batch = submit_cross_spread_market_command(
            CrossSpreadMarketCommandRequest(
                action=action,
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
        updated = mark_plan_closed(plan.plan_id, batch.batch_id)
    else:
        updated = mark_plan_manual_intervention(
            plan.plan_id,
            close_batch_id=batch.batch_id,
        )
    return CrossSpreadCloseResult(executionBatch=batch, exitPlan=updated)


def _require_market_mode(execution_mode: str) -> None:
    if execution_mode != "market":
        raise HTTPException(
            status_code=422,
            detail="Limit cross-spread execution is designed but not implemented yet",
        )
