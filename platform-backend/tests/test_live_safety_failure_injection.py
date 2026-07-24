from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

STRATEGY_ID = "strategy_funding_arbitrage_instance_default"
ACCOUNT_ID = "account_sim_usdt"
INSTRUMENT_ID = "instrument_btc_usdt"


def command_payload(key: str) -> dict[str, str]:
    return {
        "idempotencyKey": key,
        "strategyInstanceId": STRATEGY_ID,
        "accountId": ACCOUNT_ID,
        "instrumentId": INSTRUMENT_ID,
        "symbol": "BTCUSDT",
        "side": "buy",
        "orderType": "limit",
        "quantity": "1",
        "price": "100",
    }


class FakeResponse:
    status_code = 200

    def __init__(self, events: list[dict[str, object]]) -> None:
        self.events = events

    def raise_for_status(self) -> None:
        return None

    def json(self) -> list[dict[str, object]]:
        return self.events


def test_incompatible_runtime_event_keeps_order_result_unknown(
    tmp_path: Path,
    monkeypatch,
) -> None:
    get_settings().database_path = str(tmp_path / "contract-failure.db")

    def fake_post(url, json, timeout):
        assert url.endswith("/commands/orders")
        assert timeout > 0
        return FakeResponse(
            [
                {
                    "contract_name": "runtime-event",
                    "contract_version": "2.0",
                    "payload_version": "1.0",
                    "event_id": "event-incompatible-001",
                    "command_id": json["command_id"],
                    "platform_order_id": json["platform_order_id"],
                    "event_type": "order_acknowledged",
                    "occurred_at": "2026-07-24T00:00:00+00:00",
                }
            ]
        )

    monkeypatch.setattr("app.trade_command_execution.httpx.post", fake_post)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trading/commands",
            json=command_payload("failure-contract-version-001"),
        )

    assert response.status_code == 200
    assert response.json()["status"] == "result_unknown"


def test_fill_before_ack_remains_filled_and_projects_once(
    tmp_path: Path,
    monkeypatch,
) -> None:
    get_settings().database_path = str(tmp_path / "out-of-order.db")

    def fake_post(url, json, timeout):
        assert url.endswith("/commands/orders")
        assert timeout > 0
        shared = {
            "contract_name": "runtime-event",
            "contract_version": "1.0",
            "payload_version": "1.0",
            "command_id": json["command_id"],
            "platform_order_id": json["platform_order_id"],
            "external_order_id": "external-out-of-order-001",
            "reason": None,
        }
        return FakeResponse(
            [
                {
                    **shared,
                    "event_id": "fill-out-of-order-001",
                    "event_type": "order_filled",
                    "fill_price": "100",
                    "fill_quantity": "1",
                    "occurred_at": "2026-07-24T00:00:01+00:00",
                },
                {
                    **shared,
                    "event_id": "ack-out-of-order-001",
                    "event_type": "order_acknowledged",
                    "fill_price": None,
                    "fill_quantity": None,
                    "occurred_at": "2026-07-24T00:00:00+00:00",
                },
                {
                    **shared,
                    "event_id": "fill-out-of-order-001",
                    "event_type": "order_filled",
                    "fill_price": "100",
                    "fill_quantity": "1",
                    "occurred_at": "2026-07-24T00:00:01+00:00",
                },
            ]
        )

    monkeypatch.setattr("app.trade_command_execution.httpx.post", fake_post)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trading/commands",
            json=command_payload("failure-out-of-order-001"),
        )
        position = client.get(f"/api/v1/accounts/{ACCOUNT_ID}/positions/{INSTRUMENT_ID}")

    assert response.status_code == 200
    assert response.json()["status"] == "filled"
    assert position.status_code == 200
    assert position.json()["netQuantity"] == "1"
