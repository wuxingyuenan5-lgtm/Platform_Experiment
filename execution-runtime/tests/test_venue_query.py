from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_fake_venue_state_is_queryable_and_persists_across_clients(tmp_path: Path) -> None:
    get_settings().journal_path = str(tmp_path / "venue-query.db")
    command = {
        "command_id": "venue-command-001",
        "platform_order_id": "venue-order-001",
        "account_id": "account_sim_usdt",
        "instrument_id": "instrument_btc_usdt",
        "symbol": "BTCUSDT",
        "side": "buy",
        "order_type": "limit",
        "quantity": "2",
        "price": "100",
    }

    with TestClient(app) as client:
        submitted = client.post("/commands/orders", json=command)
        assert submitted.status_code == 200

        order = client.get("/venue/orders/by-platform/venue-order-001")
        assert order.status_code == 200
        assert order.json()["externalOrderId"] == "FAKE-venue-order-001"
        assert order.json()["status"] == "filled"
        assert order.json()["filledQuantity"] == "2"

        fills = client.get(
            "/venue/fills",
            params={"platformOrderId": "venue-order-001"},
        )
        assert fills.status_code == 200
        assert len(fills.json()) == 1
        assert fills.json()[0]["externalFillId"] == "FAKE-FILL-venue-order-001"
        assert fills.json()[0]["price"] == "100"

        position = client.get(
            "/venue/positions",
            params={"accountId": "account_sim_usdt"},
        )
        assert position.status_code == 200
        assert position.json()[0]["netQuantity"] == "2"

        balance = client.get(
            "/venue/balances",
            params={"accountId": "account_sim_usdt"},
        )
        assert balance.status_code == 200
        assert balance.json()[0]["equity"] == "100000"

    with TestClient(app) as restarted_client:
        order = restarted_client.get("/venue/orders/by-platform/venue-order-001")
        fills = restarted_client.get(
            "/venue/fills",
            params={"platformOrderId": "venue-order-001"},
        )
        assert order.status_code == 200
        assert fills.status_code == 200
        assert len(fills.json()) == 1


def test_fake_cancel_is_idempotent_and_does_not_claim_filled_order(tmp_path: Path) -> None:
    get_settings().journal_path = str(tmp_path / "venue-cancel.db")
    command = {
        "command_id": "venue-command-cancel-001",
        "platform_order_id": "venue-order-cancel-001",
        "account_id": "account_sim_usdt",
        "instrument_id": "instrument_btc_usdt",
        "symbol": "BTCUSDT",
        "side": "buy",
        "order_type": "market",
        "quantity": "1",
    }
    payload = {
        "idempotencyKey": "cancel-command-001",
        "reason": "test cancellation",
    }

    with TestClient(app) as client:
        assert client.post("/commands/orders", json=command).status_code == 200
        first = client.post(
            "/venue/orders/FAKE-venue-order-cancel-001/cancel",
            json=payload,
        )
        second = client.post(
            "/venue/orders/FAKE-venue-order-cancel-001/cancel",
            json=payload,
        )
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json() == second.json()
        assert first.json()["status"] == "already_final"

        conflict = client.post(
            "/venue/orders/FAKE-venue-order-cancel-001/cancel",
            json={**payload, "reason": "different reason"},
        )
        assert conflict.status_code == 409
