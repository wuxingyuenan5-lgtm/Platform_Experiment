from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database_bootstrap import bootstrap_database
from app.main import app
from app.schema_migrations import PLATFORM_MIGRATIONS, Migration, apply_migrations


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


def test_user_identity_migration_creates_protected_schema() -> None:
    db = memory_database()
    bootstrap_database(db)
    apply_migrations(db, PLATFORM_MIGRATIONS)
    apply_migrations(db, PLATFORM_MIGRATIONS)

    migration = db.execute(
        "SELECT name FROM schema_migrations WHERE version = 5"
    ).fetchone()
    assert migration["name"] == "user-identity-sessions-and-audit"

    table_names = {
        row["name"]
        for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    assert {"users", "user_sessions", "password_reset_tickets"} <= table_names

    audit_columns = {
        row["name"] for row in db.execute("PRAGMA table_info(audit_events)").fetchall()
    }
    assert {
        "actor_user_id",
        "request_id",
        "result",
        "ip_address",
        "auth_method",
    } <= audit_columns

    db.execute(
        """
        INSERT INTO users (
            id, username, username_normalized, password_hash,
            requested_role_code, lifecycle_status,
            registered_at, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "pending-user",
            "PendingUser",
            "pendinguser",
            "test-password-hash",
            "member",
            "pending",
            "2026-07-26T00:00:00+00:00",
            "2026-07-26T00:00:00+00:00",
            "2026-07-26T00:00:00+00:00",
        ),
    )

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            """
            INSERT INTO users (
                id, username, username_normalized, password_hash,
                lifecycle_status, registered_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "invalid-active-user",
                "InvalidActive",
                "invalidactive",
                "test-password-hash",
                "active",
                "2026-07-26T00:00:00+00:00",
                "2026-07-26T00:00:00+00:00",
                "2026-07-26T00:00:00+00:00",
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
    assert payload["migrations"][-1]["version"] == 5
    assert payload["migrations"][-1]["status"] == "applied"
