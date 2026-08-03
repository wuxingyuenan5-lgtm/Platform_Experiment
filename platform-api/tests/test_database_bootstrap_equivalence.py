import sqlite3
from pathlib import Path

from app import database
from app.config import get_settings

EXPECTED_TABLES = {
    "accounts",
    "audit_events",
    "balance_snapshots",
    "books",
    "contract_specifications",
    "credential_references",
    "economic_events",
    "execution_batch_legs",
    "execution_batches",
    "external_order_references",
    "fills",
    "funds",
    "instrument_mappings",
    "instruments",
    "legal_entities",
    "market_spread_snapshots",
    "orders",
    "pnl_attribution_items",
    "pnl_results",
    "portfolios",
    "positions",
    "risk_decisions",
    "strategy_account_bindings",
    "strategy_definitions",
    "strategy_instances",
    "strategy_nav_snapshots",
    "strategy_runs",
    "strategy_versions",
    "trade_commands",
    "venues",
}
EXPECTED_INDEXES = {
    "idx_balance_snapshots_account",
    "idx_execution_batch_legs_batch",
    "idx_execution_batches_account",
    "idx_execution_batches_idempotency",
    "idx_market_spread_snapshots_strategy_time",
    "idx_strategy_account_bindings_instance",
    "idx_strategy_instances_definition",
    "idx_strategy_nav_snapshots_instance",
    "idx_strategy_runs_instance",
    "idx_trade_commands_idempotency",
}


def names(db: sqlite3.Connection, object_type: str) -> set[str]:
    return {
        row[0]
        for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type = ? AND name NOT LIKE 'sqlite_%'",
            (object_type,),
        ).fetchall()
    }


def seed_counts(db: sqlite3.Connection) -> dict[str, int]:
    tables = (
        "legal_entities",
        "funds",
        "portfolios",
        "books",
        "strategy_definitions",
        "strategy_versions",
        "strategy_instances",
        "venues",
        "credential_references",
        "accounts",
        "balance_snapshots",
        "strategy_account_bindings",
        "instruments",
        "contract_specifications",
        "instrument_mappings",
    )
    return {
        table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in tables
    }


def test_fresh_database_schema_and_reference_seed_snapshot(tmp_path: Path) -> None:
    database_file = tmp_path / "fresh.db"
    get_settings().database_path = str(database_file)

    database.initialize_database()

    with sqlite3.connect(database_file) as db:
        assert names(db, "table") == EXPECTED_TABLES
        assert EXPECTED_INDEXES <= names(db, "index")
        assert seed_counts(db) == {
            "legal_entities": 1,
            "funds": 1,
            "portfolios": 1,
            "books": 1,
            "strategy_definitions": 6,
            "strategy_versions": 6,
            "strategy_instances": 6,
            "venues": 3,
            "credential_references": 3,
            "accounts": 4,
            "balance_snapshots": 4,
            "strategy_account_bindings": 5,
            "instruments": 4,
            "contract_specifications": 4,
            "instrument_mappings": 5,
        }
        assert db.execute(
            "SELECT contract_multiplier FROM contract_specifications WHERE instrument_id = ?",
            ("instrument_xau_usd",),
        ).fetchone()[0] == "100"
        assert db.execute(
            "SELECT trading_mode, status FROM strategy_instances WHERE id = ?",
            ("strategy_funding_arbitrage_instance_default",),
        ).fetchone() == ("simulation", "active")


def test_repeated_initialization_is_seed_idempotent(tmp_path: Path) -> None:
    database_file = tmp_path / "repeated.db"
    get_settings().database_path = str(database_file)

    database.initialize_database()
    with sqlite3.connect(database_file) as db:
        first = seed_counts(db)

    database.initialize_database()
    with sqlite3.connect(database_file) as db:
        assert seed_counts(db) == first


def test_existing_legacy_database_receives_compatibility_columns_and_index(
    tmp_path: Path,
) -> None:
    database_file = tmp_path / "legacy.db"
    get_settings().database_path = str(database_file)
    with sqlite3.connect(database_file) as db:
        db.executescript(
            """
            CREATE TABLE execution_batches (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                strategy_key TEXT NOT NULL,
                direction TEXT NOT NULL,
                status TEXT NOT NULL,
                requires_manual_intervention INTEGER NOT NULL DEFAULT 0,
                failure_reason TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE execution_batch_legs (
                id TEXT PRIMARY KEY,
                batch_id TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                role TEXT NOT NULL,
                instrument_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                order_type TEXT NOT NULL,
                quantity TEXT NOT NULL,
                price TEXT,
                order_id TEXT,
                status TEXT NOT NULL,
                failure_reason TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

    database.initialize_database()

    with sqlite3.connect(database_file) as db:
        batch_columns = {
            row[1] for row in db.execute("PRAGMA table_info(execution_batches)").fetchall()
        }
        leg_columns = {
            row[1] for row in db.execute("PRAGMA table_info(execution_batch_legs)").fetchall()
        }
        assert {"idempotency_key", "strategy_instance_id"} <= batch_columns
        assert "account_id" in leg_columns
        assert "idx_execution_batches_idempotency" in names(db, "index")
        assert EXPECTED_TABLES <= names(db, "table")
