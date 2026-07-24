from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.schema_migrations import Migration, apply_migrations


def memory_database() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    return db


def test_schema_migrations_are_idempotent_and_recorded() -> None:
    db = memory_database()
    migrations = (
        Migration(
            version=1,
            name="create-example",
            statements=("CREATE TABLE example (id TEXT PRIMARY KEY)",),
        ),
    )

    apply_migrations(db, migrations)
    apply_migrations(db, migrations)

    rows = db.execute(
        "SELECT version, name, checksum FROM schema_migrations ORDER BY version"
    ).fetchall()
    assert len(rows) == 1
    assert rows[0]["version"] == 1
    assert rows[0]["name"] == "create-example"
    assert rows[0]["checksum"] == migrations[0].checksum
    assert db.execute("SELECT name FROM sqlite_master WHERE name = 'example'").fetchone()


def test_applied_migration_cannot_be_rewritten() -> None:
    db = memory_database()
    original = (Migration(version=1, name="baseline"),)
    apply_migrations(db, original)

    changed = (
        Migration(
            version=1,
            name="baseline",
            statements=("CREATE TABLE unexpected (id TEXT)",),
        ),
    )
    with pytest.raises(RuntimeError, match="changed after it was applied"):
        apply_migrations(db, changed)


def test_migrations_must_be_unique_and_ordered() -> None:
    db = memory_database()
    with pytest.raises(RuntimeError, match="unique and strictly ordered"):
        apply_migrations(
            db,
            (
                Migration(version=2, name="second"),
                Migration(version=1, name="first"),
            ),
        )


def test_application_startup_applies_platform_migration_baseline(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "schema-ledger.db")

    with TestClient(app) as client:
        response = client.get("/api/v1/ops/schema-migrations")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "current"
    assert payload["migrations"][0]["version"] == 1
    assert payload["migrations"][0]["status"] == "applied"
