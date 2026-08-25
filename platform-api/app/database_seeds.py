from __future__ import annotations

import sqlite3


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
            "read_only",
            "active",
            "Bybit 只读账户：策略损益、账户资金与订单信息。",
            None,
        ),
        (
            "strategy_short_term_l",
            "short_term_l",
            "短线交易员A",
            "read_only",
            "active",
            "MT5 只读监控账户：账户、订单、持仓、Deal、费用与风控信息。",
            None,
        ),
        (
            "strategy_short_term_w",
            "short_term_w",
            "短线交易员B",
            "read_only",
            "active",
            "未绑定真实账号的只读占位策略。",
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

    db.execute(
        """
        UPDATE strategy_definitions
        SET v1_scope = 'read_only', status = 'active'
        WHERE strategy_key IN ('bottom_fishing', 'short_term_l', 'short_term_w')
        """
    )
    db.execute(
        """
        UPDATE strategy_instances
        SET status = 'active', data_quality_state = 'unavailable'
        WHERE id IN (
            'strategy_bottom_fishing_instance_default',
            'strategy_short_term_l_instance_default',
            'strategy_short_term_w_instance_default'
        )
        """
    )

    venues = [
        ("venue_simulation", "SIM", "Simulation Venue", "simulation", "active"),
        ("venue_crypto", "CRYPTO_TEST", "Crypto Test Venue", "crypto", "active"),
        ("venue_mt5", "MT5_DEMO", "MT5 Demo", "mt5", "paused"),
        ("venue_bybit", "BYBIT", "Bybit", "crypto", "active"),
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
            "credential_bybit_live_001",
            "secret://environment/bybit-live-001",
            "venue_bybit",
            "live",
            "trading",
            "pending_secret",
        ),
        (
            "credential_mt5_live_001",
            "secret://environment/mt5-live-001",
            "venue_mt5",
            "live",
            "trading",
            "pending_secret",
        ),
        (
            "credential_bybit_bottom_fishing",
            "secret://environment/bybit-bottom-fishing",
            "venue_bybit",
            "live",
            "monitoring",
            "pending_secret",
        ),
        (
            "credential_mt5_short_term_a",
            "secret://environment/mt5-short-term-a",
            "venue_mt5",
            "live",
            "monitoring",
            "pending_secret",
        ),
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
        (
            "bybit-live-main",
            "venue_bybit",
            "BYBIT-LIVE-MAIN",
            "Bybit Live Main UTA",
            "crypto",
            "live",
            "USDT",
            "secret://environment/bybit-live-001",
            "active",
            "unavailable",
        ),
        (
            "mt5-live-main",
            "venue_mt5",
            "MT5-LIVE-MAIN",
            "MT5 Live Main Account",
            "mt5",
            "live",
            "USD",
            "secret://environment/mt5-live-001",
            "active",
            "unavailable",
        ),
        (
            "account_bybit_funding",
            "venue_bybit",
            "BYBIT-FUNDING",
            "资金费账户",
            "crypto",
            "live",
            "USDT",
            "secret://environment/bybit-funding",
            "inactive",
            "unavailable",
        ),
        (
            "account_bybit_bottom_fishing",
            "venue_bybit",
            "BYBIT-BOTTOM-FISHING",
            "抄底账户",
            "crypto",
            "live",
            "USDT",
            "secret://environment/bybit-bottom-fishing",
            "active",
            "unavailable",
        ),
        (
            "account_mt5_short_term_a",
            "venue_mt5",
            "MT5-SHORT-TERM-A",
            "短线交易员A监控账户",
            "mt5",
            "live",
            "USD",
            "secret://environment/mt5-short-term-a",
            "active",
            "unavailable",
        ),
        (
            "account_bybit_short_term_w",
            "venue_bybit",
            "BYBIT-SHORT-TERM-B",
            "短线交易员B历史占位账户",
            "crypto",
            "live",
            "USDT",
            "secret://environment/bybit-short-term-b",
            "inactive",
            "unavailable",
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
        if account[1] == "venue_bybit":
            continue
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

    for account_id, currency, available_balance in (
        ("account_crypto_test", "USDT", "100000"),
        ("account_crypto_test_b", "USDT", "100000"),
        ("account_mt5_demo", "USDT", "100000"),
    ):
        db.execute(
            """
            INSERT OR IGNORE INTO balance_snapshots (
                id, account_id, currency, equity, available_balance, source,
                data_quality_state, as_of, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'complete', ?, ?)
            """,
            (
                f"balance_complete_{account_id}",
                account_id,
                currency,
                available_balance,
                available_balance,
                "seed",
                created_at,
                created_at,
            ),
        )

    db.execute(
        """
        UPDATE accounts
        SET status = 'active', data_quality_state = 'unavailable'
        WHERE id IN (
            'bybit-live-main',
            'mt5-live-main',
            'account_bybit_bottom_fishing',
            'account_mt5_short_term_a'
        )
        """
    )
    db.execute(
        """
        UPDATE accounts
        SET status = 'inactive'
        WHERE id IN (
            'account_bybit_funding',
            'account_crypto_test',
            'account_crypto_test_b',
            'account_mt5_demo',
            'account_bybit_short_term_w'
        )
        """
    )

    bindings = [
        (
            "binding_funding_bybit_live_main",
            "strategy_funding_arbitrage_instance_default",
            "bybit-live-main",
            "primary",
            "trade_and_read",
        ),
        (
            "binding_funding_bybit",
            "strategy_funding_arbitrage_instance_default",
            "account_bybit_funding",
            "primary",
            "trade_and_read",
        ),
        (
            "binding_funding_simulation",
            "strategy_funding_arbitrage_instance_default",
            "account_sim_usdt",
            "local_test",
            "trade_and_read",
        ),
        (
            "binding_cross_bybit_live_main",
            "strategy_cross_venue_spread_instance_default",
            "bybit-live-main",
            "venue_a",
            "trade_and_read",
        ),
        (
            "binding_cross_mt5_live_main",
            "strategy_cross_venue_spread_instance_default",
            "mt5-live-main",
            "mt5_leg",
            "trade_and_read",
        ),
        (
            "binding_cross_sim",
            "strategy_cross_venue_spread_instance_default",
            "account_sim_usdt",
            "local_test",
            "trade_and_read",
        ),
        (
            "binding_bottom_fishing_bybit",
            "strategy_bottom_fishing_instance_default",
            "account_bybit_bottom_fishing",
            "primary",
            "read_only",
        ),
        (
            "binding_short_term_l_mt5",
            "strategy_short_term_l_instance_default",
            "account_mt5_short_term_a",
            "primary",
            "read_only",
        ),
    ]
    for binding_id, instance_id, account_id, role, capability in bindings:
        db.execute(
            """
            INSERT OR IGNORE INTO strategy_account_bindings (
                id, strategy_instance_id, account_id, role, capability, max_notional,
                status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (binding_id, instance_id, account_id, role, capability, None, "active", created_at),
        )

    db.execute(
        """
        UPDATE strategy_account_bindings
        SET role = 'primary', capability = 'trade_and_read', status = 'active'
        WHERE strategy_instance_id = 'strategy_funding_arbitrage_instance_default'
          AND account_id = 'bybit-live-main'
        """
    )
    db.execute(
        """
        UPDATE strategy_account_bindings
        SET role = 'local_test', capability = 'trade_and_read', status = 'active'
        WHERE strategy_instance_id = 'strategy_funding_arbitrage_instance_default'
          AND account_id = 'account_sim_usdt'
          AND role = 'local_test'
        """
    )
    db.execute(
        """
        UPDATE strategy_account_bindings
        SET role = 'primary', capability = 'trade_and_read', status = 'inactive'
        WHERE strategy_instance_id = 'strategy_funding_arbitrage_instance_default'
          AND account_id = 'account_bybit_funding'
        """
    )
    db.execute(
        """
        UPDATE strategy_account_bindings
        SET role = 'venue_a', capability = 'trade_and_read', status = 'active'
        WHERE strategy_instance_id = 'strategy_cross_venue_spread_instance_default'
          AND account_id = 'bybit-live-main'
        """
    )
    db.execute(
        """
        UPDATE strategy_account_bindings
        SET role = 'mt5_leg', capability = 'trade_and_read', status = 'active'
        WHERE strategy_instance_id = 'strategy_cross_venue_spread_instance_default'
          AND account_id = 'mt5-live-main'
        """
    )
    db.execute(
        """
        UPDATE strategy_account_bindings
        SET role = 'local_test', capability = 'trade_and_read', status = 'active'
        WHERE strategy_instance_id = 'strategy_cross_venue_spread_instance_default'
          AND account_id = 'account_sim_usdt'
          AND role = 'local_test'
        """
    )
    db.execute(
        """
        UPDATE strategy_account_bindings
        SET role = 'local_test', capability = 'trade_and_read', status = 'active'
        WHERE strategy_instance_id = 'strategy_cross_venue_spread_instance_default'
          AND account_id = 'account_sim_usdt'
          AND role = 'primary'
          AND NOT EXISTS (
              SELECT 1
              FROM strategy_account_bindings existing
              WHERE existing.strategy_instance_id = 'strategy_cross_venue_spread_instance_default'
                AND existing.account_id = 'account_sim_usdt'
                AND existing.role = 'local_test'
          )
        """
    )
    db.execute(
        """
        UPDATE strategy_account_bindings
        SET role = 'primary', capability = 'read_only', status = 'active'
        WHERE strategy_instance_id = 'strategy_bottom_fishing_instance_default'
          AND account_id = 'account_bybit_bottom_fishing'
        """
    )
    db.execute(
        """
        UPDATE strategy_account_bindings
        SET role = 'primary', capability = 'read_only', status = 'active'
        WHERE strategy_instance_id = 'strategy_short_term_l_instance_default'
          AND account_id = 'account_mt5_short_term_a'
        """
    )
    db.execute(
        """
        UPDATE strategy_account_bindings
        SET role = 'primary', capability = 'read_only', status = 'inactive'
        WHERE strategy_instance_id = 'strategy_short_term_w_instance_default'
          AND account_id = 'account_bybit_short_term_w'
        """
    )

    db.execute(
        """
        UPDATE strategy_account_bindings
        SET status = CASE
            WHEN strategy_instance_id = 'strategy_funding_arbitrage_instance_default'
                 AND account_id = 'bybit-live-main'
                 THEN 'active'
            WHEN strategy_instance_id = 'strategy_funding_arbitrage_instance_default'
                 AND account_id = 'account_sim_usdt'
                 AND role = 'local_test'
                 THEN 'active'
            WHEN strategy_instance_id = 'strategy_cross_venue_spread_instance_default'
                 AND account_id IN ('bybit-live-main', 'mt5-live-main')
                 THEN 'active'
            WHEN strategy_instance_id = 'strategy_cross_venue_spread_instance_default'
                 AND account_id = 'account_sim_usdt'
                 AND role = 'local_test'
                 THEN 'active'
            WHEN strategy_instance_id = 'strategy_bottom_fishing_instance_default'
                 AND account_id = 'account_bybit_bottom_fishing'
                 THEN 'active'
            WHEN strategy_instance_id = 'strategy_short_term_l_instance_default'
                 AND account_id = 'account_mt5_short_term_a'
                 THEN 'active'
            ELSE 'inactive'
        END
        WHERE strategy_instance_id IN (
            'strategy_funding_arbitrage_instance_default',
            'strategy_cross_venue_spread_instance_default',
            'strategy_bottom_fishing_instance_default',
            'strategy_short_term_l_instance_default',
            'strategy_short_term_w_instance_default'
        )
        """
    )
    db.execute(
        """
        UPDATE strategy_instances
        SET data_quality_state = CASE
            WHEN id = 'strategy_short_term_w_instance_default' THEN 'unavailable'
            WHEN id IN (
                'strategy_bottom_fishing_instance_default',
                'strategy_short_term_l_instance_default'
            ) THEN 'partial'
            ELSE data_quality_state
        END
        WHERE id IN (
            'strategy_bottom_fishing_instance_default',
            'strategy_short_term_l_instance_default',
            'strategy_short_term_w_instance_default'
        )
        """
    )

    instruments = [
        (
            "instrument_btc_usdt",
            "BTCUSDT",
            "BTC/USDT",
            "crypto_spot",
            "BTC",
            "USDT",
            "USDT",
            "BTC",
        ),
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
        (
            "instrument_xau_usd",
            "XAUUSD",
            "XAU/USD",
            "mt5_cfd",
            "XAU",
            "USD",
            "USD",
            "LOT",
        ),
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
        (
            "mapping_btc_sim",
            "instrument_btc_usdt",
            "venue_simulation",
            "BTCUSDT",
            "simulation",
        ),
        (
            "mapping_btc_crypto",
            "instrument_btc_usdt",
            "venue_crypto",
            "BTCUSDT",
            "exchange_symbol",
        ),
        (
            "mapping_btc_perp_crypto",
            "instrument_btc_usdt_perp",
            "venue_crypto",
            "BTCUSDT",
            "exchange_symbol",
        ),
        (
            "mapping_btc_perp_sim",
            "instrument_btc_usdt_perp",
            "venue_simulation",
            "BTCUSDT",
            "simulation",
        ),
        (
            "mapping_xaut_perp_crypto",
            "instrument_xau_usdt_perp",
            "venue_crypto",
            "XAUTUSDT",
            "exchange_symbol",
        ),
        (
            "mapping_xau_mt5",
            "instrument_xau_usd",
            "venue_mt5",
            "XAUUSD",
            "mt5_symbol",
        ),
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


__all__ = ["seed_reference_data"]
