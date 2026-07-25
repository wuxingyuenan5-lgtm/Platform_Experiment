from __future__ import annotations

import asyncio
from decimal import Decimal

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
    configure_exit_plan_execution_modes,
    get_exit_plan,
    list_exit_plans,
    load_batch_fill_summaries,
    mark_plan_closed,
    mark_plan_closing,
    mark_plan_manual_intervention,
    release_exit_plan_claim,
)
from app.cross_spread_exit_schemas import (
    CrossSpreadCloseResult,
    CrossSpreadExitEvaluationResponse,
    CrossSpreadExitPlanResponse,
    CrossSpreadLimitExecutionResponse,
    CrossSpreadMarketOpenRequest,
    CrossSpreadOpenResult,
    CrossSpreadOrderIntentResponse,
)
from app.cross_spread_limit_execution import (
    get_bybit_catalog_tick_size,
    submit_cross_spread_fok_command,
)
from app.cross_spread_limit_policy import (
    CrossSpreadFokPrice,
    derive_cross_spread_fok_price,
)
from app.cross_spread_order_intent import (
    SyntheticOrderIntent,
    build_close_intent,
    build_open_intent,
    command_action,
)
from app.execution_batches import get_execution_batch
from app.schemas import CrossSpreadMarketCommandRequest


def open_cross_spread_market(request: CrossSpreadMarketOpenRequest) -> CrossSpreadOpenResult:
    intent = build_open_intent(
        request.direction,
        request.execution_mode,
        trigger_reason="MANUAL",
    )
    market_helpers._assert_acceptance_open_allowed()
    limit_execution = _prepare_limit_execution(intent, request.limit_spread)
    command_request = CrossSpreadMarketCommandRequest(
        action=command_action(intent),
        quantityOz=request.quantity_oz,
    )
    if intent.execution_type == "MARKET":
        batch = submit_cross_spread_market_command(command_request)
    else:
        assert limit_execution is not None
        batch = submit_cross_spread_fok_command(
            command_request,
            bybit_limit_price=limit_execution.bybit_limit_price,
        )

    if batch.status != "hedged":
        handled = market_helpers._handle_definitive_open_failure(batch)
        return CrossSpreadOpenResult(
            executionBatch=handled,
            orderIntent=_intent_response(intent),
            limitExecution=_limit_response(limit_execution),
            exitPlan=None,
        )

    try:
        plan = market_helpers._create_exit_plan_for_open_batch(
            batch.batch_id,
            direction=request.direction,
            take_profit_spread=request.take_profit_spread,
            stop_loss_spread=request.stop_loss_spread,
        )
        plan = configure_exit_plan_execution_modes(
            plan.plan_id,
            take_profit_execution_mode=request.take_profit_execution_mode,
            stop_loss_execution_mode=request.stop_loss_execution_mode,
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
            limitExecution=_limit_response(limit_execution),
            exitPlan=None,
        )
    return CrossSpreadOpenResult(
        executionBatch=batch,
        orderIntent=_intent_response(intent),
        limitExecution=_limit_response(limit_execution),
        exitPlan=plan,
    )


def close_cross_spread_market(
    plan_id: str,
    *,
    execution_mode: str,
    limit_spread: Decimal | None = None,
) -> CrossSpreadCloseResult:
    current_plan = get_exit_plan(plan_id)
    intent = build_close_intent(
        current_plan.direction,
        execution_mode,
        trigger_reason="MANUAL",
    )
    limit_execution = _prepare_limit_execution(intent, limit_spread)
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
                limitExecution=_limit_response(limit_execution),
                exitPlan=current,
            )
        raise HTTPException(status_code=409, detail="Exit plan is not active")
    return _close_claimed_plan(
        claimed,
        execution_mode=execution_mode,
        limit_execution=limit_execution,
    )


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
            _close_claimed_plan_for_trigger(claimed)
        except Exception:
            current = get_exit_plan(plan.plan_id)
            if current.status != "active":
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


def _close_claimed_plan_for_trigger(
    plan: CrossSpreadExitPlanResponse,
) -> CrossSpreadCloseResult:
    trigger_reason = (plan.trigger_reason or "").strip().lower()
    if trigger_reason == "take_profit":
        execution_mode = plan.take_profit_execution_mode
    elif trigger_reason == "stop_loss":
        execution_mode = plan.stop_loss_execution_mode
    else:
        raise HTTPException(status_code=409, detail="Claimed exit plan has no TP/SL trigger")

    intent = build_close_intent(
        plan.direction,
        execution_mode,
        trigger_reason=trigger_reason,
    )
    try:
        limit_execution = _prepare_limit_execution(
            intent,
            plan.trigger_spread if execution_mode == "limit" else None,
        )
    except Exception:
        if execution_mode == "limit":
            release_exit_plan_claim(plan.plan_id)
        raise
    return _close_claimed_plan(
        plan,
        execution_mode=execution_mode,
        limit_execution=limit_execution,
    )


def _close_claimed_plan(
    plan: CrossSpreadExitPlanResponse,
    *,
    execution_mode: str,
    limit_execution: CrossSpreadFokPrice | None = None,
) -> CrossSpreadCloseResult:
    intent = build_close_intent(
        plan.direction,
        execution_mode,
        trigger_reason=plan.trigger_reason or "MANUAL",
    )
    if intent.execution_type == "LIMIT" and limit_execution is None:
        raise HTTPException(status_code=422, detail="Limit close requires prepared pricing")
    command_request = CrossSpreadMarketCommandRequest(
        action=command_action(intent),
        quantityOz=plan.quantity_oz,
    )
    try:
        if intent.execution_type == "MARKET":
            batch = submit_cross_spread_market_command(
                command_request,
                idempotency_key=f"cross-spread-exit:{plan.plan_id}",
                bybit_reduce_only=True,
                mt5_reduce_only=True,
                mt5_position_id=plan.mt5_position_id,
            )
        else:
            assert limit_execution is not None
            batch = submit_cross_spread_fok_command(
                command_request,
                bybit_limit_price=limit_execution.bybit_limit_price,
                idempotency_key=_fok_exit_idempotency_key(plan),
                bybit_reduce_only=True,
                mt5_reduce_only=True,
                mt5_position_id=plan.mt5_position_id,
            )
    except Exception:
        mark_plan_manual_intervention(plan.plan_id, close_batch_id=None)
        raise

    if (
        intent.execution_type == "LIMIT"
        and batch.status == "failed"
        and not load_batch_fill_summaries(batch.batch_id)
    ):
        updated = release_exit_plan_claim(plan.plan_id)
        return CrossSpreadCloseResult(
            executionBatch=batch,
            orderIntent=_intent_response(intent),
            limitExecution=_limit_response(limit_execution),
            exitPlan=updated,
        )

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
        limitExecution=_limit_response(limit_execution),
        exitPlan=updated,
    )


def _fok_exit_idempotency_key(plan: CrossSpreadExitPlanResponse) -> str:
    if plan.triggered_at is None:
        raise HTTPException(status_code=409, detail="FOK exit claim timestamp is unavailable")
    return f"cross-spread-fok-exit:{plan.plan_id}:{plan.triggered_at.isoformat()}"


def _prepare_limit_execution(
    intent: SyntheticOrderIntent,
    limit_spread: Decimal | None,
) -> CrossSpreadFokPrice | None:
    if intent.execution_type == "MARKET":
        return None
    if limit_spread is None:
        raise HTTPException(status_code=422, detail="Limit execution requires limitSpread")
    snapshot = get_cross_spread_snapshot()
    if (
        snapshot.status != "available"
        or snapshot.bybit.quote is None
        or snapshot.mt5.quote is None
    ):
        raise HTTPException(
            status_code=503,
            detail="Executable cross-spread quotes are unavailable",
        )
    reserve = get_settings().cross_spread_limit_hedge_reserve_price
    if reserve < 0:
        raise HTTPException(
            status_code=423,
            detail="Cross-spread FOK hedge reserve is invalid",
        )
    try:
        pricing = derive_cross_spread_fok_price(
            command_action(intent),
            limit_spread=limit_spread,
            bybit_bid=snapshot.bybit.quote.bid,
            bybit_ask=snapshot.bybit.quote.ask,
            mt5_bid=snapshot.mt5.quote.bid,
            mt5_ask=snapshot.mt5.quote.ask,
            bybit_tick_size=get_bybit_catalog_tick_size(),
            hedge_reserve=reserve,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not pricing.currently_executable:
        raise HTTPException(
            status_code=409,
            detail=(
                "Current executable spread does not satisfy the requested FOK limit; "
                "no order was submitted"
            ),
        )
    return pricing


def _intent_response(intent: SyntheticOrderIntent) -> CrossSpreadOrderIntentResponse:
    return CrossSpreadOrderIntentResponse(
        action=intent.action,
        executionType=intent.execution_type,
        triggerReason=intent.trigger_reason,
        direction=intent.direction,
        isOpen=intent.is_open,
    )


def _limit_response(
    pricing: CrossSpreadFokPrice | None,
) -> CrossSpreadLimitExecutionResponse | None:
    if pricing is None:
        return None
    return CrossSpreadLimitExecutionResponse(
        direction=pricing.direction,
        limitSpread=pricing.limit_spread,
        executableSpread=pricing.executable_spread,
        mt5ReferencePrice=pricing.mt5_reference_price,
        hedgeReserve=pricing.hedge_reserve,
        bybitTickSize=pricing.bybit_tick_size,
        rawBybitLimitPrice=pricing.raw_bybit_limit_price,
        bybitLimitPrice=pricing.bybit_limit_price,
        currentlyExecutable=pricing.currently_executable,
        timeInForce="FOK",
    )
