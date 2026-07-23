from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_seeded_strategy_account_and_instrument_catalog(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "catalog.db")

    with TestClient(app) as client:
        strategies = client.get("/api/v1/strategies/definitions")
        assert strategies.status_code == 200
        body = strategies.json()
        assert len(body) == 6
        closed_loop = {item["strategyKey"] for item in body if item["v1Scope"] == "closed_loop"}
        assert closed_loop == {"funding_arbitrage", "cross_venue_spread"}

        instances = client.get("/api/v1/strategies/instances")
        assert instances.status_code == 200
        assert len(instances.json()) == 6

        accounts = client.get("/api/v1/accounts")
        assert accounts.status_code == 200
        assert {item["accountId"] for item in accounts.json()} >= {
            "account_sim_usdt",
            "account_crypto_test",
            "account_mt5_demo",
        }

        instruments = client.get("/api/v1/instruments")
        assert instruments.status_code == 200
        assert {item["instrumentId"] for item in instruments.json()} >= {
            "instrument_btc_usdt",
            "instrument_btc_usdt_perp",
            "instrument_xau_usd",
        }


def test_trade_command_is_idempotent(monkeypatch, tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "commands.db")

    def runtime_unavailable(*args, **kwargs):
        raise httpx.ConnectError("runtime unavailable")

    monkeypatch.setattr("app.trading.httpx.post", runtime_unavailable)

    payload = {
        "idempotencyKey": "idem-001",
        "strategyInstanceId": "strategy_funding_arbitrage_instance_default",
        "accountId": "account_sim_usdt",
        "instrumentId": "instrument_btc_usdt",
        "symbol": "BTCUSDT",
        "side": "buy",
        "orderType": "limit",
        "quantity": "1",
        "price": "100",
    }

    with TestClient(app) as client:
        first = client.post("/api/v1/trading/commands", json=payload)
        second = client.post("/api/v1/trading/commands", json=payload)

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["tradeCommandId"] == second.json()["tradeCommandId"]
        assert first.json()["platformOrderId"] == second.json()["platformOrderId"]

        orders = client.get("/api/v1/trading/orders")
        assert orders.status_code == 200
        assert len(orders.json()) == 1
        assert orders.json()[0]["status"] == "result_unknown"


def test_strategy_nav_snapshot_uses_seed_balance_and_capital_base(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "nav.db")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/strategies/instances/"
            "strategy_funding_arbitrage_instance_default/nav-snapshots/run"
        )
        assert response.status_code == 200
        snapshot = response.json()
        assert snapshot["equity"] == "100000"
        assert snapshot["capitalBase"] == "100000"
        assert snapshot["nav"] == "1"
        assert snapshot["dataQualityState"] == "complete"

        snapshots = client.get(
            "/api/v1/strategies/instances/"
            "strategy_funding_arbitrage_instance_default/nav-snapshots"
        )
        assert snapshots.status_code == 200
        assert len(snapshots.json()) == 1
