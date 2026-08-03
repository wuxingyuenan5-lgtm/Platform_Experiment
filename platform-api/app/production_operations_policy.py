from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException

from app import production_monitoring
from app.database import connection
from app.redaction import redact_sensitive

_original_run_controlled_operation = production_monitoring.run_controlled_operation


def run_controlled_operation_with_failure_record(request, *, actor):
    try:
        return _original_run_controlled_operation(request, actor=actor)
    except HTTPException as exc:
        safe_error = str(redact_sensitive(exc.detail))
        completed_at = datetime.now(UTC).isoformat()
        with connection() as db:
            db.execute(
                """
                UPDATE controlled_operation_runs
                SET status = 'failed', error = ?, completed_at = ?
                WHERE idempotency_key = ? AND status = 'running'
                """,
                (safe_error, completed_at, request.idempotency_key),
            )
        raise


def apply_production_operations_policy() -> None:
    production_monitoring.run_controlled_operation = (
        run_controlled_operation_with_failure_record
    )
