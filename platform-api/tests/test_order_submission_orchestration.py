from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

STRATEGY_ID = "strategy_funding_arbitrage_instance_default"
ACCOUNT_ID = "account_sim_usdt"
INSTRUMENT_ID = "instrument_btc_usdt"


class FakeRuntimeResponse:
    def __init__(self, payload: dict[str, object], events: list[dict[str, object]]) -> None:
        self.payload = payload
        self.events = events

    def raise_for_status(self) -> None:
        return None

    def json(self) -> list[dict[str, object]]:
        return self.events


def acknowledged_event(payload: dict[str, object]) -> dict[str, object]:
    return {
        "event_id": "submission-ack-001",
        "command_id": payload["command_id"],
        "platform_order_id": payload["platform_order_id"],
        "event_type": "order_acknowledged",
        "external_order_id": "external-submission-001",
        "fill_price": None,
        "fill_quantity": None,
        "occurred_at": "2026-07-24T00:00:00+00:00",
        "reason": None,
    }


def test_legacy_order_endpoint_preserves_raw_runtime_payload(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "legacy-submission.db")
    captured: dict[str, object] = {}

    def fake_post(url, json, timeout):
        captured.update(json)
        return FakeRuntimeResponse(json, [acknowledged_event(json)])

    monkeypatch.setattr("app.trade_command_execution.httpx.post", fake_post)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trading/orders",
            json={
                "accountId": ACCOUNT_ID,
                "instrumentId": INSTRUMENT_ID,
                "symbol": "BTCUSDT",
                "side": "buy",
                "orderType": "limit",
                "quantity": "1.25",
                "price": "100",
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "acknowledged"
    assert set(captured) == {
        "command_id",
        "platform_order_id",
        "account_id",
        "instrument_id",
        "symbol",
        "side",
        "order_type",
        "quantity",
        "price",
    }
    assert captured["account_id"] == ACCOUNT_ID
    assert captured["instrument_id"] == INSTRUMENT_ID
    assert captured["quantity"] == "1.25"
    assert captured["price"] == "100"


def test_trade_command_keeps_v1_payload_and_marks_invalid_events_unknown(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "v1-submission.db")
    captured: dict[str, object] = {}

    def fake_post(url, json, timeout):
        captured.update(json)
        return FakeRuntimeResponse(json, [{"unexpected": "event"}])

    monkeypatch.setattr("app.trade_command_execution.httpx.post", fake_post)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trading/commands",
            json={
                "idempotencyKey": "unified-submission-v1-001",
                "strategyInstanceId": STRATEGY_ID,
                "accountId": ACCOUNT_ID,
                "instrumentId": INSTRUMENT_ID,
                "symbol": "BTCUSDT",
                "side": "buy",
                "orderType": "market",
                "quantity": "0.01",
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "result_unknown"
    assert captured["contract_name"] == "runtime-command"
    assert captured["contract_version"] == "1.0"
    assert captured["payload_version"] == "1.0"
    assert captured["strategy_instance_id"] == STRATEGY_ID
    assert captured["reduce_only"] is False
