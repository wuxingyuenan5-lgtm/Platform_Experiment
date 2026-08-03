from __future__ import annotations

from datetime import UTC, datetime

from app.database import connection
from app.schemas import (
    AuditEventResponse,
    ReconciliationIssueResponse,
    ReconciliationSummaryResponse,
)


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def get_reconciliation_summary() -> ReconciliationSummaryResponse:
    detected_at = now_iso()
    issues: list[ReconciliationIssueResponse] = []
    with connection() as db:
        manual_batches = db.execute(
            """
            SELECT id, strategy_instance_id, failure_reason
            FROM execution_batches
            WHERE requires_manual_intervention = 1
            ORDER BY updated_at DESC
            """
        ).fetchall()
        unknown_orders = db.execute(
            """
            SELECT o.id, eb.strategy_instance_id
            FROM orders o
            LEFT JOIN execution_batch_legs ebl ON ebl.order_id = o.id
            LEFT JOIN execution_batches eb ON eb.id = ebl.batch_id
            WHERE o.status = 'result_unknown'
            ORDER BY o.updated_at DESC
            """
        ).fetchall()

    for row in manual_batches:
        issues.append(
            ReconciliationIssueResponse(
                issueType="manual_intervention_batch",
                subjectType="execution_batch",
                subjectId=row["id"],
                strategyInstanceId=row["strategy_instance_id"],
                severity="action_required",
                message=row["failure_reason"] or "Execution batch requires manual intervention",
                detectedAt=detected_at,
            )
        )
    for row in unknown_orders:
        issues.append(
            ReconciliationIssueResponse(
                issueType="result_unknown_order",
                subjectType="order",
                subjectId=row["id"],
                strategyInstanceId=row["strategy_instance_id"],
                severity="action_required",
                message="Order result is unknown and must be reconciled before live trading",
                detectedAt=detected_at,
            )
        )

    return ReconciliationSummaryResponse(
        status="action_required" if issues else "ok",
        manualInterventionBatchCount=len(manual_batches),
        resultUnknownOrderCount=len(unknown_orders),
        issues=issues,
    )


def list_audit_events(
    subject_type: str | None = None,
    limit: int = 50,
) -> list[AuditEventResponse]:
    parameters: list[object] = []
    where_clause = ""
    if subject_type is not None:
        where_clause = "WHERE subject_type = ?"
        parameters.append(subject_type)
    parameters.append(limit)

    with connection() as db:
        rows = db.execute(
            f"""
            SELECT id, event_type, subject_type, subject_id, details_json, created_at
            FROM audit_events
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ?
            """,
            parameters,
        ).fetchall()

    return [
        AuditEventResponse(
            auditEventId=row["id"],
            eventType=row["event_type"],
            subjectType=row["subject_type"],
            subjectId=row["subject_id"],
            detailsJson=row["details_json"],
            createdAt=row["created_at"],
        )
        for row in rows
    ]
