import ast
from pathlib import Path

from app import database, database_bootstrap

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
DATABASE_PATH = APP_ROOT / "database.py"
BOOTSTRAP_PATH = APP_ROOT / "database_bootstrap.py"


def function_names(path: Path) -> set[str]:
    return {
        node.name
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def test_database_facade_preserves_bootstrap_compatibility_identity() -> None:
    assert database.SCHEMA_SQL is database_bootstrap.SCHEMA_SQL
    assert database.migrate_schema is database_bootstrap.migrate_schema
    assert database.ensure_column is database_bootstrap.ensure_column


def test_bootstrap_module_is_the_core_schema_owner() -> None:
    database_source = DATABASE_PATH.read_text(encoding="utf-8")
    bootstrap_source = BOOTSTRAP_PATH.read_text(encoding="utf-8")
    database_functions = function_names(DATABASE_PATH)
    bootstrap_functions = function_names(BOOTSTRAP_PATH)

    assert {"bootstrap_database", "migrate_schema", "ensure_column"} <= bootstrap_functions
    assert not ({"migrate_schema", "ensure_column"} & database_functions)
    for forbidden in ("CREATE TABLE", "CREATE INDEX", "ALTER TABLE", "executescript("):
        assert forbidden not in database_source
    for required in ("CREATE TABLE", "CREATE INDEX", "ALTER TABLE", "SCHEMA_SQL"):
        assert required in bootstrap_source


def test_bootstrap_owner_does_not_contain_connection_or_seed_logic() -> None:
    source = BOOTSTRAP_PATH.read_text(encoding="utf-8")

    for forbidden in (
        "sqlite3.connect",
        "get_settings",
        "seed_reference_data",
        "INSERT OR IGNORE",
        "secret://",
    ):
        assert forbidden not in source
