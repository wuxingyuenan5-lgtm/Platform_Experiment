from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from sqlite3 import Row

from app.database import connection
from app.eod_reconciliation_policy import (
    EodReviewConflictError as EodReviewConflictError,
    EodReviewNotEligibleError as EodReviewNotEligibleError,
    review_disposition,
)
from app.eod_reconciliation_schemas import (
    EodReconciliationReportResponse,
    ReviewDecision,
)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS eod_reconciliation_reports (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    natural_key TEXT NOT NULL UNIQUE,
    payload_hash TEXT NOT NULL,
    business_date TEXT NOT NULL,
    timezone TEXT NOT NULL,
    valuation_time TEXT NOT NULL,
    strategy_instance_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    actor TEXT NOT NULL,
    owner TEXT NOT NULL,
    due_at TEXT NOT NULL,
    status TEXT NOT NULL,
    scale_gate_status TEXT NOT NULL,
    order_reconciliation_count INTEGER NOT NULL,
    account_reconciliation_run_id TEXT,
    economic_event_import_id TEXT,
    nav_snapshot_id TEXT,
    formal_pnl_count INTEGER NOT NULL,
    formal_pnl_incomplete_count INTEGER NOT NULL,
    open_difference_count INTEGER NOT NULL,
    resolved_difference_count INTEGER NOT NULL,
    accepted_difference_count INTEGER NOT NULL,
    skipped_external_ids_json TEXT NOT NULL,
    missing_account_ids_json TEXT NOT NULL,
    errors_json TEXT NOT NULL,
    review_payload_hash TEXT,
    reviewer TEXT,
    review_decision TEXT,
    review_reason TEXT,
    reviewed_at TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY(strategy_instance_id) REFERENCES strategy_instances(id),
    FOREIGN KEY(account_id) REFERENCES accounts(id)
);

CREATE INDEX IF NOT EXISTS idx_eod_reports_business_date
ON eod_reconciliation_reports(business_date, strategy_instance_id, account_id);

CREATE INDEX IF NOT EXISTS idx_eod_reports_status
ON eod_reconciliation_reports(status, scale_gate_status, due_at);
"""


class EodReportNotFoundError(LookupError):
    pass


@dataclass(frozen=True)
class ReviewWriteResult:
    row: Row
    changed: bool


def ensure_schema() -> None:
    with connection() as db:
        db.executescript(SCHEMA_SQL)


def load_report_by_identity(idempotency_key: str, natural_key: str) -> Row | None:
    with connection() as db:
        return db.execute(
            """
            SELECT * FROM eod_reconciliation_reports
            WHERE idempotency_key = ? OR natural_key = ?
            ORDER BY created_at
            LIMIT 1
            """,
            (idempotency_key, natural_key),
        ).fetchone()


def insert_initial_report(
    *,
    report_id: str,
    idempotency_key: str,
    natural_key: str,
    payload_hash: str,
    business_date: str,
    timezone: str,
    valuation_time: str,
    strategy_instance_id: str,
    account_id: str,
    actor: str,
    owner: str,
    due_at: str,
    created_at: str,
) -> None:
    with connection() as db:
        db.execute(
            """
            INSERT INTO eod_reconciliation_reports (
                id, idempotency_key, natural_key, payload_hash, business_date,
                timezone, valuation_time, strategy_instance_id, account_id,
                actor, owner, due_at, status, scale_gate_status,
                order_reconciliation_count, account_reconciliation_run_id,
                economic_event_import_id, nav_snapshot_id, formal_pnl_count,
                formal_pnl_incomplete_count, open_difference_count,
                resolved_difference_count, accepted_difference_count,
                skipped_external_ids_json, missing_account_ids_json, errors_json,
                review_payload_hash, reviewer, review_decision, review_reason,
                reviewed_at, created_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                      ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_id,
                idempotency_key,
                natural_key,
                payload_hash,
                business_date,
                timezone,
                valuation_time,
                strategy_instance_id,
                account_id,
                actor,
                owner,
                due_at,
                "partial",
                "blocked",
                0,
                None,
                None,
                None,
                0,
                0,
                0,
                0,
                0,
                "[]",
                "[]",
                "[]",
                None,
                None,
                None,
                None,
                None,
                created_at,
                None,
            ),
        )


def list_difference_ids_for_run(run_id: str) -> list[str]:
    with connection() as db:
        rows = db.execute(
            "SELECT id FROM reconciliation_differences WHERE run_id = ?",
            (run_id,),
        ).fetchall()
    return [row["id"] for row in rows]


def complete_report(
    *,
    report_id: str,
    status: str,
    scale_gate_status: str,
    order_reconciliation_count: int,
    account_reconciliation_run_id: str | None,
    economic_event_import_id: str | None,
    nav_snapshot_id: str | None,
    formal_pnl_count: int,
    formal_pnl_incomplete_count: int,
    open_difference_count: int,
    resolved_difference_count: int,
    accepted_difference_count: int,
    skipped_external_ids: list[str],
    missing_account_ids: list[str],
    errors: list[str],
    completed_at: str,
) -> None:
    with connection() as db:
        db.execute(
            """
            UPDATE eod_reconciliation_reports
            SET status = ?, scale_gate_status = ?, order_reconciliation_count = ?,
                account_reconciliation_run_id = ?, economic_event_import_id = ?,
                nav_snapshot_id = ?, formal_pnl_count = ?,
                formal_pnl_incomplete_count = ?, open_difference_count = ?,
                resolved_difference_count = ?, accepted_difference_count = ?,
                skipped_external_ids_json = ?, missing_account_ids_json = ?,
                errors_json = ?, completed_at = ?
            WHERE id = ?
            """,
            (
                status,
                scale_gate_status,
                order_reconciliation_count,
                account_reconciliation_run_id,
                economic_event_import_id,
                nav_snapshot_id,
                formal_pnl_count,
                formal_pnl_incomplete_count,
                open_difference_count,
                resolved_difference_count,
                accepted_difference_count,
                json.dumps(skipped_external_ids, sort_keys=True),
                json.dumps(missing_account_ids, sort_keys=True),
                json.dumps(errors, ensure_ascii=False, sort_keys=True),
                completed_at,
                report_id,
            ),
        )


def formal_pnl_counts(strategy_instance_id: str, account_id: str) -> tuple[int, int]:
    with connection() as db:
        row = db.execute(
            """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN data_quality_state != 'complete' THEN 1 ELSE 0 END)
                       AS incomplete
            FROM formal_pnl_results
            WHERE strategy_instance_id = ? AND account_id = ?
            """,
            (strategy_instance_id, account_id),
        ).fetchone()
    return int(row["total"] or 0), int(row["incomplete"] or 0)


def difference_status_counts(difference_ids: set[str]) -> tuple[int, int, int]:
    if not difference_ids:
        return 0, 0, 0
    placeholders = ",".join("?" for _ in difference_ids)
    with connection() as db:
        rows = db.execute(
            f"""
            SELECT status, COUNT(*) AS count
            FROM reconciliation_differences
            WHERE id IN ({placeholders})
            GROUP BY status
            """,
            tuple(sorted(difference_ids)),
        ).fetchall()
    counts = {row["status"]: int(row["count"]) for row in rows}
    return counts.get("open", 0), counts.get("resolved", 0), counts.get("accepted", 0)


def load_report(report_id: str) -> Row | None:
    with connection() as db:
        return db.execute(
            "SELECT * FROM eod_reconciliation_reports WHERE id = ?",
            (report_id,),
        ).fetchone()


def list_report_rows(
    strategy_instance_id: str | None = None,
    account_id: str | None = None,
    business_date: date | None = None,
) -> list[Row]:
    clauses: list[str] = []
    parameters: list[object] = []
    if strategy_instance_id is not None:
        clauses.append("strategy_instance_id = ?")
        parameters.append(strategy_instance_id)
    if account_id is not None:
        clauses.append("account_id = ?")
        parameters.append(account_id)
    if business_date is not None:
        clauses.append("business_date = ?")
        parameters.append(business_date.isoformat())
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with connection() as db:
        return db.execute(
            f"""
            SELECT * FROM eod_reconciliation_reports
            {where}
            ORDER BY business_date DESC, created_at DESC
            """,
            tuple(parameters),
        ).fetchall()


def review_report(
    *,
    report_id: str,
    payload_hash: str,
    decision: ReviewDecision,
    reviewer: str,
    reason: str,
    reviewed_at: str,
) -> ReviewWriteResult:
    with connection() as db:
        row = db.execute(
            "SELECT * FROM eod_reconciliation_reports WHERE id = ?",
            (report_id,),
        ).fetchone()
        if row is None:
            raise EodReportNotFoundError("EOD reconciliation report not found")
        disposition = review_disposition(
            existing_payload_hash=row["review_payload_hash"],
            requested_payload_hash=payload_hash,
            decision=decision,
            current_scale_gate_status=row["scale_gate_status"],
        )
        if not disposition.changed:
            return ReviewWriteResult(row=row, changed=False)
        db.execute(
            """
            UPDATE eod_reconciliation_reports
            SET review_payload_hash = ?, reviewer = ?, review_decision = ?,
                review_reason = ?, reviewed_at = ?, scale_gate_status = ?
            WHERE id = ?
            """,
            (
                payload_hash,
                reviewer,
                decision,
                reason,
                reviewed_at,
                disposition.scale_gate_status,
                report_id,
            ),
        )
        updated = db.execute(
            "SELECT * FROM eod_reconciliation_reports WHERE id = ?",
            (report_id,),
        ).fetchone()
    assert updated is not None
    return ReviewWriteResult(row=updated, changed=True)


def sla_status(row: Row) -> str:
    due_at = datetime.fromisoformat(row["due_at"])
    completed_at = (
        datetime.fromisoformat(row["completed_at"]) if row["completed_at"] is not None else None
    )
    if completed_at is not None:
        return "met" if completed_at <= due_at else "breached"
    return "overdue" if datetime.now(UTC) > due_at else "pending"


def report_from_row(row: Row) -> EodReconciliationReportResponse:
    return EodReconciliationReportResponse(
        reportId=row["id"],
        idempotencyKey=row["idempotency_key"],
        businessDate=row["business_date"],
        timezone=row["timezone"],
        valuationTime=row["valuation_time"],
        strategyInstanceId=row["strategy_instance_id"],
        accountId=row["account_id"],
        actor=row["actor"],
        owner=row["owner"],
        dueAt=row["due_at"],
        status=row["status"],
        slaStatus=sla_status(row),
        scaleGateStatus=row["scale_gate_status"],
        orderReconciliationCount=row["order_reconciliation_count"],
        accountReconciliationRunId=row["account_reconciliation_run_id"],
        economicEventImportId=row["economic_event_import_id"],
        navSnapshotId=row["nav_snapshot_id"],
        formalPnlCount=row["formal_pnl_count"],
        formalPnlIncompleteCount=row["formal_pnl_incomplete_count"],
        openDifferenceCount=row["open_difference_count"],
        resolvedDifferenceCount=row["resolved_difference_count"],
        acceptedDifferenceCount=row["accepted_difference_count"],
        skippedExternalIds=json.loads(row["skipped_external_ids_json"]),
        missingAccountIds=json.loads(row["missing_account_ids_json"]),
        errors=json.loads(row["errors_json"]),
        reviewer=row["reviewer"],
        reviewDecision=row["review_decision"],
        reviewReason=row["review_reason"],
        reviewedAt=row["reviewed_at"],
        createdAt=row["created_at"],
        completedAt=row["completed_at"],
    )


def list_strategy_order_ids(
    *,
    strategy_instance_id: str,
    account_id: str,
    start_utc: str,
    end_utc: str,
    terminal_statuses: tuple[str, ...],
) -> list[str]:
    placeholders = ",".join("?" for _ in terminal_statuses)
    with connection() as db:
        rows = db.execute(
            f"""
            SELECT o.id
            FROM orders o
            JOIN trade_commands tc ON tc.id = o.command_id
            WHERE tc.strategy_instance_id = ?
              AND o.account_id = ?
              AND o.created_at <= ?
              AND (
                    o.created_at >= ?
                    OR o.status NOT IN ({placeholders})
              )
            ORDER BY o.created_at, o.id
            """,
            (
                strategy_instance_id,
                account_id,
                end_utc,
                start_utc,
                *terminal_statuses,
            ),
        ).fetchall()
    return [row["id"] for row in rows]


def historical_difference_counts(strategy_instance_id: str, account_id: str) -> dict[str, int]:
    with connection() as db:
        rows = db.execute(
            """
            SELECT rd.status, COUNT(*) AS count
            FROM reconciliation_differences rd
            JOIN venue_reconciliation_runs vr ON vr.id = rd.run_id
            WHERE vr.strategy_instance_id = ?
              AND vr.account_id = ?
            GROUP BY rd.status
            """,
            (strategy_instance_id, account_id),
        ).fetchall()
    return {row["status"]: int(row["count"]) for row in rows}


def load_report_status(report_id: str) -> str | None:
    with connection() as db:
        row = db.execute(
            "SELECT status FROM eod_reconciliation_reports WHERE id = ?",
            (report_id,),
        ).fetchone()
    return row["status"] if row is not None else None


def update_report_gate(
    *,
    report_id: str,
    status: str,
    scale_gate_status: str,
    open_difference_count: int,
    resolved_difference_count: int,
    accepted_difference_count: int,
) -> None:
    with connection() as db:
        db.execute(
            """
            UPDATE eod_reconciliation_reports
            SET status = ?, scale_gate_status = ?, open_difference_count = ?,
                resolved_difference_count = ?, accepted_difference_count = ?
            WHERE id = ?
            """,
            (
                status,
                scale_gate_status,
                open_difference_count,
                resolved_difference_count,
                accepted_difference_count,
                report_id,
            ),
        )
