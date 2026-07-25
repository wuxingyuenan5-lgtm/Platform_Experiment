from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException

from app.database import connection
from app.execution_risk import (
    assert_execution_allowed,
    check_leg_deadline,
    complete_batch_risk,
    handle_batch_failure,
    initialize_batch_risk,
    record_filled_leg,
)
from app.schemas import (
    BatchLegResponse,
    CreateExecutionBatchRequest,
    CreateTradeCommandRequest,
    ExecutionBatchResponse,
)
from app.trade_commands import create_trade_command, validate_trade_command_catalog

CROSS_SPREAD_STRATEGY_KEY = "cross_venue_spread"
BYBIT_LEG_ROLE = "bybit_leg"
MT5_LEG_ROLE = "mt5_leg"


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
        raise HTTPException(
            status_code=422,
            detail="Execution batch requires strategyInstanceId",
        )

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


def create_execution_batch(request: CreateExecutionBatchRequest) -> ExecutionBatchResponse:
    if request.idempotency_key is None:
        raise HTTPException(
            status_code=422,
            detail="Execution batch requires idempotencyKey",
        )
    if request.strategy_instance_id is None:
        raise HTTPException(
            status_code=422,
            detail="Execution batch requires strategyInstanceId",
        )

    existing_batch_id = find_batch_by_idempotency_key(request.idempotency_key)
    if existing_batch_id is not None:
        assert_batch_request_matches(existing_batch_id, request)
        return get_execution_batch(existing_batch_id)

    strategy_key = resolve_strategy_key(request)
    default_account_id = request.account_id or request.legs[0].account_id
    if default_account_id is None:
        raise HTTPException(status_code=422, detail="Execution batch account is required")

    command_requests: list[tuple[str, CreateTradeCommandRequest]] = []
    account_ids: list[str] = []
    for leg in request.legs:
        leg_account_id = leg.account_id or default_account_id
        command_request = CreateTradeCommandRequest(
            idempotencyKey=f"{request.idempotency_key}:{leg.role}",
            strategyInstanceId=request.strategy_instance_id,
            accountId=leg_account_id,
            instrumentId=leg.instrument_id,
            symbol=leg.symbol,
            side=leg.side,
            orderType=leg.order_type,
            quantity=leg.quantity,
            price=leg.price,
        )
        validate_trade_command_catalog(command_request)
        command_requests.append((leg.role, command_request))
        account_ids.append(leg_account_id)

    assert_execution_allowed(request.strategy_instance_id, account_ids)

    batch_id = str(uuid4())
    created_at = now_iso()
    with connection() as db:
        cursor = db.execute(
            """
            INSERT OR IGNORE INTO execution_batches (
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
        if cursor.rowcount == 0:
            row = db.execute(
                "SELECT id FROM execution_batches WHERE idempotency_key = ?",
                (request.idempotency_key,),
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=409, detail="Execution batch claim failed")
            existing_id = row["id"]
        else:
            existing_id = None
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
                        leg.account_id or default_account_id,
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

    if existing_id is not None:
        assert_batch_request_matches(existing_id, request)
        return get_execution_batch(existing_id)

    initialize_batch_risk(batch_id, request.strategy_instance_id)
    update_batch_status(batch_id, "executing")
    filled_count = 0

    for index, (role, command_request) in enumerate(command_requests):
        if filled_count:
            deadline_ok, deadline_reason = check_leg_deadline(batch_id)
            if not deadline_ok:
                reason = deadline_reason or "Execution leg deadline exceeded"
                update_leg_status(batch_id, role, "blocked", failure_reason=reason)
                update_batch_status(
                    batch_id,
                    "manual_intervention",
                    failure_reason=reason,
                    requires_manual_intervention=True,
                )
                handle_batch_failure(batch_id, reason)
                return get_execution_batch(batch_id)

        try:
            assert_execution_allowed(request.strategy_instance_id, account_ids)
        except HTTPException as exc:
            reason = str(exc.detail)
            status = "manual_intervention" if filled_count else "failed"
            update_leg_status(batch_id, role, "blocked", failure_reason=reason)
            update_batch_status(
                batch_id,
                status,
                failure_reason=reason,
                requires_manual_intervention=status == "manual_intervention",
            )
            handle_batch_failure(batch_id, reason)
            return get_execution_batch(batch_id)

        update_leg_status(batch_id, role, "submitting")
        try:
            command = create_trade_command(command_request)
        except HTTPException as exc:
            reason = str(exc.detail)
            status = "manual_intervention" if filled_count else "failed"
            update_leg_status(batch_id, role, "failed", failure_reason=reason)
            update_batch_status(
                batch_id,
                status,
                failure_reason=reason,
                requires_manual_intervention=status == "manual_intervention",
            )
            handle_batch_failure(batch_id, reason)
            return get_execution_batch(batch_id)

        update_leg_status(
            batch_id,
            role,
            command.status,
            order_id=command.platform_order_id,
        )

        if command.status == "filled":
            if (
                strategy_key == CROSS_SPREAD_STRATEGY_KEY
                and role == BYBIT_LEG_ROLE
                and command.platform_order_id is not None
            ):
                try:
                    command_requests = resize_cross_spread_mt5_hedge(
                        command_requests,
                        bybit_index=index,
                        bybit_filled_quantity=get_order_filled_quantity(
                            command.platform_order_id
                        ),
                    )
                except ValueError as exc:
                    reason = str(exc)
                    update_leg_status(
                        batch_id,
                        MT5_LEG_ROLE,
                        "blocked",
                        failure_reason=reason,
                    )
                    update_batch_status(
                        batch_id,
                        "manual_intervention",
                        failure_reason=reason,
                        requires_manual_intervention=True,
                    )
                    handle_batch_failure(batch_id, reason)
                    return get_execution_batch(batch_id)

            filled_count += 1
            risk_ok, risk_reason = record_filled_leg(batch_id)
            if not risk_ok and filled_count < len(command_requests):
                reason = risk_reason or "Residual exposure policy blocked the next leg"
                update_batch_status(
                    batch_id,
                    "manual_intervention",
                    failure_reason=reason,
                    requires_manual_intervention=True,
                )
                handle_batch_failure(batch_id, reason)
                return get_execution_batch(batch_id)
            if filled_count < len(command_requests):
                update_batch_status(batch_id, "partially_executed")
            continue

        reason = f"Leg {role} completed with command status {command.status}"
        uncertain = command.status in {"accepted", "processing", "acknowledged", "result_unknown"}
        status = "manual_intervention" if filled_count or uncertain else "failed"
        update_leg_status(
            batch_id,
            role,
            command.status,
            order_id=command.platform_order_id,
            failure_reason=reason,
        )
        update_batch_status(
            batch_id,
            status,
            failure_reason=reason,
            requires_manual_intervention=status == "manual_intervention",
        )
        handle_batch_failure(batch_id, reason)
        return get_execution_batch(batch_id)

    risk = complete_batch_risk(batch_id)
    if risk.risk_status == "clear":
        update_batch_status(batch_id, "hedged")
    else:
        reason = risk.risk_reason or "Batch finished with unresolved residual exposure"
        update_batch_status(
            batch_id,
            "manual_intervention",
            failure_reason=reason,
            requires_manual_intervention=True,
        )
        handle_batch_failure(batch_id, reason)
    return get_execution_batch(batch_id)


def get_order_filled_quantity(order_id: str) -> Decimal:
    with connection() as db:
        rows = db.execute(
            "SELECT quantity FROM fills WHERE order_id = ? ORDER BY occurred_at, id",
            (order_id,),
        ).fetchall()
    return sum((Decimal(row["quantity"]) for row in rows), Decimal("0"))


def resize_cross_spread_mt5_hedge(
    command_requests: list[tuple[str, CreateTradeCommandRequest]],
    *,
    bybit_index: int,
    bybit_filled_quantity: Decimal,
) -> list[tuple[str, CreateTradeCommandRequest]]:
    if bybit_filled_quantity <= 0:
        raise ValueError("Confirmed Bybit fill quantity is unavailable; MT5 hedge is blocked")

    bybit_role, bybit_request = command_requests[bybit_index]
    if bybit_role != BYBIT_LEG_ROLE:
        raise ValueError("Cross-spread execution order must place the Bybit leg first")
    if bybit_filled_quantity > bybit_request.quantity:
        raise ValueError("Confirmed Bybit fill exceeds the requested quantity; MT5 hedge is blocked")

    mt5_index = next(
        (
            index
            for index, (role, _) in enumerate(command_requests)
            if role == MT5_LEG_ROLE
        ),
        None,
    )
    if mt5_index is None or mt5_index <= bybit_index:
        raise ValueError("Cross-spread MT5 hedge leg is missing or ordered before Bybit")

    mt5_role, mt5_request = command_requests[mt5_index]
    adjusted_quantity = (
        bybit_filled_quantity * mt5_request.quantity / bybit_request.quantity
    )
    validate_contract_quantity(
        adjusted_quantity,
        instrument_id=mt5_request.instrument_id,
        label=mt5_request.symbol,
    )

    command_requests[mt5_index] = (
        mt5_role,
        mt5_request.model_copy(update={"quantity": adjusted_quantity}),
    )
    return command_requests


def validate_contract_quantity(
    quantity: Decimal,
    *,
    instrument_id: str,
    label: str,
) -> None:
    with connection() as db:
        row = db.execute(
            """
            SELECT min_order_quantity, quantity_step
            FROM contract_specifications
            WHERE instrument_id = ?
            """,
            (instrument_id,),
        ).fetchone()
    if row is None:
        raise ValueError(f"{label} contract specification is unavailable")
    minimum = Decimal(row["min_order_quantity"])
    step = Decimal(row["quantity_step"])
    if quantity < minimum:
        raise ValueError(f"Confirmed Bybit fill is below the {label} hedge minimum")
    steps = (quantity - minimum) / step
    if steps != steps.to_integral_value():
        raise ValueError(f"Confirmed Bybit fill does not map to the {label} hedge step")


def assert_batch_request_matches(
    batch_id: str,
    request: CreateExecutionBatchRequest,
) -> None:
    with connection() as db:
        batch = db.execute(
            """
            SELECT strategy_instance_id, account_id, strategy_key, direction
            FROM execution_batches
            WHERE id = ?
            """,
            (batch_id,),
        ).fetchone()
        legs = db.execute(
            """
            SELECT role, account_id, instrument_id, symbol, side,
                   order_type, quantity, price
            FROM execution_batch_legs
            WHERE batch_id = ?
            """,
            (batch_id,),
        ).fetchall()

    if batch is None:
        raise HTTPException(status_code=409, detail="Existing execution batch is unavailable")

    default_account_id = request.account_id or request.legs[0].account_id
    batch_matches = (
        batch["strategy_instance_id"] == request.strategy_instance_id
        and batch["account_id"] == default_account_id
        and batch["strategy_key"] == request.strategy_key
        and batch["direction"] == request.direction
    )
    stored_legs = {row["role"]: row for row in legs}
    requested_roles = {leg.role for leg in request.legs}
    if not batch_matches or set(stored_legs) != requested_roles:
        raise_batch_idempotency_conflict()

    for leg in request.legs:
        row = stored_legs[leg.role]
        requested_account_id = leg.account_id or default_account_id
        stored_price = Decimal(row["price"]) if row["price"] is not None else None
        leg_matches = (
            row["account_id"] == requested_account_id
            and row["instrument_id"] == leg.instrument_id
            and row["symbol"] == leg.symbol
            and row["side"] == leg.side
            and row["order_type"] == leg.order_type
            and Decimal(row["quantity"]) == leg.quantity
            and stored_price == leg.price
        )
        if not leg_matches:
            raise_batch_idempotency_conflict()


def raise_batch_idempotency_conflict() -> None:
    raise HTTPException(
        status_code=409,
        detail="Idempotency key is already used by a different execution batch payload",
    )


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
