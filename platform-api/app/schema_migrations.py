from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TypedDict

from app.database import connection

LEDGER_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    checksum TEXT NOT NULL,
    applied_at TEXT NOT NULL
);
"""


class AppliedMigration(TypedDict):
    version: int
    name: str
    checksum: str
    appliedAt: str


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    statements: tuple[str, ...] = ()

    @property
    def checksum(self) -> str:
        payload = json.dumps(
            {
                "version": self.version,
                "name": self.name,
                "statements": self.statements,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# Version 1 records the schema that already existed before the ledger was introduced.
# It is intentionally a no-op: existing tables, indexes, columns and seed identifiers
# remain owned by their current modules until a dedicated migration is reviewed.
PLATFORM_MIGRATIONS: tuple[Migration, ...] = (
    Migration(version=1, name="existing-platform-schema-baseline"),
    Migration(
        version=2,
        name="cross-spread-market-exit-plans",
        statements=(
            """
            CREATE TABLE IF NOT EXISTS order_execution_intents (
                idempotency_key TEXT PRIMARY KEY,
                reduce_only INTEGER NOT NULL DEFAULT 0,
                position_id TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS cross_spread_exit_plans (
                id TEXT PRIMARY KEY,
                strategy_instance_id TEXT NOT NULL,
                open_batch_id TEXT NOT NULL UNIQUE,
                close_batch_id TEXT,
                direction TEXT NOT NULL,
                quantity_oz TEXT NOT NULL,
                mt5_position_id TEXT NOT NULL,
                entry_spread TEXT NOT NULL,
                take_profit_spread TEXT NOT NULL,
                stop_loss_spread TEXT NOT NULL,
                status TEXT NOT NULL,
                trigger_reason TEXT,
                trigger_spread TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                triggered_at TEXT,
                closed_at TEXT,
                FOREIGN KEY(strategy_instance_id) REFERENCES strategy_instances(id),
                FOREIGN KEY(open_batch_id) REFERENCES execution_batches(id),
                FOREIGN KEY(close_batch_id) REFERENCES execution_batches(id)
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_cross_spread_exit_plans_status
            ON cross_spread_exit_plans(status, created_at)
            """,
        ),
    ),
    Migration(
        version=3,
        name="cross-spread-exit-execution-modes",
        statements=(
            """
            ALTER TABLE cross_spread_exit_plans
            ADD COLUMN take_profit_execution_mode TEXT NOT NULL DEFAULT 'market'
            CHECK (take_profit_execution_mode IN ('market', 'limit'))
            """,
            """
            ALTER TABLE cross_spread_exit_plans
            ADD COLUMN stop_loss_execution_mode TEXT NOT NULL DEFAULT 'market'
            CHECK (stop_loss_execution_mode IN ('market', 'limit'))
            """,
        ),
    ),
    Migration(
        version=4,
        name="cross-spread-limit-execution-policies",
        statements=(
            """
            ALTER TABLE order_execution_intents
            ADD COLUMN execution_policy TEXT NOT NULL DEFAULT 'default'
            CHECK (execution_policy IN ('default', 'fok', 'post_only_chase'))
            """,
            """
            ALTER TABLE cross_spread_exit_plans
            ADD COLUMN take_profit_limit_strategy TEXT NOT NULL DEFAULT 'fok'
            CHECK (take_profit_limit_strategy IN ('fok', 'post_only_chase'))
            """,
            """
            ALTER TABLE cross_spread_exit_plans
            ADD COLUMN stop_loss_limit_strategy TEXT NOT NULL DEFAULT 'fok'
            CHECK (stop_loss_limit_strategy IN ('fok', 'post_only_chase'))
            """,
        ),
    ),
    Migration(
        version=5,
        name="user-identity-sessions-and-audit",
        statements=(
            """
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                username_normalized TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                display_name TEXT,
                real_name TEXT,
                avatar_key TEXT,
                phone TEXT,
                phone_normalized TEXT,
                email TEXT,
                email_normalized TEXT,
                role_code TEXT,
                requested_role_code TEXT,
                department TEXT,
                member_type TEXT,
                application_note TEXT,
                rejection_reason TEXT,
                lifecycle_status TEXT NOT NULL,
                auth_version INTEGER NOT NULL DEFAULT 1,
                row_version INTEGER NOT NULL DEFAULT 1,
                failed_login_count INTEGER NOT NULL DEFAULT 0,
                locked_until TEXT,
                registered_at TEXT NOT NULL,
                approved_at TEXT,
                approved_by TEXT,
                last_login_at TEXT,
                password_changed_at TEXT,
                created_by TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                CHECK (
                    role_code IS NULL
                    OR role_code IN ('ceo', 'tech_lead', 'employee', 'member')
                ),
                CHECK (
                    requested_role_code IS NULL
                    OR requested_role_code IN ('employee', 'member')
                ),
                CHECK (lifecycle_status IN ('pending', 'active', 'disabled', 'rejected')),
                CHECK (auth_version >= 1),
                CHECK (row_version >= 1),
                CHECK (failed_login_count >= 0),
                CHECK (
                    (lifecycle_status IN ('pending', 'rejected') AND role_code IS NULL)
                    OR
                    (lifecycle_status IN ('active', 'disabled') AND role_code IS NOT NULL)
                ),
                FOREIGN KEY(approved_by) REFERENCES users(id),
                FOREIGN KEY(created_by) REFERENCES users(id)
            )
            """,
            """
            CREATE UNIQUE INDEX idx_users_email_normalized_unique
            ON users(email_normalized)
            WHERE email_normalized IS NOT NULL
            """,
            """
            CREATE UNIQUE INDEX idx_users_phone_normalized_unique
            ON users(phone_normalized)
            WHERE phone_normalized IS NOT NULL
            """,
            """
            CREATE INDEX idx_users_lifecycle_role
            ON users(lifecycle_status, role_code, created_at)
            """,
            """
            CREATE INDEX idx_users_locked_until
            ON users(locked_until)
            WHERE locked_until IS NOT NULL
            """,
            """
            CREATE TABLE user_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                csrf_token_hash TEXT NOT NULL,
                auth_version INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                idle_expires_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                last_reauthenticated_at TEXT,
                revoked_at TEXT,
                revoke_reason TEXT,
                ip_address TEXT,
                user_agent TEXT,
                CHECK (auth_version >= 1),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """,
            """
            CREATE INDEX idx_user_sessions_user_active
            ON user_sessions(user_id, revoked_at, created_at)
            """,
            """
            CREATE INDEX idx_user_sessions_expiry
            ON user_sessions(expires_at, idle_expires_at)
            WHERE revoked_at IS NULL
            """,
            """
            CREATE TABLE password_reset_tickets (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                consumed_at TEXT,
                revoked_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(created_by) REFERENCES users(id)
            )
            """,
            """
            CREATE UNIQUE INDEX idx_password_reset_tickets_one_active
            ON password_reset_tickets(user_id)
            WHERE consumed_at IS NULL AND revoked_at IS NULL
            """,
            """
            CREATE INDEX idx_password_reset_tickets_expiry
            ON password_reset_tickets(expires_at)
            WHERE consumed_at IS NULL AND revoked_at IS NULL
            """,
            """
            ALTER TABLE audit_events ADD COLUMN actor_user_id TEXT
            """,
            """
            ALTER TABLE audit_events ADD COLUMN request_id TEXT
            """,
            """
            ALTER TABLE audit_events ADD COLUMN result TEXT
            """,
            """
            ALTER TABLE audit_events ADD COLUMN ip_address TEXT
            """,
            """
            ALTER TABLE audit_events ADD COLUMN auth_method TEXT
            """,
            """
            CREATE INDEX idx_audit_events_actor_created
            ON audit_events(actor_user_id, created_at)
            """,
            """
            CREATE INDEX idx_audit_events_request_id
            ON audit_events(request_id)
            WHERE request_id IS NOT NULL
            """,
        ),
    ),
    Migration(
        version=6,
        name="member-fund-holdings-and-unit-nav",
        statements=(
            """
            ALTER TABLE funds ADD COLUMN fund_code TEXT
            """,
            """
            CREATE UNIQUE INDEX idx_funds_fund_code_unique
            ON funds(fund_code)
            WHERE fund_code IS NOT NULL
            """,
            """
            CREATE TABLE member_fund_holdings (
                id TEXT PRIMARY KEY,
                member_user_id TEXT NOT NULL,
                fund_id TEXT NOT NULL,
                share_quantity TEXT NOT NULL,
                cumulative_invested TEXT NOT NULL,
                confirmed_at TEXT,
                as_of TEXT NOT NULL,
                source TEXT NOT NULL,
                status TEXT NOT NULL,
                row_version INTEGER NOT NULL DEFAULT 1,
                updated_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(member_user_id, fund_id),
                CHECK (length(trim(share_quantity)) > 0),
                CHECK (length(trim(cumulative_invested)) > 0),
                CHECK (source IN ('manual_admin', 'migration', 'external_import')),
                CHECK (status IN ('active', 'closed')),
                CHECK (row_version >= 1),
                FOREIGN KEY(member_user_id) REFERENCES users(id),
                FOREIGN KEY(fund_id) REFERENCES funds(id),
                FOREIGN KEY(updated_by) REFERENCES users(id)
            )
            """,
            """
            CREATE INDEX idx_member_fund_holdings_member_status
            ON member_fund_holdings(member_user_id, status, updated_at)
            """,
            """
            CREATE INDEX idx_member_fund_holdings_fund_status
            ON member_fund_holdings(fund_id, status, updated_at)
            """,
            """
            CREATE TABLE fund_nav_snapshots (
                id TEXT PRIMARY KEY,
                fund_id TEXT NOT NULL,
                valuation_time TEXT NOT NULL,
                unit_nav TEXT NOT NULL,
                currency TEXT NOT NULL,
                source TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(fund_id, valuation_time),
                CHECK (length(trim(unit_nav)) > 0),
                CHECK (length(currency) BETWEEN 3 AND 8),
                CHECK (source IN ('manual_admin', 'migration', 'external_import')),
                CHECK (status IN ('available', 'superseded', 'invalid')),
                FOREIGN KEY(fund_id) REFERENCES funds(id)
            )
            """,
            """
            CREATE INDEX idx_fund_nav_snapshots_latest
            ON fund_nav_snapshots(fund_id, status, valuation_time DESC)
            """,
        ),
    ),
    Migration(
        version=7,
        name="eod-report-attempt-revision",
        statements=(
            "ALTER TABLE eod_reconciliation_reports RENAME TO eod_reconciliation_reports_legacy",
            """CREATE TABLE eod_reconciliation_reports (
                id TEXT PRIMARY KEY,
                idempotency_key TEXT NOT NULL UNIQUE,
                natural_key TEXT NOT NULL,
                attempt INTEGER NOT NULL DEFAULT 1,
                payload_hash TEXT NOT NULL,
                business_date TEXT NOT NULL,
                timezone TEXT NOT NULL,
                valuation_time TEXT NOT NULL,
                strategy_instance_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                actor TEXT NOT NULL,
                owner TEXT NOT NULL,
                due_at TEXT NOT NULL,
                status TEXT NOT NULL,
                scale_gate_status TEXT NOT NULL,
                order_reconciliation_count INTEGER NOT NULL,
                account_reconciliation_run_id TEXT,
                economic_event_import_id TEXT,
                nav_snapshot_id TEXT,
                formal_pnl_count INTEGER NOT NULL,
                formal_pnl_incomplete_count INTEGER NOT NULL,
                open_difference_count INTEGER NOT NULL,
                resolved_difference_count INTEGER NOT NULL,
                accepted_difference_count INTEGER NOT NULL,
                skipped_external_ids_json TEXT NOT NULL,
                missing_account_ids_json TEXT NOT NULL,
                errors_json TEXT NOT NULL,
                review_payload_hash TEXT,
                reviewer TEXT,
                review_decision TEXT,
                review_reason TEXT,
                reviewed_at TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                UNIQUE(natural_key, attempt)
            )""",
            """INSERT INTO eod_reconciliation_reports (
                id, idempotency_key, natural_key, attempt, payload_hash, business_date,
                timezone, valuation_time, strategy_instance_id, account_id, actor, owner,
                due_at, status, scale_gate_status, order_reconciliation_count,
                account_reconciliation_run_id, economic_event_import_id, nav_snapshot_id,
                formal_pnl_count, formal_pnl_incomplete_count, open_difference_count,
                resolved_difference_count, accepted_difference_count, skipped_external_ids_json,
                missing_account_ids_json, errors_json, review_payload_hash, reviewer,
                review_decision, review_reason, reviewed_at, created_at, completed_at
            ) SELECT id, idempotency_key, natural_key, 1, payload_hash, business_date,
                timezone, valuation_time, strategy_instance_id, account_id, actor, owner,
                due_at, status, scale_gate_status, order_reconciliation_count,
                account_reconciliation_run_id, economic_event_import_id, nav_snapshot_id,
                formal_pnl_count, formal_pnl_incomplete_count, open_difference_count,
                resolved_difference_count, accepted_difference_count, skipped_external_ids_json,
                missing_account_ids_json, errors_json, review_payload_hash, reviewer,
                review_decision, review_reason, reviewed_at, created_at, completed_at
                FROM eod_reconciliation_reports_legacy""",
            "DROP TABLE eod_reconciliation_reports_legacy",
            """CREATE INDEX IF NOT EXISTS idx_eod_reports_business_date
            ON eod_reconciliation_reports(business_date, strategy_instance_id, account_id)""",
            """CREATE INDEX IF NOT EXISTS idx_eod_reports_status
            ON eod_reconciliation_reports(status, scale_gate_status, due_at)""",
        ),
    ),
)


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def validate_migrations(migrations: tuple[Migration, ...]) -> None:
    versions = [migration.version for migration in migrations]
    names = [migration.name for migration in migrations]
    if versions != sorted(versions) or len(versions) != len(set(versions)):
        raise RuntimeError("Schema migration versions must be unique and strictly ordered")
    if len(names) != len(set(names)):
        raise RuntimeError("Schema migration names must be unique")
    if any(version <= 0 for version in versions):
        raise RuntimeError("Schema migration versions must be positive integers")


def apply_migrations(
    db: sqlite3.Connection,
    migrations: tuple[Migration, ...] = PLATFORM_MIGRATIONS,
) -> None:
    validate_migrations(migrations)
    db.executescript(LEDGER_SQL)

    for migration in migrations:
        existing = db.execute(
            "SELECT name, checksum FROM schema_migrations WHERE version = ?",
            (migration.version,),
        ).fetchone()
        if existing is not None:
            if existing["name"] != migration.name or existing["checksum"] != migration.checksum:
                raise RuntimeError(
                    f"Schema migration {migration.version} changed after it was applied"
                )
            continue

        for statement in migration.statements:
            db.execute(statement)
        db.execute(
            """
            INSERT INTO schema_migrations (version, name, checksum, applied_at)
            VALUES (?, ?, ?, ?)
            """,
            (migration.version, migration.name, migration.checksum, utc_now_iso()),
        )


def apply_platform_migrations() -> None:
    with connection() as db:
        apply_migrations(db)


def list_applied_migrations() -> list[AppliedMigration]:
    with connection() as db:
        db.executescript(LEDGER_SQL)
        rows = db.execute(
            """
            SELECT version, name, checksum, applied_at
            FROM schema_migrations
            ORDER BY version
            """
        ).fetchall()
    return [
        AppliedMigration(
            version=int(row["version"]),
            name=str(row["name"]),
            checksum=str(row["checksum"]),
            appliedAt=str(row["applied_at"]),
        )
        for row in rows
    ]
