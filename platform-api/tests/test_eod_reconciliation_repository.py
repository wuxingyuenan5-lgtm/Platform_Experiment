import hashlib
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pytest

from app import eod_reconciliation as compatibility
from app import eod_reconciliation_repository as repository
from app.config import get_settings
from app.database import connection, initialize_database

STRATEGY_ID = "strategy_funding_arbitrage_instance_default"
ACCOUNT_ID = "account_sim_usdt"
DDL_SHA256 = "2858fb2fec54506f8bf6d6956e906cecc6a40959a2ae6bf643d7046c2f86133f"


def configure_database(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "eod-repository.db")
    initialize_database()
    repository.ensure_schema()


def insert_report(
    report_id: str = "report-1",
    attempt: int = 1,
    *,
    idempotency_key: str | None = None,
    natural_key: str | None = None,
) -> None:
    repository.insert_initial_report(
        report_id=report_id,
        idempotency_key=idempotency_key or f"idempotency-{report_id}",
        natural_key=natural_key or f"2026-07-23:{STRATEGY_ID}:{ACCOUNT_ID}:{report_id}",
        attempt=attempt,
        payload_hash=f"payload-{report_id}",
        business_date="2026-07-23",
        timezone="Asia/Shanghai",
        valuation_time="2026-07-23T15:59:00+00:00",
        strategy_instance_id=STRATEGY_ID,
        account_id=ACCOUNT_ID,
        actor="eod-runner",
        owner="operations-owner",
        due_at="2026-07-24T15:59:00+00:00",
        created_at="2026-07-23T16:00:00+00:00",
    )


def test_ddl_and_compatibility_aliases_are_exact() -> None:
    assert hashlib.sha256(repository.SCHEMA_SQL.encode("utf-8")).hexdigest() == DDL_SHA256
    assert compatibility.SCHEMA_SQL is repository.SCHEMA_SQL
    assert compatibility.ensure_schema is repository.ensure_schema
    assert compatibility.formal_pnl_counts is repository.formal_pnl_counts
    assert compatibility.difference_status_counts is repository.difference_status_counts
    assert compatibility.sla_status is repository.sla_status
    assert compatibility.report_from_row is repository.report_from_row


def test_report_identity_reads_and_unique_constraints_are_preserved(tmp_path: Path) -> None:
    configure_database(tmp_path)
    insert_report()

    natural_key = f"2026-07-23:{STRATEGY_ID}:{ACCOUNT_ID}:report-1"
    by_idempotency = repository.load_report_by_idempotency("idempotency-report-1")
    by_natural_key = repository.load_latest_report_by_natural_key(natural_key)

    assert by_idempotency is not None
    assert by_natural_key is not None
    assert by_idempotency["id"] == "report-1"
    assert by_natural_key["id"] == "report-1"
    assert by_natural_key["attempt"] == 1

    # idempotency_key remains globally unique: a different report cannot reuse it,
    # even with a different natural_key.
    with pytest.raises(sqlite3.IntegrityError):
        insert_report(
            report_id="report-2",
            idempotency_key="idempotency-report-1",
            natural_key=f"2026-07-24:{STRATEGY_ID}:{ACCOUNT_ID}:report-2",
        )
    assert repository.load_report("report-2") is None

    # A re-run of the same business day creates a NEW attempt row for the SAME
    # natural_key instead of overwriting the previous report; UNIQUE(natural_key,
    # attempt) is enforced and the latest attempt wins.
    insert_report(
        report_id="report-1-rerun",
        attempt=2,
        natural_key=natural_key,
    )
    latest = repository.load_latest_report_by_natural_key(natural_key)
    assert latest is not None
    assert latest["id"] == "report-1-rerun"
    assert latest["attempt"] == 2

    with pytest.raises(sqlite3.IntegrityError):
        insert_report(
            report_id="report-1-duplicate-attempt",
            attempt=2,
            natural_key=natural_key,
        )


def test_review_is_idempotent_immutable_and_preserves_approval_gate(tmp_path: Path) -> None:
    configure_database(tmp_path)
    insert_report()

    with pytest.raises(repository.EodReviewNotEligibleError):
        repository.review_report(
            report_id="report-1",
            payload_hash="approval-hash",
            decision="approved_same_limits",
            reviewer="risk-reviewer",
            reason="not clean",
            reviewed_at="2026-07-23T17:00:00+00:00",
        )

    first = repository.review_report(
        report_id="report-1",
        payload_hash="remediation-hash",
        decision="needs_remediation",
        reviewer="risk-reviewer",
        reason="open differences remain",
        reviewed_at="2026-07-23T17:00:00+00:00",
    )
    replay = repository.review_report(
        report_id="report-1",
        payload_hash="remediation-hash",
        decision="needs_remediation",
        reviewer="other-reviewer",
        reason="replay does not overwrite",
        reviewed_at="2026-07-23T18:00:00+00:00",
    )

    assert first.changed is True
    assert replay.changed is False
    assert replay.row["reviewer"] == "risk-reviewer"
    assert replay.row["review_reason"] == "open differences remain"

    with pytest.raises(repository.EodReviewConflictError):
        repository.review_report(
            report_id="report-1",
            payload_hash="different-hash",
            decision="rejected",
            reviewer="other-reviewer",
            reason="must not overwrite",
            reviewed_at="2026-07-23T18:00:00+00:00",
        )


def test_review_transaction_rolls_back_when_post_update_read_fails(
    monkeypatch,
    tmp_path: Path,
) -> None:
    configure_database(tmp_path)
    insert_report()
    real_connection = connection

    class FailingConnection:
        def __init__(self, db):
            self.db = db
            self.updated = False

        def execute(self, sql, parameters=()):
            result = self.db.execute(sql, parameters)
            if sql.lstrip().startswith("UPDATE eod_reconciliation_reports"):
                self.updated = True
                return result
            if self.updated and sql.lstrip().startswith("SELECT * FROM eod_reconciliation_reports"):
                raise RuntimeError("forced post-update read failure")
            return result

    @contextmanager
    def failing_connection():
        with real_connection() as db:
            yield FailingConnection(db)

    monkeypatch.setattr(repository, "connection", failing_connection)

    with pytest.raises(RuntimeError, match="forced post-update read failure"):
        repository.review_report(
            report_id="report-1",
            payload_hash="rollback-hash",
            decision="needs_remediation",
            reviewer="risk-reviewer",
            reason="force rollback",
            reviewed_at="2026-07-23T17:00:00+00:00",
        )

    monkeypatch.setattr(repository, "connection", real_connection)
    row = repository.load_report("report-1")
    assert row is not None
    assert row["review_payload_hash"] is None
    assert row["reviewer"] is None
    assert row["review_decision"] is None
    assert row["review_reason"] is None
    assert row["reviewed_at"] is None
    assert row["scale_gate_status"] == "blocked"
