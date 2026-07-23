from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException

from app.database import connection
from app.schemas import (
    BatchLegResponse,
    CreateExecutionBatchRequest,
    CreateOrderRequest,
    ExecutionBatchResponse,
)
from app.trading import submit_order


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def find_batch_by_idempotency_key(idempotency_key: str) -> str | None:
    with connection() as db:
        row = db.execute(
            "SELECT id FROM execution_batches WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
    return row["id"] if row is not None else None


def list_execution_batches(
    strategy_instance_id: str | None = None,
) -> list[ExecutionBatchResponse]:
    parameters: tuple[str, ...] = ()
    where_clause = ""
    if strategy_instance_id is not None:
        where_clause = "WHERE strategy_instance_id = ?"
        parameters = (strategy_instance_id,)

    with connection() as db:
        rows = db.execute(
            f"""
            SELECT id
            FROM execution_batches
            {where_clause}
            ORDER BY created_at DESC
            """,
            parameters,
        ).fetchall()
    return [get_execution_batch(row["id"]) for row in rows]


def resolve_strategy_key(request: CreateExecutionBatchRequest) -> str:
    if request.strategy_instance_id is None:
        return request.strategy_key

    with connection() as db:
        row = db.execute(
            """
            SELECT sd.strategy_key
            FROM strategy_instances si
            JOIN strategy_definitions sd ON sd.id = si.strategy_definition_id
            WHERE si.id = ?
            """,
            (request.strategy_instance_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Strategy instance not found")
    if row["strategy_key"] != request.strategy_key:
        raise HTTPException(status_code=422, detail="Strategy key does not match strategy instance")
    return row["strategy_key"]


def validate_account(account_id: str) -> None:
    with connection() as db:
        row = db.execute("SELECT id FROM accounts WHERE id = ?", (account_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Account not found: {account_id}")


def validate_instrument(instrument_id: str) -> None:
    with connection() as db:
        row = db.execute("SELECT id FROM instruments WHERE id = ?", (instrument_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Instrument not found: {instrument_id}")


def create_execution_batch(request: CreateExecutionBatchRequest) -> ExecutionBatchResponse:
    if request.idempotency_key is not None:
        existing_batch_id = find_batch_by_idempotency_key(request.idempotency_key)
        if existing_batch_id is not None:
            return get_execution_batch(existing_batch_id)

    strategy_key = resolve_strategy_key(request)
    default_account_id = request.account_id or request.legs[0].account_id
    if default_account_id is None:
        raise HTTPException(status_code=422, detail="Execution batch account is required")

    should_validate_catalog = request.strategy_instance_id is not None
    if should_validate_catalog:
        validate_account(default_account_id)
        for leg in request.legs:
            validate_account(leg.account_id or default_account_id)
            validate_instrument(leg.instrument_id)

    batch_id = str(uuid4())
    created_at = now_iso()

    with connection() as db:
        db.execute(
            """
            INSERT INTO execution_batches (
                    id, idempotency_key, strategy_instance_id, account_id,
                    strategy_key, direction, status,
                requires_manual_intervention, failure_reason, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                batch_id,
                request.idempotency_key,
                request.strategy_instance_id,
                default_account_id,
                strategy_key,
                request.direction,
                "pending",
                0,
                None,
                created_at,
                created_at,
            ),
        )
        for sequence, leg in enumerate(request.legs, start=1):
            db.execute(
                """
                INSERT INTO execution_batch_legs (
                    id, batch_id, sequence, role, account_id, instrument_id, symbol, side,
                    order_type, quantity, price, order_id, status,
                    failure_reason, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    batch_id,
                    sequence,
                    leg.role,
                    (leg.account_id or default_account_id) if should_validate_catalog else None,
                    leg.instrument_id,
                    leg.symbol,
                    leg.side,
                    leg.order_type,
                    format(leg.quantity, "f"),
                    format(leg.price, "f") if leg.price is not None else None,
                    None,
                    "pending",
                    None,
                    created_at,
                    created_at,
                ),
            )

    update_batch_status(batch_id, "executing")
    filled_count = 0

    for leg in request.legs:
        update_leg_status(batch_id, leg.role, "submitting")
        leg_account_id = leg.account_id or default_account_id
        try:
            order = submit_order(
                CreateOrderRequest(
                    accountId=leg_account_id,
                    instrumentId=leg.instrument_id,
                    symbol=leg.symbol,
                    side=leg.side,
                    orderType=leg.order_type,
                    quantity=leg.quantity,
                    price=leg.price,
                )
            )
        except HTTPException as exc:
            reason = str(exc.detail)
            status = "manual_intervention" if filled_count else "failed"
            update_leg_status(batch_id, leg.role, "failed", failure_reason=reason)
            update_batch_status(
                batch_id,
                status,
                failure_reason=reason,
                requires_manual_intervention=status == "manual_intervention",
            )
            return get_execution_batch(batch_id)

        update_leg_status(
            batch_id,
            leg.role,
            order.status,
            order_id=order.order_id,
        )

        if order.status == "filled":
            filled_count += 1
            if filled_count < len(request.legs):
                update_batch_status(batch_id, "partially_executed")
            continue

        reason = f"Leg {leg.role} completed with order status {order.status}"
        uncertain = order.status in {"processing", "acknowledged", "result_unknown"}
        status = "manual_intervention" if filled_count or uncertain else "failed"
        update_leg_status(
            batch_id,
            leg.role,
            order.status,
            order_id=order.order_id,
            failure_reason=reason,
        )
        update_batch_status(
            batch_id,
            status,
            failure_reason=reason,
            requires_manual_intervention=status == "manual_intervention",
        )
        return get_execution_batch(batch_id)

    update_batch_status(batch_id, "hedged")
    return get_execution_batch(batch_id)


def update_batch_status(
    batch_id: str,
    status: str,
    *,
    failure_reason: str | None = None,
    requires_manual_intervention: bool = False,
) -> None:
    with connection() as db:
        db.execute(
            """
            UPDATE execution_batches
            SET status = ?, requires_manual_intervention = ?, failure_reason = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                status,
                int(requires_manual_intervention),
                failure_reason,
                now_iso(),
                batch_id,
            ),
        )


def update_leg_status(
    batch_id: str,
    role: str,
    status: str,
    *,
    order_id: str | None = None,
    failure_reason: str | None = None,
) -> None:
    with connection() as db:
        db.execute(
            """
            UPDATE execution_batch_legs
            SET status = ?,
                order_id = COALESCE(?, order_id),
                failure_reason = ?,
                updated_at = ?
            WHERE batch_id = ? AND role = ?
            """,
            (status, order_id, failure_reason, now_iso(), batch_id, role),
        )


def get_execution_batch(batch_id: str) -> ExecutionBatchResponse:
    with connection() as db:
        batch = db.execute(
            """
            SELECT id, idempotency_key, strategy_instance_id, account_id,
                   strategy_key, direction, status,
                   requires_manual_intervention, failure_reason, created_at, updated_at
            FROM execution_batches
            WHERE id = ?
            """,
            (batch_id,),
        ).fetchone()
        legs = db.execute(
            """
            SELECT role, account_id, order_id, status, failure_reason
            FROM execution_batch_legs
            WHERE batch_id = ?
            ORDER BY sequence
            """,
            (batch_id,),
        ).fetchall()

    if batch is None:
        raise HTTPException(status_code=404, detail="Execution batch not found")

    return ExecutionBatchResponse(
        batchId=batch["id"],
        idempotencyKey=batch["idempotency_key"],
        strategyInstanceId=batch["strategy_instance_id"],
        accountId=batch["account_id"],
        strategyKey=batch["strategy_key"],
        direction=batch["direction"],
        status=batch["status"],
        requiresManualIntervention=bool(batch["requires_manual_intervention"]),
        failureReason=batch["failure_reason"],
        createdAt=batch["created_at"],
        updatedAt=batch["updated_at"],
        legs=[
            BatchLegResponse(
                role=row["role"],
                accountId=row["account_id"],
                orderId=row["order_id"],
                status=row["status"],
                failureReason=row["failure_reason"],
            )
            for row in legs
        ],
    )
