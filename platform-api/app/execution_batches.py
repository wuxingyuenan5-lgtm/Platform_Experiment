from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from sqlite3 import Connection, OperationalError
from typing import TypedDict
from uuid import uuid4

import httpx
from fastapi import HTTPException

from app import execution_risk_repository as risk_repository
from app.config import get_settings
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
GLOBAL_LEASE_STATUSES = (
    "pending",
    "executing",
    "partially_executed",
    "manual_intervention",
)
UNCERTAIN_EXTERNAL_LEG_STATUSES = (
    "submitting",
    "accepted",
    "processing",
    "acknowledged",
    "result_unknown",
)
LEASE_RELEASED_BATCH_STATUSES = (
    "hedged",
    "completed",
)
INSTRUMENT_TYPE_ALIASES = {
    "spot": "crypto_spot",
    "crypto_spot": "crypto_spot",
    "perp": "crypto_perp",
    "crypto_perp": "crypto_perp",
}


class BlockingBatchLeg(TypedDict):
    account_id: str
    symbol: str
    leg_status: str


class BlockingBatch(TypedDict):
    id: str
    status: str
    account_id: str
    legs: list[BlockingBatchLeg]


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def normalize_instrument_type(instrument_type: str) -> str:
    return INSTRUMENT_TYPE_ALIASES.get(instrument_type.strip().lower(), instrument_type.strip())


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
    execute_batch_id: str | None = None
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute(
            "SELECT id, status FROM execution_batches WHERE idempotency_key = ?",
            (request.idempotency_key,),
        ).fetchone()
        if existing is not None:
            existing_id = existing["id"]
            assert_batch_request_matches_in_connection(db, existing_id, request)
            if existing["status"] == "pending":
                _claim_batch_execution_resources(
                    db,
                    batch_id=existing_id,
                    strategy_instance_id=request.strategy_instance_id,
                    legs=request.legs,
                    default_account_id=default_account_id,
                )
                claimed = db.execute(
                    """
                    UPDATE execution_batches
                    SET status = 'executing', updated_at = ?
                    WHERE id = ? AND status = 'pending'
                    """,
                    (created_at, existing_id),
                )
                if claimed.rowcount == 1:
                    execute_batch_id = existing_id
        else:
            blocking_batch = _find_blocking_batch_for_resources(
                db,
                [(leg.account_id or default_account_id, leg.symbol) for leg in request.legs],
            )
            if blocking_batch is not None:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Active execution batch blocks new strategy instruction: "
                        f"{blocking_batch['id']} ({blocking_batch['status']})"
                    ),
                )
            existing_id = None
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
            _claim_batch_execution_resources(
                db,
                batch_id=batch_id,
                strategy_instance_id=request.strategy_instance_id,
                legs=request.legs,
                default_account_id=default_account_id,
            )
            claimed = db.execute(
                """
                UPDATE execution_batches
                SET status = 'executing', updated_at = ?
                WHERE id = ? AND status = 'pending'
                """,
                (created_at, batch_id),
            )
            if claimed.rowcount != 1:
                raise HTTPException(
                    status_code=409,
                    detail="New execution batch could not be claimed for dispatch",
                )
            execute_batch_id = batch_id

    if execute_batch_id is None:
        assert existing_id is not None
        return get_execution_batch(existing_id)

    batch_id = execute_batch_id
    initialize_batch_risk(batch_id, request.strategy_instance_id)
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
            unknown_order_id = _result_unknown_order_for_command(
                command_request.idempotency_key
            )
            if unknown_order_id is not None:
                update_leg_status(
                    batch_id,
                    role,
                    "result_unknown",
                    order_id=unknown_order_id,
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


def _result_unknown_order_for_command(idempotency_key: str) -> str | None:
    """Preserve an order's unknown external result when command dispatch raises."""
    with connection() as db:
        row = db.execute(
            """
            SELECT o.id
            FROM trade_commands AS command
            JOIN orders AS o ON o.command_id = command.id
            WHERE command.idempotency_key = ? AND o.status = 'result_unknown'
            """,
            (idempotency_key,),
        ).fetchone()
        if row is not None:
            db.execute(
                """
                UPDATE trade_commands SET status = 'result_unknown', updated_at = ?
                WHERE idempotency_key = ?
                """,
                (now_iso(), idempotency_key),
            )
    return row["id"] if row is not None else None


def _find_blocking_batch_for_accounts(
    db: Connection,
    account_ids: list[str],
):
    requested_accounts = tuple(dict.fromkeys(account_ids))
    if not requested_accounts:
        return None
    placeholders = ", ".join("?" for _ in requested_accounts)
    parameters = (
        *requested_accounts,
        *GLOBAL_LEASE_STATUSES,
        *LEASE_RELEASED_BATCH_STATUSES,
        *requested_accounts,
        *UNCERTAIN_EXTERNAL_LEG_STATUSES,
    )
    return db.execute(
        f"""
        SELECT batch.id, batch.status
        FROM execution_batches AS batch
        WHERE (
                batch.account_id IN ({placeholders})
                AND batch.status IN (?, ?, ?, ?)
            )
           OR EXISTS (
                SELECT 1
                FROM execution_batch_legs AS leg
                WHERE leg.batch_id = batch.id
                  AND batch.status NOT IN (?, ?)
                  AND leg.account_id IN ({placeholders})
                  AND leg.status IN (?, ?, ?, ?, ?)
           )
        ORDER BY batch.created_at, batch.id
        LIMIT 1
        """,
        parameters,
    ).fetchone()


def _find_blocking_batch_for_resources(
    db: Connection,
    resources: list[tuple[str, str]],
) -> BlockingBatch | None:
    requested = {(account_id, symbol.upper()) for account_id, symbol in resources}
    if not requested:
        return None
    rows = db.execute(
        """
        SELECT batch.id, batch.status, batch.account_id,
               leg.account_id AS leg_account_id, leg.symbol, leg.status AS leg_status
        FROM execution_batches AS batch
        JOIN execution_batch_legs AS leg ON leg.batch_id = batch.id
        ORDER BY batch.created_at, batch.id, leg.sequence
        """
    ).fetchall()
    grouped: dict[str, BlockingBatch] = {}
    for row in rows:
        batch_id = str(row["id"])
        batch = grouped.setdefault(
            batch_id,
            {
                "id": batch_id,
                "status": str(row["status"]),
                "account_id": str(row["account_id"]),
                "legs": [],
            },
        )
        batch["legs"].append(
            {
                "account_id": str(row["leg_account_id"]),
                "symbol": str(row["symbol"]).upper(),
                "leg_status": str(row["leg_status"]),
            }
        )
    for batch in grouped.values():
        batch_status = str(batch["status"])
        account_id = str(batch["account_id"])
        legs = batch["legs"]
        if batch_status in GLOBAL_LEASE_STATUSES:
            if any((str(leg["account_id"]), str(leg["symbol"])) in requested for leg in legs):
                return batch
            continue
        if batch_status == "failed":
            if any(
                str(leg["leg_status"]) in UNCERTAIN_EXTERNAL_LEG_STATUSES
                and (str(leg["account_id"]), str(leg["symbol"])) in requested
                for leg in legs
            ):
                return batch
            if any(
                str(leg["leg_status"]) == "result_unknown"
                and account_id == account
                for account, _symbol in requested
                for leg in legs
            ):
                return batch
    return None


def _claim_batch_execution_resources(
    db: Connection,
    *,
    batch_id: str,
    strategy_instance_id: str,
    legs,
    default_account_id: str,
) -> None:
    resources: dict[str, tuple[str, str, str, str]] = {}
    reservation_keys: set[tuple[str, str]] = set()
    prepared_legs = []
    reservation_timestamps = now_iso()
    for leg in legs:
        account_id = leg.account_id or default_account_id
        spec = db.execute(
            """
            SELECT account.venue_id,
                   instrument.instrument_type,
                   instrument.base_currency,
                   instrument.quote_currency,
                   specification.contract_multiplier
            FROM accounts AS account
            JOIN instruments AS instrument ON instrument.id = ?
            LEFT JOIN contract_specifications AS specification
              ON specification.instrument_id = instrument.id
            WHERE account.id = ?
            """,
            (leg.instrument_id, account_id),
        ).fetchone()
        if spec is None:
            raise HTTPException(
                status_code=409,
                detail="Execution resource metadata is unavailable",
            )
        normalized_type = normalize_instrument_type(str(spec["instrument_type"]))
        resource_key = f"{account_id}|{spec['venue_id']}|{normalized_type}|{leg.symbol.upper()}"
        resources[resource_key] = (
            account_id,
            str(spec["venue_id"]),
            normalized_type,
            leg.symbol.upper(),
        )
        base_currency = str(spec["base_currency"])
        quote_currency = str(spec["quote_currency"])
        reservation_keys.add(
            (
                account_id,
                base_currency
                if normalized_type == "crypto_spot" and leg.side == "sell"
                else quote_currency,
            )
        )
        prepared_legs.append(
            (
                leg,
                account_id,
                normalized_type,
                base_currency,
                quote_currency,
                (
                    Decimal(str(spec["contract_multiplier"]))
                    if spec["contract_multiplier"] is not None
                    else None
                ),
            )
        )

    existing_claims = db.execute(
        """
        SELECT resource_key, account_id, venue_id, resource_category, symbol, status
        FROM execution_resource_claims
        WHERE owner_type = 'batch' AND owner_id = ?
        """,
        (batch_id,),
    ).fetchall()
    existing_reservations = db.execute(
        """
        SELECT account_id, strategy_instance_id, currency, reserved_amount, status
        FROM execution_balance_reservations
        WHERE owner_type = 'batch' AND owner_id = ?
        """,
        (batch_id,),
    ).fetchall()
    if existing_claims or existing_reservations:
        persisted_claims = {
            str(row["resource_key"]): (
                str(row["account_id"]),
                str(row["venue_id"]),
                str(row["resource_category"]),
                str(row["symbol"]),
                str(row["status"]),
            )
            for row in existing_claims
        }
        expected_claims = {
            key: (*value, "active") for key, value in resources.items()
        }
        persisted_reservations = {
            (str(row["account_id"]), str(row["currency"])): (
                str(row["strategy_instance_id"]),
                str(row["status"]),
            )
            for row in existing_reservations
        }
        expected_reservations = {
            key: (strategy_instance_id, "active") for key in reservation_keys
        }
        if (
            len(existing_claims) == len(expected_claims)
            and len(existing_reservations) == len(expected_reservations)
            and persisted_claims == expected_claims
            and persisted_reservations == expected_reservations
            and all(
                Decimal(str(row["reserved_amount"])) > 0
                for row in existing_reservations
            )
        ):
            return
        raise HTTPException(
            status_code=409,
            detail="Execution batch claims or balance reservations are incomplete",
        )

    reservations: dict[tuple[str, str], Decimal] = {}
    for (
        leg,
        account_id,
        normalized_type,
        base_currency,
        quote_currency,
        contract_multiplier,
    ) in prepared_legs:
        reservation_key, amount = _reservation_requirement_for_leg(
            leg,
            account_id=account_id,
            instrument_type=normalized_type,
            base_currency=base_currency,
            quote_currency=quote_currency,
            contract_multiplier=contract_multiplier,
        )
        reservations[reservation_key] = reservations.get(reservation_key, Decimal("0")) + amount

    for resource_key, (account_id, venue_id, category, symbol) in resources.items():
        blocking_claim = risk_repository.active_claim_for_resource(
            resource_key,
            account_id=account_id,
            db=db,
        )
        if blocking_claim is not None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Active execution resource claim blocks new strategy instruction: "
                    f"{blocking_claim['resource_key']}"
                ),
            )
        db.execute(
            """
            INSERT INTO execution_resource_claims (
                id, resource_key, owner_type, owner_id, account_id, venue_id,
                resource_category, symbol, status, created_at, updated_at
            ) VALUES (?, ?, 'batch', ?, ?, ?, ?, ?, 'active', ?, ?)
            """,
            (
                str(uuid4()),
                resource_key,
                batch_id,
                account_id,
                venue_id,
                category,
                symbol,
                reservation_timestamps,
                reservation_timestamps,
            ),
        )

    for (account_id, currency), amount in reservations.items():
        available = _latest_available_balance(db, account_id=account_id, currency=currency)
        if available is None:
            raise HTTPException(
                status_code=409,
                detail=f"Available balance evidence is unavailable for {account_id} {currency}",
            )
        active_reserved = risk_repository.active_reserved_amount(account_id, currency, db=db)
        if active_reserved + amount > available:
            raise HTTPException(
                status_code=409,
                detail=f"Available balance reservation is insufficient for {account_id} {currency}",
            )
        db.execute(
            """
            INSERT INTO execution_balance_reservations (
                id, owner_type, owner_id, account_id, strategy_instance_id, instruction_id,
                currency, reserved_amount, status, created_at, updated_at
            ) VALUES (?, 'batch', ?, ?, ?, NULL, ?, ?, 'active', ?, ?)
            """,
            (
                str(uuid4()),
                batch_id,
                account_id,
                strategy_instance_id,
                currency,
                format(amount, "f"),
                reservation_timestamps,
                reservation_timestamps,
            ),
        )


def _reservation_requirement_for_leg(
    leg,
    *,
    account_id: str,
    instrument_type: str,
    base_currency: str,
    quote_currency: str,
    contract_multiplier: Decimal | None,
) -> tuple[tuple[str, str], Decimal]:
    normalized_type = normalize_instrument_type(instrument_type)
    if normalized_type == "crypto_spot" and leg.side == "sell":
        return (account_id, base_currency), leg.quantity
    reference_price = leg.price or _reservation_reference_price(
        account_id=account_id,
        symbol=leg.symbol,
        side=leg.side,
    )
    if normalized_type == "crypto_spot":
        return (account_id, quote_currency), leg.quantity * reference_price
    multiplier = contract_multiplier or Decimal("1")
    return (account_id, quote_currency), leg.quantity * reference_price * multiplier


def _reservation_reference_price(
    *,
    account_id: str,
    symbol: str,
    side: str,
) -> Decimal:
    settings = get_settings()
    try:
        with httpx.Client(
            trust_env=False,
            timeout=settings.runtime_timeout_seconds,
        ) as client:
            response = client.get(
                f"{settings.runtime_base_url}/venue/quotes/{symbol}",
                params={"accountId": account_id},
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"Reference price is unavailable for reservation of {symbol}",
        ) from exc
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=409,
            detail=f"Reference price is unavailable for reservation of {symbol}",
        )
    field = "ask" if side == "buy" else "bid"
    fallback_field = "bid" if field == "ask" else "ask"
    raw = payload.get(field)
    if raw is None:
        raw = payload.get(fallback_field)
    try:
        price = Decimal(str(raw))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=409,
            detail=f"Reference price is unavailable for reservation of {symbol}",
        ) from exc
    if price <= 0:
        raise HTTPException(
            status_code=409,
            detail=f"Reference price is unavailable for reservation of {symbol}",
        )
    return price


def _latest_available_balance(
    db: Connection,
    *,
    account_id: str,
    currency: str,
) -> Decimal | None:
    row = db.execute(
        """
        SELECT available_balance
        FROM balance_snapshots
        WHERE account_id = ? AND currency = ? AND data_quality_state = 'complete'
        ORDER BY as_of DESC
        LIMIT 1
        """,
        (account_id, currency),
    ).fetchone()
    if row is None:
        return None
    return Decimal(str(row["available_balance"]))


def _release_batch_claims_and_reservations_if_safe(batch_id: str, status: str) -> None:
    if status in LEASE_RELEASED_BATCH_STATUSES:
        with connection() as db:
            if not _batch_terminal_release_is_safe(db, batch_id=batch_id, status=status):
                return
            risk_repository.release_claims_for_owner("batch", batch_id, db=db)
            risk_repository.release_reservations_for_owner("batch", batch_id, db=db)
        return
    if status != "failed":
        return
    with connection() as db:
        has_external_orders = db.execute(
            """
            SELECT 1
            FROM execution_batch_legs
            WHERE batch_id = ? AND order_id IS NOT NULL
            LIMIT 1
            """,
            (batch_id,),
        ).fetchone()
        has_fills = db.execute(
            """
            SELECT 1
            FROM fills
            WHERE order_id IN (
                SELECT order_id FROM execution_batch_legs WHERE batch_id = ?
            )
            LIMIT 1
            """,
            (batch_id,),
        ).fetchone()
        if has_external_orders is None and has_fills is None:
            risk_repository.release_claims_for_owner("batch", batch_id, db=db)
            risk_repository.release_reservations_for_owner("batch", batch_id, db=db)


def _batch_terminal_release_is_safe(
    db: Connection,
    *,
    batch_id: str,
    status: str,
) -> bool:
    if status not in LEASE_RELEASED_BATCH_STATUSES:
        return False
    try:
        row = db.execute(
            """
            SELECT batch.strategy_key,
                   batch.strategy_instruction_id,
                   instruction.status AS instruction_status
            FROM execution_batches AS batch
            LEFT JOIN strategy_runs AS instruction
              ON instruction.id = batch.strategy_instruction_id
            WHERE batch.id = ?
            """,
            (batch_id,),
        ).fetchone()
    except OperationalError as exc:
        if "strategy_instruction_id" in str(exc):
            return _legacy_batch_terminal_release_is_safe(db, batch_id=batch_id, status=status)
        raise
    if row is None:
        return False
    if row["strategy_instruction_id"] is None:
        return True
    if row["strategy_key"] != "funding_arbitrage":
        return True
    return row["instruction_status"] == "completed"


def _legacy_batch_terminal_release_is_safe(
    db: Connection,
    *,
    batch_id: str,
    status: str,
) -> bool:
    if status not in LEASE_RELEASED_BATCH_STATUSES:
        return False
    row = db.execute(
        """
        SELECT strategy_key, status
        FROM execution_batches
        WHERE id = ?
        """,
        (batch_id,),
    ).fetchone()
    if row is None:
        return False
    persisted_status = str(row["status"])
    if persisted_status not in LEASE_RELEASED_BATCH_STATUSES:
        return False
    if row["strategy_key"] == "funding_arbitrage":
        return persisted_status == "completed"
    return True


def complete_funding_reconciliation(batch_id: str, instruction_id: str) -> None:
    """Atomically complete Funding truth and release its shared-account resources."""

    timestamp = now_iso()
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            """
            SELECT batch.status AS batch_status,
                   batch.strategy_key,
                   batch.strategy_instruction_id,
                   instruction.status AS instruction_status
            FROM execution_batches AS batch
            JOIN strategy_runs AS instruction
              ON instruction.id = batch.strategy_instruction_id
            WHERE batch.id = ? AND instruction.id = ?
            """,
            (batch_id, instruction_id),
        ).fetchone()
        if row is None or row["strategy_key"] != "funding_arbitrage":
            raise HTTPException(
                status_code=409,
                detail="Funding reconciliation identity is invalid",
            )
        if row["batch_status"] == "completed" and row["instruction_status"] == "completed":
            risk_repository.release_claims_for_owner("batch", batch_id, db=db)
            risk_repository.release_reservations_for_owner("batch", batch_id, db=db)
            return
        if row["batch_status"] != "hedged" or row["instruction_status"] != "reconciling":
            raise HTTPException(
                status_code=409,
                detail="Funding reconciliation is not ready for completion",
            )
        db.execute(
            """
            UPDATE strategy_runs
            SET status = 'completed', failure_reason = NULL, updated_at = ?
            WHERE id = ? AND status = 'reconciling'
            """,
            (timestamp, instruction_id),
        )
        db.execute(
            """
            UPDATE execution_batches
            SET status = 'completed', requires_manual_intervention = 0,
                failure_reason = NULL, updated_at = ?
            WHERE id = ? AND status = 'hedged'
            """,
            (timestamp, batch_id),
        )
        db.execute(
            """
            UPDATE execution_batch_legs
            SET status = 'filled', failure_reason = NULL, updated_at = ?
            WHERE batch_id = ? AND order_id IS NOT NULL
              AND status IN (?, ?, ?, ?, ?)
            """,
            (timestamp, batch_id, *UNCERTAIN_EXTERNAL_LEG_STATUSES),
        )
        risk_repository.release_claims_for_owner("batch", batch_id, db=db)
        risk_repository.release_reservations_for_owner("batch", batch_id, db=db)


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
        raise ValueError(
            "Confirmed Bybit fill exceeds the requested quantity; MT5 hedge is blocked"
        )

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
        assert_batch_request_matches_in_connection(db, batch_id, request)


def assert_batch_request_matches_in_connection(
    db: Connection,
    batch_id: str,
    request: CreateExecutionBatchRequest,
) -> None:
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
        SELECT sequence, role, account_id, instrument_id, symbol, side,
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

    for sequence, leg in enumerate(request.legs, start=1):
        row = stored_legs[leg.role]
        requested_account_id = leg.account_id or default_account_id
        stored_price = Decimal(row["price"]) if row["price"] is not None else None
        leg_matches = (
            row["sequence"] == sequence
            and row["account_id"] == requested_account_id
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
        updated_at = now_iso()
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
                updated_at,
                batch_id,
            ),
        )
        if status in LEASE_RELEASED_BATCH_STATUSES:
            db.execute(
                """
                UPDATE execution_batch_legs
                SET status = 'filled',
                    failure_reason = NULL,
                    updated_at = ?
                WHERE batch_id = ?
                  AND order_id IS NOT NULL
                  AND status IN (?, ?, ?, ?, ?)
                """,
                (
                    updated_at,
                    batch_id,
                    *UNCERTAIN_EXTERNAL_LEG_STATUSES,
                ),
            )
    _release_batch_claims_and_reservations_if_safe(batch_id, status)


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
