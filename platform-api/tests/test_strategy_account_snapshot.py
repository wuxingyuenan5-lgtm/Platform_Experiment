from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection
from app.main import app


def test_unconfigured_bybit_strategy_account_is_explicitly_unavailable(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "strategy-account-snapshot.db")

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/strategies/instances/"
            "strategy_bottom_fishing_instance_default/account-snapshot"
        )

    assert response.status_code == 200
    assert response.json() == {
        "strategyInstanceId": "strategy_bottom_fishing_instance_default",
        "accountId": "account_bybit_bottom_fishing",
        "accountCode": "BYBIT-BOTTOM-FISHING",
        "capability": "read_only",
        "dataQualityState": "waiting_initial_sync",
        "asOf": None,
        "balance": None,
        "equityHistory": [],
        "accountRisk": None,
        "positions": [],
        "orders": [],
        "fills": [],
        "pnl": None,
        "syncStatus": "waiting_initial_sync",
        "syncErrorCode": None,
    }


def test_unbound_strategy_account_snapshot_returns_explicit_unbound_state(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "strategy-account-unbound.db")

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/strategies/instances/"
            "strategy_short_term_w_instance_default/account-snapshot"
        )

    assert response.status_code == 200
    assert response.json() == {
        "strategyInstanceId": "strategy_short_term_w_instance_default",
        "accountId": None,
        "accountCode": None,
        "capability": None,
        "dataQualityState": "unbound",
        "asOf": None,
        "balance": None,
        "equityHistory": [],
        "accountRisk": None,
        "positions": [],
        "orders": [],
        "fills": [],
        "pnl": None,
        "syncStatus": "unbound",
        "syncErrorCode": "account_unbound",
    }


def test_strategy_account_snapshot_aggregates_assets_in_account_currency(
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "strategy-account-assets.db")

    with TestClient(app) as client:
        with connection() as db:
            db.execute(
                """
                INSERT INTO balance_snapshots (
                    id, account_id, currency, equity, available_balance, source,
                    data_quality_state, as_of, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?), (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "balance-bottom-usdt",
                    "account_bybit_bottom_fishing",
                    "USD",
                    "100",
                    "90",
                    "test",
                    "complete",
                    "2026-08-21T00:00:00+00:00",
                    "2026-08-21T00:00:00+00:00",
                    "balance-bottom-xpl",
                    "account_bybit_bottom_fishing",
                    "XPL",
                    "0.0136",
                    "0.0136",
                    "test",
                    "complete",
                    "2026-08-21T00:00:00+00:00",
                    "2026-08-21T00:00:00+00:00",
                ),
            )
        response = client.get(
            "/api/v1/strategies/instances/"
            "strategy_bottom_fishing_instance_default/account-snapshot"
        )

    assert response.status_code == 200
    body = response.json()
    assert body["balance"]["currency"] == "USD"
    assert body["balance"]["equity"] == "100"
    assert body["equityHistory"] == [
        {"asOf": "2026-08-21T00:00:00Z", "equity": "100"}
    ]


def test_strategy_account_snapshot_reports_single_asset_in_account_currency(
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "strategy-account-single-asset.db")

    with TestClient(app) as client:
        with connection() as db:
            db.execute(
                """
                INSERT INTO balance_snapshots (
                    id, account_id, currency, equity, available_balance, source,
                    data_quality_state, as_of, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?), (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "balance-bottom-xpl",
                    "account_bybit_bottom_fishing",
                    "XPL",
                    "0.0136",
                    "0.0136",
                    "test",
                    "complete",
                    "2026-08-21T00:00:00+00:00",
                    "2026-08-21T00:00:00+00:00",
                    "balance-bottom-usd",
                    "account_bybit_bottom_fishing",
                    "USD",
                    "100",
                    "90",
                    "test",
                    "complete",
                    "2026-08-21T00:00:00+00:00",
                    "2026-08-21T00:00:00+00:00",
                ),
            )
        response = client.get(
            "/api/v1/strategies/instances/"
            "strategy_bottom_fishing_instance_default/account-snapshot"
        )

    assert response.json()["balance"]["currency"] == "USD"


def test_strategy_account_snapshot_uses_account_risk_for_live_account_funds(
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "strategy-account-risk.db")

    with TestClient(app) as client:
        with connection() as db:
            db.execute(
                """
                INSERT INTO balance_snapshots (
                    id, account_id, currency, equity, available_balance, source,
                    data_quality_state, as_of, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "balance-bottom-xpl",
                    "account_bybit_bottom_fishing",
                    "XPL",
                    "0.0136",
                    "28944",
                    "bybit_live",
                    "complete",
                    "2026-08-21T00:00:00+00:00",
                    "2026-08-21T00:00:00+00:00",
                ),
            )
            db.execute(
                """
                INSERT INTO account_risk_snapshots (
                    account_id, as_of, currency, equity, margin, free_margin,
                    margin_level, data_quality_state, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "account_bybit_bottom_fishing",
                    "2026-08-21T00:00:01+00:00",
                    "USDT",
                    "73436.92",
                    "1000",
                    "28944.58",
                    None,
                    "complete",
                    "2026-08-21T00:00:01+00:00",
                ),
            )
            db.execute(
                """
                INSERT INTO account_risk_snapshots (
                    account_id, as_of, currency, equity, margin, free_margin,
                    margin_level, data_quality_state, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "account_bybit_bottom_fishing",
                    "2026-08-22T00:00:01+00:00",
                    "USD",
                    "100000",
                    "1000",
                    "60000",
                    None,
                    "complete",
                    "2026-08-22T00:00:01+00:00",
                ),
            )
        response = client.get(
            "/api/v1/strategies/instances/"
            "strategy_bottom_fishing_instance_default/account-snapshot"
        )

    assert response.status_code == 200
    body = response.json()
    assert body["balance"]["source"] == "account_risk"
    assert body["balance"]["equity"] == "100000"
    assert body["balance"]["availableBalance"] == "60000"
    assert body["equityHistory"] == [
        {"asOf": "2026-08-22T00:00:01Z", "equity": "100000"}
    ]


def test_strategy_account_snapshot_uses_strategy_scoped_pnl_rows(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "strategy-account-pnl.db")

    with TestClient(app) as client:
        with connection() as db:
            db.execute(
                """
                INSERT INTO trade_commands (
                    id, idempotency_key, strategy_instance_id, account_id, instrument_id,
                    command_type, side, order_type, quantity, price, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "command-bottom-fishing-pnl",
                    "idempotency-bottom-fishing-pnl",
                    "strategy_bottom_fishing_instance_default",
                    "account_bybit_bottom_fishing",
                    "instrument_btc_usdt",
                    "create_order",
                    "buy",
                    "market",
                    "1",
                    None,
                    "accepted",
                    "2026-08-21T00:00:00+00:00",
                    "2026-08-21T00:00:00+00:00",
                ),
            )
            db.execute(
                """
                INSERT INTO pnl_results (
                    account_id, instrument_id, realized_pnl, trading_pnl, fees, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    "account_bybit_bottom_fishing",
                    "instrument_btc_usdt",
                    "5.00",
                    "7.00",
                    "0.30",
                    "2026-08-21T00:00:00+00:00",
                ),
            )
        response = client.get(
            "/api/v1/strategies/instances/"
            "strategy_bottom_fishing_instance_default/account-snapshot"
        )

    assert response.status_code == 200
    assert response.json()["pnl"] == {
        "accountId": "account_bybit_bottom_fishing",
        "instrumentId": "strategy_total",
        "realizedPnl": "0",
        "tradingPnl": "7.00",
        "fees": "0.30",
    }
