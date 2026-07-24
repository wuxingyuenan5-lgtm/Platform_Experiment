import sqlite3
from pathlib import Path

import pytest

from app import database
from app import database_connection
from app.config import get_settings


def test_database_path_is_dynamic_and_creates_parent_directories(tmp_path: Path) -> None:
    first = tmp_path / "first" / "platform.db"
    second = tmp_path / "second" / "nested" / "platform.db"

    get_settings().database_path = str(first)
    assert database_connection.database_path() == first
    assert first.parent.is_dir()

    get_settings().database_path = str(second)
    assert database_connection.database_path() == second
    assert second.parent.is_dir()


def test_connection_enables_rows_foreign_keys_and_commits(tmp_path: Path) -> None:
    database_file = tmp_path / "commit.db"
    get_settings().database_path = str(database_file)

    with database_connection.connection() as db:
        assert db.row_factory is sqlite3.Row
        assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        db.execute("CREATE TABLE parent (id TEXT PRIMARY KEY)")
        db.execute(
            "CREATE TABLE child (id TEXT PRIMARY KEY, parent_id TEXT REFERENCES parent(id))"
        )
        db.execute("INSERT INTO parent (id) VALUES (?)", ("parent-1",))

    with sqlite3.connect(database_file) as db:
        assert db.execute("SELECT COUNT(*) FROM parent").fetchone()[0] == 1


def test_connection_rolls_back_and_reraises_on_exception(tmp_path: Path) -> None:
    database_file = tmp_path / "rollback.db"
    get_settings().database_path = str(database_file)
    with sqlite3.connect(database_file) as db:
        db.execute("CREATE TABLE records (id TEXT PRIMARY KEY)")

    with pytest.raises(RuntimeError, match="forced rollback"):
        with database_connection.connection() as db:
            db.execute("INSERT INTO records (id) VALUES (?)", ("record-1",))
            raise RuntimeError("forced rollback")

    with sqlite3.connect(database_file) as db:
        assert db.execute("SELECT COUNT(*) FROM records").fetchone()[0] == 0


def test_database_module_preserves_connection_compatibility_identity() -> None:
    assert database.connection is database_connection.connection
    assert database.database_path is database_connection.database_path
