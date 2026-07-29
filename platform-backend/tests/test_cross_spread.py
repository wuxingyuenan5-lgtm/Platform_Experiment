from decimal import Decimal
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.config import get_settings
from app.cross_spread import CrossSpreadLiveSizing, submit_cross_spread_market_command
from app.database import connection
from app.main import app
from app.schemas import CrossSpreadMarketCommandRequest

def test_cross_spread_snapshot_proxies_runtime_market_data(monkeypatch, tmp_path: Path) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / "cross-spread-snapshot.db")
    settings.runtime_base_url = "http://runtime.local"

    def fake_get(url: str, timeout: float) -> httpx.Response:
        assert url == "http://runtime.local/gateway/cross-spread/snapshot"
        return httpx.Response(
            200,
            json={
                "status": "available",
                "bybit": {
                    "venue": "bybit",
                    "symbol": "XAUTUSDT",
                    "status": "available",
                    "quote": {
                        "bid": "3330.10",
                        "ask": "3330.30",
                        "mid": "3330.20",
                        "last": "3330.20",
                        "currency": "USDT",
                    },
                    "positions": [],
                    "reason": None,
                },
                "mt5": {
                    "venue": "mt5",
                    "symbol": "XAUUSD.s",
                    "status": "available",
                    "quote": {
                        "bid": "3331.00",
                        "ask": "3331.40",
                        "mid": "3331.20",
                        "last": "3331.20",
                        "currency": "USD",
                    },
                    "positions": [],
                    "reason": None,
                },
                "longSpread": "-0.70",
                "shortSpread": "-1.30",
                "metrics": {
                    "fundingRate": "0.0001",
                    "usdtUsd": "0.9998",
                    "buyerInventoryFee": "-42.5",
                    "sellerInventoryFee": "24.25",
                },
                "asOf": "2026-07-22T00:00:00+00:00",
            },
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    with TestClient(app) as client:
        response = client.get("/api/v1/trading/cross-spread/snapshot")

    assert response.status_code == 200
    assert response.json()["bybit"]["quote"]["bid"] == "3330.10"
    assert response.json()["longSpread"] == "-0.70"
    assert response.json()["metrics"]["fundingRate"] == "0.0001"
    with connection() as db:
        row = db.execute(
            """
            SELECT strategy_key, left_symbol, right_symbol, long_spread, funding_rate, usdt_usd
            FROM market_spread_snapshots
            """
        ).fetchone()
    assert row["strategy_key"] == "cross_venue_spread"
    assert row["left_symbol"] == "XAUTUSDT"
    assert row["right_symbol"] == "XAUUSD.s"
    assert row["long_spread"] == "-0.70"
    assert row["funding_rate"] == "0.0001"
    assert row["usdt_usd"] == "0.9998"

    with TestClient(app) as client:
        history_response = client.get("/api/v1/trading/cross-spread/history?limit=10")
    assert history_response.status_code == 200
    assert history_response.json() == [
        {
            "asOf": "2026-07-22T00:00:00Z",
            "longSpread": "-0.70",
            "shortSpread": "-1.30",
            "bybitMid": "3330.20",
            "mt5Mid": "3331.20",
        }
    ]


def test_cross_spread_market_command_maps_open_long_to_two_market_legs(
    monkeypatch,
    tmp_path: Path,
) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / "cross-spread-command.db")
    settings.runtime_base_url = "http://runtime.local"
    settings.live_trading_enabled = True
    settings.cross_spread_acceptance_max_quantity_oz = Decimal("1")
    captured = {}

    def fake_create_execution_batch(request):
        captured["request"] = request
        return {
            "batchId": "batch-1",
            "idempotencyKey": request.idempotency_key,
            "strategyInstanceId": request.strategy_instance_id,
            "accountId": request.account_id,
            "strategyKey": request.strategy_key,
            "direction": request.direction,
            "status": "failed",
            "requiresManualIntervention": False,
            "failureReason": "live trading disabled",
            "legs": [
                {
                    "role": "bybit_leg",
                    "accountId": "account_crypto_test",
                    "orderId": None,
                    "status": "failed",
                    "failureReason": "live trading disabled",
                },
                {
                    "role": "mt5_leg",
                    "accountId": "account_mt5_demo",
                    "orderId": None,
                    "status": "failed",
                    "failureReason": "live trading disabled",
                },
            ],
            "createdAt": "2026-07-22T00:00:00+00:00",
            "updatedAt": "2026-07-22T00:00:00+00:00",
        }

    monkeypatch.setattr("app.cross_spread.create_execution_batch", fake_create_execution_batch)
    monkeypatch.setattr(
        "app.cross_spread._load_live_cross_spread_sizing",
        lambda: CrossSpreadLiveSizing(
            bybit_min=Decimal("0.001"),
            bybit_step=Decimal("0.001"),
            bybit_max=Decimal("10"),
            mt5_min=Decimal("0.01"),
            mt5_step=Decimal("0.01"),
            mt5_max=Decimal("100"),
            mt5_multiplier=Decimal("100"),
        ),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trading/cross-spread/market-command",
            json={"action": "OPEN_LONG", "quantityOz": "1"},
        )

    assert response.status_code == 200
    request = captured["request"]
    assert request.strategy_key == "cross_venue_spread"
    assert request.direction == "OPEN_LONG"
    assert request.legs[0].account_id == "account_crypto_test"
    assert request.legs[0].symbol == "XAUTUSDT"
    assert request.legs[0].side == "buy"
    assert request.legs[0].order_type == "market"
    assert request.legs[0].quantity == 1
    assert request.legs[1].account_id == "account_mt5_demo"
    assert request.legs[1].symbol == "XAUUSD.s"
    assert request.legs[1].side == "sell"
    assert request.legs[1].quantity == Decimal("0.01")


def test_cross_spread_market_command_rejects_quantity_above_acceptance_cap(
    tmp_path: Path,
) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / "cross-spread-command-invalid-qty.db")
    settings.live_trading_enabled = True
    settings.cross_spread_acceptance_max_quantity_oz = Decimal("1")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trading/cross-spread/market-command",
            json={"action": "OPEN_LONG", "quantityOz": "1.001"},
        )

    assert response.status_code == 422
    assert "temporarily capped" in response.json()["detail"]


def test_cross_spread_market_command_rejects_when_live_trading_disabled(
    tmp_path: Path,
) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / "cross-spread-command-disabled.db")
    settings.environment = "development"
    settings.default_trading_environment = "paper"
    settings.live_trading_enabled = False

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trading/cross-spread/market-command",
            json={"action": "OPEN_LONG", "quantityOz": "50"},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Live cross-spread execution is disabled"


def test_cross_spread_market_command_rejects_development_simulation_without_live_flag(
    monkeypatch,
    tmp_path: Path,
) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / "cross-spread-command-simulation.db")
    settings.environment = "development"
    settings.default_trading_environment = "simulation"
    settings.live_trading_enabled = False
    settings.cross_spread_acceptance_max_quantity_oz = Decimal("1")
    monkeypatch.setattr(
        "app.cross_spread._load_live_cross_spread_sizing",
        lambda: CrossSpreadLiveSizing(
            bybit_min=Decimal("0.001"),
            bybit_step=Decimal("0.001"),
            bybit_max=Decimal("10"),
            mt5_min=Decimal("0.01"),
            mt5_step=Decimal("0.01"),
            mt5_max=Decimal("100"),
            mt5_multiplier=Decimal("100"),
        ),
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trading/cross-spread/market-command",
            json={"action": "OPEN_LONG", "quantityOz": "1"},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Live cross-spread execution is disabled"


def test_cross_spread_market_command_still_rejects_live_environment_without_live_flag(
    tmp_path: Path,
) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / "cross-spread-command-live-disabled.db")
    settings.environment = "live"
    settings.default_trading_environment = "simulation"
    settings.environment = "development"
    settings.default_trading_environment = "paper"
    settings.live_trading_enabled = False

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trading/cross-spread/market-command",
            json={"action": "OPEN_LONG", "quantityOz": "1"},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Live cross-spread execution is disabled"




