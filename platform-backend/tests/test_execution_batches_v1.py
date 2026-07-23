from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def filled_runtime_response(command: dict[str, object]) -> object:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict[str, object]]:
            return [
                {
                    "event_id": str(uuid4()),
                    "command_id": command["command_id"],
                    "platform_order_id": command["platform_order_id"],
                    "event_type": "order_acknowledged",
                    "external_order_id": f"fake-{command['platform_order_id']}",
                    "fill_price": None,
                    "fill_quantity": None,
                    "occurred_at": "2026-07-19T10:00:00+00:00",
                    "reason": None,
                },
                {
                    "event_id": str(uuid4()),
                    "command_id": command["command_id"],
                    "platform_order_id": command["platform_order_id"],
                    "event_type": "order_filled",
                    "external_order_id": f"fake-{command['platform_order_id']}",
                    "fill_price": command["price"] or "100",
                    "fill_quantity": command["quantity"],
                    "occurred_at": "2026-07-19T10:00:01+00:00",
                    "reason": None,
                },
            ]

    return FakeResponse()


def test_execution_batch_is_idempotent(monkeypatch, tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "batch-idempotency.db")
    monkeypatch.setattr(
        "app.trading.httpx.post",
        lambda *args, **kwargs: filled_runtime_response(kwargs["json"]),
    )

    payload = {
        "idempotencyKey": "cross-venue-001",
        "strategyInstanceId": "strategy_cross_venue_spread_instance_default",
        "strategyKey": "cross_venue_spread",
        "direction": "buy_a_sell_b",
        "legs": [
            {
                "role": "venue_a",
                "accountId": "account_crypto_test",
                "instrumentId": "instrument_btc_usdt",
                "symbol": "BTCUSDT",
                "side": "buy",
                "orderType": "limit",
                "quantity": "0.01",
                "price": "65000",
            },
            {
                "role": "venue_b",
                "accountId": "account_crypto_test_b",
                "instrumentId": "instrument_btc_usdt",
                "symbol": "BTCUSDT",
                "side": "sell",
                "orderType": "limit",
                "quantity": "0.01",
                "price": "65100",
            },
        ],
    }

    with TestClient(app) as client:
        first = client.post("/api/v1/trading/execution-batches", json=payload)
        second = client.post("/api/v1/trading/execution-batches", json=payload)

        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json() == first.json()
        assert first.json()["status"] == "hedged"
        assert first.json()["strategyInstanceId"] == "strategy_cross_venue_spread_instance_default"
        assert {leg["accountId"] for leg in first.json()["legs"]} == {
            "account_crypto_test",
            "account_crypto_test_b",
        }


def test_execution_batch_rejects_mismatched_strategy_instance(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "batch-mismatch.db")

    payload = {
        "strategyInstanceId": "strategy_funding_arbitrage_instance_default",
        "strategyKey": "cross_venue_spread",
        "direction": "bad_key",
        "accountId": "account_sim_usdt",
        "legs": [
            {
                "role": "spot",
                "instrumentId": "instrument_btc_usdt",
                "symbol": "BTCUSDT",
                "side": "buy",
                "orderType": "limit",
                "quantity": "0.01",
                "price": "65000",
            },
            {
                "role": "perp",
                "instrumentId": "instrument_btc_usdt_perp",
                "symbol": "BTCUSDT",
                "side": "sell",
                "orderType": "limit",
                "quantity": "0.01",
                "price": "65100",
            },
        ],
    }

    with TestClient(app) as client:
        response = client.post("/api/v1/trading/execution-batches", json=payload)

        assert response.status_code == 422
