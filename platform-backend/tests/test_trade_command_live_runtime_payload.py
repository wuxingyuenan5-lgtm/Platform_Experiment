from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

STRATEGY_ID = "strategy_funding_arbitrage_instance_default"
ACCOUNT_ID = "account_sim_usdt"
INSTRUMENT_ID = "instrument_btc_usdt"


class FakeRuntimeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return [
            {
                "event_id": "runtime-ack-1",
                "command_id": self.payload["command_id"],
                "platform_order_id": self.payload["platform_order_id"],
                "event_type": "order_acknowledged",
                "external_order_id": "external-order-1",
                "fill_price": None,
                "fill_quantity": None,
                "occurred_at": "2026-07-23T12:00:00+00:00",
                "reason": None,
            }
        ]


def test_trade_command_sends_strategy_identity_to_runtime(tmp_path: Path, monkeypatch) -> None:
    get_settings().database_path = str(tmp_path / "trade-command-live.db")
    captured: dict[str, object] = {}

    def fake_post(url, json, timeout):
        captured.update(json)
        return FakeRuntimeResponse(json)

    monkeypatch.setattr("app.trade_command_execution.httpx.post", fake_post)
    payload = {
        "idempotencyKey": "live-command-payload-1",
        "strategyInstanceId": STRATEGY_ID,
        "accountId": ACCOUNT_ID,
        "instrumentId": INSTRUMENT_ID,
        "symbol": "BTCUSDT",
        "side": "buy",
        "orderType": "market",
        "quantity": "0.01",
    }

    with TestClient(app) as client:
        response = client.post("/api/v1/trading/commands", json=payload)

    assert response.status_code == 200
    assert captured["strategy_instance_id"] == STRATEGY_ID
    assert captured["account_id"] == ACCOUNT_ID
    assert captured["instrument_id"] == INSTRUMENT_ID
    assert captured["reduce_only"] is False
