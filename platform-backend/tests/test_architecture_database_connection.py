import ast
from pathlib import Path

from app import database
from app import database_connection

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
DATABASE_PATH = APP_ROOT / "database.py"
CONNECTION_PATH = APP_ROOT / "database_connection.py"


def imported_modules(path: Path) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
            modules.update(f"{node.module}.{alias.name}" for alias in node.names)
    return modules


def test_database_facade_preserves_connection_identity() -> None:
    assert database.connection is database_connection.connection
    assert database.database_path is database_connection.database_path


def test_database_facade_no_longer_owns_connection_implementation() -> None:
    source = DATABASE_PATH.read_text(encoding="utf-8")
    imports = imported_modules(DATABASE_PATH)

    assert "app.database_connection" in imports
    assert "sqlite3.connect" not in source
    assert "@contextmanager" not in source
    assert "get_settings" not in source
    assert "def connection(" not in source
    assert "def database_path(" not in source


def test_connection_module_owns_only_connection_concerns() -> None:
    source = CONNECTION_PATH.read_text(encoding="utf-8")
    imports = imported_modules(CONNECTION_PATH)

    assert "sqlite3" in imports
    assert "app.config" in imports
    for anchor in (
        "sqlite3.connect",
        "sqlite3.Row",
        'PRAGMA foreign_keys = ON',
        "db.commit()",
        "db.rollback()",
        "db.close()",
    ):
        assert anchor in source
    for forbidden in (
        "CREATE TABLE",
        "CREATE INDEX",
        "ALTER TABLE",
        "INSERT OR IGNORE",
        "seed_reference_data",
        "SCHEMA_SQL",
    ):
        assert forbidden not in source
