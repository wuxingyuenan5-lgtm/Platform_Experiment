from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from sqlite3 import Connection, Row
from typing import Literal
from uuid import uuid4

from app.database import connection
from app.execution_risk_models import (
    BatchRiskResponse,
    ExecutionRiskPolicyResponse,
    ExecutionRiskPolicyUpdateRequest,
    KillSwitchResponse,
    KillSwitchScope,
    KillSwitchUpdateRequest,
    RiskActionRequest,
    RiskActionResponse,
    RiskStatus,
)

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

CREATE TABLE IF NOT EXISTS execution_resource_claims (
    id TEXT PRIMARY KEY,
    resource_key TEXT NOT NULL,
    owner_type TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    venue_id TEXT NOT NULL,
    resource_category TEXT NOT NULL,
    symbol TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS execution_balance_reservations (
    id TEXT PRIMARY KEY,
    owner_type TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    strategy_instance_id TEXT NOT NULL,
    instruction_id TEXT,
    currency TEXT NOT NULL,
    reserved_amount TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_execution_resource_claims_owner
ON execution_resource_claims(owner_type, owner_id, status);

CREATE UNIQUE INDEX IF NOT EXISTS idx_execution_resource_claims_active_resource
ON execution_resource_claims(resource_key)
WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_execution_balance_reservations_account
ON execution_balance_reservations(account_id, currency, status);
"""


class ExecutionRiskRepositoryError(RuntimeError):
    pass


class IdempotencyConflictError(ExecutionRiskRepositoryError):
    pass


class RepositoryInvariantError(ExecutionRiskRepositoryError):
    pass


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def canonical_hash(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def ensure_schema() -> None:
    with connection() as db:
        db.executescript(SCHEMA_SQL)


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


def strategy_exists(strategy_instance_id: str) -> bool:
    with connection() as db:
        row = db.execute(
            "SELECT id FROM strategy_instances WHERE id = ?", (strategy_instance_id,)
        ).fetchone()
    return row is not None


def account_exists(account_id: str) -> bool:
    with connection() as db:
        row = db.execute("SELECT id FROM accounts WHERE id = ?", (account_id,)).fetchone()
    return row is not None


def get_kill_switch(scope_type: KillSwitchScope, scope_id: str) -> KillSwitchResponse | None:
    ensure_schema()
    with connection() as db:
        row = db.execute(
            "SELECT * FROM trading_kill_switches WHERE scope_type = ? AND scope_id = ?",
            (scope_type, scope_id),
        ).fetchone()
    return None if row is None else kill_switch_from_row(row)


def set_kill_switch(
    scope_type: KillSwitchScope,
    scope_id: str,
    request: KillSwitchUpdateRequest,
) -> KillSwitchResponse:
    ensure_schema()
    payload = {
        "scopeType": scope_type,
        "scopeId": scope_id,
        "enabled": request.enabled,
        "reason": request.reason,
        "actor": request.actor,
    }
    payload_hash = canonical_hash(payload)
    changed_at = now_iso()
    with connection() as db:
        existing = db.execute(
            "SELECT payload_hash FROM kill_switch_commands WHERE idempotency_key = ?",
            (request.idempotency_key,),
        ).fetchone()
        if existing is not None:
            if existing["payload_hash"] != payload_hash:
                raise IdempotencyConflictError(
                    "Kill-switch idempotency key was reused with a different payload"
                )
            row = db.execute(
                "SELECT * FROM trading_kill_switches WHERE scope_type = ? AND scope_id = ?",
                (scope_type, scope_id),
            ).fetchone()
            if row is None:
                raise RepositoryInvariantError("Kill-switch command result is unavailable")
            return kill_switch_from_row(row)
        previous = db.execute(
            "SELECT version FROM trading_kill_switches WHERE scope_type = ? AND scope_id = ?",
            (scope_type, scope_id),
        ).fetchone()
        version = (previous["version"] if previous is not None else 0) + 1
        db.execute(
            """
            INSERT INTO kill_switch_commands (
                idempotency_key, payload_hash, scope_type, scope_id, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (request.idempotency_key, payload_hash, scope_type, scope_id, changed_at),
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
                scope_type,
                scope_id,
                int(request.enabled),
                request.reason,
                request.actor,
                version,
                changed_at,
            ),
        )
        row = db.execute(
            "SELECT * FROM trading_kill_switches WHERE scope_type = ? AND scope_id = ?",
            (scope_type, scope_id),
        ).fetchone()
    assert row is not None
    audit(
        "kill_switch_changed",
        scope_type,
        scope_id,
        {**payload, "version": version, "idempotencyKey": request.idempotency_key},
    )
    return kill_switch_from_row(row)


def first_enabled_kill_switch(
    strategy_instance_id: str, account_ids: list[str]
) -> tuple[str, str, str] | None:
    ensure_schema()
    candidates = [("global", "*"), ("strategy", strategy_instance_id)]
    candidates.extend(("account", account_id) for account_id in sorted(set(account_ids)))
    with connection() as db:
        for scope_type, scope_id in candidates:
            row = db.execute(
                """
                SELECT enabled, reason FROM trading_kill_switches
                WHERE scope_type = ? AND scope_id = ?
                """,
                (scope_type, scope_id),
            ).fetchone()
            if row is not None and bool(row["enabled"]):
                return scope_type, scope_id, row["reason"] or "No reason provided"
    return None


def get_configured_policy(strategy_instance_id: str) -> ExecutionRiskPolicyResponse | None:
    ensure_schema()
    with connection() as db:
        row = db.execute(
            "SELECT * FROM execution_risk_policies WHERE strategy_instance_id = ?",
            (strategy_instance_id,),
        ).fetchone()
    return None if row is None else policy_from_row(row, source="configured")


def set_execution_risk_policy(
    strategy_instance_id: str,
    request: ExecutionRiskPolicyUpdateRequest,
) -> ExecutionRiskPolicyResponse:
    ensure_schema()
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
                raise IdempotencyConflictError(
                    "Risk-policy idempotency key was reused with a different payload"
                )
            row = db.execute(
                "SELECT * FROM execution_risk_policies WHERE strategy_instance_id = ?",
                (strategy_instance_id,),
            ).fetchone()
            if row is None:
                raise RepositoryInvariantError("Risk-policy command result is unavailable")
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
    assert row is not None
    audit(
        "execution_risk_policy_changed",
        "strategy_instance",
        strategy_instance_id,
        {**payload, "idempotencyKey": request.idempotency_key},
    )
    return policy_from_row(row, source="configured")


def initialize_batch_risk(
    batch_id: str,
    strategy_instance_id: str,
    policy: ExecutionRiskPolicyResponse,
) -> None:
    ensure_schema()
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


def get_batch_risk(batch_id: str) -> BatchRiskResponse | None:
    ensure_schema()
    with connection() as db:
        row = db.execute(
            "SELECT * FROM execution_batch_risk WHERE batch_id = ?", (batch_id,)
        ).fetchone()
    return None if row is None else batch_risk_from_row(row)


def get_batch_strategy_instance_id(batch_id: str) -> str | None:
    with connection() as db:
        row = db.execute(
            "SELECT strategy_instance_id FROM execution_batches WHERE id = ?", (batch_id,)
        ).fetchone()
    return None if row is None else str(row["strategy_instance_id"])


def record_filled_leg(
    batch_id: str,
    status: RiskStatus,
    residual: Decimal,
    currency: str,
    quality: str,
    reason: str | None,
) -> None:
    filled_at = now_iso()
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


def complete_batch_risk(
    batch_id: str,
    status: RiskStatus,
    residual: Decimal,
    currency: str,
    quality: str,
    reason: str | None,
) -> None:
    updated_at = now_iso()
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
                updated_at,
                reason,
                updated_at,
                batch_id,
            ),
        )


def set_batch_risk_state(
    batch_id: str,
    status: RiskStatus,
    *,
    residual: Decimal | None = None,
    currency: str | None = None,
    quality: str | None = None,
    reason: str | None = None,
) -> None:
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


def claim_risk_action(
    batch_id: str, request: RiskActionRequest
) -> tuple[RiskActionResponse, bool]:
    ensure_schema()
    payload_hash = canonical_hash(request.model_dump(by_alias=True, mode="json"))
    created_at = now_iso()
    action_id = str(uuid4())
    with connection() as db:
        existing = db.execute(
            "SELECT * FROM execution_risk_actions WHERE idempotency_key = ?",
            (request.idempotency_key,),
        ).fetchone()
        if existing is not None:
            if existing["payload_hash"] != payload_hash:
                raise IdempotencyConflictError(
                    "Risk-action idempotency key was reused with a different payload"
                )
            return risk_action_from_row(existing), False
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
        row = db.execute(
            "SELECT * FROM execution_risk_actions WHERE id = ?", (action_id,)
        ).fetchone()
    assert row is not None
    return risk_action_from_row(row), True


def finish_risk_action(
    action_id: str,
    batch_id: str,
    request: RiskActionRequest,
    status: str,
    order_ids: list[str],
    failure_reason: str | None,
) -> RiskActionResponse:
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
    assert row is not None
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


def list_risk_actions(batch_id: str) -> list[RiskActionResponse]:
    ensure_schema()
    with connection() as db:
        rows = db.execute(
            "SELECT * FROM execution_risk_actions WHERE batch_id = ? ORDER BY created_at",
            (batch_id,),
        ).fetchall()
    return [risk_action_from_row(row) for row in rows]


def mark_batch_manual_intervention(batch_id: str, reason: str) -> None:
    with connection() as db:
        db.execute(
            """
            UPDATE execution_batches
            SET status = 'manual_intervention', requires_manual_intervention = 1,
                failure_reason = ?, updated_at = ?
            WHERE id = ?
            """,
            (reason, now_iso(), batch_id),
        )


def cancel_pending_legs(batch_id: str, reason: str) -> int:
    with connection() as db:
        db.execute(
            """
            UPDATE execution_batch_legs
            SET status = 'canceled', failure_reason = ?, updated_at = ?
            WHERE batch_id = ? AND order_id IS NULL
              AND status IN ('pending', 'submitting')
            """,
            (reason, now_iso(), batch_id),
        )
        row = db.execute(
            """
            SELECT COUNT(*) AS count FROM execution_batch_legs
            WHERE batch_id = ? AND order_id IS NOT NULL
              AND status IN ('accepted', 'processing', 'acknowledged', 'result_unknown')
            """,
            (batch_id,),
        ).fetchone()
    return int(row["count"])


def mark_batch_hedged(batch_id: str) -> None:
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


def mark_batch_failed_flattened(batch_id: str) -> None:
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


def filled_legs(batch_id: str) -> list[Row]:
    with connection() as db:
        return db.execute(
            """
            SELECT role, account_id, instrument_id, symbol, side, quantity, order_id
            FROM execution_batch_legs
            WHERE batch_id = ? AND status = 'filled'
            ORDER BY sequence
            """,
            (batch_id,),
        ).fetchall()


def filled_quantity(order_id: str | None, fallback: Decimal) -> Decimal:
    if order_id is None:
        return fallback
    with connection() as db:
        rows = db.execute(
            "SELECT quantity FROM fills WHERE order_id = ?", (order_id,)
        ).fetchall()
    if not rows:
        return fallback
    return sum((Decimal(row["quantity"]) for row in rows), start=Decimal("0"))


def active_claim_for_resource(
    resource_key: str,
    *,
    account_id: str,
    db: Connection | None = None,
) -> Row | None:
    if db is not None:
        return db.execute(
            """
            SELECT *
            FROM execution_resource_claims
            WHERE status = 'active'
              AND (
                    resource_key = ?
                    OR (account_id = ? AND resource_category = 'account')
                  )
            LIMIT 1
            """,
            (resource_key, account_id),
        ).fetchone()
    with connection() as managed_db:
        return active_claim_for_resource(resource_key, account_id=account_id, db=managed_db)


def active_non_account_claim_for_account(
    account_id: str,
    *,
    db: Connection | None = None,
) -> Row | None:
    if db is not None:
        return db.execute(
            """
            SELECT *
            FROM execution_resource_claims
            WHERE status = 'active'
              AND account_id = ?
              AND resource_category != 'account'
            LIMIT 1
            """,
            (account_id,),
        ).fetchone()
    with connection() as managed_db:
        return active_non_account_claim_for_account(account_id, db=managed_db)


def active_reserved_amount(
    account_id: str,
    currency: str,
    *,
    db: Connection | None = None,
) -> Decimal:
    if db is not None:
        rows = db.execute(
            """
            SELECT reserved_amount
            FROM execution_balance_reservations
            WHERE account_id = ? AND currency = ? AND status = 'active'
            """,
            (account_id, currency),
        ).fetchall()
        return sum((Decimal(str(row["reserved_amount"])) for row in rows), start=Decimal("0"))
    with connection() as managed_db:
        return active_reserved_amount(account_id, currency, db=managed_db)


def release_claims_for_owner(
    owner_type: str,
    owner_id: str,
    *,
    db: Connection | None = None,
) -> None:
    if db is not None:
        db.execute(
            """
            UPDATE execution_resource_claims
            SET status = 'released', updated_at = ?
            WHERE owner_type = ? AND owner_id = ? AND status = 'active'
            """,
            (now_iso(), owner_type, owner_id),
        )
        return
    ensure_schema()
    with connection() as managed_db:
        release_claims_for_owner(owner_type, owner_id, db=managed_db)


def release_reservations_for_owner(
    owner_type: str,
    owner_id: str,
    *,
    db: Connection | None = None,
) -> None:
    if db is not None:
        db.execute(
            """
            UPDATE execution_balance_reservations
            SET status = 'released', updated_at = ?
            WHERE owner_type = ? AND owner_id = ? AND status = 'active'
            """,
            (now_iso(), owner_type, owner_id),
        )
        return
    ensure_schema()
    with connection() as managed_db:
        release_reservations_for_owner(owner_type, owner_id, db=managed_db)


def kill_switch_from_row(row: Row) -> KillSwitchResponse:
    return KillSwitchResponse(
        scopeType=row["scope_type"],
        scopeId=row["scope_id"],
        enabled=bool(row["enabled"]),
        reason=row["reason"],
        actor=row["actor"],
        version=row["version"],
        updatedAt=row["updated_at"],
    )


def policy_from_row(
    row: Row, *, source: Literal["default", "configured"]
) -> ExecutionRiskPolicyResponse:
    return ExecutionRiskPolicyResponse(
        strategyInstanceId=row["strategy_instance_id"],
        maxLegDelaySeconds=row["max_leg_delay_seconds"],
        maxResidualNotional=Decimal(row["max_residual_notional"]),
        failureAction=row["failure_action"],
        source=source,
        actor=row["actor"],
        updatedAt=row["updated_at"],
    )


def batch_risk_from_row(row: Row) -> BatchRiskResponse:
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


def risk_action_from_row(row: Row) -> RiskActionResponse:
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
