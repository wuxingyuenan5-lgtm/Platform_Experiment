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
        statements=("ALTER TABLE funding_perpetual_attempts ADD COLUMN requested_quantity TEXT",),
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
    Migration(
        version=18,
        name="assisted-capital-transfer-reconciliation",
        statements=(
            "ALTER TABLE internal_capital_transfers ADD COLUMN mode TEXT",
            "ALTER TABLE internal_capital_transfers ADD COLUMN source_account_id TEXT",
            "ALTER TABLE internal_capital_transfers ADD COLUMN destination_account_id TEXT",
            "ALTER TABLE internal_capital_transfers ADD COLUMN source_balance_before TEXT",
            "ALTER TABLE internal_capital_transfers ADD COLUMN destination_balance_before TEXT",
            """
            UPDATE internal_capital_transfers
            SET mode = CASE
                WHEN external_transfer_id IS NULL AND failure_reason IS NULL
                    THEN 'assisted'
                ELSE 'automated'
            END
            WHERE mode IS NULL
            """,
        ),
    ),
    Migration(
        # Version 19 is already owned by the deployed capital-transfer
        # migration.  A-share persistence must be additive and therefore has
        # its own immutable ledger entry.
        version=20,
        name="a-share-research-persistent-snapshots",
        statements=(
            """
            CREATE TABLE IF NOT EXISTS research_a_share_refresh_runs (
                run_id TEXT PRIMARY KEY,
                target_trade_date TEXT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL CHECK(status IN ('running','ready','partial','error')),
                error_code TEXT,
                message TEXT
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_research_a_share_refresh_runs_finished
            ON research_a_share_refresh_runs(finished_at DESC)
            """,
            """
            CREATE TABLE IF NOT EXISTS research_a_share_dataset_snapshots (
                dataset TEXT PRIMARY KEY,
                observed_at TEXT,
                fetched_at TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('ready','partial','stale','error','no_data')),
                source TEXT NOT NULL,
                payload_json TEXT,
                error_code TEXT,
                message TEXT,
                refresh_run_id TEXT,
                FOREIGN KEY(refresh_run_id) REFERENCES research_a_share_refresh_runs(run_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS research_a_share_history (
                dataset TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                entity_code TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                source TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                refresh_run_id TEXT,
                PRIMARY KEY(dataset, observed_at, entity_code),
                FOREIGN KEY(refresh_run_id) REFERENCES research_a_share_refresh_runs(run_id)
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_research_a_share_history_lookup
            ON research_a_share_history(dataset, observed_at DESC)
            """,
        ),
    ),
    Migration(
        version=21,
        name="a-share-enforced-schema-and-pool-configuration",
        statements=(
            # Repair databases created by the former repository DDL guard.
            # That guard allowed orphaned refresh IDs, so preserve the snapshot
            # while dropping only an unverifiable legacy provenance reference.
            """CREATE TABLE research_a_share_refresh_runs_v21 (
                run_id TEXT PRIMARY KEY, target_trade_date TEXT, started_at TEXT NOT NULL,
                finished_at TEXT, status TEXT NOT NULL
                    CHECK(status IN ('running','ready','partial','error')),
                error_code TEXT, message TEXT)""",
            "INSERT INTO research_a_share_refresh_runs_v21 "
            "SELECT * FROM research_a_share_refresh_runs",
            """CREATE TABLE research_a_share_dataset_snapshots_v21 (
                dataset TEXT PRIMARY KEY, observed_at TEXT, fetched_at TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('ready','partial','stale','error','no_data')),
                source TEXT NOT NULL, payload_json TEXT, error_code TEXT, message TEXT,
                refresh_run_id TEXT REFERENCES research_a_share_refresh_runs_v21(run_id))""",
            """INSERT INTO research_a_share_dataset_snapshots_v21
                SELECT dataset, observed_at, fetched_at, status, source, payload_json,
                    error_code, message,
                    CASE WHEN refresh_run_id IS NULL OR EXISTS (
                        SELECT 1 FROM research_a_share_refresh_runs_v21 run
                        WHERE run.run_id = research_a_share_dataset_snapshots.refresh_run_id
                    ) THEN refresh_run_id ELSE NULL END
                FROM research_a_share_dataset_snapshots""",
            """CREATE TABLE research_a_share_history_v21 (
                dataset TEXT NOT NULL, observed_at TEXT NOT NULL, entity_code TEXT NOT NULL,
                payload_json TEXT NOT NULL, source TEXT NOT NULL, fetched_at TEXT NOT NULL,
                refresh_run_id TEXT REFERENCES research_a_share_refresh_runs_v21(run_id),
                PRIMARY KEY(dataset, observed_at, entity_code))""",
            """INSERT INTO research_a_share_history_v21
                SELECT dataset, observed_at, entity_code, payload_json, source, fetched_at,
                    CASE WHEN refresh_run_id IS NULL OR EXISTS (
                        SELECT 1 FROM research_a_share_refresh_runs_v21 run
                        WHERE run.run_id = research_a_share_history.refresh_run_id
                    ) THEN refresh_run_id ELSE NULL END
                FROM research_a_share_history""",
            "DROP TABLE research_a_share_history",
            "DROP TABLE research_a_share_dataset_snapshots",
            "DROP TABLE research_a_share_refresh_runs",
            "ALTER TABLE research_a_share_refresh_runs_v21 RENAME TO research_a_share_refresh_runs",
            (
                "ALTER TABLE research_a_share_dataset_snapshots_v21 RENAME TO research_a_shar"
                "e_dataset_snapshots"
            ),
            "ALTER TABLE research_a_share_history_v21 RENAME TO research_a_share_history",
            (
                "CREATE INDEX idx_research_a_share_refresh_runs_finished ON research_a_share_"
                "refresh_runs(finished_at DESC)"
            ),
            (
                "CREATE INDEX idx_research_a_share_history_lookup ON research_a_share_history"
                "(dataset, observed_at DESC)"
            ),
            """CREATE TABLE research_a_share_pool_config (
                id INTEGER PRIMARY KEY CHECK(id=1), codes_json TEXT NOT NULL,
                row_version INTEGER NOT NULL CHECK(row_version>=1), updated_at TEXT NOT NULL)""",
            """INSERT INTO research_a_share_pool_config (id,codes_json,row_version,updated_at)
                SELECT 1, (SELECT json_group_array(json_extract(value,'$.code'))
                    FROM json_each(payload_json,'$.stocks')), 1, fetched_at
                FROM research_a_share_dataset_snapshots WHERE dataset='stock_pool'
                    AND json_type(payload_json,'$.stocks')='array'""",
        ),
    ),
    Migration(
        version=22,
        name="strategy-account-snapshot-scope-and-venue-events",
        statements=(
            """CREATE TABLE IF NOT EXISTS financial_facts (
                id TEXT PRIMARY KEY, idempotency_key TEXT NOT NULL UNIQUE,
                content_hash TEXT NOT NULL, fact_type TEXT NOT NULL, source TEXT NOT NULL,
                external_id TEXT NOT NULL, strategy_instance_id TEXT NOT NULL,
                account_id TEXT, instrument_id TEXT, side TEXT, quantity TEXT,
                quantity_unit TEXT, price TEXT, contract_multiplier TEXT, amount TEXT,
                currency TEXT, base_currency TEXT NOT NULL, fx_rate_to_base TEXT,
                converted_amount TEXT, available_balance TEXT, occurred_at TEXT NOT NULL,
                payload_json TEXT NOT NULL, data_quality_state TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(source, external_id, fact_type, strategy_instance_id),
                FOREIGN KEY(strategy_instance_id) REFERENCES strategy_instances(id),
                FOREIGN KEY(account_id) REFERENCES accounts(id),
                FOREIGN KEY(instrument_id) REFERENCES instruments(id))""",
            """CREATE INDEX IF NOT EXISTS idx_financial_facts_strategy_time
                ON financial_facts(strategy_instance_id, occurred_at)""",
            """CREATE INDEX IF NOT EXISTS idx_financial_facts_account_instrument
                ON financial_facts(account_id, instrument_id, occurred_at)""",
            """CREATE TABLE IF NOT EXISTS account_sync_status (
                account_id TEXT PRIMARY KEY, status TEXT NOT NULL, error_code TEXT,
                last_attempt_at TEXT, last_success_at TEXT, updated_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES accounts(id))""",
            """CREATE TABLE IF NOT EXISTS account_risk_snapshots (
                account_id TEXT NOT NULL, as_of TEXT NOT NULL, currency TEXT NOT NULL,
                equity TEXT, margin TEXT, free_margin TEXT, margin_level TEXT,
                data_quality_state TEXT NOT NULL, created_at TEXT NOT NULL,
                PRIMARY KEY(account_id, as_of), FOREIGN KEY(account_id) REFERENCES accounts(id))""",
            "ALTER TABLE account_risk_snapshots ADD COLUMN payload_json TEXT NOT NULL DEFAULT '{}'",
            "ALTER TABLE account_risk_snapshots ADD COLUMN total_assets TEXT",
            (
                "ALTER TABLE account_risk_snapshots ADD COLUMN asset_scope "
                "TEXT NOT NULL DEFAULT 'unspecified'"
            ),
            """CREATE TABLE account_venue_snapshots (
                account_id TEXT PRIMARY KEY, source TEXT NOT NULL, venue TEXT NOT NULL,
                as_of TEXT NOT NULL, history_start TEXT, history_end TEXT,
                data_quality_state TEXT NOT NULL, payload_json TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES accounts(id))""",
            """CREATE TABLE venue_account_events (
                account_id TEXT NOT NULL, source TEXT NOT NULL, event_type TEXT NOT NULL,
                external_id TEXT NOT NULL, instrument_id TEXT, platform_order_id TEXT,
                occurred_at TEXT NOT NULL, amount TEXT, currency TEXT, payload_json TEXT NOT NULL,
                PRIMARY KEY(account_id, source, event_type, external_id),
                FOREIGN KEY(account_id) REFERENCES accounts(id))""",
            (
                "CREATE INDEX idx_venue_account_events_time "
                "ON venue_account_events(account_id, occurred_at DESC)"
            ),
            (
                "CREATE INDEX idx_venue_account_events_order "
                "ON venue_account_events(platform_order_id, event_type)"
            ),
            "ALTER TABLE orders ADD COLUMN venue_payload_json TEXT",
            """CREATE TABLE balance_snapshots_v22 (
                id TEXT PRIMARY KEY, account_id TEXT NOT NULL, currency TEXT NOT NULL,
                equity TEXT NOT NULL, available_balance TEXT, source TEXT NOT NULL,
                data_quality_state TEXT NOT NULL, as_of TEXT NOT NULL, created_at TEXT NOT NULL,
                FOREIGN KEY(account_id) REFERENCES accounts(id))""",
            "INSERT INTO balance_snapshots_v22 SELECT * FROM balance_snapshots",
            "DROP TABLE balance_snapshots",
            "ALTER TABLE balance_snapshots_v22 RENAME TO balance_snapshots",
            "CREATE INDEX idx_balance_snapshots_account ON balance_snapshots(account_id, as_of)",
        ),
    ),
    Migration(
        version=23,
        name="operational-fill-provenance",
        statements=(
            "ALTER TABLE fills ADD COLUMN origin TEXT NOT NULL DEFAULT 'legacy' "
            "CHECK(origin IN ('legacy','runtime_confirmation','venue_execution'))",
            "ALTER TABLE fills ADD COLUMN source TEXT",
            "ALTER TABLE fills ADD COLUMN external_fill_id TEXT",
        ),
    ),
)


PLATFORM_MIGRATIONS += (
    Migration(version=24, name="account-capital-movements", statements=(
        """CREATE TABLE account_capital_movements (
            account_id TEXT NOT NULL REFERENCES accounts(id), external_event_id TEXT NOT NULL,
            asset_scope TEXT NOT NULL, occurred_at TEXT NOT NULL, currency TEXT NOT NULL,
            amount TEXT, event_type TEXT NOT NULL, payload_json TEXT NOT NULL,
            PRIMARY KEY(account_id, asset_scope, external_event_id))""",
        "CREATE INDEX ix_capital_movement_time ON "
        "account_capital_movements(account_id, asset_scope, occurred_at)",
        """CREATE TABLE account_capital_coverage (
            account_id TEXT NOT NULL REFERENCES accounts(id), asset_scope TEXT NOT NULL,
            start_at TEXT NOT NULL, end_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            PRIMARY KEY(account_id, asset_scope, start_at))""",
        """CREATE TABLE account_capital_sync (
            account_id TEXT PRIMARY KEY REFERENCES accounts(id), attempted_at TEXT NOT NULL,
            status TEXT NOT NULL, error_code TEXT)""",
        """CREATE TABLE account_valuation_rates (
            account_id TEXT NOT NULL REFERENCES accounts(id), currency TEXT NOT NULL,
            as_of TEXT NOT NULL, usd_rate TEXT NOT NULL,
            PRIMARY KEY(account_id, currency, as_of))""",
    )),
)


PLATFORM_MIGRATIONS += (
    Migration(version=25, name="capital-valuation-provenance", statements=(
        "ALTER TABLE account_valuation_rates "
        "ADD COLUMN source TEXT NOT NULL DEFAULT 'bybit_wallet'",
    )),
)

PLATFORM_MIGRATIONS += (
    Migration(version=26, name="cross-spread-adverse-spread-guards", statements=(
        "ALTER TABLE cross_spread_exit_plans "
        "ADD COLUMN take_profit_max_adverse_spread TEXT NOT NULL DEFAULT '0'",
        "ALTER TABLE cross_spread_exit_plans "
        "ADD COLUMN stop_loss_max_adverse_spread TEXT NOT NULL DEFAULT '0'",
    )),
)


PLATFORM_MIGRATIONS += (
    Migration(version=27, name="cross-spread-terminal-fill-evidence", statements=(
        "CREATE TABLE runtime_order_terminals (order_id TEXT PRIMARY KEY REFERENCES orders(id), "
        "event_id TEXT NOT NULL UNIQUE, filled_quantity TEXT NOT NULL, occurred_at TEXT NOT NULL)",
    )),
)

PLATFORM_MIGRATIONS += (
    Migration(version=28, name="cross-spread-open-triggers", statements=(
        """CREATE TABLE cross_spread_open_triggers (
            id TEXT PRIMARY KEY, idempotency_key TEXT NOT NULL UNIQUE,
            direction TEXT NOT NULL, quantity_oz TEXT NOT NULL, limit_spread TEXT NOT NULL,
            limit_strategy TEXT NOT NULL, request_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, triggered_at TEXT, execution_batch_id TEXT,
            failure_reason TEXT
        )""",
        "CREATE INDEX idx_cross_spread_open_triggers_status "
        "ON cross_spread_open_triggers(status, created_at)",
    )),
)


PLATFORM_MIGRATIONS += (
    Migration(version=29, name="account-read-job-status", statements=(
        """CREATE TABLE account_read_jobs (
            account_id TEXT NOT NULL REFERENCES accounts(id),
            job TEXT NOT NULL CHECK(job IN ('history','settlements')),
            status TEXT NOT NULL, last_attempt_at TEXT NOT NULL,
            last_success_at TEXT, error_code TEXT,
            PRIMARY KEY(account_id, job)
        )""",
    )),
)


PLATFORM_MIGRATIONS += (
    Migration(version=30, name="strategy-research-archive", statements=(
        """CREATE TABLE research_strategy_parts (
            part_id TEXT PRIMARY KEY, start_cursor TEXT, end_cursor TEXT NOT NULL UNIQUE,
            path TEXT NOT NULL UNIQUE, checksum TEXT NOT NULL, row_count INTEGER NOT NULL,
            first_at TEXT NOT NULL,last_at TEXT NOT NULL,published_at TEXT NOT NULL)""",
        """CREATE TABLE research_strategy_capture (
            id INTEGER PRIMARY KEY CHECK(id=1),cursor TEXT,state_json TEXT NOT NULL,
            status_json TEXT NOT NULL)""",
        """CREATE TABLE research_strategy_experiments (
            run_id TEXT PRIMARY KEY,user_id TEXT NOT NULL,parameters_json TEXT NOT NULL,
            parts_json TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN
            ('queued','running','completed','failed','cancelled')),
            result_json TEXT,error TEXT,created_at TEXT NOT NULL)""",
        """CREATE TABLE research_strategy_drafts (
            id TEXT PRIMARY KEY,user_id TEXT NOT NULL,payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL)""",
    )),
)


PLATFORM_MIGRATIONS += (
    Migration(version=31, name="strategy-research-serving-projection", statements=(
        """CREATE TABLE research_strategy_projection (
            kind TEXT NOT NULL, entity TEXT NOT NULL, at_ms INTEGER NOT NULL,
            payload_json TEXT NOT NULL, PRIMARY KEY(kind,entity,at_ms)) WITHOUT ROWID""",
        """CREATE TABLE research_strategy_projection_cursor (
            id INTEGER PRIMARY KEY CHECK(id=1), part_rowid INTEGER NOT NULL,
            state_json TEXT NOT NULL, updated_at TEXT NOT NULL)""",
    )),
    Migration(version=32, name="strategy-management-serving-projection", statements=(
        """CREATE TABLE strategy_management_projection (
          strategy_instance_id TEXT NOT NULL, account_id TEXT NOT NULL DEFAULT '',
          kind TEXT NOT NULL, payload_json TEXT, updated_at TEXT, requested_at TEXT NOT NULL,
          attempted_at TEXT, error_code TEXT,
          PRIMARY KEY(strategy_instance_id,account_id,kind)) WITHOUT ROWID""",
    )),
    Migration(version=33, name="execution-risk-persistence", statements=(
        """CREATE TABLE IF NOT EXISTS trading_kill_switches (
          scope_type TEXT NOT NULL, scope_id TEXT NOT NULL, enabled INTEGER NOT NULL,
          reason TEXT, actor TEXT NOT NULL, version INTEGER NOT NULL, updated_at TEXT NOT NULL,
          PRIMARY KEY(scope_type, scope_id))""",
        """CREATE TABLE IF NOT EXISTS kill_switch_commands (
          idempotency_key TEXT PRIMARY KEY, payload_hash TEXT NOT NULL,
          scope_type TEXT NOT NULL, scope_id TEXT NOT NULL, created_at TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS execution_risk_policies (
          strategy_instance_id TEXT PRIMARY KEY, max_leg_delay_seconds INTEGER NOT NULL,
          max_residual_notional TEXT NOT NULL, failure_action TEXT NOT NULL,
          actor TEXT NOT NULL, updated_at TEXT NOT NULL,
          FOREIGN KEY(strategy_instance_id) REFERENCES strategy_instances(id))""",
        """CREATE TABLE IF NOT EXISTS execution_risk_policy_commands (
          idempotency_key TEXT PRIMARY KEY, payload_hash TEXT NOT NULL,
          strategy_instance_id TEXT NOT NULL, created_at TEXT NOT NULL,
          FOREIGN KEY(strategy_instance_id) REFERENCES strategy_instances(id))""",
        """CREATE TABLE IF NOT EXISTS execution_batch_risk (
          batch_id TEXT PRIMARY KEY, strategy_instance_id TEXT NOT NULL,
          max_leg_delay_seconds INTEGER NOT NULL, max_residual_notional TEXT NOT NULL,
          failure_action TEXT NOT NULL, risk_status TEXT NOT NULL,
          residual_exposure_notional TEXT NOT NULL, residual_currency TEXT NOT NULL,
          data_quality_state TEXT NOT NULL, first_fill_at TEXT, last_leg_at TEXT,
          risk_reason TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
          FOREIGN KEY(batch_id) REFERENCES execution_batches(id),
          FOREIGN KEY(strategy_instance_id) REFERENCES strategy_instances(id))""",
        """CREATE TABLE IF NOT EXISTS execution_risk_actions (
          id TEXT PRIMARY KEY, idempotency_key TEXT NOT NULL UNIQUE,
          payload_hash TEXT NOT NULL, batch_id TEXT NOT NULL, action TEXT NOT NULL,
          status TEXT NOT NULL, actor TEXT NOT NULL, reason TEXT,
          generated_order_ids_json TEXT NOT NULL, failure_reason TEXT,
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
          FOREIGN KEY(batch_id) REFERENCES execution_batches(id))""",
        """CREATE INDEX IF NOT EXISTS idx_execution_risk_actions_batch
          ON execution_risk_actions(batch_id, created_at)""",
    )),
    Migration(version=34, name="funding-basis-serving-projection", statements=(
        """CREATE TABLE funding_basis_projection_cursor (
          id INTEGER PRIMARY KEY CHECK(id=1), last_at_ms INTEGER NOT NULL DEFAULT 0,
          completed INTEGER NOT NULL DEFAULT 0 CHECK(completed IN (0,1)),
          updated_at TEXT NOT NULL)""",
    )),
)


PLATFORM_MIGRATIONS += (
    Migration(version=35, name="management-history-read-indexes", statements=(
        "CREATE INDEX idx_account_risk_history_cover\n"
        "        ON account_risk_snapshots(account_id,as_of,created_at,"
        "currency,equity,asset_scope,total_assets)\n"
        "        WHERE equity IS NOT NULL",
        """CREATE INDEX idx_market_spread_instance_time
        ON market_spread_snapshots(strategy_key,strategy_instance_id,observed_at)""",
    )),
)


PLATFORM_MIGRATIONS += (
    Migration(version=36, name="data-audit-persistence", statements=(
        """CREATE TABLE IF NOT EXISTS data_audit_runs (
          id INTEGER PRIMARY KEY, checked_at TEXT NOT NULL, report_json TEXT NOT NULL)""",
        """CREATE TABLE IF NOT EXISTS data_audit_calendar (
          market TEXT PRIMARY KEY, fetched_at TEXT NOT NULL,
          days_json TEXT NOT NULL, source TEXT NOT NULL)""",
    )),
)


PLATFORM_MIGRATIONS += (
    Migration(version=37, name="cross-market-sampling-read-index", statements=(
        """CREATE INDEX idx_market_spread_instance_created
        ON market_spread_snapshots(strategy_key,strategy_instance_id,created_at DESC)""",
    )),
    Migration(version=38, name="user-research-market-layouts", statements=(
        """CREATE TABLE user_research_market_layouts (
            user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            market_id TEXT NOT NULL,
            groups_json TEXT NOT NULL,
            row_version INTEGER NOT NULL CHECK(row_version >= 1),
            updated_at TEXT NOT NULL,
            PRIMARY KEY(user_id, market_id)
        )""",
    )),
    Migration(version=39, name="funding-executable-spread-exit-plans", statements=(
        """CREATE TABLE funding_exit_plans (
            open_instruction_id TEXT PRIMARY KEY REFERENCES strategy_runs(id),
            account_id TEXT NOT NULL REFERENCES accounts(id),
            revision INTEGER NOT NULL CHECK(revision>0),
            enabled INTEGER NOT NULL CHECK(enabled IN (0,1)),
            take_profit_spread TEXT,
            stop_loss_spread TEXT,
            configured_by TEXT NOT NULL,
            close_key TEXT UNIQUE,
            trigger_json TEXT,
            close_instruction_id TEXT REFERENCES strategy_runs(id),
            last_error TEXT,
            updated_at TEXT NOT NULL
        )""",
    )),
    Migration(version=40, name="execution-audit-subject-lookup", statements=(
        "CREATE INDEX idx_audit_events_subject_type ON audit_events(subject_id,event_type)",
    )),
    Migration(version=41, name="account-current-observation-lookups", statements=(
        "CREATE INDEX idx_balance_current_currency "
        "ON balance_snapshots(account_id,upper(currency),as_of DESC,id)",
        "CREATE INDEX idx_account_risk_observed_time "
        "ON account_risk_snapshots(account_id,julianday(as_of) DESC,asset_scope)",
        "CREATE INDEX idx_account_capital_coverage_end "
        "ON account_capital_coverage(account_id,asset_scope,julianday(end_at) DESC)",
    )),
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

        db.execute("SAVEPOINT schema_migration")
        try:
            for statement in migration.statements:
                db.execute(statement)
            db.execute(
                """
                INSERT INTO schema_migrations (version, name, checksum, applied_at)
                VALUES (?, ?, ?, ?)
                """,
                (migration.version, migration.name, migration.checksum, utc_now_iso()),
            )
        except Exception:
            db.execute("ROLLBACK TO SAVEPOINT schema_migration")
            db.execute("RELEASE SAVEPOINT schema_migration")
            raise
        db.execute("RELEASE SAVEPOINT schema_migration")


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
