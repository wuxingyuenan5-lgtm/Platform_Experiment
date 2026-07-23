from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.config import get_settings

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


def database_path() -> Path:
    path = Path(get_settings().database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    db = sqlite3.connect(database_path())
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def initialize_database() -> None:
    with connection() as db:
        db.executescript(SCHEMA_SQL)
        migrate_schema(db)
        seed_reference_data(db)


def migrate_schema(db: sqlite3.Connection) -> None:
    ensure_column(db, "execution_batches", "idempotency_key", "TEXT")
    ensure_column(db, "execution_batches", "strategy_instance_id", "TEXT")
    ensure_column(db, "execution_batch_legs", "account_id", "TEXT")
    db.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_execution_batches_idempotency
        ON execution_batches(idempotency_key)
        WHERE idempotency_key IS NOT NULL
        """
    )


def ensure_column(
    db: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> None:
    columns = {row["name"] for row in db.execute(f"PRAGMA table_info({table_name})").fetchall()}
    if column_name not in columns:
        db.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")


def seed_reference_data(db: sqlite3.Connection) -> None:
    created_at = "2026-07-19T00:00:00+00:00"

    db.execute(
        "INSERT OR IGNORE INTO legal_entities (id, name, created_at) VALUES (?, ?, ?)",
        ("le_default", "Variable Global", created_at),
    )
    db.execute(
        """
        INSERT OR IGNORE INTO funds (id, legal_entity_id, name, base_currency, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("fund_default", "le_default", "Default Internal Fund", "USDT", created_at),
    )
    db.execute(
        """
        INSERT OR IGNORE INTO portfolios (id, fund_id, name, created_at)
        VALUES (?, ?, ?, ?)
        """,
        ("portfolio_default", "fund_default", "Default Portfolio", created_at),
    )
    db.execute(
        """
        INSERT OR IGNORE INTO books (id, portfolio_id, name, created_at)
        VALUES (?, ?, ?, ?)
        """,
        ("book_default", "portfolio_default", "Default Book", created_at),
    )

    strategies = [
        (
            "strategy_funding_arbitrage",
            "funding_arbitrage",
            "资费套利",
            "closed_loop",
            "active",
            "V1 完整闭环：Crypto Funding、订单、持仓、费用、PnL、固定时间净值。",
            "100000",
        ),
        (
            "strategy_cross_venue_spread",
            "cross_venue_spread",
            "跨所价差",
            "closed_loop",
            "active",
            "V1 完整闭环：Crypto 腿和 MT5 腿的订单、Deal、持仓、费用、PnL。",
            "100000",
        ),
        (
            "strategy_home_abroad_spread",
            "home_abroad_spread",
            "海内外价差",
            "reserved",
            "paused",
            "V1 保留分析、模拟和字段，不做 CTP 与正式汇率损益闭环。",
            None,
        ),
        (
            "strategy_bottom_fishing",
            "bottom_fishing",
            "抄底",
            "placeholder",
            "paused",
            "V1 保留管理入口和占位状态。",
            None,
        ),
        (
            "strategy_short_term_l",
            "short_term_l",
            "短线交易员 L",
            "placeholder",
            "paused",
            "V1 保留管理入口和占位状态。",
            None,
        ),
        (
            "strategy_short_term_w",
            "short_term_w",
            "短线交易员 W",
            "placeholder",
            "paused",
            "V1 保留管理入口和占位状态。",
            None,
        ),
    ]
    for strategy_id, key, name, scope, status, description, capital_base in strategies:
        version_id = f"{strategy_id}_v1"
        instance_id = f"{strategy_id}_instance_default"
        db.execute(
            """
            INSERT OR IGNORE INTO strategy_definitions (
                id, strategy_key, name, v1_scope, status, description, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (strategy_id, key, name, scope, status, description, created_at),
        )
        db.execute(
            """
            INSERT OR IGNORE INTO strategy_versions (
                id, strategy_definition_id, version, status, pnl_policy, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (version_id, strategy_id, "v1", status, "strategy_operational_nav", created_at),
        )
        db.execute(
            """
            INSERT OR IGNORE INTO strategy_instances (
                id, strategy_definition_id, strategy_version_id, book_id, name,
                trading_mode, status, capital_base, base_currency, data_quality_state, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                instance_id,
                strategy_id,
                version_id,
                "book_default",
                f"{name} 默认实例",
                "simulation",
                status,
                capital_base,
                "USDT",
                "complete" if capital_base else "partial",
                created_at,
            ),
        )

    venues = [
        ("venue_simulation", "SIM", "Simulation Venue", "simulation", "active"),
        ("venue_crypto", "CRYPTO_TEST", "Crypto Test Venue", "crypto", "active"),
        ("venue_mt5", "MT5_DEMO", "MT5 Demo", "mt5", "paused"),
    ]
    for venue in venues:
        db.execute(
            """
            INSERT OR IGNORE INTO venues (id, venue_code, name, venue_type, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (*venue, created_at),
        )

    credential_references = [
        (
            "credential_crypto_test_001",
            "secret://crypto-test-001",
            "venue_crypto",
            "testnet",
            "trading",
            "pending_secret",
        ),
        (
            "credential_crypto_test_002",
            "secret://crypto-test-002",
            "venue_crypto",
            "testnet",
            "trading",
            "pending_secret",
        ),
        (
            "credential_mt5_demo_001",
            "secret://mt5-demo-001",
            "venue_mt5",
            "demo",
            "trading",
            "pending_secret",
        ),
    ]
    for credential in credential_references:
        db.execute(
            """
            INSERT OR IGNORE INTO credential_references (
                id, credential_ref, venue_id, environment, purpose, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (*credential, created_at),
        )

    accounts = [
        (
            "account_sim_usdt",
            "venue_simulation",
            "SIM-USDT-001",
            "Simulation USDT Account",
            "internal",
            "simulation",
            "USDT",
            None,
            "active",
            "complete",
        ),
        (
            "account_crypto_test",
            "venue_crypto",
            "CRYPTO-TEST-001",
            "Crypto Test Account",
            "crypto",
            "testnet",
            "USDT",
            "secret://crypto-test-001",
            "paused",
            "partial",
        ),
        (
            "account_crypto_test_b",
            "venue_crypto",
            "CRYPTO-TEST-002",
            "Crypto Test Account B",
            "crypto",
            "testnet",
            "USDT",
            "secret://crypto-test-002",
            "paused",
            "partial",
        ),
        (
            "account_mt5_demo",
            "venue_mt5",
            "MT5-DEMO-001",
            "MT5 Demo Account",
            "mt5",
            "demo",
            "USDT",
            "secret://mt5-demo-001",
            "paused",
            "partial",
        ),
    ]
    for account in accounts:
        db.execute(
            """
            INSERT OR IGNORE INTO accounts (
                id, venue_id, account_code, name, account_type, environment, base_currency,
                credential_ref, status, data_quality_state, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (*account, created_at),
        )
        db.execute(
            """
            INSERT OR IGNORE INTO balance_snapshots (
                id, account_id, currency, equity, available_balance, source,
                data_quality_state, as_of, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"balance_{account[0]}",
                account[0],
                account[6],
                "100000",
                "100000",
                "seed",
                account[9],
                created_at,
                created_at,
            ),
        )

    bindings = [
        (
            "binding_funding_sim",
            "strategy_funding_arbitrage_instance_default",
            "account_sim_usdt",
            "primary",
        ),
        (
            "binding_cross_sim",
            "strategy_cross_venue_spread_instance_default",
            "account_sim_usdt",
            "primary",
        ),
        (
            "binding_cross_crypto",
            "strategy_cross_venue_spread_instance_default",
            "account_crypto_test",
            "venue_a",
        ),
        (
            "binding_cross_crypto_b",
            "strategy_cross_venue_spread_instance_default",
            "account_crypto_test_b",
            "venue_b",
        ),
        (
            "binding_cross_mt5",
            "strategy_cross_venue_spread_instance_default",
            "account_mt5_demo",
            "mt5_leg",
        ),
    ]
    for binding_id, instance_id, account_id, role in bindings:
        db.execute(
            """
            INSERT OR IGNORE INTO strategy_account_bindings (
                id, strategy_instance_id, account_id, role, max_notional, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (binding_id, instance_id, account_id, role, "100000", "active", created_at),
        )

    instruments = [
        ("instrument_btc_usdt", "BTCUSDT", "BTC/USDT", "crypto_spot", "BTC", "USDT", "USDT", "BTC"),
        (
            "instrument_btc_usdt_perp",
            "BTCUSDT-PERP",
            "BTC/USDT Perpetual",
            "crypto_perp",
            "BTC",
            "USDT",
            "USDT",
            "BTC",
        ),
        (
            "instrument_xau_usdt_perp",
            "XAUTUSDT-PERP",
            "XAUT/USDT Perpetual",
            "crypto_perp",
            "XAU",
            "USDT",
            "USDT",
            "XAU",
        ),
        ("instrument_xau_usd", "XAUUSD", "XAU/USD", "mt5_cfd", "XAU", "USD", "USD", "LOT"),
    ]
    for instrument in instruments:
        db.execute(
            """
            INSERT OR IGNORE INTO instruments (
                id, instrument_code, name, instrument_type, base_currency, quote_currency,
                settle_currency, quantity_unit, data_quality_state, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (*instrument, "complete", created_at),
        )
        db.execute(
            """
            INSERT OR IGNORE INTO contract_specifications (
                id, instrument_id, version, price_tick, min_order_quantity,
                quantity_step, contract_multiplier, effective_from, data_quality_state
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"contract_{instrument[0]}_v1",
                instrument[0],
                "v1",
                "0.01",
                "0.001" if instrument[3] != "mt5_cfd" else "0.01",
                "0.001" if instrument[3] != "mt5_cfd" else "0.01",
                "1",
                created_at,
                "complete",
            ),
        )
    db.execute(
        """
        UPDATE contract_specifications
        SET min_order_quantity = ?, quantity_step = ?, contract_multiplier = ?
        WHERE instrument_id = ?
        """,
        ("0.01", "0.01", "100", "instrument_xau_usd"),
    )

    mappings = [
        ("mapping_btc_sim", "instrument_btc_usdt", "venue_simulation", "BTCUSDT", "simulation"),
        ("mapping_btc_crypto", "instrument_btc_usdt", "venue_crypto", "BTCUSDT", "exchange_symbol"),
        (
            "mapping_btc_perp_crypto",
            "instrument_btc_usdt_perp",
            "venue_crypto",
            "BTCUSDT",
            "exchange_symbol",
        ),
        (
            "mapping_xaut_perp_crypto",
            "instrument_xau_usdt_perp",
            "venue_crypto",
            "XAUTUSDT",
            "exchange_symbol",
        ),
        ("mapping_xau_mt5", "instrument_xau_usd", "venue_mt5", "XAUUSD", "mt5_symbol"),
    ]
    for mapping in mappings:
        db.execute(
            """
            INSERT OR IGNORE INTO instrument_mappings (
                id, instrument_id, venue_id, external_symbol, mapping_type, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (*mapping, "active", created_at),
        )
