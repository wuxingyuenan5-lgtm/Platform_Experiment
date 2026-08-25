import hashlib
import json
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
                    "event_type": "order_filled",
                    "external_order_id": f"fake-{command['platform_order_id']}",
                    "fill_price": command["price"] or "100",
                    "fill_quantity": command["quantity"],
                    "occurred_at": "2026-07-23T07:00:00+00:00",
                    "reason": None,
                }
            ]

    return FakeResponse()


def credential(user_id: str, token: str, roles: list[str]) -> dict[str, object]:
    return {
        "credentialId": f"credential-{user_id}",
        "userId": user_id,
        "tokenSha256": hashlib.sha256(token.encode("utf-8")).hexdigest(),
        "roles": roles,
        "status": "active",
    }


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def trade_command_payload(quantity: str) -> dict[str, str]:
    return {
        "idempotencyKey": "command-collision-001",
        "strategyInstanceId": "strategy_funding_arbitrage_instance_default",
        "accountId": "account_sim_usdt",
        "instrumentId": "instrument_btc_usdt",
        "symbol": "BTCUSDT",
        "side": "buy",
        "orderType": "limit",
        "quantity": quantity,
        "price": "100",
    }


def batch_payload(direction: str) -> dict[str, object]:
    return {
        "idempotencyKey": "batch-collision-001",
        "strategyInstanceId": "strategy_funding_arbitrage_instance_default",
        "accountId": "account_sim_usdt",
        "strategyKey": "funding_arbitrage",
        "direction": direction,
        "legs": [
            {
                "role": "spot",
                "instrumentId": "instrument_btc_usdt",
                "symbol": "BTCUSDT",
                "side": "buy",
                "orderType": "limit",
                "quantity": "1",
                "price": "100",
            },
            {
                "role": "perp",
                "instrumentId": "instrument_btc_usdt_perp",
                "symbol": "BTCUSDT-PERP",
                "side": "sell",
                "orderType": "limit",
                "quantity": "1",
                "price": "100",
            },
        ],
    }


def test_trade_command_key_cannot_be_reused_for_different_payload(
    monkeypatch,
    tmp_path: Path,
) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / "command-collision.db")
    settings.environment = "live"
    settings.auth_mode = "api_key"
    settings.auth_credentials_json = json.dumps(
        [credential("admin-1", "admin-token", ["admin"])]
    )
    runtime_calls = 0

    def runtime_post(*args, **kwargs):
        nonlocal runtime_calls
        runtime_calls += 1
        return filled_runtime_response(kwargs["json"])

    monkeypatch.setattr("app.trade_command_execution.httpx.post", runtime_post)
    monkeypatch.setattr("app.auth.has_ceo_trade_authority", lambda principal, current: True)

    with TestClient(app) as client:
        first = client.post(
            "/api/v1/trading/commands",
            headers=headers("admin-token"),
            json=trade_command_payload("1"),
        )
        conflict = client.post(
            "/api/v1/trading/commands",
            headers=headers("admin-token"),
            json=trade_command_payload("2"),
        )

    assert first.status_code == 200
    assert conflict.status_code == 409
    assert "different trade command payload" in conflict.json()["detail"]
    assert runtime_calls == 1


def test_execution_batch_key_cannot_be_reused_for_different_payload(
    monkeypatch,
    tmp_path: Path,
) -> None:
    settings = get_settings()
    settings.database_path = str(tmp_path / "batch-collision.db")
    settings.environment = "live"
    settings.auth_mode = "api_key"
    settings.auth_credentials_json = json.dumps(
        [credential("admin-1", "admin-token", ["admin"])]
    )
    runtime_calls = 0

    def runtime_post(*args, **kwargs):
        nonlocal runtime_calls
        runtime_calls += 1
        return filled_runtime_response(kwargs["json"])

    monkeypatch.setattr("app.trade_command_execution.httpx.post", runtime_post)
    monkeypatch.setattr("app.auth.has_ceo_trade_authority", lambda principal, current: True)

    with TestClient(app) as client:
        first = client.post(
            "/api/v1/trading/execution-batches",
            headers=headers("admin-token"),
            json=batch_payload("collect"),
        )
        conflict = client.post(
            "/api/v1/trading/execution-batches",
            headers=headers("admin-token"),
            json=batch_payload("pay"),
        )

    assert first.status_code == 200
    assert conflict.status_code == 409
    assert "different execution batch payload" in conflict.json()["detail"]
    assert runtime_calls == 2
