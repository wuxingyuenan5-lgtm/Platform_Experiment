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


def test_audit_subject_index_migration_preserves_evidence_and_uses_index():
    db = memory_database()
    bootstrap_database(db)
    apply_migrations(db, tuple(m for m in PLATFORM_MIGRATIONS if m.version < 40))
    db.execute(
        "INSERT INTO audit_events(id,event_type,subject_type,subject_id,details_json,created_at) "
        "VALUES ('proof','execution_batch_flattened','batch','batch-1','{}','2026-10-02')"
    )
    before = [tuple(row) for row in db.execute("SELECT * FROM audit_events")]
    apply_migrations(db)
    apply_migrations(db)
    assert [tuple(row) for row in db.execute("SELECT * FROM audit_events")] == before
    plan = db.execute(
        "EXPLAIN QUERY PLAN SELECT 1 FROM audit_events "
        "WHERE subject_id=? AND event_type='execution_batch_flattened' LIMIT 1", ("batch-1",)
    ).fetchone()
    assert "idx_audit_events_subject_type" in plan[3]


def test_account_lookup_indexes_preserve_timestamp_and_missing_currency_results():
    db = memory_database()
    bootstrap_database(db)
    apply_migrations(db, tuple(m for m in PLATFORM_MIGRATIONS if m.version < 41))
    db.execute("INSERT INTO venues VALUES ('v','test','test','test','active','2026-10-02')")
    db.execute(
        "INSERT INTO accounts (id,venue_id,account_code,name,account_type,environment,"
        "base_currency,status,data_quality_state,created_at) "
        "VALUES ('a','v','a','a','test','simulation','USD','active','complete','2026-10-02')"
    )
    for at, scope in (("2026-10-02T09:00:00+08:00", "older"),
                      ("2026-10-02T02:00:00Z", "newer")):
        db.execute(
            "INSERT INTO account_risk_snapshots "
            "(account_id,as_of,currency,equity,data_quality_state,created_at,asset_scope) "
            "VALUES ('a',?,'USD','100','complete',?,?)", (at, at, scope),
        )
        db.execute("INSERT INTO account_capital_coverage VALUES ('a','scope',?,?,?)",
                   (at, at, at))
    queries = (
        ("SELECT asset_scope FROM account_risk_snapshots WHERE account_id='a' "
         "ORDER BY julianday(as_of) DESC LIMIT 1", "idx_account_risk_observed_time"),
        ("SELECT end_at FROM account_capital_coverage WHERE account_id='a' "
         "AND asset_scope='scope' ORDER BY julianday(end_at) DESC LIMIT 1",
         "idx_account_capital_coverage_end"),
        ("SELECT id FROM balance_snapshots WHERE account_id='a' "
         "AND upper(currency)='MISSING' ORDER BY as_of DESC,id LIMIT 1",
         "idx_balance_current_currency"),
    )
    before = [[tuple(row) for row in db.execute(sql)] for sql, _ in queries]
    assert before == [[("newer",)], [("2026-10-02T02:00:00Z",)], []]
    apply_migrations(db)
    apply_migrations(db)
    for (sql, index), expected in zip(queries, before, strict=True):
        assert [tuple(row) for row in db.execute(sql)] == expected
        assert index in str([tuple(row) for row in db.execute("EXPLAIN QUERY PLAN " + sql)])


@pytest.mark.parametrize("legacy_tables", [False, True])
def test_data_audit_migration_owns_fresh_and_existing_tables(legacy_tables):
    db = memory_database()
    bootstrap_database(db)
    apply_migrations(db, tuple(m for m in PLATFORM_MIGRATIONS if m.version < 36))
    previous = [tuple(row) for row in db.execute("SELECT * FROM schema_migrations")]
    migration = next(m for m in PLATFORM_MIGRATIONS if m.version == 36)
    if legacy_tables:
        for statement in migration.statements:
            db.execute(statement)
        db.execute("INSERT INTO data_audit_runs VALUES (1,'2026-09-26','{}')")
        db.execute("INSERT INTO data_audit_calendar VALUES ('CN','2026-09-26','[]','sina')")
    apply_migrations(db)
    apply_migrations(db)
    assert [
        tuple(row) for row in db.execute("SELECT * FROM schema_migrations WHERE version<36")
    ] == previous
    assert db.execute("SELECT COUNT(*) FROM data_audit_runs").fetchone()[0] == int(legacy_tables)
    assert db.execute("SELECT COUNT(*) FROM data_audit_calendar").fetchone()[0] == int(
        legacy_tables
    )
    assert (
        db.execute("SELECT checksum FROM schema_migrations WHERE version=36").fetchone()[0]
        == migration.checksum
    )


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


def test_cross_market_sampler_uses_covering_index_without_history_sort():
    db = memory_database()
    bootstrap_database(db)
    apply_migrations(db)
    plan = db.execute(
        "EXPLAIN QUERY PLAN SELECT created_at FROM market_spread_snapshots "
        "WHERE strategy_key=? AND strategy_instance_id=? ORDER BY created_at DESC LIMIT 1",
        ("cross_venue_spread", "strategy_cross_venue_spread_instance_default"),
    ).fetchall()
    detail = " ".join(row["detail"] for row in plan)
    assert "COVERING INDEX idx_market_spread_instance_created" in detail
    assert "TEMP B-TREE" not in detail


def test_fill_provenance_upgrade_preserves_legacy_facts_and_repeated_startup():
    db = memory_database()
    bootstrap_database(db)
    apply_migrations(db, PLATFORM_MIGRATIONS[:-1])
    db.execute(
        "INSERT INTO orders (id,command_id,account_id,instrument_id,symbol,side,order_type,"
        "quantity,status,created_at,updated_at) VALUES "
        "('old-order','old-command','account','instrument','TEST','buy','market','1',"
        "'filled','2026-09-08T00:00:00+00:00','2026-09-08T00:00:00+00:00')"
    )
    legacy = (
        "old-fill",
        "old-order",
        "account",
        "instrument",
        "buy",
        "0.123456789012345678",
        "2000.123456789012345678",
        "2026-09-08T00:00:00+00:00",
    )
    db.execute(
        "INSERT INTO fills "
        "(id,order_id,account_id,instrument_id,side,quantity,price,occurred_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        legacy,
    )
    apply_migrations(db, PLATFORM_MIGRATIONS)
    apply_migrations(db, PLATFORM_MIGRATIONS)
    row = db.execute("SELECT * FROM fills").fetchone()
    assert tuple(row)[:8] == legacy
    assert (row["origin"], row["source"], row["external_fill_id"]) == ("legacy", None, None)
    assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


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


def test_management_history_indexes_preserve_exact_values_and_cover_reads():
    from app.database_seeds import seed_reference_data

    db = memory_database()
    bootstrap_database(db)
    apply_migrations(db, tuple(m for m in PLATFORM_MIGRATIONS if m.version < 35))
    seed_reference_data(db)
    values = (
        "bybit-live-main", "2026-09-26T01:02:03.123456+08:00", "BTC",
        "0.123456789012345678", "complete", "2026-09-26T01:02:04.654321+08:00",
        "1.234567890123456789", "coin",
    )
    db.execute(
        "INSERT INTO account_risk_snapshots "
        "(account_id,as_of,currency,equity,data_quality_state,created_at,total_assets,asset_scope) "
        "VALUES (?,?,?,?,?,?,?,?)", values,
    )
    before = tuple(db.execute("SELECT * FROM account_risk_snapshots").fetchone())
    apply_migrations(db, PLATFORM_MIGRATIONS)
    assert tuple(db.execute("SELECT * FROM account_risk_snapshots").fetchone()) == before
    plan = db.execute(
        "EXPLAIN QUERY PLAN SELECT as_of,currency,equity,asset_scope,total_assets "
        "FROM account_risk_snapshots WHERE account_id=? AND equity IS NOT NULL "
        "AND as_of>=? ORDER BY as_of,created_at", ("bybit-live-main", "2026-01-01"),
    ).fetchall()
    assert any("COVERING INDEX idx_account_risk_history_cover" in row[3] for row in plan)
    plan = db.execute(
        "EXPLAIN QUERY PLAN SELECT payload_json FROM market_spread_snapshots "
        "WHERE strategy_key=? AND strategy_instance_id=? AND observed_at>=? "
        "ORDER BY observed_at DESC LIMIT 1", ("cross_venue_spread", "instance", "2026-01-01"),
    ).fetchall()
    assert any("idx_market_spread_instance_time" in row[3] for row in plan)


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

    migration = db.execute("SELECT name FROM schema_migrations WHERE version = 5").fetchone()
    assert migration["name"] == "user-identity-sessions-and-audit"

    table_names = {
        row["name"]
        for row in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
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
    assert [row["version"] for row in payload["migrations"]] == sorted(
        row["version"] for row in payload["migrations"]
    )
    assert payload["migrations"][-1]["version"] == max(
        migration.version for migration in PLATFORM_MIGRATIONS
    )
    assert (
        next(item for item in payload["migrations"] if item["version"] == 8)["name"]
        == "user-research-watchlist"
    )
    assert payload["migrations"][-1]["status"] == "applied"


def test_chase_terminal_table_is_an_append_only_upgrade_from_live_migration_26():
    migration26 = next(m for m in PLATFORM_MIGRATIONS if m.version == 26)
    assert (
        migration26.checksum == "68e2f141e69d6f6b349254c24ae0e2fb41d2efe3c08d94d0ce220f8696174040"
    )
    db = memory_database()
    bootstrap_database(db)
    apply_migrations(db, tuple(m for m in PLATFORM_MIGRATIONS if m.version <= 26))
    assert (
        db.execute("SELECT name FROM sqlite_master WHERE name='runtime_order_terminals'").fetchone()
        is None
    )
    apply_migrations(db)
    apply_migrations(db)
    assert db.execute(
        "SELECT name FROM sqlite_master WHERE name='runtime_order_terminals'"
    ).fetchone()
