from contextlib import contextmanager
from pathlib import Path

import pytest

from app import venue_reconciliation as compatibility
from app import venue_reconciliation_repository as repository
from app.config import get_settings
from app.database import connection as actual_connection
from app.database import initialize_database

DDL_SHA256 = "f71ad3d4a5762586dee3e32c91418723bbee80bb07db3678204f4ca19b3725b4"
STRATEGY_ID = "strategy_funding_arbitrage_instance_default"
ACCOUNT_ID = "account_sim_usdt"


def setup_database(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "venue-repository.db")
    initialize_database()
    repository.ensure_schema()


def create_run(run_id: str = "repository-run-1") -> None:
    repository.create_account_snapshot_run(
        run_id=run_id,
        idempotency_key=f"idempotency:{run_id}",
        payload_hash=f"hash:{run_id}",
        strategy_instance_id=STRATEGY_ID,
        account_id=ACCOUNT_ID,
        source="runtime",
        position_count=0,
        balance_count=0,
        started_at="2026-07-24T00:00:00+00:00",
    )


def test_ddl_and_compatibility_aliases_are_exact() -> None:
    import hashlib

    assert hashlib.sha256(repository.SCHEMA_SQL.encode("utf-8")).hexdigest() == DDL_SHA256
    assert compatibility.SCHEMA_SQL is repository.SCHEMA_SQL
    assert compatibility.ensure_schema is repository.ensure_schema
    assert compatibility.audit is repository.audit
    assert compatibility.create_difference is repository.store_difference
    assert compatibility.run_from_row is repository.run_from_row
    assert compatibility.difference_from_row is repository.difference_from_row


def test_difference_storage_is_idempotent(tmp_path: Path) -> None:
    setup_database(tmp_path)
    create_run()

    first = repository.store_difference(
        "repository-run-1",
        "position:instrument-1:missing_local",
        "missing_local",
        "position",
        None,
        "external-position-1",
        {},
        {"netQuantity": "1"},
    )
    second = repository.store_difference(
        "repository-run-1",
        "position:instrument-1:missing_local",
        "missing_local",
        "position",
        None,
        "external-position-1",
        {},
        {"netQuantity": "1"},
    )

    assert second == first
    with actual_connection() as db:
        count = db.execute(
            "SELECT COUNT(*) AS count FROM reconciliation_differences WHERE run_id = ?",
            ("repository-run-1",),
        ).fetchone()["count"]
    assert count == 1


def test_difference_insert_rolls_back_when_identity_read_fails(
    monkeypatch,
    tmp_path: Path,
) -> None:
    setup_database(tmp_path)
    create_run()

    class FailOnIdentityRead:
        def __init__(self, db):
            self.db = db

        def execute(self, sql, params=()):
            if "SELECT id FROM reconciliation_differences" in sql:
                raise RuntimeError("forced identity read failure")
            return self.db.execute(sql, params)

    @contextmanager
    def failing_connection():
        with actual_connection() as db:
            yield FailOnIdentityRead(db)

    monkeypatch.setattr(repository, "connection", failing_connection)
    with pytest.raises(RuntimeError, match="forced identity read failure"):
        repository.store_difference(
            "repository-run-1",
            "balance:USD:missing_local",
            "missing_local",
            "balance",
            ACCOUNT_ID,
            "external-balance-1",
            {},
            {"currency": "USD"},
        )

    with actual_connection() as db:
        count = db.execute(
            "SELECT COUNT(*) AS count FROM reconciliation_differences WHERE run_id = ?",
            ("repository-run-1",),
        ).fetchone()["count"]
    assert count == 0


def test_run_completion_rolls_back_when_result_read_fails(
    monkeypatch,
    tmp_path: Path,
) -> None:
    setup_database(tmp_path)
    create_run()

    class FailAfterUpdate:
        def __init__(self, db):
            self.db = db
            self.updated = False

        def execute(self, sql, params=()):
            if "UPDATE venue_reconciliation_runs" in sql:
                self.updated = True
                return self.db.execute(sql, params)
            if self.updated and "SELECT * FROM venue_reconciliation_runs" in sql:
                raise RuntimeError("forced run read failure")
            return self.db.execute(sql, params)

    @contextmanager
    def failing_connection():
        with actual_connection() as db:
            yield FailAfterUpdate(db)

    monkeypatch.setattr(repository, "connection", failing_connection)
    with pytest.raises(RuntimeError, match="forced run read failure"):
        repository.complete_account_snapshot_run(
            run_id="repository-run-1",
            status="completed",
            fact_count=4,
            difference_count=2,
            completed_at="2026-07-24T01:00:00+00:00",
        )

    with actual_connection() as db:
        row = db.execute(
            "SELECT status, fact_count, difference_count, completed_at "
            "FROM venue_reconciliation_runs WHERE id = ?",
            ("repository-run-1",),
        ).fetchone()
    assert dict(row) == {
        "status": "processing",
        "fact_count": 0,
        "difference_count": 0,
        "completed_at": None,
    }
