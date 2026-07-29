from __future__ import annotations

import sqlite3

import pytest

from app.database_bootstrap import bootstrap_database
from app.schema_migrations import PLATFORM_MIGRATIONS, apply_migrations


def database() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


@pytest.mark.integration
def test_member_holding_migration_upgrades_existing_funds_additively() -> None:
    db = database()
    bootstrap_database(db)
    apply_migrations(db, PLATFORM_MIGRATIONS[:5])
    db.execute(
        """
        INSERT INTO legal_entities (id, name, created_at)
        VALUES ('legacy-entity', 'Legacy Entity', '2026-07-01T00:00:00+00:00')
        """
    )
    db.execute(
        """
        INSERT INTO funds (id, legal_entity_id, name, base_currency, created_at)
        VALUES (
            'legacy-fund', 'legacy-entity', 'Legacy Fund', 'CNY',
            '2026-07-01T00:00:00+00:00'
        )
        """
    )

    apply_migrations(db, PLATFORM_MIGRATIONS)
    apply_migrations(db, PLATFORM_MIGRATIONS)

    migration = db.execute(
        "SELECT name, checksum FROM schema_migrations WHERE version = 6"
    ).fetchone()
    assert migration["name"] == "member-fund-holdings-and-unit-nav"
    assert migration["checksum"] == PLATFORM_MIGRATIONS[5].checksum

    fund_columns = {
        str(row["name"])
        for row in db.execute("PRAGMA table_info(funds)").fetchall()
    }
    assert "fund_code" in fund_columns
    legacy = db.execute(
        "SELECT name, base_currency, fund_code FROM funds WHERE id = 'legacy-fund'"
    ).fetchone()
    assert legacy["name"] == "Legacy Fund"
    assert legacy["base_currency"] == "CNY"
    assert legacy["fund_code"] is None

    tables = {
        str(row["name"])
        for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    assert {"member_fund_holdings", "fund_nav_snapshots"} <= tables

    indexes = {
        str(row["name"])
        for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index'"
        ).fetchall()
    }
    assert {
        "idx_funds_fund_code_unique",
        "idx_member_fund_holdings_member_status",
        "idx_member_fund_holdings_fund_status",
        "idx_fund_nav_snapshots_latest",
    } <= indexes


@pytest.mark.integration
def test_fund_code_is_unique_only_when_present() -> None:
    db = database()
    bootstrap_database(db)
    apply_migrations(db, PLATFORM_MIGRATIONS)
    db.execute(
        """
        INSERT INTO legal_entities (id, name, created_at)
        VALUES ('entity', 'Entity', '2026-07-01T00:00:00+00:00')
        """
    )
    db.executemany(
        """
        INSERT INTO funds (
            id, legal_entity_id, name, base_currency, fund_code, created_at
        ) VALUES (?, 'entity', ?, 'CNY', ?, '2026-07-01T00:00:00+00:00')
        """,
        [
            ("fund-one", "Fund One", None),
            ("fund-two", "Fund Two", None),
            ("fund-three", "Fund Three", "VG-001"),
        ],
    )

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            """
            INSERT INTO funds (
                id, legal_entity_id, name, base_currency, fund_code, created_at
            ) VALUES (
                'fund-four', 'entity', 'Fund Four', 'CNY', 'VG-001',
                '2026-07-01T00:00:00+00:00'
            )
            """
        )


@pytest.mark.integration
def test_holding_schema_rejects_invalid_authority_values() -> None:
    db = database()
    bootstrap_database(db)
    apply_migrations(db, PLATFORM_MIGRATIONS)
    db.execute(
        """
        INSERT INTO legal_entities (id, name, created_at)
        VALUES ('entity', 'Entity', '2026-07-01T00:00:00+00:00')
        """
    )
    db.execute(
        """
        INSERT INTO funds (id, legal_entity_id, name, base_currency, created_at)
        VALUES ('fund', 'entity', 'Fund', 'CNY', '2026-07-01T00:00:00+00:00')
        """
    )
    db.execute(
        """
        INSERT INTO users (
            id, username, username_normalized, password_hash,
            role_code, lifecycle_status, registered_at, created_at, updated_at
        ) VALUES (
            'member', 'member', 'member', 'hash', 'member', 'active',
            '2026-07-01T00:00:00+00:00',
            '2026-07-01T00:00:00+00:00',
            '2026-07-01T00:00:00+00:00'
        )
        """
    )

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            """
            INSERT INTO member_fund_holdings (
                id, member_user_id, fund_id, share_quantity,
                cumulative_invested, as_of, source, status,
                updated_by, created_at, updated_at
            ) VALUES (
                'holding', 'member', 'fund', '1', '1',
                '2026-07-01T00:00:00+00:00', 'unknown_source', 'active',
                'member', '2026-07-01T00:00:00+00:00',
                '2026-07-01T00:00:00+00:00'
            )
            """
        )
