from __future__ import annotations

import asyncio
from decimal import Decimal

from fastapi import HTTPException

from app.config import get_settings
from app.cross_spread import (
    BYBIT_ACCOUNT_ID,
    BYBIT_LEG_ROLE,
    BYBIT_SYMBOL,
    MT5_ACCOUNT_ID,
    MT5_LEG_ROLE,
    MT5_SYMBOL,
    STRATEGY_INSTANCE_ID,
    get_cross_spread_snapshot,
    submit_bybit_definitive_failure_rollback,
    submit_cross_spread_market_command,
)
from app.cross_spread_exit_policy import (
    evaluate_exit_threshold,
    select_executable_close_spread,
)
from app.cross_spread_exit_repository import (
    claim_exit_plan,
    count_non_closed_exit_plans,
    count_unresolved_cross_spread_batches,
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
    SpreadDirection,
)
from app.cross_spread_live_read_client import (
    CrossSpreadLiveReadError,
    LivePosition,
    list_positions,
)
from app.execution_batches import get_execution_batch, update_batch_status
from app.schemas import CrossSpreadMarketCommandRequest, ExecutionBatchResponse


def open_cross_spread_market(request: CrossSpreadMarketOpenRequest) -> CrossSpreadOpenResult:
    _require_market_mode(request.execution_mode)
    _assert_acceptance_open_allowed()
    action = "OPEN_LONG" if request.direction == "LONG_SPREAD" else "OPEN_SHORT"
    batch = submit_cross_spread_market_command(
        CrossSpreadMarketCommandRequest(
            action=action,
            quantityOz=request.quantity_oz,
        )
    )
    if batch.status != "hedged":
        handled = _handle_definitive_open_failure(batch)
        return CrossSpreadOpenResult(executionBatch=handled, exitPlan=None)

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
            # A later interval may evaluate other active plans. A claimed plan is
            # never retried because its state no longer matches the atomic claim.
            pass
        await asyncio.sleep(settings.cross_spread_exit_monitor_interval_seconds)


def _assert_acceptance_open_allowed() -> None:
    settings = get_settings()
    maximum = settings.cross_spread_acceptance_max_active_plans
    if maximum <= 0:
        raise HTTPException(
            status_code=423,
            detail="Cross-spread acceptance active-plan limit is not configured",
        )
    if count_non_closed_exit_plans() >= maximum:
        raise HTTPException(
            status_code=409,
            detail="A non-closed cross-spread lifecycle already exists",
        )
    if count_unresolved_cross_spread_batches() > 0:
        raise HTTPException(
            status_code=409,
            detail="An unresolved cross-spread execution batch blocks new opens",
        )
    if settings.cross_spread_position_verification_required:
        bybit_positions, mt5_positions = _load_live_positions()
        if _target_positions(bybit_positions, BYBIT_SYMBOL):
            raise HTTPException(
                status_code=409,
                detail="A live Bybit gold position already exists",
            )
        if _target_positions(mt5_positions, MT5_SYMBOL):
            raise HTTPException(
                status_code=409,
                detail="A live MT5 gold position already exists",
            )


def _handle_definitive_open_failure(batch: ExecutionBatchResponse) -> ExecutionBatchResponse:
    if not _is_definitive_second_leg_failure(batch):
        return batch
    summaries = load_batch_fill_summaries(batch.batch_id)
    bybit = summaries.get(BYBIT_LEG_ROLE)
    mt5 = summaries.get(MT5_LEG_ROLE)
    if bybit is None or mt5 is not None:
        return batch

    original_reason = batch.failure_reason or "MT5 hedge failed after confirmed Bybit fill"
    try:
        bybit_positions, mt5_positions = _load_live_positions()
    except HTTPException as exc:
        update_batch_status(
            batch.batch_id,
            "manual_intervention",
            failure_reason=(
                f"{original_reason}; pre-rollback position verification failed: "
                f"{exc.detail}"
            ),
            requires_manual_intervention=True,
        )
        return get_execution_batch(batch.batch_id)

    live_mt5 = _target_positions(mt5_positions, MT5_SYMBOL)
    if live_mt5:
        update_batch_status(
            batch.batch_id,
            "manual_intervention",
            failure_reason=(
                f"{original_reason}; live MT5 exposure exists despite the definitive "
                "failure state, so automatic Bybit rollback is blocked"
            ),
            requires_manual_intervention=True,
        )
        return get_execution_batch(batch.batch_id)

    live_bybit = _target_positions(bybit_positions, BYBIT_SYMBOL)
    if not live_bybit:
        update_batch_status(
            batch.batch_id,
            "failed",
            failure_reason=(
                f"{original_reason}; external positions were already flat before rollback, "
                "so no duplicate rollback was submitted"
            ),
            requires_manual_intervention=False,
        )
        return get_execution_batch(batch.batch_id)

    expected_positive = batch.direction == "OPEN_LONG"
    matching_bybit = [
        position
        for position in live_bybit
        if _sign_matches(position.net_quantity, expected_positive)
        and abs(position.net_quantity) == bybit.quantity
    ]
    if len(live_bybit) != 1 or len(matching_bybit) != 1:
        update_batch_status(
            batch.batch_id,
            "manual_intervention",
            failure_reason=(
                f"{original_reason}; live Bybit exposure does not match exactly one "
                "confirmed first-leg position, so automatic rollback is blocked"
            ),
            requires_manual_intervention=True,
        )
        return get_execution_batch(batch.batch_id)

    try:
        rollback = submit_bybit_definitive_failure_rollback(
            open_batch_id=batch.batch_id,
            open_action=batch.direction,
            quantity_oz=bybit.quantity,
        )
    except Exception as exc:
        update_batch_status(
            batch.batch_id,
            "manual_intervention",
            failure_reason=f"{original_reason}; Bybit rollback submission failed: {exc}",
            requires_manual_intervention=True,
        )
        return get_execution_batch(batch.batch_id)

    if rollback.status != "filled":
        update_batch_status(
            batch.batch_id,
            "manual_intervention",
            failure_reason=(
                f"{original_reason}; Bybit rollback ended with status {rollback.status}; "
                "do not retry blindly"
            ),
            requires_manual_intervention=True,
        )
        return get_execution_batch(batch.batch_id)

    try:
        _verify_flat_positions()
    except HTTPException as exc:
        update_batch_status(
            batch.batch_id,
            "manual_intervention",
            failure_reason=(
                f"{original_reason}; rollback order {rollback.platform_order_id} filled, "
                f"but flat-position verification failed: {exc.detail}"
            ),
            requires_manual_intervention=True,
        )
        return get_execution_batch(batch.batch_id)

    update_batch_status(
        batch.batch_id,
        "failed",
        failure_reason=(
            f"{original_reason}; Bybit exposure was reduced by rollback order "
            f"{rollback.platform_order_id}"
        ),
        requires_manual_intervention=False,
    )
    return get_execution_batch(batch.batch_id)


def _is_definitive_second_leg_failure(batch: ExecutionBatchResponse) -> bool:
    legs = {leg.role: leg for leg in batch.legs}
    bybit = legs.get(BYBIT_LEG_ROLE)
    mt5 = legs.get(MT5_LEG_ROLE)
    if bybit is None or mt5 is None or bybit.status != "filled":
        return False
    return mt5.status in {"failed", "rejected", "blocked"}


def _create_exit_plan_for_open_batch(
    batch_id: str,
    *,
    direction: SpreadDirection,
    take_profit_spread: Decimal,
    stop_loss_spread: Decimal,
) -> CrossSpreadExitPlanResponse:
    summaries = load_batch_fill_summaries(batch_id)
    bybit = summaries.get(BYBIT_LEG_ROLE)
    mt5 = summaries.get(MT5_LEG_ROLE)
    if bybit is None or mt5 is None:
        raise HTTPException(status_code=409, detail="Hedged batch fill evidence is incomplete")

    mt5_position_id = _verify_open_positions(
        direction=direction,
        bybit_quantity=bybit.quantity,
        mt5_quantity=mt5.quantity,
    )
    return create_exit_plan(
        strategy_instance_id=STRATEGY_INSTANCE_ID,
        open_batch_id=batch_id,
        direction=direction,
        quantity_oz=bybit.quantity,
        mt5_position_id=mt5_position_id,
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
        try:
            _verify_flat_positions(expected_mt5_position_id=plan.mt5_position_id)
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
    return CrossSpreadCloseResult(executionBatch=batch, exitPlan=updated)


def _verify_open_positions(
    *,
    direction: SpreadDirection,
    bybit_quantity: Decimal,
    mt5_quantity: Decimal,
) -> str:
    bybit_positions, mt5_positions = _load_live_positions()
    bybit_expected_positive = direction == "LONG_SPREAD"
    mt5_expected_positive = direction == "SHORT_SPREAD"
    bybit_matches = [
        position
        for position in _target_positions(bybit_positions, BYBIT_SYMBOL)
        if _sign_matches(position.net_quantity, bybit_expected_positive)
        and abs(position.net_quantity) == bybit_quantity
    ]
    mt5_matches = [
        position
        for position in _target_positions(mt5_positions, MT5_SYMBOL)
        if _sign_matches(position.net_quantity, mt5_expected_positive)
        and abs(position.net_quantity) == mt5_quantity
    ]
    if len(bybit_matches) != 1:
        raise HTTPException(
            status_code=409,
            detail="Confirmed Bybit fill does not match exactly one live position",
        )
    if len(mt5_matches) != 1:
        raise HTTPException(
            status_code=409,
            detail="Confirmed MT5 fill does not match exactly one live Position Ticket",
        )
    return mt5_matches[0].external_position_id


def _verify_flat_positions(*, expected_mt5_position_id: str | None = None) -> None:
    bybit_positions, mt5_positions = _load_live_positions()
    if _target_positions(bybit_positions, BYBIT_SYMBOL):
        raise HTTPException(status_code=409, detail="Bybit gold exposure remains after close")
    target_mt5 = _target_positions(mt5_positions, MT5_SYMBOL)
    if target_mt5:
        expected = (
            f"; expected closed Position Ticket {expected_mt5_position_id}"
            if expected_mt5_position_id is not None
            else ""
        )
        raise HTTPException(
            status_code=409,
            detail=f"MT5 gold exposure remains after close{expected}",
        )


def _load_live_positions() -> tuple[list[LivePosition], list[LivePosition]]:
    try:
        return list_positions(BYBIT_ACCOUNT_ID), list_positions(MT5_ACCOUNT_ID)
    except CrossSpreadLiveReadError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _target_positions(positions: list[LivePosition], symbol: str) -> list[LivePosition]:
    normalized = symbol.upper()
    return [
        position
        for position in positions
        if position.symbol.upper() == normalized and position.net_quantity != 0
    ]


def _sign_matches(quantity: Decimal, expected_positive: bool) -> bool:
    return quantity > 0 if expected_positive else quantity < 0


def _require_market_mode(execution_mode: str) -> None:
    if execution_mode != "market":
        raise HTTPException(
            status_code=422,
            detail="Limit cross-spread execution is designed but not implemented yet",
        )
