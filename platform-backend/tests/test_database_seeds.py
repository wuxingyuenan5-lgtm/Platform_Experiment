import hashlib
import json
import sqlite3
from pathlib import Path

from app import database, database_seeds
from app.config import get_settings

SEED_TABLES = (
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
EXPECTED_SEED_SHA256 = "d42f7e4f95a6efa9044b1e91b4e603f1d87f515923a57d941ee16e75109e6183"


def canonical_seed_snapshot(database_file: Path) -> tuple[str, dict[str, list[dict[str, object]]]]:
    with sqlite3.connect(database_file) as db:
        db.row_factory = sqlite3.Row
        snapshot = {
            table: [dict(row) for row in db.execute(f"SELECT * FROM {table} ORDER BY id")]
            for table in SEED_TABLES
        }
    payload = json.dumps(
        snapshot,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest(), snapshot


def test_database_facade_preserves_seed_compatibility_identity() -> None:
    assert database.seed_reference_data is database_seeds.seed_reference_data


def test_fixed_seed_snapshot_and_safety_defaults(tmp_path: Path) -> None:
    database_file = tmp_path / "seed-snapshot.db"
    get_settings().database_path = str(database_file)

    database.initialize_database()
    digest, snapshot = canonical_seed_snapshot(database_file)

    assert digest == EXPECTED_SEED_SHA256
    instances = {row["id"]: row for row in snapshot["strategy_instances"]}
    accounts = {row["id"]: row for row in snapshot["accounts"]}
    contracts = {row["instrument_id"]: row for row in snapshot["contract_specifications"]}

    assert instances["strategy_funding_arbitrage_instance_default"]["trading_mode"] == (
        "simulation"
    )
    assert instances["strategy_funding_arbitrage_instance_default"]["status"] == "active"
    assert instances["strategy_home_abroad_spread_instance_default"]["status"] == "paused"
    assert accounts["account_sim_usdt"]["status"] == "active"
    assert accounts["account_crypto_test"]["status"] == "paused"
    assert accounts["account_mt5_demo"]["status"] == "paused"
    assert contracts["instrument_xau_usd"]["min_order_quantity"] == "0.01"
    assert contracts["instrument_xau_usd"]["quantity_step"] == "0.01"
    assert contracts["instrument_xau_usd"]["contract_multiplier"] == "100"


def test_repeated_initialization_preserves_exact_seed_snapshot(tmp_path: Path) -> None:
    database_file = tmp_path / "seed-repeated.db"
    get_settings().database_path = str(database_file)

    database.initialize_database()
    first_digest, first_snapshot = canonical_seed_snapshot(database_file)
    database.initialize_database()
    second_digest, second_snapshot = canonical_seed_snapshot(database_file)

    assert second_digest == first_digest
    assert second_snapshot == first_snapshot
