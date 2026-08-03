from __future__ import annotations

import json
from datetime import UTC, datetime
from sqlite3 import Row
from uuid import uuid4

from app.database import connection
from app.venue_reconciliation_schemas import (
    DifferenceType,
    ReconciliationDifferenceResponse,
    VenueReconciliationRunResponse,
)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS venue_reconciliation_runs (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    payload_hash TEXT NOT NULL,
    strategy_instance_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    run_type TEXT NOT NULL,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    order_count INTEGER NOT NULL,
    fill_count INTEGER NOT NULL,
    position_count INTEGER NOT NULL,
    balance_count INTEGER NOT NULL,
    fact_count INTEGER NOT NULL,
    difference_count INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY(strategy_instance_id) REFERENCES strategy_instances(id),
    FOREIGN KEY(account_id) REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS reconciliation_differences (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    difference_key TEXT NOT NULL,
    difference_type TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    local_reference TEXT,
    external_reference TEXT,
    local_value_json TEXT NOT NULL,
    external_value_json TEXT NOT NULL,
    status TEXT NOT NULL,
    resolution_actor TEXT,
    resolution_reason TEXT,
    resolved_at TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(run_id, difference_key),
    FOREIGN KEY(run_id) REFERENCES venue_reconciliation_runs(id)
);

CREATE INDEX IF NOT EXISTS idx_reconciliation_runs_account
ON venue_reconciliation_runs(account_id, started_at);

CREATE INDEX IF NOT EXISTS idx_reconciliation_differences_run
ON reconciliation_differences(run_id, status, difference_type);
"""


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


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


def load_strategy_instance_id_for_command(command_id: str) -> str | None:
    with connection() as db:
        row = db.execute(
            "SELECT strategy_instance_id FROM trade_commands WHERE id = ?",
            (command_id,),
        ).fetchone()
    return row["strategy_instance_id"] if row is not None else None


def update_order_from_external(
    order_id: str,
    status: str,
    external_order_id: object,
    updated_at: object,
) -> None:
    with connection() as db:
        db.execute(
            """
            UPDATE orders
            SET status = ?, external_order_id = ?, updated_at = ?
            WHERE id = ? AND status != 'filled'
            """,
            (status, external_order_id, updated_at, order_id),
        )


def list_fill_quantities(order_id: str) -> list[object]:
    with connection() as db:
        rows = db.execute(
            "SELECT quantity FROM fills WHERE order_id = ?",
            (order_id,),
        ).fetchall()
    return [row["quantity"] for row in rows]


def ensure_standalone_order_run(
    *,
    order_id: str,
    run_id: str,
    payload_hash: str,
    started_at: str,
    completed_at: str,
) -> None:
    with connection() as db:
        db.execute(
            """
            INSERT OR IGNORE INTO venue_reconciliation_runs (
                id, idempotency_key, payload_hash, strategy_instance_id, account_id,
                run_type, source, status, order_count, fill_count, position_count,
                balance_count, fact_count, difference_count, started_at, completed_at
            )
            SELECT ?, ?, ?, tc.strategy_instance_id, o.account_id, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            FROM orders o JOIN trade_commands tc ON tc.id = o.command_id
            WHERE o.id = ?
            """,
            (
                run_id,
                run_id,
                payload_hash,
                "order",
                "runtime",
                "completed_with_differences",
                1,
                0,
                0,
                0,
                0,
                1,
                started_at,
                completed_at,
                order_id,
            ),
        )


def load_run_by_idempotency_key(idempotency_key: str) -> Row | None:
    with connection() as db:
        return db.execute(
            "SELECT * FROM venue_reconciliation_runs WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()


def create_account_snapshot_run(
    *,
    run_id: str,
    idempotency_key: str,
    payload_hash: str,
    strategy_instance_id: str,
    account_id: str,
    source: str,
    position_count: int,
    balance_count: int,
    started_at: str,
) -> None:
    with connection() as db:
        db.execute(
            """
            INSERT INTO venue_reconciliation_runs (
                id, idempotency_key, payload_hash, strategy_instance_id, account_id,
                run_type, source, status, order_count, fill_count, position_count,
                balance_count, fact_count, difference_count, started_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                idempotency_key,
                payload_hash,
                strategy_instance_id,
                account_id,
                "account_snapshot",
                source,
                "processing",
                0,
                0,
                position_count,
                balance_count,
                0,
                0,
                started_at,
                None,
            ),
        )


def complete_account_snapshot_run(
    *,
    run_id: str,
    status: str,
    fact_count: int,
    difference_count: int,
    completed_at: str,
) -> Row:
    with connection() as db:
        db.execute(
            """
            UPDATE venue_reconciliation_runs
            SET status = ?, fact_count = ?, difference_count = ?, completed_at = ?
            WHERE id = ?
            """,
            (status, fact_count, difference_count, completed_at, run_id),
        )
        row = db.execute(
            "SELECT * FROM venue_reconciliation_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
    assert row is not None
    return row


def has_active_strategy_account(strategy_instance_id: str, account_id: str) -> bool:
    with connection() as db:
        row = db.execute(
            """
            SELECT sab.id
            FROM strategy_account_bindings sab
            JOIN strategy_instances si ON si.id = sab.strategy_instance_id
            JOIN accounts a ON a.id = sab.account_id
            WHERE sab.strategy_instance_id = ? AND sab.account_id = ?
              AND sab.status = 'active' AND si.status = 'active' AND a.status = 'active'
            """,
            (strategy_instance_id, account_id),
        ).fetchone()
    return row is not None


def load_comparison_position(
    strategy_instance_id: str,
    account_id: str,
    instrument_id: object,
) -> dict[str, object] | None:
    with connection() as db:
        row = db.execute(
            """
            SELECT net_quantity, average_price
            FROM formal_positions
            WHERE strategy_instance_id = ? AND account_id = ? AND instrument_id = ?
            """,
            (strategy_instance_id, account_id, instrument_id),
        ).fetchone()
        if row is None:
            row = db.execute(
                """
                SELECT net_quantity, average_price
                FROM positions
                WHERE account_id = ? AND instrument_id = ?
                """,
                (account_id, instrument_id),
            ).fetchone()
    return dict(row) if row is not None else None


def load_latest_balance(account_id: str) -> dict[str, object] | None:
    with connection() as db:
        row = db.execute(
            """
            SELECT equity, available_balance, currency
            FROM balance_snapshots
            WHERE account_id = ?
            ORDER BY as_of DESC, created_at DESC
            LIMIT 1
            """,
            (account_id,),
        ).fetchone()
    return dict(row) if row is not None else None


def store_difference(
    run_id: str,
    difference_key: str,
    difference_type: DifferenceType,
    entity_type: str,
    local_reference: str | None,
    external_reference: str | None,
    local_value: dict[str, object],
    external_value: dict[str, object],
) -> str:
    difference_id = str(uuid4())
    with connection() as db:
        db.execute(
            """
            INSERT OR IGNORE INTO reconciliation_differences (
                id, run_id, difference_key, difference_type, entity_type,
                local_reference, external_reference, local_value_json,
                external_value_json, status, resolution_actor, resolution_reason,
                resolved_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                difference_id,
                run_id,
                difference_key,
                difference_type,
                entity_type,
                local_reference,
                external_reference,
                json.dumps(local_value, sort_keys=True, default=str),
                json.dumps(external_value, sort_keys=True, default=str),
                "open",
                None,
                None,
                None,
                now_iso(),
            ),
        )
        row = db.execute(
            """
            SELECT id FROM reconciliation_differences
            WHERE run_id = ? AND difference_key = ?
            """,
            (run_id, difference_key),
        ).fetchone()
    assert row is not None
    return row["id"]


def load_run(run_id: str) -> Row | None:
    with connection() as db:
        return db.execute(
            "SELECT * FROM venue_reconciliation_runs WHERE id = ?",
            (run_id,),
        ).fetchone()


def list_difference_rows(run_id: str) -> list[Row]:
    with connection() as db:
        return db.execute(
            """
            SELECT * FROM reconciliation_differences
            WHERE run_id = ? ORDER BY created_at, difference_key
            """,
            (run_id,),
        ).fetchall()


def resolve_difference_row(
    *,
    difference_id: str,
    status: str,
    actor: str,
    reason: str,
    resolved_at: str,
) -> tuple[Row | None, bool]:
    with connection() as db:
        row = db.execute(
            "SELECT * FROM reconciliation_differences WHERE id = ?",
            (difference_id,),
        ).fetchone()
        if row is None or row["status"] != "open":
            return row, False
        db.execute(
            """
            UPDATE reconciliation_differences
            SET status = ?, resolution_actor = ?, resolution_reason = ?, resolved_at = ?
            WHERE id = ?
            """,
            (status, actor, reason, resolved_at, difference_id),
        )
        row = db.execute(
            "SELECT * FROM reconciliation_differences WHERE id = ?",
            (difference_id,),
        ).fetchone()
    assert row is not None
    return row, True


def run_from_row(row: Row) -> VenueReconciliationRunResponse:
    return VenueReconciliationRunResponse(
        runId=row["id"],
        idempotencyKey=row["idempotency_key"],
        strategyInstanceId=row["strategy_instance_id"],
        accountId=row["account_id"],
        runType=row["run_type"],
        source=row["source"],
        status=row["status"],
        orderCount=row["order_count"],
        fillCount=row["fill_count"],
        positionCount=row["position_count"],
        balanceCount=row["balance_count"],
        factCount=row["fact_count"],
        differenceCount=row["difference_count"],
        startedAt=row["started_at"],
        completedAt=row["completed_at"],
    )


def difference_from_row(row: Row) -> ReconciliationDifferenceResponse:
    return ReconciliationDifferenceResponse(
        differenceId=row["id"],
        runId=row["run_id"],
        differenceKey=row["difference_key"],
        differenceType=row["difference_type"],
        entityType=row["entity_type"],
        localReference=row["local_reference"],
        externalReference=row["external_reference"],
        localValue=json.loads(row["local_value_json"]),
        externalValue=json.loads(row["external_value_json"]),
        status=row["status"],
        resolutionActor=row["resolution_actor"],
        resolutionReason=row["resolution_reason"],
        resolvedAt=row["resolved_at"],
        createdAt=row["created_at"],
    )
