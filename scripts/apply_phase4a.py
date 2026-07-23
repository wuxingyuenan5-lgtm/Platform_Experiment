from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"marker not found in {path}: {old[:100]!r}")
    file.write_text(text.replace(old, new, 1), encoding="utf-8")


def append_once(path: str, marker: str, content: str) -> None:
    file = Path(path)
    text = file.read_text(encoding="utf-8")
    if marker not in text:
        file.write_text(text.rstrip() + "\n\n" + content.strip() + "\n", encoding="utf-8")


replace_once(
    "platform-backend/app/config.py",
    '    live_trading_enabled: bool = False\n    default_trading_environment: str = "simulation"\n',
    '    live_trading_enabled: bool = False\n'
    '    demo_trading_enabled: bool = False\n'
    '    default_trading_environment: str = "simulation"\n',
)

# Execution options are optional to preserve all Phase 1-3 clients.
for class_name in ("CreateOrderRequest", "BatchLegRequest", "CreateTradeCommandRequest"):
    path = "platform-backend/app/schemas.py"
    text = Path(path).read_text(encoding="utf-8")
    start = text.index(f"class {class_name}(BaseModel):")
    next_class = text.index("\n\nclass ", start + 8)
    block = text[start:next_class]
    if "time_in_force" not in block:
        marker = "    price: Decimal | None = Field(default=None, gt=0)\n"
        replacement = marker + (
            '    time_in_force: Literal["GTC", "IOC", "FOK"] = Field(default="GTC", alias="timeInForce")\n'
            '    reduce_only: bool = Field(default=False, alias="reduceOnly")\n'
            '    position_idx: int = Field(default=0, alias="positionIdx", ge=0, le=2)\n'
            '    max_deviation: int | None = Field(default=None, alias="maxDeviation", ge=0)\n'
            '    allow_partial_fill: bool = Field(default=True, alias="allowPartialFill")\n'
            '    max_slippage_bps: Decimal | None = Field(default=None, alias="maxSlippageBps", ge=0)\n'
        )
        block = block.replace(marker, replacement, 1)
        text = text[:start] + block + text[next_class:]
        Path(path).write_text(text, encoding="utf-8")

replace_once(
    "platform-backend/app/schemas.py",
    '    direction: str = Field(min_length=1, max_length=32)\n    legs: list[BatchLegRequest] = Field(min_length=2, max_length=2)\n',
    '    direction: str = Field(min_length=1, max_length=32)\n'
    '    max_leg_delay_ms: int = Field(default=3000, alias="maxLegDelayMs", ge=1, le=60000)\n'
    '    max_residual_notional: Decimal = Field(default=Decimal("0"), alias="maxResidualNotional", ge=0)\n'
    '    allow_partial_fill: bool = Field(default=False, alias="allowPartialFill")\n'
    '    emergency_flatten: bool = Field(default=True, alias="emergencyFlatten")\n'
    '    disposition_policy: Literal["flatten_filled_legs", "hold_and_escalate"] = Field(\n'
    '        default="flatten_filled_legs", alias="dispositionPolicy"\n'
    '    )\n'
    '    legs: list[BatchLegRequest] = Field(min_length=2, max_length=2)\n',
)
replace_once(
    "platform-backend/app/schemas.py",
    '    failure_reason: str | None = Field(default=None, alias="failureReason")\n\n\nclass ExecutionBatchResponse',
    '    failure_reason: str | None = Field(default=None, alias="failureReason")\n'
    '    filled_quantity: Decimal | None = Field(default=None, alias="filledQuantity")\n'
    '    average_fill_price: Decimal | None = Field(default=None, alias="averageFillPrice")\n'
    '    repair_order_id: str | None = Field(default=None, alias="repairOrderId")\n'
    '    repair_status: str | None = Field(default=None, alias="repairStatus")\n\n\nclass ExecutionBatchResponse',
)
replace_once(
    "platform-backend/app/schemas.py",
    '        "manual_intervention",\n    ]\n    requires_manual_intervention: bool = Field(alias="requiresManualIntervention")\n',
    '        "manual_intervention",\n'
    '        "compensating",\n'
    '        "compensated",\n'
    '        "risk_unresolved",\n'
    '        "kill_switch_blocked",\n'
    '    ]\n'
    '    requires_manual_intervention: bool = Field(alias="requiresManualIntervention")\n'
    '    risk_state: str = Field(default="none", alias="riskState")\n'
    '    residual_notional: Decimal = Field(default=Decimal("0"), alias="residualNotional")\n'
    '    disposition_status: str | None = Field(default=None, alias="dispositionStatus")\n'
    '    kill_switch_engaged: bool = Field(default=False, alias="killSwitchEngaged")\n'
    '    max_leg_delay_ms: int = Field(default=3000, alias="maxLegDelayMs")\n'
    '    max_residual_notional: Decimal = Field(default=Decimal("0"), alias="maxResidualNotional")\n'
    '    allow_partial_fill: bool = Field(default=False, alias="allowPartialFill")\n'
    '    emergency_flatten: bool = Field(default=True, alias="emergencyFlatten")\n',
)
append_once(
    "platform-backend/app/schemas.py",
    "class KillSwitchRequest",
    '''
class KillSwitchRequest(BaseModel):
    engaged: bool
    reason: str = Field(min_length=1, max_length=512)


class KillSwitchResponse(BaseModel):
    scope_type: Literal["global", "strategy", "account"] = Field(alias="scopeType")
    scope_id: str = Field(alias="scopeId")
    engaged: bool
    reason: str | None = None
    updated_at: datetime = Field(alias="updatedAt")


class ExecutionDispositionRequest(BaseModel):
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    action: Literal["flatten_filled_legs", "hold_and_escalate", "mark_resolved"]
    reason: str = Field(min_length=1, max_length=512)


class ExecutionDispositionResponse(BaseModel):
    disposition_id: str = Field(alias="dispositionId")
    idempotency_key: str = Field(alias="idempotencyKey")
    batch_id: str = Field(alias="batchId")
    action: str
    status: str
    details_json: str = Field(alias="detailsJson")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
''',
)

# Persist execution options separately so old command tables remain stable.
replace_once(
    "platform-backend/app/trade_commands.py",
    'def create_trade_command(request: CreateTradeCommandRequest) -> TradeCommandResponse:\n    existing = find_trade_command_by_idempotency_key(request.idempotency_key)\n',
    'def create_trade_command(request: CreateTradeCommandRequest) -> TradeCommandResponse:\n'
    '    ensure_execution_option_schema()\n'
    '    existing = find_trade_command_by_idempotency_key(request.idempotency_key)\n',
)
append_once(
    "platform-backend/app/trade_commands.py",
    "def ensure_execution_option_schema",
    '''
def ensure_execution_option_schema() -> None:
    with connection() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS trade_command_execution_options (
                trade_command_id TEXT PRIMARY KEY,
                time_in_force TEXT NOT NULL,
                reduce_only INTEGER NOT NULL,
                position_idx INTEGER NOT NULL,
                max_deviation INTEGER,
                allow_partial_fill INTEGER NOT NULL,
                max_slippage_bps TEXT,
                FOREIGN KEY(trade_command_id) REFERENCES trade_commands(id)
            );
            """
        )
''',
)
replace_once(
    "platform-backend/app/trade_commands.py",
    '        db.execute(\n            """\n            INSERT INTO risk_decisions',
    '''        db.execute(
            """
            INSERT INTO trade_command_execution_options (
                trade_command_id, time_in_force, reduce_only, position_idx,
                max_deviation, allow_partial_fill, max_slippage_bps
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade_command_id,
                request.time_in_force,
                int(request.reduce_only),
                request.position_idx,
                request.max_deviation,
                int(request.allow_partial_fill),
                decimal_text(request.max_slippage_bps)
                if request.max_slippage_bps is not None
                else None,
            ),
        )
        db.execute(
            """
            INSERT INTO risk_decisions''',
)
replace_once(
    "platform-backend/app/trade_commands.py",
    '                quantity=request.quantity,\n                price=request.price,\n            ),',
    '                quantity=request.quantity,\n'
    '                price=request.price,\n'
    '                timeInForce=request.time_in_force,\n'
    '                reduceOnly=request.reduce_only,\n'
    '                positionIdx=request.position_idx,\n'
    '                maxDeviation=request.max_deviation,\n'
    '                allowPartialFill=request.allow_partial_fill,\n'
    '                maxSlippageBps=request.max_slippage_bps,\n'
    '            ),',
)

# Runtime payload now includes authoritative account context and execution controls.
replace_once(
    "platform-backend/app/trading.py",
    '    command = {\n        "command_id": command_id,',
    '    context = load_execution_context(request.account_id, request.instrument_id)\n'
    '    command = {\n'
    '        "command_id": command_id,',
)
replace_once(
    "platform-backend/app/trading.py",
    '        "price": decimal_text(request.price) if request.price is not None else None,\n    }\n',
    '        "price": decimal_text(request.price) if request.price is not None else None,\n'
    '        **context,\n'
    '        "time_in_force": request.time_in_force,\n'
    '        "reduce_only": request.reduce_only,\n'
    '        "position_idx": request.position_idx,\n'
    '        "max_deviation": request.max_deviation,\n'
    '        "allow_partial_fill": request.allow_partial_fill,\n'
    '        "max_slippage_bps": (\n'
    '            decimal_text(request.max_slippage_bps)\n'
    '            if request.max_slippage_bps is not None\n'
    '            else None\n'
    '        ),\n'
    '    }\n',
)
append_once(
    "platform-backend/app/trading.py",
    "def load_execution_context",
    '''
def load_execution_context(account_id: str, instrument_id: str) -> dict[str, object]:
    with connection() as db:
        row = db.execute(
            """
            SELECT v.venue_code, a.environment, a.credential_ref, i.instrument_type
            FROM accounts a
            JOIN venues v ON v.id = a.venue_id
            JOIN instruments i ON i.id = ?
            WHERE a.id = ?
            """,
            (instrument_id, account_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=422, detail="Execution context is unavailable")
    return {
        "venue_code": row["venue_code"],
        "environment": row["environment"],
        "credential_ref": row["credential_ref"],
        "instrument_type": row["instrument_type"],
    }
''',
)

phase4_risk = '''from __future__ import annotations

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


def set_kill_switch(scope_type: str, scope_id: str, request: KillSwitchRequest) -> KillSwitchResponse:
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
            raise HTTPException(status_code=423, detail=f"Execution blocked by {scope[0]} kill switch")
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
                    str(uuid4()), batch_id, sequence, leg.role, account_id,
                    leg.instrument_id, leg.symbol, leg.side, leg.order_type,
                    decimal_text(leg.quantity),
                    decimal_text(leg.price) if leg.price is not None else None,
                    created, created,
                ),
            )
            db.execute(
                """
                INSERT INTO execution_batch_leg_metrics (
                    batch_id, role, filled_quantity, average_fill_price,
                    contract_multiplier, base_exposure, notional,
                    repair_order_id, repair_status
                ) VALUES (?, ?, NULL, NULL, ?, '0', '0', NULL, NULL)
                """,
                (batch_id, leg.role, decimal_text(contract_multiplier)),
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


def apply_disposition(batch_id: str, request: ExecutionDispositionRequest) -> ExecutionDispositionResponse:
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
        status = "completed" if compensate(batch_id, batch.idempotency_key or batch_id) else "failed"
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
                disposition_id, request.idempotency_key, batch_id,
                request.action, status, details, created, created,
            ),
        )
        row = db.execute("SELECT * FROM execution_dispositions WHERE id = ?", (disposition_id,)).fetchone()
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


def find_batch(key: str) -> str | None:
    with connection() as db:
        row = db.execute("SELECT id FROM execution_batches WHERE idempotency_key = ?", (key,)).fetchone()
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
        rows = db.execute("SELECT quantity, price FROM fills WHERE order_id = ?", (order_id,)).fetchall()
    if not rows:
        return None, None
    quantity = sum((Decimal(row["quantity"]) for row in rows), Decimal("0"))
    notional = sum((Decimal(row["quantity"]) * Decimal(row["price"]) for row in rows), Decimal("0"))
    return quantity, notional / quantity


def record_metrics(batch_id: str, role: str, side: str, quantity: Decimal, price: Decimal | None, contract_multiplier: Decimal) -> None:
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
                decimal_text(quantity), decimal_text(price) if price else None,
                decimal_text(exposure), decimal_text(notional), batch_id, role,
            ),
        )


def residual_notional(batch_id: str) -> Decimal:
    with connection() as db:
        rows = db.execute(
            "SELECT base_exposure, average_fill_price FROM execution_batch_leg_metrics WHERE batch_id = ?",
            (batch_id,),
        ).fetchall()
    net = sum((Decimal(row["base_exposure"]) for row in rows), Decimal("0"))
    price = next((Decimal(row["average_fill_price"]) for row in rows if row["average_fill_price"]), Decimal("0"))
    return abs(net) * price


def update_leg(batch_id: str, role: str, status: str, order_id: str | None = None, reason: str | None = None) -> None:
    with connection() as db:
        db.execute(
            """
            UPDATE execution_batch_legs
            SET status = ?, order_id = COALESCE(?, order_id), failure_reason = ?, updated_at = ?
            WHERE batch_id = ? AND role = ?
            """,
            (status, order_id, reason, now_iso(), batch_id, role),
        )


def update_batch(batch_id: str, status: str, reason: str | None = None, manual: bool = False) -> None:
    with connection() as db:
        db.execute(
            """
            UPDATE execution_batches SET status = ?, failure_reason = ?,
                requires_manual_intervention = ?, updated_at = ? WHERE id = ?
            """,
            (status, reason, int(manual), now_iso(), batch_id),
        )


def update_risk(batch_id: str, state: str, residual: Decimal, disposition: str | None = None, kill: bool = False) -> None:
    with connection() as db:
        db.execute(
            """
            UPDATE execution_batch_risk_profiles
            SET risk_state = ?, residual_notional = ?, disposition_status = ?, kill_switch_engaged = ?
            WHERE batch_id = ?
            """,
            (state, decimal_text(residual), disposition, int(kill), batch_id),
        )


def leg_response(row) -> BatchLegResponse:
    return BatchLegResponse(
        role=row["role"], accountId=row["account_id"], orderId=row["order_id"],
        status=row["status"], failureReason=row["failure_reason"],
        filledQuantity=Decimal(row["filled_quantity"]) if row["filled_quantity"] else None,
        averageFillPrice=Decimal(row["average_fill_price"]) if row["average_fill_price"] else None,
        repairOrderId=row["repair_order_id"], repairStatus=row["repair_status"],
    )


def disposition_response(row) -> ExecutionDispositionResponse:
    return ExecutionDispositionResponse(
        dispositionId=row["id"], idempotencyKey=row["idempotency_key"],
        batchId=row["batch_id"], action=row["action"], status=row["status"],
        detailsJson=row["details_json"], createdAt=row["created_at"], updatedAt=row["updated_at"],
    )


@router.get("/trading/kill-switches/{scope_type}/{scope_id}", response_model=KillSwitchResponse, tags=["risk"])
def read_kill_switch(scope_type: str, scope_id: str) -> KillSwitchResponse:
    return get_kill_switch(scope_type, scope_id)


@router.put("/trading/kill-switches/{scope_type}/{scope_id}", response_model=KillSwitchResponse, tags=["risk"])
def write_kill_switch(scope_type: str, scope_id: str, request: KillSwitchRequest) -> KillSwitchResponse:
    return set_kill_switch(scope_type, scope_id, request)


@router.post("/trading/execution-batches/{batch_id}/dispositions", response_model=ExecutionDispositionResponse, tags=["risk"])
def create_disposition(batch_id: str, request: ExecutionDispositionRequest) -> ExecutionDispositionResponse:
    return apply_disposition(batch_id, request)
'''
Path("platform-backend/app/phase4_risk.py").write_text(phase4_risk, encoding="utf-8")

replace_once(
    "platform-backend/app/application.py",
    'from app.execution_batches import (\n    create_execution_batch,\n    get_execution_batch,\n    list_execution_batches,\n)\n',
    'from app.phase4_risk import create_execution_batch, get_execution_batch, list_execution_batches\n',
)
replace_once(
    "platform-backend/app/strategy_runs.py",
    'from app.execution_batches import create_execution_batch, get_execution_batch\n',
    'from app.phase4_risk import create_execution_batch, get_execution_batch\n',
)
replace_once(
    "platform-backend/app/main.py",
    'from app.financial_facts import router as financial_facts_router\n',
    'from app.financial_facts import router as financial_facts_router\n'
    'from app.phase4_risk import router as phase4_risk_router\n',
)
replace_once(
    "platform-backend/app/main.py",
    'app.include_router(financial_facts_router)\n',
    'app.include_router(financial_facts_router)\napp.include_router(phase4_risk_router)\n',
)

# Demo is separate from Live and defaults off.
replace_once(
    "platform-backend/app/security.py",
    '    if account["environment"] != LIVE_ENVIRONMENT:\n        return\n\n    settings = get_settings()\n',
    '    settings = get_settings()\n'
    '    if account["environment"] in {"demo", "testnet"}:\n'
    '        if not settings.demo_trading_enabled:\n'
    '            raise HTTPException(status_code=403, detail="Demo trading is disabled")\n'
    '        return\n'
    '    if account["environment"] != LIVE_ENVIRONMENT:\n'
    '        return\n\n',
)

# Risk goldens.
Path("platform-backend/tests/test_phase4_risk.py").write_text('''from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection
from app.main import app

STRATEGY = "strategy_funding_arbitrage_instance_default"


def batch(key: str) -> dict[str, object]:
    return {
        "idempotencyKey": key,
        "strategyInstanceId": STRATEGY,
        "accountId": "account_sim_usdt",
        "strategyKey": "funding_arbitrage",
        "direction": "collect",
        "maxLegDelayMs": 3000,
        "maxResidualNotional": "0",
        "allowPartialFill": False,
        "emergencyFlatten": True,
        "dispositionPolicy": "flatten_filled_legs",
        "legs": [
            {"role": "spot", "instrumentId": "instrument_btc_usdt", "symbol": "BTCUSDT", "side": "buy", "orderType": "market", "quantity": "0.01", "timeInForce": "FOK", "allowPartialFill": False},
            {"role": "perp", "instrumentId": "instrument_btc_usdt_perp", "symbol": "BTCUSDT", "side": "sell", "orderType": "market", "quantity": "0.01", "timeInForce": "FOK", "allowPartialFill": False},
        ],
    }


def test_phase4_batch_is_hedged_and_idempotent(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "hedged.db")
    with TestClient(app) as client:
        first = client.post("/api/v1/trading/execution-batches", json=batch("phase4-hedged"))
        assert first.status_code == 200
        assert first.json()["status"] == "hedged"
        assert first.json()["riskState"] == "hedged"
        duplicate = client.post("/api/v1/trading/execution-batches", json=batch("phase4-hedged"))
        assert duplicate.json()["batchId"] == first.json()["batchId"]
        assert len(client.get("/api/v1/trading/orders").json()) == 2


def test_kill_switch_blocks_execution(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "switch.db")
    with TestClient(app) as client:
        switch = client.put(
            f"/api/v1/trading/kill-switches/strategy/{STRATEGY}",
            json={"engaged": True, "reason": "test stop"},
        )
        assert switch.status_code == 200
        blocked = client.post("/api/v1/trading/execution-batches", json=batch("blocked"))
        assert blocked.status_code == 423


def test_second_leg_failure_repairs_actual_first_fill(tmp_path: Path, monkeypatch) -> None:
    get_settings().database_path = str(tmp_path / "repair.db")
    with TestClient(app) as client:
        from app import phase4_risk
        from app.schemas import TradeCommandResponse

        calls = []

        def fake_create(request):
            calls.append(request)
            if len(calls) == 1:
                with connection() as db:
                    db.execute("""
                        INSERT INTO orders (id, command_id, account_id, instrument_id, symbol, side, order_type, quantity, price, status, created_at, updated_at)
                        VALUES ('o1', 'c1', ?, ?, ?, ?, ?, ?, NULL, 'filled', '2026-07-23T00:00:00+00:00', '2026-07-23T00:00:00+00:00')
                    """, (request.account_id, request.instrument_id, request.symbol, request.side, request.order_type, str(request.quantity)))
                    db.execute("""
                        INSERT INTO fills (id, order_id, account_id, instrument_id, side, quantity, price, occurred_at)
                        VALUES ('f1', 'o1', ?, ?, ?, '0.01', '100', '2026-07-23T00:00:00+00:00')
                    """, (request.account_id, request.instrument_id, request.side))
                status, order_id = "filled", "o1"
            elif len(calls) == 2:
                status, order_id = "rejected", "o2"
            else:
                status, order_id = "filled", "repair"
            return TradeCommandResponse(
                tradeCommandId=f"c{len(calls)}", idempotencyKey=request.idempotency_key,
                strategyInstanceId=request.strategy_instance_id, accountId=request.account_id,
                instrumentId=request.instrument_id, platformOrderId=order_id, status=status,
                createdAt="2026-07-23T00:00:00+00:00", updatedAt="2026-07-23T00:00:00+00:00",
            )

        monkeypatch.setattr(phase4_risk, "create_trade_command", fake_create)
        result = client.post("/api/v1/trading/execution-batches", json=batch("repair"))
        assert result.status_code == 200
        assert result.json()["status"] == "compensated"
        assert calls[-1].reduce_only is True
        assert calls[-1].time_in_force == "FOK"
        assert calls[-1].quantity == calls[0].quantity
        assert calls[-1].side == "sell"
''', encoding="utf-8")

replace_once(
    ".github/workflows/platform-ci.yml",
    '            app/financial_facts.py \\\n',
    '            app/financial_facts.py \\\n            app/phase4_risk.py \\\n',
)
replace_once(
    ".github/workflows/platform-ci.yml",
    '            tests/test_financial_facts.py \\\n',
    '            tests/test_financial_facts.py \\\n            tests/test_phase4_risk.py \\\n',
)

# First Phase 4 document is intentionally precise about the external credential boundary.
Path("docs/planning/V6-Phase4-双腿风险与Demo对账.md").write_text('''# V6 Phase 4：双腿风险处置、Demo 执行与日终对账

状态：`Phase 4A implemented / 4B-4D in progress`  
实施分支：`hardening/v6-phase4-demo-risk-reconciliation`  
跟踪 Issue：`#12`  
更新时间：`2026-07-23`

## Phase 4A 已实现

- ExecutionBatch 最大腿间延迟、最大残留名义敞口、禁止部分成交和自动修复参数。
- 第一腿成交、第二腿失败时，按实际 Fill 数量生成反向 `reduceOnly + FOK` 修复命令。
- 修复成功状态为 `compensated`；修复失败状态为 `risk_unresolved`，自动开启 Strategy Kill Switch。
- Global、Strategy、Account Kill Switch。
- 幂等人工处置：flatten、hold-and-escalate、mark-resolved。
- Demo 与 Live 独立门禁，默认均关闭；Phase 4 永不允许 Live。

## 后续同一 Phase 4 分支

- 4B：外部订单、成交、持仓和余额主动查询及 FinancialFact 导入。
- 4C：Bybit Demo 与 MT5 Demo 正式适配器。
- 4D：日终对账差异对象和演练。
''', encoding="utf-8")

append_once(
    "CHANGELOG.md",
    "### Phase 4A execution risk control",
    '''
### Phase 4A execution risk control

- Added global, strategy, and account Kill Switches.
- Added risk-managed ExecutionBatch parameters and explicit residual-exposure states.
- Added automatic actual-fill reverse compensation using FOK and reduce-only commands.
- Added idempotent manual disposition records and automatic strategy stop on unresolved repair.
- Added a separate Demo safety gate while keeping Live disabled.
- Added Phase 4A golden tests and synchronized the Phase 4 implementation plan.
''',
)
