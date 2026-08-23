from __future__ import annotations

import sqlite3

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS execution_batches (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT,
    strategy_instance_id TEXT,
    account_id TEXT NOT NULL,
    strategy_key TEXT NOT NULL,
    direction TEXT NOT NULL,
    status TEXT NOT NULL,
    requires_manual_intervention INTEGER NOT NULL DEFAULT 0,
    failure_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(strategy_instance_id) REFERENCES strategy_instances(id)
);

CREATE TABLE IF NOT EXISTS legal_entities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS funds (
    id TEXT PRIMARY KEY,
    legal_entity_id TEXT NOT NULL,
    name TEXT NOT NULL,
    base_currency TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(legal_entity_id) REFERENCES legal_entities(id)
);

CREATE TABLE IF NOT EXISTS portfolios (
    id TEXT PRIMARY KEY,
    fund_id TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(fund_id) REFERENCES funds(id)
);

CREATE TABLE IF NOT EXISTS books (
    id TEXT PRIMARY KEY,
    portfolio_id TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(portfolio_id) REFERENCES portfolios(id)
);

CREATE TABLE IF NOT EXISTS strategy_definitions (
    id TEXT PRIMARY KEY,
    strategy_key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    v1_scope TEXT NOT NULL,
    status TEXT NOT NULL,
    description TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS strategy_versions (
    id TEXT PRIMARY KEY,
    strategy_definition_id TEXT NOT NULL,
    version TEXT NOT NULL,
    status TEXT NOT NULL,
    pnl_policy TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(strategy_definition_id, version),
    FOREIGN KEY(strategy_definition_id) REFERENCES strategy_definitions(id)
);

CREATE TABLE IF NOT EXISTS strategy_instances (
    id TEXT PRIMARY KEY,
    strategy_definition_id TEXT NOT NULL,
    strategy_version_id TEXT NOT NULL,
    book_id TEXT NOT NULL,
    name TEXT NOT NULL,
    trading_mode TEXT NOT NULL,
    status TEXT NOT NULL,
    capital_base TEXT,
    base_currency TEXT NOT NULL,
    data_quality_state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(strategy_definition_id) REFERENCES strategy_definitions(id),
    FOREIGN KEY(strategy_version_id) REFERENCES strategy_versions(id),
    FOREIGN KEY(book_id) REFERENCES books(id)
);

CREATE TABLE IF NOT EXISTS venues (
    id TEXT PRIMARY KEY,
    venue_code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    venue_type TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    venue_id TEXT NOT NULL,
    account_code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    account_type TEXT NOT NULL,
    environment TEXT NOT NULL,
    base_currency TEXT NOT NULL,
    credential_ref TEXT,
    status TEXT NOT NULL,
    data_quality_state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(venue_id) REFERENCES venues(id)
);

CREATE TABLE IF NOT EXISTS credential_references (
    id TEXT PRIMARY KEY,
    credential_ref TEXT NOT NULL UNIQUE,
    venue_id TEXT NOT NULL,
    environment TEXT NOT NULL,
    purpose TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(venue_id) REFERENCES venues(id)
);

CREATE TABLE IF NOT EXISTS strategy_account_bindings (
    id TEXT PRIMARY KEY,
    strategy_instance_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    role TEXT NOT NULL,
    capability TEXT NOT NULL DEFAULT 'read_only',
    max_notional TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(strategy_instance_id, account_id, role),
    FOREIGN KEY(strategy_instance_id) REFERENCES strategy_instances(id),
    FOREIGN KEY(account_id) REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS instruments (
    id TEXT PRIMARY KEY,
    instrument_code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    instrument_type TEXT NOT NULL,
    base_currency TEXT NOT NULL,
    quote_currency TEXT NOT NULL,
    settle_currency TEXT NOT NULL,
    quantity_unit TEXT NOT NULL,
    data_quality_state TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS instrument_mappings (
    id TEXT PRIMARY KEY,
    instrument_id TEXT NOT NULL,
    venue_id TEXT NOT NULL,
    external_symbol TEXT NOT NULL,
    mapping_type TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(instrument_id, venue_id, external_symbol),
    FOREIGN KEY(instrument_id) REFERENCES instruments(id),
    FOREIGN KEY(venue_id) REFERENCES venues(id)
);

CREATE TABLE IF NOT EXISTS contract_specifications (
    id TEXT PRIMARY KEY,
    instrument_id TEXT NOT NULL,
    version TEXT NOT NULL,
    price_tick TEXT NOT NULL,
    min_order_quantity TEXT NOT NULL,
    quantity_step TEXT NOT NULL,
    contract_multiplier TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    data_quality_state TEXT NOT NULL,
    UNIQUE(instrument_id, version),
    FOREIGN KEY(instrument_id) REFERENCES instruments(id)
);

CREATE TABLE IF NOT EXISTS balance_snapshots (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    currency TEXT NOT NULL,
    equity TEXT NOT NULL,
    available_balance TEXT NOT NULL,
    source TEXT NOT NULL,
    data_quality_state TEXT NOT NULL,
    as_of TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(account_id) REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS trade_commands (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    strategy_instance_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    command_type TEXT NOT NULL,
    side TEXT NOT NULL,
    order_type TEXT NOT NULL,
    quantity TEXT NOT NULL,
    price TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(strategy_instance_id) REFERENCES strategy_instances(id),
    FOREIGN KEY(account_id) REFERENCES accounts(id),
    FOREIGN KEY(instrument_id) REFERENCES instruments(id)
);

CREATE TABLE IF NOT EXISTS external_order_references (
    id TEXT PRIMARY KEY,
    platform_order_id TEXT NOT NULL,
    venue_id TEXT NOT NULL,
    external_order_id TEXT NOT NULL,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(venue_id, external_order_id),
    FOREIGN KEY(platform_order_id) REFERENCES orders(id),
    FOREIGN KEY(venue_id) REFERENCES venues(id)
);

CREATE TABLE IF NOT EXISTS pnl_attribution_items (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    category TEXT NOT NULL,
    amount TEXT NOT NULL,
    currency TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS strategy_nav_snapshots (
    id TEXT PRIMARY KEY,
    strategy_instance_id TEXT NOT NULL,
    valuation_time TEXT NOT NULL,
    equity TEXT NOT NULL,
    capital_base TEXT NOT NULL,
    nav TEXT NOT NULL,
    currency TEXT NOT NULL,
    data_quality_state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(strategy_instance_id) REFERENCES strategy_instances(id)
);

CREATE TABLE IF NOT EXISTS strategy_runs (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    strategy_instance_id TEXT NOT NULL,
    strategy_key TEXT NOT NULL,
    direction TEXT NOT NULL,
    status TEXT NOT NULL,
    execution_batch_id TEXT,
    reason TEXT,
    failure_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(strategy_instance_id) REFERENCES strategy_instances(id),
    FOREIGN KEY(execution_batch_id) REFERENCES execution_batches(id)
);

CREATE TABLE IF NOT EXISTS risk_decisions (
    id TEXT PRIMARY KEY,
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    reason TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    details_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id TEXT PRIMARY KEY,
    command_id TEXT NOT NULL UNIQUE,
    account_id TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    order_type TEXT NOT NULL,
    quantity TEXT NOT NULL,
    price TEXT,
    status TEXT NOT NULL,
    external_order_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS execution_batch_legs (
    id TEXT PRIMARY KEY,
    batch_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    role TEXT NOT NULL,
    account_id TEXT,
    instrument_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    order_type TEXT NOT NULL,
    quantity TEXT NOT NULL,
    price TEXT,
    order_id TEXT,
    status TEXT NOT NULL,
    failure_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(batch_id, role),
    UNIQUE(batch_id, sequence),
    FOREIGN KEY(batch_id) REFERENCES execution_batches(id),
    FOREIGN KEY(account_id) REFERENCES accounts(id),
    FOREIGN KEY(order_id) REFERENCES orders(id)
);

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
);

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
);

CREATE TABLE IF NOT EXISTS fills (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity TEXT NOT NULL,
    price TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    UNIQUE(order_id, id),
    FOREIGN KEY(order_id) REFERENCES orders(id)
);

CREATE TABLE IF NOT EXISTS positions (
    account_id TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    net_quantity TEXT NOT NULL,
    average_price TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(account_id, instrument_id)
);

CREATE TABLE IF NOT EXISTS economic_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    account_id TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    order_id TEXT,
    amount TEXT NOT NULL,
    currency TEXT NOT NULL,
    occurred_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS market_spread_snapshots (
    id TEXT PRIMARY KEY,
    strategy_key TEXT NOT NULL,
    strategy_instance_id TEXT,
    left_venue_code TEXT NOT NULL,
    left_symbol TEXT NOT NULL,
    right_venue_code TEXT NOT NULL,
    right_symbol TEXT NOT NULL,
    status TEXT NOT NULL,
    left_bid TEXT,
    left_ask TEXT,
    left_mid TEXT,
    right_bid TEXT,
    right_ask TEXT,
    right_mid TEXT,
    long_spread TEXT,
    short_spread TEXT,
    funding_rate TEXT,
    usdt_usd TEXT,
    buyer_inventory_fee TEXT,
    seller_inventory_fee TEXT,
    payload_json TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_market_spread_snapshots_strategy_time
ON market_spread_snapshots(strategy_key, observed_at);

CREATE TABLE IF NOT EXISTS pnl_results (
    account_id TEXT NOT NULL,
    instrument_id TEXT NOT NULL,
    realized_pnl TEXT NOT NULL,
    trading_pnl TEXT NOT NULL,
    fees TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(account_id, instrument_id)
);

CREATE INDEX IF NOT EXISTS idx_execution_batches_account
ON execution_batches(account_id, created_at);

CREATE INDEX IF NOT EXISTS idx_execution_batch_legs_batch
ON execution_batch_legs(batch_id, sequence);

CREATE UNIQUE INDEX IF NOT EXISTS idx_execution_resource_claims_active_resource
ON execution_resource_claims(resource_key)
WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_execution_resource_claims_owner
ON execution_resource_claims(owner_type, owner_id, status);

CREATE INDEX IF NOT EXISTS idx_execution_balance_reservations_account
ON execution_balance_reservations(account_id, currency, status);

CREATE INDEX IF NOT EXISTS idx_strategy_instances_definition
ON strategy_instances(strategy_definition_id);

CREATE INDEX IF NOT EXISTS idx_strategy_account_bindings_instance
ON strategy_account_bindings(strategy_instance_id);

CREATE INDEX IF NOT EXISTS idx_balance_snapshots_account
ON balance_snapshots(account_id, as_of);

CREATE INDEX IF NOT EXISTS idx_trade_commands_idempotency
ON trade_commands(idempotency_key);

CREATE INDEX IF NOT EXISTS idx_strategy_nav_snapshots_instance
ON strategy_nav_snapshots(strategy_instance_id, valuation_time);

CREATE INDEX IF NOT EXISTS idx_strategy_runs_instance
ON strategy_runs(strategy_instance_id, created_at);
"""


def ensure_column(
    db: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> None:
    columns = {row["name"] for row in db.execute(f"PRAGMA table_info({table_name})").fetchall()}
    if column_name not in columns:
        db.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")


def migrate_schema(db: sqlite3.Connection) -> None:
    ensure_column(db, "execution_batches", "idempotency_key", "TEXT")
    ensure_column(db, "execution_batches", "strategy_instance_id", "TEXT")
    ensure_column(db, "execution_batch_legs", "account_id", "TEXT")
    ensure_column(
        db,
        "strategy_account_bindings",
        "capability",
        "TEXT NOT NULL DEFAULT 'read_only'",
    )
    db.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_execution_batches_idempotency
        ON execution_batches(idempotency_key)
        WHERE idempotency_key IS NOT NULL
        """
    )


def bootstrap_database(db: sqlite3.Connection) -> None:
    db.executescript(SCHEMA_SQL)
    migrate_schema(db)


__all__ = ["SCHEMA_SQL", "bootstrap_database", "ensure_column", "migrate_schema"]
