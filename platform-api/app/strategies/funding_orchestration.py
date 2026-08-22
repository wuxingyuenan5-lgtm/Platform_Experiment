from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, localcontext

from fastapi import HTTPException

from app.database import connection
from app.execution_batches import get_execution_batch, update_batch_status, update_leg_status
from app.execution_schemas import ExecutionBatchResponse
from app.order_execution_intents import register_order_execution_intent
from app.schemas import CreateTradeCommandRequest
from app.strategies.domain import ExecutionPlan, ExecutionPlanLeg, StrategyInstructionStatus
from app.trade_commands import create_trade_command

PERPETUAL_ROLE = "perpetual_leg"
SPOT_ROLE = "spot_leg"
PHASE_2_CAPABILITY_MESSAGE = (
    "Funding controlled-live execution requires Phase 2 post-only "
    "chase and authoritative incremental release"
)


@dataclass(frozen=True, slots=True)
class FundingReleaseRow:
    child_id: str
    cumulative_perpetual_fill: Decimal
    release_quantity: Decimal
    cumulative_spot_quantity: Decimal
    status: str
    trade_command_id: str | None
    order_id: str | None
    failure_reason: str | None


def execute_funding_instruction(
    instruction_id: str,
    *,
    instruction_row,
    plan: ExecutionPlan,
) -> ExecutionBatchResponse:
    trading_mode = _strategy_trading_mode(instruction_row["strategy_instance_id"])
    if trading_mode != "simulation":
        raise HTTPException(status_code=423, detail=PHASE_2_CAPABILITY_MESSAGE)

    perpetual_leg = _leg(plan, PERPETUAL_ROLE)
    spot_leg = _leg(plan, SPOT_ROLE)
    batch_id = str(instruction_row["execution_batch_id"])

    _set_instruction_status(instruction_id, StrategyInstructionStatus.EXECUTING)
    perpetual_order_id, perpetual_status = _ensure_perpetual_submission(
        instruction_id=instruction_id,
        batch_id=batch_id,
        plan_leg=perpetual_leg,
        strategy_instance_id=instruction_row["strategy_instance_id"],
        request_idempotency_key=instruction_row["idempotency_key"],
    )
    if perpetual_status == "result_unknown":
        return _manual_intervention(
            instruction_id,
            batch_id,
            "Funding perpetual PostOnly result is unknown",
        )
    if perpetual_status not in {"filled", "acknowledged", "accepted", "processing"}:
        return _failed_without_side_effects(
            instruction_id,
            batch_id,
            f"Funding perpetual leg stopped with status {perpetual_status}",
        )

    perpetual_cumulative_fill = _order_cumulative_fill(perpetual_order_id)
    releases = _release_rows(batch_id)
    resumable = [
        row
        for row in releases
        if row.status == "declared" and row.trade_command_id is None
    ]
    if resumable:
        for row in resumable:
            _submit_spot_release(
                instruction_id=instruction_id,
                batch_id=batch_id,
                strategy_instance_id=instruction_row["strategy_instance_id"],
                request_idempotency_key=instruction_row["idempotency_key"],
                spot_leg=spot_leg,
                child_id=row.child_id,
                quantity=row.release_quantity,
            )
        releases = _release_rows(batch_id)

    if any(row.status in {"failed", "result_unknown"} for row in releases):
        first = next(row for row in releases if row.status in {"failed", "result_unknown"})
        return _manual_intervention(
            instruction_id,
            batch_id,
            first.failure_reason or "Funding Spot release requires manual intervention",
        )

    allowed_cumulative_spot = _allowed_cumulative_spot(
        perpetual_cumulative_fill=perpetual_cumulative_fill,
        spot_leg=spot_leg,
    )
    already_released = sum((row.release_quantity for row in releases), Decimal("0"))
    release_delta = allowed_cumulative_spot - already_released
    if release_delta > 0:
        child_id = f"{batch_id}:spot:{_decimal_key(allowed_cumulative_spot)}"
        _declare_release(
            batch_id=batch_id,
            child_id=child_id,
            cumulative_perpetual_fill=perpetual_cumulative_fill,
            release_quantity=release_delta,
            cumulative_spot_quantity=allowed_cumulative_spot,
        )
        _submit_spot_release(
            instruction_id=instruction_id,
            batch_id=batch_id,
            strategy_instance_id=instruction_row["strategy_instance_id"],
            request_idempotency_key=instruction_row["idempotency_key"],
            spot_leg=spot_leg,
            child_id=child_id,
            quantity=release_delta,
        )
        releases = _release_rows(batch_id)
        if any(row.status in {"failed", "result_unknown"} for row in releases):
            first = next(row for row in releases if row.status in {"failed", "result_unknown"})
            return _manual_intervention(
                instruction_id,
                batch_id,
                first.failure_reason or "Funding Spot release requires manual intervention",
            )

    final_released = sum((row.release_quantity for row in _release_rows(batch_id)), Decimal("0"))
    if (
        perpetual_cumulative_fill == perpetual_leg.maximum_quantity
        and final_released == spot_leg.release_cap
    ):
        update_batch_status(batch_id, "hedged")
        _set_instruction_status(instruction_id, StrategyInstructionStatus.RECONCILING)
        _set_instruction_status(instruction_id, StrategyInstructionStatus.COMPLETED)
        return get_execution_batch(batch_id)

    update_batch_status(batch_id, "partially_executed")
    update_leg_status(
        batch_id,
        SPOT_ROLE,
        "filled" if final_released > 0 else "pending",
    )
    return get_execution_batch(batch_id)


def _strategy_trading_mode(strategy_instance_id: str) -> str:
    with connection() as db:
        row = db.execute(
            "SELECT trading_mode FROM strategy_instances WHERE id = ?",
            (strategy_instance_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Strategy instance is not runnable")
    return str(row["trading_mode"])


def _leg(plan: ExecutionPlan, role: str) -> ExecutionPlanLeg:
    for leg in plan.legs:
        if leg.role == role:
            return leg
    raise HTTPException(status_code=423, detail=f"Funding plan leg {role} is unavailable")


def _batch_leg(batch_id: str, role: str):
    with connection() as db:
        row = db.execute(
            """
            SELECT account_id, instrument_id, symbol, side, order_type,
                   quantity, price, order_id, status
            FROM execution_batch_legs WHERE batch_id = ? AND role = ?
            """,
            (batch_id, role),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=409, detail=f"Execution batch leg {role} is unavailable")
    return row


def _ensure_perpetual_submission(
    *,
    instruction_id: str,
    batch_id: str,
    plan_leg: ExecutionPlanLeg,
    strategy_instance_id: str,
    request_idempotency_key: str,
) -> tuple[str, str]:
    leg = _batch_leg(batch_id, PERPETUAL_ROLE)
    if leg["order_id"] is not None:
        return str(leg["order_id"]), _order_status(str(leg["order_id"]))
    idempotency_key = f"instruction:{request_idempotency_key}:{PERPETUAL_ROLE}"
    register_order_execution_intent(
        idempotency_key,
        reduce_only=False,
        execution_policy="post_only_chase",
    )
    limit_price = _simulation_reference_limit_price(plan_leg)
    try:
        command = create_trade_command(
            CreateTradeCommandRequest(
                idempotencyKey=idempotency_key,
                strategyInstanceId=strategy_instance_id,
                accountId=plan_leg.account_id,
                instrumentId=plan_leg.instrument_id,
                symbol=plan_leg.external_symbol,
                side=plan_leg.side,
                orderType="limit",
                quantity=plan_leg.maximum_quantity,
                price=limit_price,
            )
        )
    except HTTPException:
        unknown_order_id = _result_unknown_order_for_idempotency_key(idempotency_key)
        if unknown_order_id is None:
            raise
        _update_batch_leg_order(
            batch_id=batch_id,
            role=PERPETUAL_ROLE,
            order_id=unknown_order_id,
            status="result_unknown",
            price=limit_price,
        )
        return unknown_order_id, "result_unknown"
    _update_batch_leg_order(
        batch_id=batch_id,
        role=PERPETUAL_ROLE,
        order_id=command.platform_order_id,
        status=command.status,
        price=limit_price,
    )
    return str(command.platform_order_id), command.status


def _simulation_reference_limit_price(plan_leg: ExecutionPlanLeg) -> Decimal:
    reference = Decimal("100")
    rounding = ROUND_FLOOR if plan_leg.side == "buy" else ROUND_CEILING
    with localcontext() as context:
        context.prec = 28
        ticks = (reference / plan_leg.price_tick).to_integral_value(rounding=rounding)
        price = ticks * plan_leg.price_tick
    if price <= 0:
        raise HTTPException(status_code=423, detail="Funding simulation reference price is invalid")
    return price


def _order_status(order_id: str) -> str:
    with connection() as db:
        row = db.execute("SELECT status FROM orders WHERE id = ?", (order_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=409, detail="Funding order evidence is unavailable")
    return str(row["status"])


def _order_cumulative_fill(order_id: str) -> Decimal:
    with connection() as db:
        row = db.execute(
            """
            SELECT COALESCE(SUM(CAST(quantity AS REAL)), 0) AS total
            FROM fills
            WHERE order_id = ?
            """,
            (order_id,),
        ).fetchone()
    return Decimal(str(row["total"]))


def _allowed_cumulative_spot(
    *,
    perpetual_cumulative_fill: Decimal,
    spot_leg: ExecutionPlanLeg,
) -> Decimal:
    assert spot_leg.release_ratio is not None
    assert spot_leg.release_cap is not None
    with localcontext() as context:
        context.prec = 28
        proportional = perpetual_cumulative_fill * spot_leg.release_ratio
        steps = (proportional / spot_leg.quantity_step).to_integral_value(rounding=ROUND_FLOOR)
        releasable = steps * spot_leg.quantity_step
    return min(releasable, spot_leg.release_cap)


def _release_rows(batch_id: str) -> list[FundingReleaseRow]:
    with connection() as db:
        rows = db.execute(
            """
            SELECT child_id, cumulative_perpetual_fill, release_quantity, cumulative_spot_quantity,
                   status, trade_command_id, order_id, failure_reason
            FROM funding_spot_release_commands
            WHERE batch_id = ?
            ORDER BY created_at, child_id
            """,
            (batch_id,),
        ).fetchall()
    return [
        FundingReleaseRow(
            child_id=str(row["child_id"]),
            cumulative_perpetual_fill=Decimal(str(row["cumulative_perpetual_fill"])),
            release_quantity=Decimal(str(row["release_quantity"])),
            cumulative_spot_quantity=Decimal(str(row["cumulative_spot_quantity"])),
            status=str(row["status"]),
            trade_command_id=row["trade_command_id"],
            order_id=row["order_id"],
            failure_reason=row["failure_reason"],
        )
        for row in rows
    ]


def _declare_release(
    *,
    batch_id: str,
    child_id: str,
    cumulative_perpetual_fill: Decimal,
    release_quantity: Decimal,
    cumulative_spot_quantity: Decimal,
) -> None:
    timestamp = _utc_now()
    with connection() as db:
        existing = db.execute(
            "SELECT child_id FROM funding_spot_release_commands WHERE child_id = ?",
            (child_id,),
        ).fetchone()
        if existing is not None:
            return
        db.execute(
            """
            INSERT INTO funding_spot_release_commands (
                child_id, batch_id, cumulative_perpetual_fill, release_quantity,
                cumulative_spot_quantity, trade_command_id, order_id, status,
                failure_reason, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, NULL, NULL, 'declared', NULL, ?, ?)
            """,
            (
                child_id,
                batch_id,
                _decimal_text(cumulative_perpetual_fill),
                _decimal_text(release_quantity),
                _decimal_text(cumulative_spot_quantity),
                timestamp,
                timestamp,
            ),
        )


def _submit_spot_release(
    *,
    instruction_id: str,
    batch_id: str,
    strategy_instance_id: str,
    request_idempotency_key: str,
    spot_leg: ExecutionPlanLeg,
    child_id: str,
    quantity: Decimal,
) -> None:
    idempotency_key = _spot_child_idempotency_key(
        request_idempotency_key=request_idempotency_key,
        child_id=child_id,
    )
    register_order_execution_intent(idempotency_key, reduce_only=False)
    try:
        command = create_trade_command(
            CreateTradeCommandRequest(
                idempotencyKey=idempotency_key,
                strategyInstanceId=strategy_instance_id,
                accountId=spot_leg.account_id,
                instrumentId=spot_leg.instrument_id,
                symbol=spot_leg.external_symbol,
                side=spot_leg.side,
                orderType="market",
                quantity=quantity,
            )
        )
    except HTTPException as exc:
        unknown_order_id = _result_unknown_order_for_idempotency_key(idempotency_key)
        if unknown_order_id is not None:
            _mark_release_status(
                child_id,
                "result_unknown",
                order_id=unknown_order_id,
                failure_reason=str(exc.detail),
            )
            update_leg_status(batch_id, SPOT_ROLE, "result_unknown", order_id=unknown_order_id)
            return
        _mark_release_status(child_id, "failed", failure_reason=str(exc.detail))
        raise

    release_status = "filled" if command.status == "filled" else command.status
    if release_status not in {"filled", "result_unknown"}:
        release_status = "failed"
    _mark_release_status(
        child_id,
        release_status,
        trade_command_id=command.trade_command_id,
        order_id=command.platform_order_id,
        failure_reason=(
            None
            if release_status == "filled"
            else f"Funding Spot release stopped with status {command.status}"
        ),
    )
    update_leg_status(batch_id, SPOT_ROLE, command.status, order_id=command.platform_order_id)
    if release_status == "result_unknown":
        _manual_intervention(
            instruction_id,
            batch_id,
            "Funding Spot release result is unknown",
        )


def _mark_release_status(
    child_id: str,
    status: str,
    *,
    trade_command_id: str | None = None,
    order_id: str | None = None,
    failure_reason: str | None = None,
) -> None:
    with connection() as db:
        db.execute(
            """
            UPDATE funding_spot_release_commands
            SET trade_command_id = COALESCE(?, trade_command_id),
                order_id = COALESCE(?, order_id),
                status = ?, failure_reason = ?, updated_at = ?
            WHERE child_id = ?
            """,
            (trade_command_id, order_id, status, failure_reason, _utc_now(), child_id),
        )


def _update_batch_leg_order(
    *,
    batch_id: str,
    role: str,
    order_id: str | None,
    status: str,
    price: Decimal | None = None,
) -> None:
    with connection() as db:
        db.execute(
            """
            UPDATE execution_batch_legs
            SET order_id = COALESCE(?, order_id),
                status = ?,
                price = COALESCE(?, price),
                updated_at = ?
            WHERE batch_id = ? AND role = ?
            """,
            (
                order_id,
                status,
                _decimal_text(price) if price is not None else None,
                _utc_now(),
                batch_id,
                role,
            ),
        )


def _manual_intervention(instruction_id: str, batch_id: str, reason: str):
    update_batch_status(
        batch_id,
        "manual_intervention",
        failure_reason=reason,
        requires_manual_intervention=True,
    )
    _set_instruction_status(
        instruction_id,
        StrategyInstructionStatus.MANUAL_INTERVENTION,
        failure_reason=reason,
    )
    return get_execution_batch(batch_id)


def _failed_without_side_effects(instruction_id: str, batch_id: str, reason: str):
    update_batch_status(batch_id, "failed", failure_reason=reason)
    _set_instruction_status(
        instruction_id,
        StrategyInstructionStatus.FAILED,
        failure_reason=reason,
    )
    return get_execution_batch(batch_id)


def _set_instruction_status(
    instruction_id: str,
    status: StrategyInstructionStatus,
    failure_reason: str | None = None,
) -> None:
    with connection() as db:
        db.execute(
            """
            UPDATE strategy_runs
            SET status = ?, failure_reason = ?, updated_at = ?
            WHERE id = ?
            """,
            (status.value, failure_reason, _utc_now(), instruction_id),
        )


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


def _decimal_key(value: Decimal) -> str:
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _spot_child_idempotency_key(*, request_idempotency_key: str, child_id: str) -> str:
    digest = hashlib.sha256(f"{request_idempotency_key}|{child_id}".encode()).hexdigest()
    prefix = request_idempotency_key[:48]
    return f"funding-spot:{prefix}:{digest[:32]}"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _result_unknown_order_for_idempotency_key(idempotency_key: str) -> str | None:
    with connection() as db:
        row = db.execute(
            """
            SELECT o.id
            FROM trade_commands command
            JOIN orders o ON o.command_id = command.id
            WHERE command.idempotency_key = ? AND o.status = 'result_unknown'
            """,
            (idempotency_key,),
        ).fetchone()
    return str(row["id"]) if row is not None else None
