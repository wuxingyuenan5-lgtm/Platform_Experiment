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
        version=9,
        name="strategy-instruction-immutable-plan",
        statements=(
            "ALTER TABLE strategy_runs ADD COLUMN action TEXT",
            "ALTER TABLE strategy_runs ADD COLUMN position_group_id TEXT",
            "ALTER TABLE strategy_runs ADD COLUMN requested_parameters_json TEXT",
            "ALTER TABLE strategy_runs ADD COLUMN execution_plan_json TEXT",
            "ALTER TABLE strategy_runs ADD COLUMN requested_by TEXT",
            "ALTER TABLE execution_batches ADD COLUMN strategy_instruction_id TEXT",
            (
                "CREATE UNIQUE INDEX idx_execution_batches_strategy_instruction "
                "ON execution_batches(strategy_instruction_id) "
                "WHERE strategy_instruction_id IS NOT NULL"
            ),
        ),
    ),
    Migration(
        version=10,
        name="strategy-instruction-request-fingerprint",
        statements=("ALTER TABLE strategy_runs ADD COLUMN request_fingerprint TEXT",),
    ),
    Migration(
        version=11,
        name="cross-spread-internal-capital-transfers",
        statements=(
            """
            CREATE TABLE internal_capital_transfers (
                id TEXT PRIMARY KEY,
                idempotency_key TEXT NOT NULL UNIQUE,
                strategy_instance_id TEXT NOT NULL,
                direction TEXT NOT NULL CHECK (
                    direction IN ('bybit_to_mt5', 'mt5_to_bybit')
                ),
                currency TEXT NOT NULL,
                amount TEXT NOT NULL,
                status TEXT NOT NULL CHECK (
                    status IN ('pending', 'completed', 'failed', 'result_unknown')
                ),
                external_transfer_id TEXT,
                failure_reason TEXT,
                requested_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(strategy_instance_id) REFERENCES strategy_instances(id)
            )
            """,
            """
            CREATE INDEX idx_internal_capital_transfers_strategy_created
            ON internal_capital_transfers(strategy_instance_id, created_at DESC)
            """,
        ),
    ),
    Migration(
        version=12,
        name="funding-spot-release-commands",
        statements=(
            """
            CREATE TABLE funding_spot_release_commands (
                child_id TEXT PRIMARY KEY,
                batch_id TEXT NOT NULL,
                cumulative_perpetual_fill TEXT NOT NULL,
                release_quantity TEXT NOT NULL,
                cumulative_spot_quantity TEXT NOT NULL,
                trade_command_id TEXT,
                order_id TEXT,
                status TEXT NOT NULL CHECK (
                    status IN ('declared', 'filled', 'failed', 'result_unknown')
                ),
                failure_reason TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(batch_id) REFERENCES execution_batches(id),
                FOREIGN KEY(trade_command_id) REFERENCES trade_commands(id),
                FOREIGN KEY(order_id) REFERENCES orders(id)
            )
            """,
            """
            CREATE INDEX idx_funding_spot_release_batch_created
            ON funding_spot_release_commands(batch_id, created_at)
            """,
        ),
    ),
    Migration(
        version=13,
        name="funding-perpetual-attempts",
        statements=(
            """
            CREATE TABLE funding_perpetual_attempts (
                id TEXT PRIMARY KEY,
                batch_id TEXT NOT NULL,
                attempt_number INTEGER NOT NULL,
                idempotency_key TEXT NOT NULL UNIQUE,
                limit_price TEXT NOT NULL,
                trade_command_id TEXT,
                order_id TEXT,
                status TEXT NOT NULL CHECK (
                    status IN (
                        'declared', 'acknowledged', 'accepted', 'partially_filled',
                        'filled', 'cancel_pending', 'canceled', 'rejected', 'result_unknown'
                    )
                ),
                cancel_requested_at TEXT,
                cancel_terminal_at TEXT,
                failure_reason TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(batch_id, attempt_number),
                FOREIGN KEY(batch_id) REFERENCES execution_batches(id),
                FOREIGN KEY(trade_command_id) REFERENCES trade_commands(id),
                FOREIGN KEY(order_id) REFERENCES orders(id)
            )
            """,
            """
            CREATE UNIQUE INDEX idx_funding_perpetual_attempts_one_active
            ON funding_perpetual_attempts(batch_id)
            WHERE status IN (
                'declared',
                'acknowledged',
                'accepted',
                'partially_filled',
                'cancel_pending'
            )
            """,
            """
            CREATE INDEX idx_funding_perpetual_attempts_batch_created
            ON funding_perpetual_attempts(batch_id, created_at)
            """,
        ),
    ),
    Migration(
        version=14,
        name="funding-attempt-requested-quantity",
        statements=(
            "ALTER TABLE funding_perpetual_attempts ADD COLUMN requested_quantity TEXT",
        ),
    ),
    Migration(
        version=15,
        name="execution-resource-claims",
        statements=(
            """
            CREATE TABLE IF NOT EXISTS execution_resource_claims (
                id TEXT PRIMARY KEY,
                resource_key TEXT NOT NULL,
                owner_type TEXT NOT NULL,
                owner_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                venue_id TEXT NOT NULL,
                resource_category TEXT NOT NULL,
                symbol TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """,
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_execution_resource_claims_active_resource
            ON execution_resource_claims(resource_key)
            WHERE status = 'active'
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_execution_resource_claims_owner
            ON execution_resource_claims(owner_type, owner_id, status)
            """,
        ),
    ),
    Migration(
        version=16,
        name="execution-balance-reservations",
        statements=(
            """
            CREATE TABLE IF NOT EXISTS execution_balance_reservations (
                id TEXT PRIMARY KEY,
                owner_type TEXT NOT NULL,
                owner_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                strategy_instance_id TEXT NOT NULL,
                instruction_id TEXT,
                currency TEXT NOT NULL,
                reserved_amount TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(strategy_instance_id) REFERENCES strategy_instances(id)
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_execution_balance_reservations_account
            ON execution_balance_reservations(account_id, currency, status)
            """,
        ),
    ),
    Migration(
        version=17,
        name="order-execution-intent-single-postonly-attempt",
        statements=(
            """
            CREATE TABLE IF NOT EXISTS order_execution_intents_v17 (
                idempotency_key TEXT PRIMARY KEY,
                reduce_only INTEGER NOT NULL DEFAULT 0,
                position_id TEXT,
                execution_policy TEXT NOT NULL DEFAULT 'default'
                CHECK (
                    execution_policy IN (
                        'default',
                        'fok',
                        'post_only_chase',
                        'post_only_single_attempt'
                    )
                )
            )
            """,
            """
            INSERT INTO order_execution_intents_v17 (
                idempotency_key, reduce_only, position_id, execution_policy
            )
            SELECT idempotency_key, reduce_only, position_id, execution_policy
            FROM order_execution_intents
            """,
            "DROP TABLE order_execution_intents",
            "ALTER TABLE order_execution_intents_v17 RENAME TO order_execution_intents",
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
