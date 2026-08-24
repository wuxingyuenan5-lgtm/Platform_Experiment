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
        "accountRisk": None,
        "positions": [],
        "orders": [],
        "fills": [],
        "pnl": None,
        "syncStatus": "unbound",
        "syncErrorCode": "account_unbound",
    }


def test_strategy_account_snapshot_aggregates_all_account_pnl_rows(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "strategy-account-pnl.db")

    with TestClient(app) as client:
        with connection() as db:
            db.execute(
                """
                INSERT INTO pnl_results (
                    account_id, instrument_id, realized_pnl, trading_pnl, fees, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?), (?, ?, ?, ?, ?, ?)
                """,
                (
                    "account_bybit_bottom_fishing",
                    "instrument-one",
                    "1.25",
                    "2.50",
                    "0.10",
                    "2026-08-21T00:00:00+00:00",
                    "account_bybit_bottom_fishing",
                    "instrument-two",
                    "3.75",
                    "4.50",
                    "0.20",
                    "2026-08-21T00:01:00+00:00",
                ),
            )
        response = client.get(
            "/api/v1/strategies/instances/"
            "strategy_bottom_fishing_instance_default/account-snapshot"
        )

    assert response.status_code == 200
    assert response.json()["pnl"] == {
        "accountId": "account_bybit_bottom_fishing",
        "instrumentId": "account_total",
        "realizedPnl": "5.00",
        "tradingPnl": "7.00",
        "fees": "0.30",
    }
