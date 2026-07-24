import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import financial_fact_repository as repository
from app.config import get_settings
from app.database import connection
from app.main import app

STRATEGY_ID = "strategy_funding_arbitrage_instance_default"
ACCOUNT_ID = "account_sim_usdt"
INSTRUMENT_ID = "instrument_btc_usdt"


def install_abort_trigger(*, name: str, event_type: str) -> None:
    with connection() as db:
        db.execute(
            f"""
            CREATE TRIGGER {name}
            BEFORE INSERT ON audit_events
            WHEN NEW.event_type = '{event_type}'
            BEGIN
                SELECT RAISE(ABORT, 'forced transaction failure');
            END
            """
        )


def test_financial_fact_and_audit_write_roll_back_together(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "fact-audit-atomicity.db")
    with TestClient(app, raise_server_exceptions=False) as client:
        install_abort_trigger(
            name="abort_financial_fact_audit",
            event_type="financial_fact_recorded",
        )
        response = client.post(
            "/api/v1/financial-facts",
            json={
                "idempotencyKey": "atomic-fact-1",
                "factType": "balance",
                "source": "repository-atomicity",
                "externalId": "atomic-fact-1",
                "strategyInstanceId": STRATEGY_ID,
                "accountId": ACCOUNT_ID,
                "amount": "100",
                "currency": "USDT",
                "occurredAt": "2026-07-24T00:00:00Z",
            },
        )
        assert response.status_code == 500

        with connection() as db:
            fact_count = db.execute(
                "SELECT COUNT(*) AS count FROM financial_facts WHERE idempotency_key = ?",
                ("atomic-fact-1",),
            ).fetchone()["count"]
            audit_count = db.execute(
                "SELECT COUNT(*) AS count FROM audit_events WHERE event_type = ?",
                ("financial_fact_recorded",),
            ).fetchone()["count"]
        assert fact_count == 0
        assert audit_count == 0


def test_formal_position_and_pnl_upsert_roll_back_together(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "projection-atomicity.db")
    with TestClient(app):
        repository.ensure_schema()
        with connection() as db:
            db.execute(
                """
                CREATE TRIGGER abort_formal_pnl_insert
                BEFORE INSERT ON formal_pnl_results
                BEGIN
                    SELECT RAISE(ABORT, 'forced transaction failure');
                END
                """
            )

        with pytest.raises(sqlite3.IntegrityError, match="forced transaction failure"):
            repository.save_formal_projection(
                strategy_instance_id=STRATEGY_ID,
                account_id=ACCOUNT_ID,
                instrument_id=INSTRUMENT_ID,
                has_trade=True,
                net_quantity="1",
                average_price="100",
                quantity_unit="BTC",
                currency="USDT",
                trading_pnl="10",
                funding_pnl="0",
                swap_pnl="0",
                fee_pnl="0",
                fx_pnl="0",
                total_pnl="10",
                fact_count=1,
                data_quality_state="complete",
                updated_at="2026-07-24T00:00:00+00:00",
            )

        with connection() as db:
            position_count = db.execute(
                "SELECT COUNT(*) AS count FROM formal_positions"
            ).fetchone()["count"]
            pnl_count = db.execute(
                "SELECT COUNT(*) AS count FROM formal_pnl_results"
            ).fetchone()["count"]
        assert position_count == 0
        assert pnl_count == 0


def test_strategy_rebuild_clear_rolls_back_as_one_transaction(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "rebuild-clear-atomicity.db")
    with TestClient(app):
        repository.ensure_schema()
        with connection() as db:
            db.execute(
                """
                INSERT INTO formal_positions (
                    strategy_instance_id, account_id, instrument_id, net_quantity,
                    average_price, quantity_unit, data_quality_state, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    STRATEGY_ID,
                    ACCOUNT_ID,
                    INSTRUMENT_ID,
                    "1",
                    "100",
                    "BTC",
                    "complete",
                    "2026-07-24T00:00:00+00:00",
                ),
            )
            db.execute(
                """
                INSERT INTO formal_pnl_results (
                    strategy_instance_id, account_id, instrument_id, currency,
                    trading_pnl, funding_pnl, swap_pnl, fee_pnl, fx_pnl, total_pnl,
                    fact_count, data_quality_state, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    STRATEGY_ID,
                    ACCOUNT_ID,
                    INSTRUMENT_ID,
                    "USDT",
                    "10",
                    "0",
                    "0",
                    "0",
                    "0",
                    "10",
                    1,
                    "complete",
                    "2026-07-24T00:00:00+00:00",
                ),
            )
            db.execute(
                """
                CREATE TRIGGER abort_formal_pnl_delete
                BEFORE DELETE ON formal_pnl_results
                BEGIN
                    SELECT RAISE(ABORT, 'forced transaction failure');
                END
                """
            )

        with pytest.raises(sqlite3.IntegrityError, match="forced transaction failure"):
            repository.prepare_strategy_rebuild(STRATEGY_ID)

        with connection() as db:
            position_count = db.execute(
                "SELECT COUNT(*) AS count FROM formal_positions"
            ).fetchone()["count"]
            pnl_count = db.execute(
                "SELECT COUNT(*) AS count FROM formal_pnl_results"
            ).fetchone()["count"]
        assert position_count == 1
        assert pnl_count == 1


def test_nav_snapshot_and_audit_write_roll_back_together(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "nav-audit-atomicity.db")
    with TestClient(app):
        repository.ensure_schema()
        install_abort_trigger(
            name="abort_formal_nav_audit",
            event_type="formal_nav_snapshot_created",
        )

        with pytest.raises(sqlite3.IntegrityError, match="forced transaction failure"):
            repository.store_formal_nav_snapshot(
                snapshot_id="atomic-nav-1",
                audit_event_id="atomic-nav-audit-1",
                strategy_instance_id=STRATEGY_ID,
                valuation_time="2026-07-24T00:00:00+00:00",
                equity="100000",
                capital_base="100000",
                nav="1",
                currency="USDT",
                data_quality_state="complete",
                required_account_count=1,
                included_account_count=1,
                missing_account_ids_json="[]",
                audit_details_json="{}",
                created_at="2026-07-24T00:00:00+00:00",
            )

        with connection() as db:
            snapshot_count = db.execute(
                "SELECT COUNT(*) AS count FROM formal_strategy_nav_snapshots"
            ).fetchone()["count"]
            audit_count = db.execute(
                "SELECT COUNT(*) AS count FROM audit_events WHERE event_type = ?",
                ("formal_nav_snapshot_created",),
            ).fetchone()["count"]
        assert snapshot_count == 0
        assert audit_count == 0
