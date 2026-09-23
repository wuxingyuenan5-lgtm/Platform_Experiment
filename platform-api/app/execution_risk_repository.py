from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import ROUND_FLOOR, Decimal
from sqlite3 import Connection, Row
from typing import Any, Literal
from uuid import uuid4

from app.database import connection
from app.execution_exposure import batch_order_ids, exposure_evidence
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
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode(
        "utf-8"
    )
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


def claim_risk_action(batch_id: str, request: RiskActionRequest) -> tuple[RiskActionResponse, bool]:
    ensure_schema()
    payload_hash = canonical_hash(request.model_dump(by_alias=True, mode="json"))
    created_at = now_iso()
    action_id = str(uuid4())
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute(
            "SELECT * FROM execution_risk_actions WHERE idempotency_key = ?",
            (request.idempotency_key,),
        ).fetchone()
        if existing is not None:
            if existing["payload_hash"] != payload_hash or existing["batch_id"] != batch_id:
                raise IdempotencyConflictError(
                    "Risk-action idempotency key was reused with a different payload"
                )
            return risk_action_from_row(existing), False
        active = db.execute(
            "SELECT id FROM execution_risk_actions WHERE batch_id=? AND status='processing'",
            (batch_id,),
        ).fetchone()
        if active is not None:
            raise ExecutionRiskRepositoryError("Another risk action is still processing")
        if request.action == "flatten_filled_legs":
            batch = db.execute(
                "SELECT status FROM execution_batches WHERE id=?", (batch_id,)
            ).fetchone()
            if batch is None or batch["status"] not in {"failed", "manual_intervention"}:
                raise ExecutionRiskRepositoryError("Pause the failed batch before flattening")
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
        # Preserve commands already sent even if a later query or leg raises.
        sent = db.execute(
            "SELECT o.id FROM execution_risk_actions a "
            "JOIN execution_batch_legs l ON l.batch_id=a.batch_id "
            "JOIN trade_commands c ON c.idempotency_key=a.idempotency_key || ':' || l.role "
            "JOIN orders o ON o.command_id=c.id WHERE a.id=? "
            "UNION SELECT o.id FROM execution_risk_actions a "
            "JOIN trade_commands c ON c.idempotency_key=a.idempotency_key || ':replacement' "
            "JOIN orders o ON o.command_id=c.id WHERE a.id=?",
            (action_id, action_id),
        ).fetchall()
        order_ids = list(dict.fromkeys([*order_ids, *(row[0] for row in sent)]))
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
    """Finalize only proven flat positions, together with Funding resource release."""
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        batch_key = db.execute(
            "SELECT strategy_key FROM execution_batches WHERE id=?", (batch_id,)
        ).fetchone()
        allow_funding_dust = batch_key is not None and batch_key["strategy_key"] == "funding_arbitrage"
        positions, proof = flattening_positions(db, batch_id, allow_dust=allow_funding_dust)
        if any(item["quantity"] != 0 for item in positions):
            raise ExecutionRiskRepositoryError(
                "Risk-reduction executions do not prove flat positions"
            )
        action = db.execute(
            "SELECT id FROM execution_risk_actions WHERE batch_id=? "
            "AND action='flatten_filled_legs' AND status='completed' LIMIT 1",
            (batch_id,),
        ).fetchone()
        if action is None:
            raise ExecutionRiskRepositoryError("A completed flatten action is required")
        batch = db.execute("SELECT * FROM execution_batches WHERE id=?", (batch_id,)).fetchone()
        instruction = db.execute(
            "SELECT status,failure_reason FROM strategy_runs WHERE id=?",
            (batch["strategy_instruction_id"],),
        ).fetchone()
        already_final = (
            batch["status"] == "failed"
            and not batch["requires_manual_intervention"]
            and (instruction is None or instruction["status"] == "failed")
            and db.execute(
                "SELECT risk_status FROM execution_batch_risk WHERE batch_id=?", (batch_id,)
            ).fetchone()[0]
            == "resolved"
            and db.execute(
                "SELECT 1 FROM audit_events WHERE event_type='execution_batch_flattened' "
                "AND subject_id=?",
                (batch_id,),
            ).fetchone()
            is not None
        )
        if already_final:
            return
        at = now_iso()
        db.execute(
            """
            UPDATE execution_batches
            SET status = 'failed', requires_manual_intervention = 0,
                failure_reason = 'Residual exposure flattened', updated_at = ?
            WHERE id = ?
            """,
            (at, batch_id),
        )
        db.execute(
            "UPDATE execution_batch_legs SET status='canceled',failure_reason=?,updated_at=? "
            "WHERE batch_id=? AND order_id IS NULL AND status IN ('pending','blocked')",
            ("Canceled after verified risk flattening", at, batch_id),
        )
        if batch["strategy_key"] == "funding_arbitrage":
            db.execute(
                "UPDATE strategy_runs SET status='failed',failure_reason=?,updated_at=? WHERE id=?",
                ("Residual exposure flattened", at, batch["strategy_instruction_id"]),
            )
        db.execute(
            "UPDATE execution_batch_risk SET risk_status='resolved',residual_exposure_notional='0',"
            "data_quality_state='complete',risk_reason=?,updated_at=? WHERE batch_id=?",
            ("All owned positions verified flat", at, batch_id),
        )
        release_claims_for_owner("batch", batch_id, db=db)
        release_reservations_for_owner("batch", batch_id, db=db)
        db.execute(
            "INSERT INTO audit_events(id,event_type,subject_type,subject_id,details_json,created_at) "
            "VALUES (?,'execution_batch_flattened','execution_batch',?,?,?)",
            (
                str(uuid4()),
                batch_id,
                json.dumps(
                    {
                        "orders": proof,
                        "previousBatchStatus": batch["status"],
                        "previousFailureReason": batch["failure_reason"],
                        "previousInstructionFailureReason": instruction["failure_reason"]
                        if instruction
                        else None,
                    },
                    sort_keys=True,
                ),
                at,
            ),
        )


def live_order_ids_for_batch(batch_id: str) -> list[str]:
    with connection() as db:
        owned = batch_order_ids(db, batch_id)
        return [
            row[0]
            for row in db.execute(
                "SELECT o.id FROM orders o JOIN accounts a ON a.id=o.account_id "
                "JOIN trade_commands c ON c.id=o.command_id WHERE a.environment='live' "
                "AND NOT (o.status='rejected' AND c.status='rejected' "
                "AND o.external_order_id IS NULL AND NOT EXISTS "
                "(SELECT 1 FROM fills f WHERE f.order_id=o.id)) ORDER BY o.created_at,o.id"
            )
            if row[0] in owned
        ]


def flattening_positions(
    db: Connection, batch_id: str, allow_dust: bool = False
) -> tuple[list[dict[str, Any]], list[dict]]:
    """Calculate remaining positions, optionally flooring Funding fee dust to venue steps."""
    from app.strategies.domain import ExecutionPlan
    from app.strategy_financial_readmodel import _native_fills_for_orders

    _, _, quality, proof = exposure_evidence(db, batch_id)
    if quality != "complete":
        raise ExecutionRiskRepositoryError(
            "Risk reduction requires complete terminal execution evidence"
        )
    uncertain = db.execute(
        "SELECT 1 FROM funding_perpetual_attempts WHERE batch_id=? AND order_id IS NULL "
        "AND status NOT IN ('rejected','canceled','failed') "
        "UNION SELECT 1 FROM funding_spot_release_commands WHERE batch_id=? AND order_id IS NULL "
        "AND status NOT IN ('rejected','canceled','failed') LIMIT 1",
        (batch_id, batch_id),
    ).fetchone()
    if uncertain is not None:
        raise ExecutionRiskRepositoryError("Funding child command outcome is unresolved")
    positions: dict[tuple[str, str], dict[str, Any]] = {}
    instruction = db.execute(
        "SELECT r.execution_plan_json FROM strategy_runs r JOIN execution_batches b "
        "ON b.strategy_instruction_id=r.id WHERE b.id=? AND b.strategy_key='funding_arbitrage'",
        (batch_id,),
    ).fetchone()
    plan_legs = (
        ExecutionPlan.model_validate_json(instruction[0]).legs
        if instruction and instruction[0]
        else []
    )
    for leg in db.execute(
        "SELECT * FROM execution_batch_legs WHERE batch_id=? ORDER BY sequence", (batch_id,)
    ):
        key = (leg["account_id"], leg["instrument_id"])
        if key in positions:
            raise ExecutionRiskRepositoryError("Risk reduction has ambiguous instrument legs")
        positions[key] = {**dict(leg), "quantity": Decimal(0), "net": Decimal(0)}
    for item in proof:
        order = db.execute(
            "SELECT o.*,i.instrument_type,i.base_currency,a.environment FROM orders o "
            "JOIN instruments i ON i.id=o.instrument_id JOIN accounts a ON a.id=o.account_id "
            "WHERE o.id=?",
            (item["orderId"],),
        ).fetchone()
        key = (order["account_id"], order["instrument_id"])
        if key not in positions:
            raise ExecutionRiskRepositoryError(
                "Replacement instrument requires separate disposition"
            )
        quantity = Decimal(item["quantity"])
        delta = quantity * (1 if order["side"] == "buy" else -1)
        if (
            order["instrument_type"] == "crypto_spot"
            and order["environment"] == "live"
            and quantity
        ):
            fills = _native_fills_for_orders(db, {item["orderId"]})
            if not fills:
                raise ExecutionRiskRepositoryError("Native spot fees are required for flattening")
            observed = Decimal(0)
            for fill in fills:
                native = json.loads(fill["payload_json"])
                observed += Decimal(str(native["quantity"]))
                if native.get("fee") is None or native.get("currency") in {None, "", "UNKNOWN"}:
                    raise ExecutionRiskRepositoryError("Native spot fee currency is unavailable")
                if native["currency"] == order["base_currency"]:
                    delta -= Decimal(str(native["fee"]))
            if observed != quantity:
                raise ExecutionRiskRepositoryError("Native spot execution coverage is incomplete")
        positions[key]["net"] += delta
    for position in positions.values():
        net = position.pop("net")
        if net and (net > 0) != (position["side"] == "buy"):
            raise ExecutionRiskRepositoryError(
                "Prior risk reduction exceeded the original position"
            )
        quantity = abs(net)
        spec = db.execute(
            "SELECT i.instrument_type,cs.quantity_step FROM instruments i "
            "JOIN contract_specifications cs ON cs.instrument_id=i.id WHERE i.id=? "
            "ORDER BY cs.effective_from DESC LIMIT 1",
            (position["instrument_id"],),
        ).fetchone()
        if quantity and spec["instrument_type"] not in {"crypto_spot", "crypto_perp"}:
            raise ExecutionRiskRepositoryError(
                "This position requires a venue-specific close target"
            )
        step = Decimal(spec["quantity_step"])
        planned = [
            leg
            for leg in plan_legs
            if leg.account_id == position["account_id"]
            and leg.instrument_id == position["instrument_id"]
        ]
        if len(planned) == 1:
            step = planned[0].quantity_step
        if step <= 0 or not step.is_finite():
            raise ExecutionRiskRepositoryError("Risk reduction quantity step is unavailable")
        position["quantity"] = (quantity / step).to_integral_value(rounding=ROUND_FLOOR) * step
        dust = quantity - position["quantity"]
        if dust and allow_dust and spec["instrument_type"] == "crypto_spot":
            position["dustQuantity"] = str(dust)
        elif position["quantity"] != quantity:
            raise ExecutionRiskRepositoryError(
                "Residual quantity requires explicit dust disposition"
            )
    return list(positions.values()), proof


def batch_has_verified_flattening(batch_id: str) -> bool:
    with connection() as db:
        if (
            db.execute(
                "SELECT 1 FROM audit_events WHERE subject_id=? "
                "AND event_type='execution_batch_flattened' LIMIT 1",
                (batch_id,),
            ).fetchone()
            is None
        ):
            return False
        row = db.execute(
            "SELECT 1 FROM audit_events e JOIN execution_batches b ON b.id=e.subject_id "
            "JOIN execution_batch_risk r ON r.batch_id=b.id WHERE b.id=? "
            "AND e.event_type='execution_batch_flattened' AND b.status='failed' "
            "AND r.risk_status='resolved' AND r.data_quality_state='complete' LIMIT 1",
            (batch_id,),
        ).fetchone()
        return row is not None


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
    from app.venue_identity_repository import order_execution_evidence

    if order_id is None:
        raise ExecutionRiskRepositoryError("Risk reduction requires an identified order")
    with connection() as db:
        quantity, _, complete, _ = order_execution_evidence(db, order_id)
    if not complete or quantity <= 0:
        raise ExecutionRiskRepositoryError("Risk reduction requires unambiguous execution evidence")
    return quantity


def recheck_batch_risk(batch_id: str, *, reason: str) -> BatchRiskResponse | None:
    """Refresh a finished batch's risk atomically with an evidence-bearing audit.

    Never submits orders or rewrites fills, financial facts or exit plans.
    A background account snapshot alone is not an execution reconciliation.
    """
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        if (
            db.execute("SELECT 1 FROM sqlite_master WHERE name='execution_batch_risk'").fetchone()
            is None
        ):
            return None
        before = db.execute(
            "SELECT * FROM execution_batch_risk WHERE batch_id=?", (batch_id,)
        ).fetchone()
        batch = db.execute(
            "SELECT status FROM execution_batches WHERE id=?", (batch_id,)
        ).fetchone()
        if before is None or batch is None:
            return None
        if batch["status"] not in {"hedged", "failed", "manual_intervention"}:
            return batch_risk_from_row(before)
        residual, currency, quality, proof = exposure_evidence(db, batch_id)
        pending = db.execute(
            "SELECT 1 FROM execution_batch_legs WHERE batch_id=? AND order_id IS NULL "
            "AND status NOT IN ('blocked','failed','rejected','canceled') LIMIT 1",
            (batch_id,),
        ).fetchone()
        if pending is not None:
            quality = "incomplete"
        status = (
            ("resolved" if before["risk_status"] != "clear" else "clear")
            if residual == 0 and quality == "complete"
            else "escalated"
        )
        state = (status, format(residual, "f"), currency, quality)
        previous = tuple(
            before[key]
            for key in (
                "risk_status",
                "residual_exposure_notional",
                "residual_currency",
                "data_quality_state",
            )
        )
        if state != previous:
            at = now_iso()
            db.execute(
                "UPDATE execution_batch_risk SET risk_status=?,residual_exposure_notional=?,"
                "residual_currency=?,data_quality_state=?,risk_reason=?,updated_at=? WHERE batch_id=?",
                (*state, reason, at, batch_id),
            )
            db.execute(
                "INSERT INTO audit_events (id,event_type,subject_type,subject_id,details_json,created_at) "
                "VALUES (?,?,?,?,?,?)",
                (
                    str(uuid4()),
                    "execution_batch_risk_reconciled",
                    "execution_batch",
                    batch_id,
                    json.dumps(
                        {
                            "before": dict(before),
                            "riskStatus": status,
                            "residualExposureNotional": str(residual),
                            "residualCurrency": currency,
                            "dataQualityState": quality,
                            "reason": reason,
                            "orders": proof,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    at,
                ),
            )
        after = db.execute(
            "SELECT * FROM execution_batch_risk WHERE batch_id=?", (batch_id,)
        ).fetchone()
        return batch_risk_from_row(after)


def recheck_risks_for_order(order_id: str, *, reason: str) -> None:
    with connection() as db:
        if (
            db.execute("SELECT 1 FROM sqlite_master WHERE name='execution_batch_risk'").fetchone()
            is None
        ):
            return
        batch_ids = {
            row[0]
            for row in db.execute(
                "SELECT batch_id FROM execution_batch_legs WHERE order_id=?", (order_id,)
            )
        }
        command = db.execute(
            "SELECT tc.idempotency_key FROM orders o JOIN trade_commands tc ON tc.id=o.command_id WHERE o.id=?",
            (order_id,),
        ).fetchone()
        if (
            command
            and command[0].startswith("cross-spread-rollback:")
            and command[0].endswith(":bybit")
        ):
            batch_ids.add(command[0][len("cross-spread-rollback:") : -len(":bybit")])
        batch_ids.update(
            row[0]
            for row in db.execute(
                "SELECT a.batch_id FROM execution_risk_actions a,json_each(a.generated_order_ids_json) j "
                "WHERE j.value=?",
                (order_id,),
            )
        )
    for batch_id in sorted(batch_ids):
        recheck_batch_risk(batch_id, reason=reason)


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
