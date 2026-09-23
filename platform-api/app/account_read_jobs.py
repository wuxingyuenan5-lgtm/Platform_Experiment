"""Persist history/accounting health separately from current account observations."""

from datetime import UTC, datetime

from app.database import connection


def record_job(account_id: str, job: str, status: str, error: str | None = None) -> None:
    at = datetime.now(UTC).isoformat()
    with connection() as db:
        db.execute(
            """INSERT INTO account_read_jobs
            (account_id,job,status,last_attempt_at,last_success_at,error_code)
            VALUES (?,?,?,?,?,?) ON CONFLICT(account_id,job) DO UPDATE SET
            status=excluded.status,last_attempt_at=excluded.last_attempt_at,
            last_success_at=coalesce(excluded.last_success_at,account_read_jobs.last_success_at),
            error_code=excluded.error_code""",
            (account_id, job, status, at, at if status == "ready" else None, error),
        )


def financial_sync_state(db, account_id: str) -> dict:
    rows = db.execute(
        "SELECT job,status,error_code,last_success_at FROM account_read_jobs WHERE account_id=?",
        (account_id,),
    ).fetchall()
    capital = db.execute(
        "SELECT 'capital' AS job,status,error_code,NULL AS last_success_at "
        "FROM account_capital_sync WHERE account_id=?",
        (account_id,),
    ).fetchone()
    if capital is not None:
        rows.append(capital)
    failures = [row for row in rows if row["status"] == "failed"]
    history = next((row for row in rows if row["job"] == "history"), None)
    return {
        "financialSyncStatus": "failed"
        if failures
        else (
            "syncing"
            if any(row["status"] == "syncing" for row in rows)
            else "ready"
            if history and history["status"] == "ready"
            else "waiting_initial_sync"
        ),
        "financialSyncErrorCode": ";".join(f"{row['job']}:{row['error_code']}" for row in failures)
        or None,
        "lastSuccessfulFinancialSyncAt": history["last_success_at"] if history else None,
    }
