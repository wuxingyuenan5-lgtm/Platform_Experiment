"""Read-only operational aggregates. Scraping never initializes or repairs a store."""

import sqlite3
from contextlib import closing
from pathlib import Path

from app.config import get_settings


def read_operational_metrics() -> dict[str, list[tuple] | None]:
    path = Path(get_settings().database_path).resolve()
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=1)) as db:
        # One snapshot across all groups; no DDL, writes, or external reads.
        db.execute("BEGIN")
        risk_store = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='execution_batch_risk'"
        ).fetchone()
        return {
            "instructions": db.execute(
                "SELECT strategy_key, status, COUNT(*), MIN(created_at) FROM strategy_runs "
                "WHERE status IN ('accepted','executing','reconciling','result_unknown',"
                "'manual_intervention') GROUP BY strategy_key,status"
            ).fetchall(),
            "batches": db.execute(
                "SELECT strategy_key, status, COUNT(*), MIN(created_at) FROM execution_batches "
                "WHERE status NOT IN ('completed','failed','cancelled','hedged','closed') "
                "GROUP BY strategy_key,status"
            ).fetchall(),
            "accounts": db.execute(
                "SELECT v.venue_code, s.status, COUNT(*), MIN(s.last_success_at), "
                "MIN(p.as_of), SUM(s.last_success_at IS NULL), SUM(p.as_of IS NULL) "
                "FROM account_sync_status s "
                "JOIN accounts a ON a.id=s.account_id JOIN venues v ON v.id=a.venue_id "
                "LEFT JOIN account_venue_snapshots p ON p.account_id=s.account_id "
                "GROUP BY v.venue_code,s.status"
            ).fetchall(),
            "risks": db.execute(
                "SELECT b.strategy_key, r.risk_status, COUNT(*), MIN(r.updated_at) "
                "FROM execution_batch_risk r JOIN execution_batches b ON b.id=r.batch_id "
                "WHERE r.risk_status IN "
                "('residual_exposure','disposition_in_progress','escalated') "
                "GROUP BY b.strategy_key,r.risk_status"
            ).fetchall()
            if risk_store
            else None,
        }
