from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_order_fill_updates_position_and_pnl(monkeypatch, tmp_path: Path) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / "platform.db")

    account_id = "account_sim_usdt"
    instrument_id = "instrument_btc_usdt"

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict[str, object]]:
            return [
                {
                    "event_id": str(uuid4()),
                    "command_id": str(uuid4()),
                    "platform_order_id": str(uuid4()),
                    "event_type": "order_acknowledged",
                    "external_order_id": "fake-1",
                    "fill_price": None,
                    "fill_quantity": None,
                    "occurred_at": "2026-07-18T10:00:00+00:00",
                    "reason": None,
                },
                {
                    "event_id": str(uuid4()),
                    "command_id": str(uuid4()),
                    "platform_order_id": str(uuid4()),
                    "event_type": "order_filled",
                    "external_order_id": "fake-1",
                    "fill_price": "100",
                    "fill_quantity": "2",
                    "occurred_at": "2026-07-18T10:00:01+00:00",
                    "reason": None,
                },
            ]

    monkeypatch.setattr("app.trading.httpx.post", lambda *args, **kwargs: FakeResponse())

    with TestClient(app) as client:
        order_response = client.post(
            "/api/v1/trading/orders",
            json={
                "accountId": account_id,
                "instrumentId": instrument_id,
                "symbol": "BTCUSDT",
                "side": "buy",
                "orderType": "limit",
                "quantity": "2",
                "price": "100",
            },
        )
        assert order_response.status_code == 200
        assert order_response.json()["status"] == "filled"

        position_response = client.get(
            f"/api/v1/accounts/{account_id}/positions/{instrument_id}"
        )
        assert position_response.status_code == 200
        assert position_response.json()["netQuantity"] == "2"
        assert position_response.json()["averagePrice"] == "100"

        pnl_response = client.get(f"/api/v1/accounts/{account_id}/pnl/{instrument_id}")
        assert pnl_response.status_code == 200
        assert pnl_response.json()["realizedPnl"] == "0"
        assert pnl_response.json()["tradingPnl"] == "0"
