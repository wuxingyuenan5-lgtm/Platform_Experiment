from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.database import connection
from app.schemas import (
    BatchLegResponse,
    CreateExecutionBatchRequest,
    CreateTradeCommandRequest,
    ExecutionBatchResponse,
    ExecutionDispositionRequest,
    ExecutionDispositionResponse,
    KillSwitchRequest,
    KillSwitchResponse,
)
from app.trade_commands import create_trade_command, validate_trade_command_catalog

router = APIRouter(prefix=get_settings().api_prefix)

SCHEMA = """
CREATE TABLE IF NOT EXISTS trading_kill_switches (
    scope_type TEXT NOT NULL,
    scope_id TEXT NOT NULL,
    engaged INTEGER NOT NULL,
    reason TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(scope_type, scope_id)
);
CREATE TABLE IF NOT EXISTS execution_batch_risk_profiles (
    batch_id TEXT PRIMARY KEY,
    max_leg_delay_ms INTEGER NOT NULL,
    max_residual_notional TEXT NOT NULL,
    allow_partial_fill INTEGER NOT NULL,
    emergency_flatten INTEGER NOT NULL,
    disposition_policy TEXT NOT NULL,
    risk_state TEXT NOT NULL,
    residual_notional TEXT NOT NULL,
    disposition_status TEXT,
    kill_switch_engaged INTEGER NOT NULL,
    first_fill_at TEXT
);
CREATE TABLE IF NOT EXISTS execution_batch_leg_metrics (
    batch_id TEXT NOT NULL,
    role TEXT NOT NULL,
    filled_quantity TEXT,
    average_fill_price TEXT,
    contract_multiplier TEXT NOT NULL,
    time_in_force TEXT NOT NULL,
    reduce_only INTEGER NOT NULL,
    position_idx INTEGER NOT NULL,
    max_deviation INTEGER,
    allow_partial_fill INTEGER NOT NULL,
    max_slippage_bps TEXT,
    base_exposure TEXT NOT NULL,
    notional TEXT NOT NULL,
    repair_order_id TEXT,
    repair_status TEXT,
    PRIMARY KEY(batch_id, role)
);
CREATE TABLE IF NOT EXISTS execution_dispositions (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    batch_id TEXT NOT NULL,
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    details_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def decimal_text(value: Decimal) -> str:
    return format(value, "f")


def ensure_schema() -> None:
    with connection() as db:
        db.executescript(SCHEMA)
        db.execute(
            """
            INSERT OR IGNORE INTO trading_kill_switches
                (scope_type, scope_id, engaged, reason, updated_at)
            VALUES ('global', 'global', 0, 'default safe state', ?)
            """,
            (now_iso(),),
        )


def set_kill_switch(
    scope_type: str, scope_id: str, request: KillSwitchRequest
) -> KillSwitchResponse:
    ensure_schema()
    if scope_type not in {"global", "strategy", "account"}:
        raise HTTPException(status_code=422, detail="Unsupported kill switch scope")
    updated_at = now_iso()
    with connection() as db:
        db.execute(
            """
            INSERT INTO trading_kill_switches
                (scope_type, scope_id, engaged, reason, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(scope_type, scope_id) DO UPDATE SET
                engaged = excluded.engaged,
                reason = excluded.reason,
                updated_at = excluded.updated_at
            """,
            (scope_type, scope_id, int(request.engaged), request.reason, updated_at),
        )
        db.execute(
            """
            INSERT INTO audit_events
                (id, event_type, subject_type, subject_id, details_json, created_at)
            VALUES (?, 'kill_switch_changed', ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                scope_type,
                scope_id,
                json.dumps({"engaged": request.engaged, "reason": request.reason}, sort_keys=True),
                updated_at,
            ),
        )
    return get_kill_switch(scope_type, scope_id)


def get_kill_switch(scope_type: str, scope_id: str) -> KillSwitchResponse:
    ensure_schema()
    with connection() as db:
        row = db.execute(
            "SELECT * FROM trading_kill_switches WHERE scope_type = ? AND scope_id = ?",
            (scope_type, scope_id),
        ).fetchone()
    if row is None:
        return KillSwitchResponse(
            scopeType=scope_type,
            scopeId=scope_id,
            engaged=False,
            reason=None,
            updatedAt=now_iso(),
        )
    return KillSwitchResponse(
        scopeType=row["scope_type"],
        scopeId=row["scope_id"],
        engaged=bool(row["engaged"]),
        reason=row["reason"],
        updatedAt=row["updated_at"],
    )


def enforce_gate(strategy_id: str, account_ids: list[str]) -> None:
    ensure_schema()
    settings = get_settings()
    scopes = [("global", "global"), ("strategy", strategy_id)] + [
        ("account", account_id) for account_id in account_ids
    ]
    with connection() as db:
        switches = db.execute("SELECT * FROM trading_kill_switches WHERE engaged = 1").fetchall()
        active = {(row["scope_type"], row["scope_id"]): row for row in switches}
        placeholders = ",".join("?" for _ in account_ids)
        accounts = db.execute(
            f"SELECT id, environment, status FROM accounts WHERE id IN ({placeholders})",
            tuple(account_ids),
        ).fetchall()
    for scope in scopes:
        if scope in active:
            raise HTTPException(
                status_code=423, detail=f"Execution blocked by {scope[0]} kill switch"
            )
    if len(accounts) != len(set(account_ids)):
        raise HTTPException(status_code=422, detail="Execution account is unavailable")
    for account in accounts:
        if account["status"] != "active":
            raise HTTPException(status_code=403, detail="Execution account is inactive")
        if account["environment"] == "live":
            raise HTTPException(status_code=403, detail="Phase 4 refuses Live execution")
        if account["environment"] in {"demo", "testnet"} and not settings.demo_trading_enabled:
            raise HTTPException(status_code=403, detail="Demo execution is disabled")


def create_execution_batch(request: CreateExecutionBatchRequest) -> ExecutionBatchResponse:
    ensure_schema()
    if request.idempotency_key is None or request.strategy_instance_id is None:
        raise HTTPException(status_code=422, detail="Execution batch identity is required")
    existing = find_batch(request.idempotency_key)
    if existing:
        assert_batch_request_matches(existing, request)
        return get_execution_batch(existing)
    account_ids = [leg.account_id or request.account_id for leg in request.legs]
    if any(account_id is None for account_id in account_ids):
        raise HTTPException(status_code=422, detail="Every leg requires accountId")
    account_ids = [str(value) for value in account_ids]
    enforce_gate(request.strategy_instance_id, account_ids)
    if strategy_key(request.strategy_instance_id) != request.strategy_key:
        raise HTTPException(status_code=422, detail="Strategy key mismatch")

    prepared = []
    for leg, account_id in zip(request.legs, account_ids, strict=True):
        command = CreateTradeCommandRequest(
            idempotencyKey=f"{request.idempotency_key}:{leg.role}",
            strategyInstanceId=request.strategy_instance_id,
            accountId=account_id,
            instrumentId=leg.instrument_id,
            symbol=leg.symbol,
            side=leg.side,
            orderType=leg.order_type,
            quantity=leg.quantity,
            price=leg.price,
            timeInForce=leg.time_in_force,
            reduceOnly=leg.reduce_only,
            positionIdx=leg.position_idx,
            maxDeviation=leg.max_deviation,
            allowPartialFill=request.allow_partial_fill and leg.allow_partial_fill,
            maxSlippageBps=leg.max_slippage_bps,
        )
        validate_trade_command_catalog(command)
        prepared.append((leg, command, multiplier(leg.instrument_id)))

    batch_id = str(uuid4())
    created = now_iso()
    with connection() as db:
        db.execute(
            """
            INSERT INTO execution_batches (
                id, idempotency_key, strategy_instance_id, account_id,
                strategy_key, direction, status, requires_manual_intervention,
                failure_reason, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'pending', 0, NULL, ?, ?)
            """,
            (
                batch_id,
                request.idempotency_key,
                request.strategy_instance_id,
                account_ids[0],
                request.strategy_key,
                request.direction,
                created,
                created,
            ),
        )
        db.execute(
            """
            INSERT INTO execution_batch_risk_profiles (
                batch_id, max_leg_delay_ms, max_residual_notional,
                allow_partial_fill, emergency_flatten, disposition_policy,
                risk_state, residual_notional, disposition_status,
                kill_switch_engaged, first_fill_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'none', '0', NULL, 0, NULL)
            """,
            (
                batch_id,
                request.max_leg_delay_ms,
                decimal_text(request.max_residual_notional),
                int(request.allow_partial_fill),
                int(request.emergency_flatten),
                request.disposition_policy,
            ),
        )
        for sequence, ((leg, _, contract_multiplier), account_id) in enumerate(
            zip(prepared, account_ids, strict=True), start=1
        ):
            db.execute(
                """
                INSERT INTO execution_batch_legs (
                    id, batch_id, sequence, role, account_id, instrument_id,
                    symbol, side, order_type, quantity, price, order_id,
                    status, failure_reason, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, 'pending', NULL, ?, ?)
                """,
                (
                    str(uuid4()),
                    batch_id,
                    sequence,
                    leg.role,
                    account_id,
                    leg.instrument_id,
                    leg.symbol,
                    leg.side,
                    leg.order_type,
                    decimal_text(leg.quantity),
                    decimal_text(leg.price) if leg.price is not None else None,
                    created,
                    created,
                ),
            )
            db.execute(
                """
                INSERT INTO execution_batch_leg_metrics (
                    batch_id, role, filled_quantity, average_fill_price,
                    contract_multiplier, time_in_force, reduce_only,
                    position_idx, max_deviation, allow_partial_fill,
                    max_slippage_bps, base_exposure, notional,
                    repair_order_id, repair_status
                ) VALUES (?, ?, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, '0', '0', NULL, NULL)
                """,
                (
                    batch_id,
                    leg.role,
                    decimal_text(contract_multiplier),
                    leg.time_in_force,
                    int(leg.reduce_only),
                    leg.position_idx,
                    leg.max_deviation,
                    int(request.allow_partial_fill and leg.allow_partial_fill),
                    decimal_text(leg.max_slippage_bps)
                    if leg.max_slippage_bps is not None
                    else None,
                ),
            )

    update_batch(batch_id, "executing")
    filled_roles: list[str] = []
    first_fill_time: float | None = None
    reason: str | None = None
    for leg, command_request, contract_multiplier in prepared:
        if first_fill_time is not None:
            elapsed = int((time.monotonic() - first_fill_time) * 1000)
            if elapsed > request.max_leg_delay_ms:
                reason = f"Maximum leg delay exceeded before {leg.role}"
                update_leg(batch_id, leg.role, "skipped", reason=reason)
                break
        update_leg(batch_id, leg.role, "submitting")
        try:
            command = create_trade_command(command_request)
        except HTTPException as exc:
            reason = str(exc.detail)
            update_leg(batch_id, leg.role, "failed", reason=reason)
            break
        update_leg(batch_id, leg.role, command.status, order_id=command.platform_order_id)
        quantity, price = order_fill(command.platform_order_id)
        if quantity is not None:
            record_metrics(batch_id, leg.role, leg.side, quantity, price, contract_multiplier)
            filled_roles.append(leg.role)
            first_fill_time = first_fill_time or time.monotonic()
            if quantity < command_request.quantity and not request.allow_partial_fill:
                reason = f"Partial fill forbidden for {leg.role}"
        if command.status != "filled" or reason:
            reason = reason or f"Leg {leg.role} ended with {command.status}"
            break
        if len(filled_roles) < len(prepared):
            update_batch(batch_id, "partially_executed")

    if reason is None and len(filled_roles) == len(prepared):
        residual = residual_notional(batch_id)
        if residual <= request.max_residual_notional:
            update_risk(batch_id, "hedged", residual)
            update_batch(batch_id, "hedged")
            return get_execution_batch(batch_id)
        reason = "Residual exposure exceeds threshold"

    if not filled_roles:
        update_batch(batch_id, "failed", reason=reason)
        return get_execution_batch(batch_id)

    residual = residual_notional(batch_id)
    update_risk(batch_id, "residual_exposure", residual)
    if request.emergency_flatten and request.disposition_policy == "flatten_filled_legs":
        update_batch(batch_id, "compensating", reason=reason)
        if compensate(batch_id, request.idempotency_key):
            update_risk(batch_id, "resolved_by_flatten", Decimal("0"), "completed")
            update_batch(batch_id, "compensated", reason=reason)
            return get_execution_batch(batch_id)

    set_kill_switch(
        "strategy",
        request.strategy_instance_id,
        KillSwitchRequest(engaged=True, reason=f"Automatic risk stop: {reason}"),
    )
    update_risk(batch_id, "unresolved", residual, "action_required", True)
    update_batch(batch_id, "risk_unresolved", reason=reason, manual=True)
    return get_execution_batch(batch_id)


def compensate(batch_id: str, batch_key: str) -> bool:
    with connection() as db:
        rows = db.execute(
            """
            SELECT l.role, l.account_id, l.instrument_id, l.symbol, l.side,
                   m.filled_quantity
            FROM execution_batch_legs l
            JOIN execution_batch_leg_metrics m
              ON m.batch_id = l.batch_id AND m.role = l.role
            WHERE l.batch_id = ? AND m.filled_quantity IS NOT NULL
            ORDER BY l.sequence DESC
            """,
            (batch_id,),
        ).fetchall()
        strategy_id = db.execute(
            "SELECT strategy_instance_id FROM execution_batches WHERE id = ?",
            (batch_id,),
        ).fetchone()["strategy_instance_id"]
    success = bool(rows)
    for row in rows:
        request = CreateTradeCommandRequest(
            idempotencyKey=f"{batch_key}:repair:{row['role']}",
            strategyInstanceId=strategy_id,
            accountId=row["account_id"],
            instrumentId=row["instrument_id"],
            symbol=row["symbol"],
            side="sell" if row["side"] == "buy" else "buy",
            orderType="market",
            quantity=Decimal(row["filled_quantity"]),
            timeInForce="FOK",
            reduceOnly=True,
            allowPartialFill=False,
        )
        try:
            command = create_trade_command(request)
            repaired = command.status == "filled"
            with connection() as db:
                db.execute(
                    """
                    UPDATE execution_batch_leg_metrics
                    SET repair_order_id = ?, repair_status = ?
                    WHERE batch_id = ? AND role = ?
                    """,
                    (command.platform_order_id, command.status, batch_id, row["role"]),
                )
            success = success and repaired
        except Exception as exc:
            with connection() as db:
                db.execute(
                    """
                    UPDATE execution_batch_leg_metrics SET repair_status = ?
                    WHERE batch_id = ? AND role = ?
                    """,
                    (f"failed:{type(exc).__name__}", batch_id, row["role"]),
                )
            success = False
    return success


def apply_disposition(
    batch_id: str, request: ExecutionDispositionRequest
) -> ExecutionDispositionResponse:
    ensure_schema()
    with connection() as db:
        existing = db.execute(
            "SELECT * FROM execution_dispositions WHERE idempotency_key = ?",
            (request.idempotency_key,),
        ).fetchone()
    if existing is not None:
        if existing["batch_id"] != batch_id or existing["action"] != request.action:
            raise HTTPException(status_code=409, detail="Disposition idempotency conflict")
        return disposition_response(existing)
    batch = get_execution_batch(batch_id)
    status = "recorded"
    if request.action == "flatten_filled_legs":
        status = (
            "completed" if compensate(batch_id, batch.idempotency_key or batch_id) else "failed"
        )
        if status == "completed":
            update_risk(batch_id, "resolved_by_flatten", Decimal("0"), "completed")
            update_batch(batch_id, "compensated")
    elif request.action == "hold_and_escalate":
        status = "action_required"
        set_kill_switch(
            "strategy",
            batch.strategy_instance_id or "",
            KillSwitchRequest(engaged=True, reason=request.reason),
        )
    elif batch.residual_notional != 0:
        raise HTTPException(status_code=422, detail="Residual exposure is not zero")
    else:
        status = "completed"
        update_risk(batch_id, "resolved_manually", Decimal("0"), "completed")
    disposition_id = str(uuid4())
    created = now_iso()
    details = json.dumps({"reason": request.reason}, sort_keys=True)
    with connection() as db:
        db.execute(
            """
            INSERT INTO execution_dispositions (
                id, idempotency_key, batch_id, action, status,
                details_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                disposition_id,
                request.idempotency_key,
                batch_id,
                request.action,
                status,
                details,
                created,
                created,
            ),
        )
        row = db.execute(
            "SELECT * FROM execution_dispositions WHERE id = ?", (disposition_id,)
        ).fetchone()
    return disposition_response(row)


def get_execution_batch(batch_id: str) -> ExecutionBatchResponse:
    ensure_schema()
    with connection() as db:
        batch = db.execute("SELECT * FROM execution_batches WHERE id = ?", (batch_id,)).fetchone()
        risk = db.execute(
            "SELECT * FROM execution_batch_risk_profiles WHERE batch_id = ?", (batch_id,)
        ).fetchone()
        legs = db.execute(
            """
            SELECT l.*, m.filled_quantity, m.average_fill_price,
                   m.repair_order_id, m.repair_status
            FROM execution_batch_legs l
            LEFT JOIN execution_batch_leg_metrics m
              ON m.batch_id = l.batch_id AND m.role = l.role
            WHERE l.batch_id = ? ORDER BY l.sequence
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
        riskState=risk["risk_state"] if risk else "legacy",
        residualNotional=Decimal(risk["residual_notional"]) if risk else Decimal("0"),
        dispositionStatus=risk["disposition_status"] if risk else None,
        killSwitchEngaged=bool(risk["kill_switch_engaged"]) if risk else False,
        maxLegDelayMs=risk["max_leg_delay_ms"] if risk else 3000,
        maxResidualNotional=Decimal(risk["max_residual_notional"]) if risk else Decimal("0"),
        allowPartialFill=bool(risk["allow_partial_fill"]) if risk else False,
        emergencyFlatten=bool(risk["emergency_flatten"]) if risk else True,
        legs=[leg_response(row) for row in legs],
        createdAt=batch["created_at"],
        updatedAt=batch["updated_at"],
    )


def list_execution_batches(strategy_instance_id: str | None = None) -> list[ExecutionBatchResponse]:
    where = "WHERE strategy_instance_id = ?" if strategy_instance_id else ""
    params = (strategy_instance_id,) if strategy_instance_id else ()
    with connection() as db:
        rows = db.execute(
            f"SELECT id FROM execution_batches {where} ORDER BY created_at DESC", params
        ).fetchall()
    return [get_execution_batch(row["id"]) for row in rows]


def assert_batch_request_matches(
    batch_id: str,
    request: CreateExecutionBatchRequest,
) -> None:
    with connection() as db:
        batch = db.execute(
            """
            SELECT strategy_instance_id, account_id, strategy_key, direction
            FROM execution_batches WHERE id = ?
            """,
            (batch_id,),
        ).fetchone()
        risk = db.execute(
            "SELECT * FROM execution_batch_risk_profiles WHERE batch_id = ?",
            (batch_id,),
        ).fetchone()
        legs = db.execute(
            """
            SELECT l.role, l.account_id, l.instrument_id, l.symbol, l.side,
                   l.order_type, l.quantity, l.price,
                   m.time_in_force, m.reduce_only, m.position_idx,
                   m.max_deviation, m.allow_partial_fill, m.max_slippage_bps
            FROM execution_batch_legs l
            JOIN execution_batch_leg_metrics m
              ON m.batch_id = l.batch_id AND m.role = l.role
            WHERE l.batch_id = ?
            """,
            (batch_id,),
        ).fetchall()

    default_account_id = request.account_id or request.legs[0].account_id
    if batch is None or risk is None:
        raise HTTPException(status_code=409, detail="Existing batch is incomplete")
    batch_matches = (
        batch["strategy_instance_id"] == request.strategy_instance_id
        and batch["account_id"] == default_account_id
        and batch["strategy_key"] == request.strategy_key
        and batch["direction"] == request.direction
        and risk["max_leg_delay_ms"] == request.max_leg_delay_ms
        and Decimal(risk["max_residual_notional"]) == request.max_residual_notional
        and bool(risk["allow_partial_fill"]) == request.allow_partial_fill
        and bool(risk["emergency_flatten"]) == request.emergency_flatten
        and risk["disposition_policy"] == request.disposition_policy
    )
    stored = {row["role"]: row for row in legs}
    if not batch_matches or set(stored) != {leg.role for leg in request.legs}:
        raise_batch_conflict()

    for leg in request.legs:
        row = stored[leg.role]
        account_id = leg.account_id or default_account_id
        stored_price = Decimal(row["price"]) if row["price"] is not None else None
        stored_slippage = (
            Decimal(row["max_slippage_bps"]) if row["max_slippage_bps"] is not None else None
        )
        leg_matches = (
            row["account_id"] == account_id
            and row["instrument_id"] == leg.instrument_id
            and row["symbol"] == leg.symbol
            and row["side"] == leg.side
            and row["order_type"] == leg.order_type
            and Decimal(row["quantity"]) == leg.quantity
            and stored_price == leg.price
            and row["time_in_force"] == leg.time_in_force
            and bool(row["reduce_only"]) == leg.reduce_only
            and row["position_idx"] == leg.position_idx
            and row["max_deviation"] == leg.max_deviation
            and bool(row["allow_partial_fill"])
            == (request.allow_partial_fill and leg.allow_partial_fill)
            and stored_slippage == leg.max_slippage_bps
        )
        if not leg_matches:
            raise_batch_conflict()


def raise_batch_conflict() -> None:
    raise HTTPException(
        status_code=409,
        detail="Idempotency key is already used by a different execution batch payload",
    )


def find_batch(key: str) -> str | None:
    with connection() as db:
        row = db.execute(
            "SELECT id FROM execution_batches WHERE idempotency_key = ?", (key,)
        ).fetchone()
    return row["id"] if row else None


def strategy_key(strategy_id: str) -> str:
    with connection() as db:
        row = db.execute(
            """
            SELECT sd.strategy_key FROM strategy_instances si
            JOIN strategy_definitions sd ON sd.id = si.strategy_definition_id
            WHERE si.id = ? AND si.status = 'active' AND sd.v1_scope = 'closed_loop'
            """,
            (strategy_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=422, detail="Strategy instance is not runnable")
    return row["strategy_key"]


def multiplier(instrument_id: str) -> Decimal:
    with connection() as db:
        row = db.execute(
            """
            SELECT contract_multiplier FROM contract_specifications
            WHERE instrument_id = ? ORDER BY effective_from DESC LIMIT 1
            """,
            (instrument_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=422, detail="Contract multiplier unavailable")
    return Decimal(row["contract_multiplier"])


def order_fill(order_id: str | None) -> tuple[Decimal | None, Decimal | None]:
    if not order_id:
        return None, None
    with connection() as db:
        rows = db.execute(
            "SELECT quantity, price FROM fills WHERE order_id = ?", (order_id,)
        ).fetchall()
    if not rows:
        return None, None
    quantity = sum((Decimal(row["quantity"]) for row in rows), Decimal("0"))
    notional = sum((Decimal(row["quantity"]) * Decimal(row["price"]) for row in rows), Decimal("0"))
    return quantity, notional / quantity


def record_metrics(
    batch_id: str,
    role: str,
    side: str,
    quantity: Decimal,
    price: Decimal | None,
    contract_multiplier: Decimal,
) -> None:
    sign = Decimal("1") if side == "buy" else Decimal("-1")
    exposure = quantity * contract_multiplier * sign
    notional = abs(exposure) * (price or Decimal("0"))
    with connection() as db:
        db.execute(
            """
            UPDATE execution_batch_leg_metrics
            SET filled_quantity = ?, average_fill_price = ?, base_exposure = ?, notional = ?
            WHERE batch_id = ? AND role = ?
            """,
            (
                decimal_text(quantity),
                decimal_text(price) if price else None,
                decimal_text(exposure),
                decimal_text(notional),
                batch_id,
                role,
            ),
        )


def residual_notional(batch_id: str) -> Decimal:
    with connection() as db:
        rows = db.execute(
            """
            SELECT base_exposure, average_fill_price
            FROM execution_batch_leg_metrics
            WHERE batch_id = ?
            """,
            (batch_id,),
        ).fetchall()
    net = sum((Decimal(row["base_exposure"]) for row in rows), Decimal("0"))
    price = next(
        (Decimal(row["average_fill_price"]) for row in rows if row["average_fill_price"]),
        Decimal("0"),
    )
    return abs(net) * price


def update_leg(
    batch_id: str, role: str, status: str, order_id: str | None = None, reason: str | None = None
) -> None:
    with connection() as db:
        db.execute(
            """
            UPDATE execution_batch_legs
            SET status = ?, order_id = COALESCE(?, order_id), failure_reason = ?, updated_at = ?
            WHERE batch_id = ? AND role = ?
            """,
            (status, order_id, reason, now_iso(), batch_id, role),
        )


def update_batch(
    batch_id: str, status: str, reason: str | None = None, manual: bool = False
) -> None:
    with connection() as db:
        db.execute(
            """
            UPDATE execution_batches SET status = ?, failure_reason = ?,
                requires_manual_intervention = ?, updated_at = ? WHERE id = ?
            """,
            (status, reason, int(manual), now_iso(), batch_id),
        )


def update_risk(
    batch_id: str, state: str, residual: Decimal, disposition: str | None = None, kill: bool = False
) -> None:
    with connection() as db:
        db.execute(
            """
            UPDATE execution_batch_risk_profiles
            SET risk_state = ?, residual_notional = ?,
                disposition_status = ?, kill_switch_engaged = ?
            WHERE batch_id = ?
            """,
            (state, decimal_text(residual), disposition, int(kill), batch_id),
        )


def leg_response(row) -> BatchLegResponse:
    return BatchLegResponse(
        role=row["role"],
        accountId=row["account_id"],
        orderId=row["order_id"],
        status=row["status"],
        failureReason=row["failure_reason"],
        filledQuantity=Decimal(row["filled_quantity"]) if row["filled_quantity"] else None,
        averageFillPrice=Decimal(row["average_fill_price"]) if row["average_fill_price"] else None,
        repairOrderId=row["repair_order_id"],
        repairStatus=row["repair_status"],
    )


def disposition_response(row) -> ExecutionDispositionResponse:
    return ExecutionDispositionResponse(
        dispositionId=row["id"],
        idempotencyKey=row["idempotency_key"],
        batchId=row["batch_id"],
        action=row["action"],
        status=row["status"],
        detailsJson=row["details_json"],
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


@router.get(
    "/trading/kill-switches/{scope_type}/{scope_id}",
    response_model=KillSwitchResponse,
    tags=["risk"],
)
def read_kill_switch(scope_type: str, scope_id: str) -> KillSwitchResponse:
    return get_kill_switch(scope_type, scope_id)


@router.put(
    "/trading/kill-switches/{scope_type}/{scope_id}",
    response_model=KillSwitchResponse,
    tags=["risk"],
)
def write_kill_switch(
    scope_type: str, scope_id: str, request: KillSwitchRequest
) -> KillSwitchResponse:
    return set_kill_switch(scope_type, scope_id, request)


@router.post(
    "/trading/execution-batches/{batch_id}/dispositions",
    response_model=ExecutionDispositionResponse,
    tags=["risk"],
)
def create_disposition(
    batch_id: str, request: ExecutionDispositionRequest
) -> ExecutionDispositionResponse:
    return apply_disposition(batch_id, request)
