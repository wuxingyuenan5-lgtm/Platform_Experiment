from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.schemas import CreateOrderRequest
from app.trading import apply_execution_events


def command_payload(idempotency_key: str) -> dict[str, str]:
    return {
        "idempotencyKey": idempotency_key,
        "strategyInstanceId": "strategy_funding_arbitrage_instance_default",
        "accountId": "account_sim_usdt",
        "instrumentId": "instrument_btc_usdt",
        "symbol": "BTCUSDT",
        "side": "buy",
        "orderType": "limit",
        "quantity": "1",
        "price": "100",
    }


def runtime_events(command_id: str, order_id: str) -> list[dict[str, object]]:
    return [
        {
            "event_id": "event-recovery-ack-001",
            "command_id": command_id,
            "platform_order_id": order_id,
            "event_type": "order_acknowledged",
            "external_order_id": "external-recovery-001",
            "fill_price": None,
            "fill_quantity": None,
            "occurred_at": "2026-07-23T06:00:00+00:00",
            "reason": None,
        },
        {
            "event_id": "event-recovery-fill-001",
            "command_id": command_id,
            "platform_order_id": order_id,
            "event_type": "order_filled",
            "external_order_id": "external-recovery-001",
            "fill_price": "100",
            "fill_quantity": "1",
            "occurred_at": "2026-07-23T06:00:01+00:00",
            "reason": None,
        },
    ]


def test_result_unknown_recovers_from_runtime_journal(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "recover.db")
    monkeypatch.setattr(
        "app.trading.httpx.post",
        lambda *args, **kwargs: (_ for _ in ()).throw(httpx.ConnectError("timeout")),
    )

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/trading/commands",
            json=command_payload("recovery-command-001"),
        )
        assert created.status_code == 200
        command = created.json()
        assert command["status"] == "result_unknown"
        order_id = command["platformOrderId"]
        command_id = command["tradeCommandId"]

        class FakeResponse:
            status_code = 200

            def raise_for_status(self) -> None:
                return None

            def json(self) -> list[dict[str, object]]:
                return runtime_events(command_id, order_id)

        monkeypatch.setattr("app.trading.httpx.get", lambda *args, **kwargs: FakeResponse())
        recovered = client.post(f"/api/v1/trading/orders/{order_id}/reconcile")

        assert recovered.status_code == 200
        assert recovered.json()["status"] == "filled"
        assert recovered.json()["externalOrderId"] == "external-recovery-001"

        position = client.get(
            "/api/v1/accounts/account_sim_usdt/positions/instrument_btc_usdt"
        )
        assert position.status_code == 200
        assert position.json()["netQuantity"] == "1"

        command_after = client.get(f"/api/v1/trading/commands/{command_id}")
        assert command_after.json()["status"] == "filled"

        replay_request = CreateOrderRequest(
            accountId="account_sim_usdt",
            instrumentId="instrument_btc_usdt",
            symbol="BTCUSDT",
            side="buy",
            orderType="limit",
            quantity="1",
            price="100",
        )
        apply_execution_events(
            order_id,
            replay_request,
            runtime_events(command_id, order_id),
            expected_command_id=command_id,
        )

        position_after_replay = client.get(
            "/api/v1/accounts/account_sim_usdt/positions/instrument_btc_usdt"
        )
        assert position_after_replay.json()["netQuantity"] == "1"


def test_result_unknown_remains_unknown_when_runtime_has_no_events(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "recover-missing.db")
    monkeypatch.setattr(
        "app.trading.httpx.post",
        lambda *args, **kwargs: (_ for _ in ()).throw(httpx.ConnectError("timeout")),
    )

    with TestClient(app) as client:
        created = client.post(
            "/api/v1/trading/commands",
            json=command_payload("recovery-command-missing-001"),
        )
        order_id = created.json()["platformOrderId"]

        monkeypatch.setattr(
            "app.trading.httpx.get",
            lambda *args, **kwargs: (_ for _ in ()).throw(httpx.ConnectError("offline")),
        )
        recovered = client.post(f"/api/v1/trading/orders/{order_id}/reconcile")

        assert recovered.status_code == 200
        assert recovered.json()["status"] == "result_unknown"
