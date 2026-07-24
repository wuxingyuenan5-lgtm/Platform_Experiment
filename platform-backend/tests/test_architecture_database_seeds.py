import ast
from pathlib import Path

from app import database, database_seeds

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
DATABASE_PATH = APP_ROOT / "database.py"
SEEDS_PATH = APP_ROOT / "database_seeds.py"


def function_names(path: Path) -> set[str]:
    return {
        node.name
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def test_database_facade_preserves_seed_compatibility_identity() -> None:
    assert database.seed_reference_data is database_seeds.seed_reference_data


def test_seed_module_is_the_fixed_seed_owner() -> None:
    database_source = DATABASE_PATH.read_text(encoding="utf-8")
    seed_source = SEEDS_PATH.read_text(encoding="utf-8")
    database_functions = function_names(DATABASE_PATH)
    seed_functions = function_names(SEEDS_PATH)

    assert "seed_reference_data" in seed_functions
    assert "seed_reference_data" not in database_functions
    for forbidden in (
        "INSERT OR IGNORE",
        "UPDATE contract_specifications",
        "2026-07-19T00:00:00+00:00",
        "secret://",
        "strategy_funding_arbitrage",
        "instrument_xau_usd",
    ):
        assert forbidden not in database_source
    for required in (
        "INSERT OR IGNORE",
        "UPDATE contract_specifications",
        "2026-07-19T00:00:00+00:00",
        "strategy_funding_arbitrage",
        "instrument_xau_usd",
    ):
        assert required in seed_source


def test_seed_owner_does_not_contain_connection_or_schema_logic() -> None:
    source = SEEDS_PATH.read_text(encoding="utf-8")

    for forbidden in (
        "sqlite3.connect",
        "get_settings",
        "SCHEMA_SQL",
        "CREATE TABLE",
        "CREATE INDEX",
        "ALTER TABLE",
        "bootstrap_database",
    ):
        assert forbidden not in source
