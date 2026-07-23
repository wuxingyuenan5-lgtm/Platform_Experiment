from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.config import get_settings
from app.database import connection
from app.schemas import CreateTradeCommandRequest
from app.trade_commands import create_trade_command

KillSwitchScope = Literal["global", "strategy", "account"]
FailureAction = Literal["hold_and_escalate", "auto_flatten"]
RiskStatus = Literal[
    "clear",
    "residual_exposure",
    "disposition_in_progress",
    "resolved",
    "escalated",
]
RiskActionName = Literal[
    "hold_and_escalate",
    "flatten_filled_legs",
    "cancel_open_legs",
    "substitute_hedge",
]

DEFAULT_MAX_LEG_DELAY_SECONDS = 10
DEFAULT_MAX_RESIDUAL_NOTIONAL = Decimal("100000")
DEFAULT_FAILURE_ACTION: FailureAction = "hold_and_escalate"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS trading_kill_switches (
    scope_type TEXT NOT NULL,
    scope_id TEXT NOT NULL,
    enabled INTEGER NOT NULL,
    reason TEXT,
    actor TEXT NOT NULL,
    version INTEGER NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(scope_type, scope_id)
);

CREATE TABLE IF NOT EXISTS kill_switch_commands (
    idempotency_key TEXT PRIMARY KEY,
    payload_hash TEXT NOT NULL,
    scope_type TEXT NOT NULL,
    scope_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS execution_risk_policies (
    strategy_instance_id TEXT PRIMARY KEY,
    max_leg_delay_seconds INTEGER NOT NULL,
    max_residual_notional TEXT NOT NULL,
    failure_action TEXT NOT NULL,
    actor TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(strategy_instance_id) REFERENCES strategy_instances(id)
);

CREATE TABLE IF NOT EXISTS execution_risk_policy_commands (
    idempotency_key TEXT PRIMARY KEY,
    payload_hash TEXT NOT NULL,
    strategy_instance_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(strategy_instance_id) REFERENCES strategy_instances(id)
);

CREATE TABLE IF NOT EXISTS execution_batch_risk (
    batch_id TEXT PRIMARY KEY,
    strategy_instance_id TEXT NOT NULL,
    max_leg_delay_seconds INTEGER NOT NULL,
    max_residual_notional TEXT NOT NULL,
    failure_action TEXT NOT NULL,
    risk_status TEXT NOT NULL,
    residual_exposure_notional TEXT NOT NULL,
    residual_currency TEXT NOT NULL,
    data_quality_state TEXT NOT NULL,
    first_fill_at TEXT,
    last_leg_at TEXT,
    risk_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(batch_id) REFERENCES execution_batches(id),
    FOREIGN KEY(strategy_instance_id) REFERENCES strategy_instances(id)
);

CREATE TABLE IF NOT EXISTS execution_risk_actions (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    payload_hash TEXT NOT NULL,
    batch_id TEXT NOT NULL,
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    actor TEXT NOT NULL,
    reason TEXT,
    generated_order_ids_json TEXT NOT NULL,
    failure_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(batch_id) REFERENCES execution_batches(id)
);

CREATE INDEX IF NOT EXISTS idx_execution_risk_actions_batch
ON execution_risk_actions(batch_id, created_at);
"""


class KillSwitchUpdateRequest(BaseModel):
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    enabled: bool
    reason: str | None = Field(default=None, max_length=512)
    actor: str = Field(min_length=1, max_length=128)


class KillSwitchResponse(BaseModel):
    scope_type: KillSwitchScope = Field(alias="scopeType")
    scope_id: str = Field(alias="scopeId")
    enabled: bool
    reason: str | None = None
    actor: str
    version: int
    updated_at: datetime = Field(alias="updatedAt")


class ExecutionRiskPolicyUpdateRequest(BaseModel):
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    max_leg_delay_seconds: int = Field(alias="maxLegDelaySeconds", ge=1, le=3600)
    max_residual_notional: Decimal = Field(alias="maxResidualNotional", gt=0)
    failure_action: FailureAction = Field(alias="failureAction")
    actor: str = Field(min_length=1, max_length=128)


class ExecutionRiskPolicyResponse(BaseModel):
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    max_leg_delay_seconds: int = Field(alias="maxLegDelaySeconds")
    max_residual_notional: Decimal = Field(alias="maxResidualNotional")
    failure_action: FailureAction = Field(alias="failureAction")
    source: Literal["default", "configured"]
    actor: str
    updated_at: datetime = Field(alias="updatedAt")


class BatchRiskResponse(BaseModel):
    batch_id: str = Field(alias="batchId")
    strategy_instance_id: str = Field(alias="strategyInstanceId")
    max_leg_delay_seconds: int = Field(alias="maxLegDelaySeconds")
    max_residual_notional: Decimal = Field(alias="maxResidualNotional")
    failure_action: FailureAction = Field(alias="failureAction")
    risk_status: RiskStatus = Field(alias="riskStatus")
    residual_exposure_notional: Decimal = Field(alias="residualExposureNotional")
    residual_currency: str = Field(alias="residualCurrency")
    data_quality_state: str = Field(alias="dataQualityState")
    first_fill_at: datetime | None = Field(default=None, alias="firstFillAt")
    last_leg_at: datetime | None = Field(default=None, alias="lastLegAt")
    risk_reason: str | None = Field(default=None, alias="riskReason")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class RiskActionRequest(BaseModel):
    idempotency_key: str = Field(alias="idempotencyKey", min_length=1, max_length=128)
    action: RiskActionName
    actor: str = Field(min_length=1, max_length=128)
    reason: str | None = Field(default=None, max_length=512)
    replacement_account_id: str | None = Field(default=None, alias="replacementAccountId")
    replacement_instrument_id: str | None = Field(default=None, alias="replacementInstrumentId")
    replacement_symbol: str | None = Field(default=None, alias="replacementSymbol")
    replacement_side: Literal["buy", "sell"] | None = Field(
        default=None, alias="replacementSide"
    )
    replacement_quantity: Decimal | None = Field(
        default=None, alias="replacementQuantity", gt=0
    )
    replacement_price: Decimal | None = Field(default=None, alias="replacementPrice", gt=0)

    @model_validator(mode="after")
    def validate_replacement(self) -> "RiskActionRequest":
        if self.action == "substitute_hedge":
            required = (
                self.replacement_account_id,
                self.replacement_instrument_id,
                self.replacement_symbol,
                self.replacement_side,
                self.replacement_quantity,
            )
            if any(value is None for value in required):
                raise ValueError("substitute_hedge requires a complete replacement leg")
        return self


class RiskActionResponse(BaseModel):
    risk_action_id: str = Field(alias="riskActionId")
    idempotency_key: str = Field(alias="idempotencyKey")
    batch_id: str = Field(alias="batchId")
    action: RiskActionName
    status: str
    actor: str
    reason: str | None = None
    generated_order_ids: list[str] = Field(alias="generatedOrderIds")
    failure_reason: str | None = Field(default=None, alias="failureReason")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def ensure_schema() -> None:
    with connection() as db:
        db.executescript(SCHEMA_SQL)


def canonical_hash(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def audit(event_type: str, subject_type: str, subject_id: str, details: dict[str, object]) -> None:
    with connection() as db:
        db.execute(
            """
            INSERT INTO audit_events (
                id, event_type, subject_type, subject_id, details_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                event_type,
                subject_type,
                subject_id,
                json.dumps(details, ensure_ascii=False, sort_keys=True, default=str),
                now_iso(),
            ),
        )


def validate_scope(scope_type: str, scope_id: str) -> KillSwitchScope:
    if scope_type not in {"global", "strategy", "account"}:
        raise HTTPException(status_code=422, detail="Unsupported kill-switch scope")
    if scope_type == "global" and scope_id != "*":
        raise HTTPException(status_code=422, detail="Global kill switch must use scopeId '*' ")
    if scope_type == "strategy":
        with connection() as db:
            row = db.execute(
                "SELECT id FROM strategy_instances WHERE id = ?", (scope_id,)
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Strategy instance not found")
    if scope_type == "account":
        with connection() as db:
            row = db.execute("SELECT id FROM accounts WHERE id = ?", (scope_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Account not found")
    return scope_type


def get_kill_switch(scope_type: str, scope_id: str) -> KillSwitchResponse:
    ensure_schema()
    validated_scope = validate_scope(scope_type, scope_id)
    with connection() as db:
        row = db.execute(
            """
            SELECT * FROM trading_kill_switches
            WHERE scope_type = ? AND scope_id = ?
            """,
            (validated_scope, scope_id),
        ).fetchone()
    if row is None:
        return KillSwitchResponse(
            scopeType=validated_scope,
            scopeId=scope_id,
            enabled=False,
            reason=None,
            actor="system-default",
            version=0,
            updatedAt=datetime.now(UTC),
        )
    return kill_switch_from_row(row)


def set_kill_switch(
    scope_type: str,
    scope_id: str,
    request: KillSwitchUpdateRequest,
) -> KillSwitchResponse:
    ensure_schema()
    validated_scope = validate_scope(scope_type, scope_id)
    payload = {
        "scopeType": validated_scope,
        "scopeId": scope_id,
        "enabled": request.enabled,
        "reason": request.reason,
        "actor": request.actor,
    }
    payload_hash = canonical_hash(payload)
    changed_at = now_iso()
    with connection() as db:
        existing_command = db.execute(
            "SELECT payload_hash FROM kill_switch_commands WHERE idempotency_key = ?",
            (request.idempotency_key,),
        ).fetchone()
        if existing_command is not None:
            if existing_command["payload_hash"] != payload_hash:
                raise HTTPException(
                    status_code=409,
                    detail="Kill-switch idempotency key was reused with a different payload",
                )
            row = db.execute(
                """
                SELECT * FROM trading_kill_switches
                WHERE scope_type = ? AND scope_id = ?
                """,
                (validated_scope, scope_id),
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=409, detail="Kill-switch command result is unavailable")
            return kill_switch_from_row(row)

        previous = db.execute(
            """
            SELECT version FROM trading_kill_switches
            WHERE scope_type = ? AND scope_id = ?
            """,
            (validated_scope, scope_id),
        ).fetchone()
        version = (previous["version"] if previous is not None else 0) + 1
        db.execute(
            """
            INSERT INTO kill_switch_commands (
                idempotency_key, payload_hash, scope_type, scope_id, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                request.idempotency_key,
                payload_hash,
                validated_scope,
                scope_id,
                changed_at,
            ),
        )
        db.execute(
            """
            INSERT INTO trading_kill_switches (
                scope_type, scope_id, enabled, reason, actor, version, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(scope_type, scope_id) DO UPDATE SET
                enabled = excluded.enabled,
                reason = excluded.reason,
                actor = excluded.actor,
                version = excluded.version,
                updated_at = excluded.updated_at
            """,
            (
                validated_scope,
                scope_id,
                int(request.enabled),
                request.reason,
                request.actor,
                version,
                changed_at,
            ),
        )
        row = db.execute(
            """
            SELECT * FROM trading_kill_switches
            WHERE scope_type = ? AND scope_id = ?
            """,
            (validated_scope, scope_id),
        ).fetchone()
    audit(
        "kill_switch_changed",
        validated_scope,
        scope_id,
        {**payload, "version": version, "idempotencyKey": request.idempotency_key},
    )
    return kill_switch_from_row(row)


def assert_execution_allowed(strategy_instance_id: str, account_ids: list[str]) -> None:
    ensure_schema()
    candidates: list[tuple[str, str]] = [("global", "*"), ("strategy", strategy_instance_id)]
    candidates.extend(("account", account_id) for account_id in sorted(set(account_ids)))
    with connection() as db:
        for scope_type, scope_id in candidates:
            row = db.execute(
                """
                SELECT enabled, reason
                FROM trading_kill_switches
                WHERE scope_type = ? AND scope_id = ?
                """,
                (scope_type, scope_id),
            ).fetchone()
            if row is not None and bool(row["enabled"]):
                reason = row["reason"] or "No reason provided"
                raise HTTPException(
                    status_code=423,
                    detail=f"Execution blocked by {scope_type} kill switch {scope_id}: {reason}",
                )


def get_execution_risk_policy(strategy_instance_id: str) -> ExecutionRiskPolicyResponse:
    ensure_schema()
    with connection() as db:
        strategy = db.execute(
            "SELECT id FROM strategy_instances WHERE id = ?", (strategy_instance_id,)
        ).fetchone()
        if strategy is None:
            raise HTTPException(status_code=404, detail="Strategy instance not found")
        row = db.execute(
            "SELECT * FROM execution_risk_policies WHERE strategy_instance_id = ?",
            (strategy_instance_id,),
        ).fetchone()
    if row is None:
        return ExecutionRiskPolicyResponse(
            strategyInstanceId=strategy_instance_id,
            maxLegDelaySeconds=DEFAULT_MAX_LEG_DELAY_SECONDS,
            maxResidualNotional=DEFAULT_MAX_RESIDUAL_NOTIONAL,
            failureAction=DEFAULT_FAILURE_ACTION,
            source="default",
            actor="system-default",
            updatedAt=datetime.now(UTC),
        )
    return policy_from_row(row, source="configured")


def set_execution_risk_policy(
    strategy_instance_id: str,
    request: ExecutionRiskPolicyUpdateRequest,
) -> ExecutionRiskPolicyResponse:
    ensure_schema()
    get_execution_risk_policy(strategy_instance_id)
    payload = {
        "strategyInstanceId": strategy_instance_id,
        "maxLegDelaySeconds": request.max_leg_delay_seconds,
        "maxResidualNotional": format(request.max_residual_notional, "f"),
        "failureAction": request.failure_action,
        "actor": request.actor,
    }
    payload_hash = canonical_hash(payload)
    changed_at = now_iso()
    with connection() as db:
        existing = db.execute(
            """
            SELECT payload_hash FROM execution_risk_policy_commands
            WHERE idempotency_key = ?
            """,
            (request.idempotency_key,),
        ).fetchone()
        if existing is not None:
            if existing["payload_hash"] != payload_hash:
                raise HTTPException(
                    status_code=409,
                    detail="Risk-policy idempotency key was reused with a different payload",
                )
            row = db.execute(
                "SELECT * FROM execution_risk_policies WHERE strategy_instance_id = ?",
                (strategy_instance_id,),
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=409, detail="Risk-policy command result is unavailable")
            return policy_from_row(row, source="configured")

        db.execute(
            """
            INSERT INTO execution_risk_policy_commands (
                idempotency_key, payload_hash, strategy_instance_id, created_at
            ) VALUES (?, ?, ?, ?)
            """,
            (request.idempotency_key, payload_hash, strategy_instance_id, changed_at),
        )
        db.execute(
            """
            INSERT INTO execution_risk_policies (
                strategy_instance_id, max_leg_delay_seconds, max_residual_notional,
                failure_action, actor, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(strategy_instance_id) DO UPDATE SET
                max_leg_delay_seconds = excluded.max_leg_delay_seconds,
                max_residual_notional = excluded.max_residual_notional,
                failure_action = excluded.failure_action,
                actor = excluded.actor,
                updated_at = excluded.updated_at
            """,
            (
                strategy_instance_id,
                request.max_leg_delay_seconds,
                format(request.max_residual_notional, "f"),
                request.failure_action,
                request.actor,
                changed_at,
            ),
        )
        row = db.execute(
            "SELECT * FROM execution_risk_policies WHERE strategy_instance_id = ?",
            (strategy_instance_id,),
        ).fetchone()
    audit(
        "execution_risk_policy_changed",
        "strategy_instance",
        strategy_instance_id,
        {**payload, "idempotencyKey": request.idempotency_key},
    )
    return policy_from_row(row, source="configured")


def initialize_batch_risk(batch_id: str, strategy_instance_id: str) -> BatchRiskResponse:
    ensure_schema()
    policy = get_execution_risk_policy(strategy_instance_id)
    created_at = now_iso()
    with connection() as db:
        db.execute(
            """
            INSERT OR IGNORE INTO execution_batch_risk (
                batch_id, strategy_instance_id, max_leg_delay_seconds,
                max_residual_notional, failure_action, risk_status,
                residual_exposure_notional, residual_currency, data_quality_state,
                first_fill_at, last_leg_at, risk_reason, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                batch_id,
                strategy_instance_id,
                policy.max_leg_delay_seconds,
                format(policy.max_residual_notional, "f"),
                policy.failure_action,
                "clear",
                "0",
                "UNKNOWN",
                "complete",
                None,
                None,
                None,
                created_at,
                created_at,
            ),
        )
    return get_batch_risk(batch_id)


def get_batch_risk(batch_id: str) -> BatchRiskResponse:
    ensure_schema()
    with connection() as db:
        row = db.execute(
            "SELECT * FROM execution_batch_risk WHERE batch_id = ?", (batch_id,)
        ).fetchone()
        if row is None:
            batch = db.execute(
                "SELECT strategy_instance_id FROM execution_batches WHERE id = ?", (batch_id,)
            ).fetchone()
            if batch is None:
                raise HTTPException(status_code=404, detail="Execution batch not found")
    if row is None:
        return initialize_batch_risk(batch_id, batch["strategy_instance_id"])
    return batch_risk_from_row(row)


def check_leg_deadline(batch_id: str, at: datetime | None = None) -> tuple[bool, str | None]:
    risk = get_batch_risk(batch_id)
    if risk.first_fill_at is None:
        return True, None
    current = at or datetime.now(UTC)
    first_fill = risk.first_fill_at
    if first_fill.tzinfo is None:
        first_fill = first_fill.replace(tzinfo=UTC)
    elapsed = (current.astimezone(UTC) - first_fill.astimezone(UTC)).total_seconds()
    if elapsed <= risk.max_leg_delay_seconds:
        return True, None
    reason = (
        f"Leg delay {elapsed:.3f}s exceeded policy limit "
        f"{risk.max_leg_delay_seconds}s"
    )
    set_batch_risk_state(batch_id, "residual_exposure", reason=reason)
    return False, reason


def record_filled_leg(batch_id: str) -> tuple[bool, str | None]:
    risk = get_batch_risk(batch_id)
    residual, currency, quality = calculate_residual_exposure(batch_id)
    filled_at = now_iso()
    exceeded = quality != "complete" or residual > risk.max_residual_notional
    reason = None
    status: RiskStatus = "residual_exposure" if residual > 0 else "clear"
    if quality != "complete":
        reason = "Residual exposure cannot be compared reliably because currency data is mixed"
        status = "residual_exposure"
    elif residual > risk.max_residual_notional:
        reason = (
            f"Residual exposure {residual} {currency} exceeded policy limit "
            f"{risk.max_residual_notional}"
        )
        status = "residual_exposure"

    with connection() as db:
        db.execute(
            """
            UPDATE execution_batch_risk
            SET risk_status = ?, residual_exposure_notional = ?, residual_currency = ?,
                data_quality_state = ?, first_fill_at = COALESCE(first_fill_at, ?),
                last_leg_at = ?, risk_reason = ?, updated_at = ?
            WHERE batch_id = ?
            """,
            (
                status,
                format(residual, "f"),
                currency,
                quality,
                filled_at,
                filled_at,
                reason,
                filled_at,
                batch_id,
            ),
        )
    return not exceeded, reason


def complete_batch_risk(batch_id: str) -> BatchRiskResponse:
    residual, currency, quality = calculate_residual_exposure(batch_id)
    status: RiskStatus = "clear" if residual == 0 and quality == "complete" else "residual_exposure"
    reason = None if status == "clear" else "Batch completed with unresolved residual exposure"
    with connection() as db:
        db.execute(
            """
            UPDATE execution_batch_risk
            SET risk_status = ?, residual_exposure_notional = ?, residual_currency = ?,
                data_quality_state = ?, last_leg_at = ?, risk_reason = ?, updated_at = ?
            WHERE batch_id = ?
            """,
            (
                status,
                format(residual, "f"),
                currency,
                quality,
                now_iso(),
                reason,
                now_iso(),
                batch_id,
            ),
        )
    return get_batch_risk(batch_id)


def handle_batch_failure(batch_id: str, reason: str) -> RiskActionResponse | None:
    risk = get_batch_risk(batch_id)
    residual, currency, quality = calculate_residual_exposure(batch_id)
    if residual == 0 and quality == "complete":
        set_batch_risk_state(
            batch_id,
            "resolved",
            residual=residual,
            currency=currency,
            quality=quality,
            reason=reason,
        )
        return None

    set_batch_risk_state(
        batch_id,
        "residual_exposure",
        residual=residual,
        currency=currency,
        quality=quality,
        reason=reason,
    )
    if risk.failure_action == "auto_flatten":
        return execute_risk_action(
            batch_id,
            RiskActionRequest(
                idempotencyKey=f"auto-flatten:{batch_id}",
                action="flatten_filled_legs",
                actor="system-risk-engine",
                reason=reason,
            ),
        )
    set_batch_risk_state(batch_id, "escalated", reason=reason)
    return None


def set_batch_risk_state(
    batch_id: str,
    status: RiskStatus,
    *,
    residual: Decimal | None = None,
    currency: str | None = None,
    quality: str | None = None,
    reason: str | None = None,
) -> None:
    get_batch_risk(batch_id)
    with connection() as db:
        db.execute(
            """
            UPDATE execution_batch_risk
            SET risk_status = ?,
                residual_exposure_notional = COALESCE(?, residual_exposure_notional),
                residual_currency = COALESCE(?, residual_currency),
                data_quality_state = COALESCE(?, data_quality_state),
                risk_reason = ?, updated_at = ?
            WHERE batch_id = ?
            """,
            (
                status,
                format(residual, "f") if residual is not None else None,
                currency,
                quality,
                reason,
                now_iso(),
                batch_id,
            ),
        )
    audit(
        "execution_batch_risk_state_changed",
        "execution_batch",
        batch_id,
        {
            "riskStatus": status,
            "residualExposureNotional": residual,
            "residualCurrency": currency,
            "dataQualityState": quality,
            "reason": reason,
        },
    )


def calculate_residual_exposure(batch_id: str) -> tuple[Decimal, str, str]:
    ensure_schema()
    with connection() as db:
        legs = db.execute(
            """
            SELECT l.role, l.side, l.quantity, l.price, l.order_id,
                   i.settle_currency, cs.contract_multiplier
            FROM execution_batch_legs l
            JOIN instruments i ON i.id = l.instrument_id
            JOIN contract_specifications cs ON cs.instrument_id = l.instrument_id
            WHERE l.batch_id = ? AND l.status = 'filled'
              AND cs.effective_from = (
                  SELECT MAX(cs2.effective_from)
                  FROM contract_specifications cs2
                  WHERE cs2.instrument_id = l.instrument_id
              )
            ORDER BY l.sequence
            """,
            (batch_id,),
        ).fetchall()
        exposure_by_currency: dict[str, Decimal] = {}
        for leg in legs:
            fill_rows = []
            if leg["order_id"] is not None:
                fill_rows = db.execute(
                    "SELECT quantity, price FROM fills WHERE order_id = ? ORDER BY occurred_at",
                    (leg["order_id"],),
                ).fetchall()
            multiplier = Decimal(leg["contract_multiplier"])
            if fill_rows:
                notional = sum(
                    Decimal(fill["quantity"]) * Decimal(fill["price"]) * multiplier
                    for fill in fill_rows
                )
            elif leg["price"] is not None:
                notional = Decimal(leg["quantity"]) * Decimal(leg["price"]) * multiplier
            else:
                return Decimal("0"), "UNKNOWN", "incomplete"
            signed = notional if leg["side"] == "buy" else -notional
            currency = leg["settle_currency"]
            exposure_by_currency[currency] = exposure_by_currency.get(currency, Decimal("0")) + signed

    if not exposure_by_currency:
        return Decimal("0"), "UNKNOWN", "complete"
    if len(exposure_by_currency) == 1:
        currency, signed_exposure = next(iter(exposure_by_currency.items()))
        return abs(signed_exposure), currency, "complete"
    conservative = sum(abs(value) for value in exposure_by_currency.values())
    return conservative, "MIXED", "incomplete"


def execute_risk_action(batch_id: str, request: RiskActionRequest) -> RiskActionResponse:
    ensure_schema()
    risk = get_batch_risk(batch_id)
    payload = request.model_dump(by_alias=True, mode="json")
    payload_hash = canonical_hash(payload)
    created_at = now_iso()
    action_id = str(uuid4())
    with connection() as db:
        existing = db.execute(
            "SELECT * FROM execution_risk_actions WHERE idempotency_key = ?",
            (request.idempotency_key,),
        ).fetchone()
        if existing is not None:
            if existing["payload_hash"] != payload_hash:
                raise HTTPException(
                    status_code=409,
                    detail="Risk-action idempotency key was reused with a different payload",
                )
            return risk_action_from_row(existing)
        db.execute(
            """
            INSERT INTO execution_risk_actions (
                id, idempotency_key, payload_hash, batch_id, action, status, actor,
                reason, generated_order_ids_json, failure_reason, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action_id,
                request.idempotency_key,
                payload_hash,
                batch_id,
                request.action,
                "processing",
                request.actor,
                request.reason,
                "[]",
                None,
                created_at,
                created_at,
            ),
        )

    set_batch_risk_state(batch_id, "disposition_in_progress", reason=request.reason)
    try:
        status, order_ids, failure_reason = perform_risk_action(batch_id, request, risk)
    except Exception as exc:
        status = "failed"
        order_ids = []
        failure_reason = str(exc)
        set_batch_risk_state(batch_id, "escalated", reason=failure_reason)

    updated_at = now_iso()
    with connection() as db:
        db.execute(
            """
            UPDATE execution_risk_actions
            SET status = ?, generated_order_ids_json = ?, failure_reason = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                status,
                json.dumps(order_ids, sort_keys=True),
                failure_reason,
                updated_at,
                action_id,
            ),
        )
        row = db.execute(
            "SELECT * FROM execution_risk_actions WHERE id = ?", (action_id,)
        ).fetchone()
    audit(
        "execution_risk_action_completed",
        "execution_batch",
        batch_id,
        {
            "riskActionId": action_id,
            "idempotencyKey": request.idempotency_key,
            "action": request.action,
            "status": status,
            "generatedOrderIds": order_ids,
            "failureReason": failure_reason,
        },
    )
    return risk_action_from_row(row)


def perform_risk_action(
    batch_id: str,
    request: RiskActionRequest,
    risk: BatchRiskResponse,
) -> tuple[str, list[str], str | None]:
    if request.action == "hold_and_escalate":
        with connection() as db:
            db.execute(
                """
                UPDATE execution_batches
                SET status = 'manual_intervention', requires_manual_intervention = 1,
                    failure_reason = ?, updated_at = ?
                WHERE id = ?
                """,
                (request.reason or "Risk held for manual intervention", now_iso(), batch_id),
            )
        set_batch_risk_state(batch_id, "escalated", reason=request.reason)
        return "completed", [], None

    if request.action == "cancel_open_legs":
        with connection() as db:
            db.execute(
                """
                UPDATE execution_batch_legs
                SET status = 'canceled', failure_reason = ?, updated_at = ?
                WHERE batch_id = ? AND order_id IS NULL
                  AND status IN ('pending', 'submitting')
                """,
                (request.reason or "Canceled by risk action", now_iso(), batch_id),
            )
            unresolved = db.execute(
                """
                SELECT COUNT(*) AS count
                FROM execution_batch_legs
                WHERE batch_id = ? AND order_id IS NOT NULL
                  AND status IN ('accepted', 'processing', 'acknowledged', 'result_unknown')
                """,
                (batch_id,),
            ).fetchone()["count"]
        if unresolved:
            reason = "Open external orders require Venue cancellation support from Phase 4B/4C"
            set_batch_risk_state(batch_id, "escalated", reason=reason)
            return "action_required", [], reason
        set_batch_risk_state(batch_id, "resolved", residual=Decimal("0"), reason=request.reason)
        return "completed", [], None

    if request.action == "substitute_hedge":
        command = create_trade_command(
            CreateTradeCommandRequest(
                idempotencyKey=f"{request.idempotency_key}:replacement",
                strategyInstanceId=risk.strategy_instance_id,
                accountId=request.replacement_account_id,
                instrumentId=request.replacement_instrument_id,
                symbol=request.replacement_symbol,
                side=request.replacement_side,
                orderType="limit" if request.replacement_price is not None else "market",
                quantity=request.replacement_quantity,
                price=request.replacement_price,
            )
        )
        order_ids = [command.platform_order_id] if command.platform_order_id else []
        if command.status != "filled":
            reason = f"Replacement hedge completed with status {command.status}"
            set_batch_risk_state(batch_id, "escalated", reason=reason)
            return "action_required", order_ids, reason
        with connection() as db:
            db.execute(
                """
                UPDATE execution_batches
                SET status = 'hedged', requires_manual_intervention = 0,
                    failure_reason = NULL, updated_at = ?
                WHERE id = ?
                """,
                (now_iso(), batch_id),
            )
        set_batch_risk_state(
            batch_id,
            "resolved",
            residual=Decimal("0"),
            currency="UNKNOWN",
            quality="complete",
            reason="Replacement hedge filled",
        )
        return "completed", order_ids, None

    with connection() as db:
        legs = db.execute(
            """
            SELECT role, account_id, instrument_id, symbol, side, quantity, order_id
            FROM execution_batch_legs
            WHERE batch_id = ? AND status = 'filled'
            ORDER BY sequence
            """,
            (batch_id,),
        ).fetchall()
    if not legs:
        set_batch_risk_state(
            batch_id,
            "resolved",
            residual=Decimal("0"),
            currency="UNKNOWN",
            quality="complete",
            reason="No filled legs required flattening",
        )
        return "completed", [], None

    order_ids: list[str] = []
    failures: list[str] = []
    for leg in legs:
        quantity = filled_quantity(leg["order_id"], Decimal(leg["quantity"]))
        command = create_trade_command(
            CreateTradeCommandRequest(
                idempotencyKey=f"{request.idempotency_key}:{leg['role']}",
                strategyInstanceId=risk.strategy_instance_id,
                accountId=leg["account_id"],
                instrumentId=leg["instrument_id"],
                symbol=leg["symbol"],
                side="sell" if leg["side"] == "buy" else "buy",
                orderType="market",
                quantity=quantity,
                price=None,
            )
        )
        if command.platform_order_id:
            order_ids.append(command.platform_order_id)
        if command.status != "filled":
            failures.append(f"{leg['role']} flatten status {command.status}")

    if failures:
        failure_reason = "; ".join(failures)
        set_batch_risk_state(batch_id, "escalated", reason=failure_reason)
        with connection() as db:
            db.execute(
                """
                UPDATE execution_batches
                SET status = 'manual_intervention', requires_manual_intervention = 1,
                    failure_reason = ?, updated_at = ?
                WHERE id = ?
                """,
                (failure_reason, now_iso(), batch_id),
            )
        return "action_required", order_ids, failure_reason

    with connection() as db:
        db.execute(
            """
            UPDATE execution_batches
            SET status = 'failed', requires_manual_intervention = 0,
                failure_reason = 'Residual exposure flattened', updated_at = ?
            WHERE id = ?
            """,
            (now_iso(), batch_id),
        )
    set_batch_risk_state(
        batch_id,
        "resolved",
        residual=Decimal("0"),
        currency="UNKNOWN",
        quality="complete",
        reason="All filled legs flattened",
    )
    return "completed", order_ids, None


def filled_quantity(order_id: str | None, fallback: Decimal) -> Decimal:
    if order_id is None:
        return fallback
    with connection() as db:
        rows = db.execute("SELECT quantity FROM fills WHERE order_id = ?", (order_id,)).fetchall()
    if not rows:
        return fallback
    return sum(Decimal(row["quantity"]) for row in rows)


def list_risk_actions(batch_id: str) -> list[RiskActionResponse]:
    ensure_schema()
    get_batch_risk(batch_id)
    with connection() as db:
        rows = db.execute(
            """
            SELECT * FROM execution_risk_actions
            WHERE batch_id = ? ORDER BY created_at
            """,
            (batch_id,),
        ).fetchall()
    return [risk_action_from_row(row) for row in rows]


def kill_switch_from_row(row) -> KillSwitchResponse:
    return KillSwitchResponse(
        scopeType=row["scope_type"],
        scopeId=row["scope_id"],
        enabled=bool(row["enabled"]),
        reason=row["reason"],
        actor=row["actor"],
        version=row["version"],
        updatedAt=row["updated_at"],
    )


def policy_from_row(row, *, source: Literal["default", "configured"]) -> ExecutionRiskPolicyResponse:
    return ExecutionRiskPolicyResponse(
        strategyInstanceId=row["strategy_instance_id"],
        maxLegDelaySeconds=row["max_leg_delay_seconds"],
        maxResidualNotional=Decimal(row["max_residual_notional"]),
        failureAction=row["failure_action"],
        source=source,
        actor=row["actor"],
        updatedAt=row["updated_at"],
    )


def batch_risk_from_row(row) -> BatchRiskResponse:
    return BatchRiskResponse(
        batchId=row["batch_id"],
        strategyInstanceId=row["strategy_instance_id"],
        maxLegDelaySeconds=row["max_leg_delay_seconds"],
        maxResidualNotional=Decimal(row["max_residual_notional"]),
        failureAction=row["failure_action"],
        riskStatus=row["risk_status"],
        residualExposureNotional=Decimal(row["residual_exposure_notional"]),
        residualCurrency=row["residual_currency"],
        dataQualityState=row["data_quality_state"],
        firstFillAt=row["first_fill_at"],
        lastLegAt=row["last_leg_at"],
        riskReason=row["risk_reason"],
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


def risk_action_from_row(row) -> RiskActionResponse:
    return RiskActionResponse(
        riskActionId=row["id"],
        idempotencyKey=row["idempotency_key"],
        batchId=row["batch_id"],
        action=row["action"],
        status=row["status"],
        actor=row["actor"],
        reason=row["reason"],
        generatedOrderIds=json.loads(row["generated_order_ids_json"]),
        failureReason=row["failure_reason"],
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


router = APIRouter(prefix=get_settings().api_prefix)


@router.get(
    "/risk/kill-switches/{scope_type}/{scope_id}",
    response_model=KillSwitchResponse,
    tags=["execution-risk"],
)
def read_kill_switch(scope_type: str, scope_id: str) -> KillSwitchResponse:
    return get_kill_switch(scope_type, scope_id)


@router.put(
    "/risk/kill-switches/{scope_type}/{scope_id}",
    response_model=KillSwitchResponse,
    tags=["execution-risk"],
)
def change_kill_switch(
    scope_type: str,
    scope_id: str,
    request: KillSwitchUpdateRequest,
) -> KillSwitchResponse:
    return set_kill_switch(scope_type, scope_id, request)


@router.get(
    "/strategies/instances/{strategy_instance_id}/execution-risk-policy",
    response_model=ExecutionRiskPolicyResponse,
    tags=["execution-risk"],
)
def read_execution_risk_policy(strategy_instance_id: str) -> ExecutionRiskPolicyResponse:
    return get_execution_risk_policy(strategy_instance_id)


@router.put(
    "/strategies/instances/{strategy_instance_id}/execution-risk-policy",
    response_model=ExecutionRiskPolicyResponse,
    tags=["execution-risk"],
)
def change_execution_risk_policy(
    strategy_instance_id: str,
    request: ExecutionRiskPolicyUpdateRequest,
) -> ExecutionRiskPolicyResponse:
    return set_execution_risk_policy(strategy_instance_id, request)


@router.get(
    "/trading/execution-batches/{batch_id}/risk",
    response_model=BatchRiskResponse,
    tags=["execution-risk"],
)
def read_batch_risk(batch_id: str) -> BatchRiskResponse:
    return get_batch_risk(batch_id)


@router.get(
    "/trading/execution-batches/{batch_id}/risk-actions",
    response_model=list[RiskActionResponse],
    tags=["execution-risk"],
)
def read_risk_actions(batch_id: str) -> list[RiskActionResponse]:
    return list_risk_actions(batch_id)


@router.post(
    "/trading/execution-batches/{batch_id}/risk-actions",
    response_model=RiskActionResponse,
    tags=["execution-risk"],
)
def create_risk_action(batch_id: str, request: RiskActionRequest) -> RiskActionResponse:
    return execute_risk_action(batch_id, request)
