from pathlib import Path
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection
from app.main import app

STRATEGY_INSTANCE_ID = "strategy_funding_arbitrage_instance_default"


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


def batch_payload(
    account_id: str,
    spot_id: str,
    perp_id: str,
    *,
    idempotency_key: str,
) -> dict[str, object]:
    return {
        "idempotencyKey": idempotency_key,
        "strategyInstanceId": STRATEGY_INSTANCE_ID,
        "accountId": account_id,
        "strategyKey": "funding_arbitrage",
        "direction": "collect",
        "legs": [
            {
                "role": "spot",
                "instrumentId": spot_id,
                "symbol": "BTCUSDT",
                "side": "buy",
                "orderType": "limit",
                "quantity": "1",
                "price": "100",
            },
            {
                "role": "perp",
                "instrumentId": perp_id,
                "symbol": "BTCUSDT-PERP",
                "side": "sell",
                "orderType": "limit",
                "quantity": "1",
                "price": "100",
            },
        ],
    }


def test_execution_batch_becomes_hedged_and_creates_two_commands(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "hedged.db")
    runtime_calls = 0

    def runtime_post(*args, **kwargs):
        nonlocal runtime_calls
        runtime_calls += 1
        return filled_runtime_response(kwargs["json"])

    monkeypatch.setattr("app.trade_command_execution.httpx.post", runtime_post)

    account_id = "account_sim_usdt"
    spot_id = "instrument_btc_usdt"
    perp_id = "instrument_btc_usdt_perp"
    payload = batch_payload(
        account_id,
        spot_id,
        perp_id,
        idempotency_key="funding-batch-hedged-001",
    )

    with TestClient(app) as client:
        first = client.post("/api/v1/trading/execution-batches", json=payload)
        second = client.post("/api/v1/trading/execution-batches", json=payload)

        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json() == first.json()
        batch = first.json()
        assert batch["status"] == "hedged"
        assert batch["requiresManualIntervention"] is False
        assert [leg["status"] for leg in batch["legs"]] == ["filled", "filled"]
        assert runtime_calls == 2

        with connection() as db:
            command_rows = db.execute(
                """
                SELECT idempotency_key
                FROM trade_commands
                WHERE strategy_instance_id = ?
                ORDER BY idempotency_key
                """,
                (STRATEGY_INSTANCE_ID,),
            ).fetchall()
        assert [row["idempotency_key"] for row in command_rows] == [
            "funding-batch-hedged-001:perp",
            "funding-batch-hedged-001:spot",
        ]

        spot = client.get(f"/api/v1/accounts/{account_id}/positions/{spot_id}")
        perp = client.get(f"/api/v1/accounts/{account_id}/positions/{perp_id}")
        assert spot.json()["netQuantity"] == "1"
        assert perp.json()["netQuantity"] == "-1"

        stored = client.get(f"/api/v1/trading/execution-batches/{batch['batchId']}")
        assert stored.status_code == 200
        assert stored.json()["status"] == "hedged"


def test_second_leg_unknown_requires_manual_intervention(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "manual.db")
    call_count = 0

    def runtime_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return filled_runtime_response(kwargs["json"])
        raise httpx.ConnectError("runtime unavailable")

    monkeypatch.setattr("app.trade_command_execution.httpx.post", runtime_post)

    account_id = "account_sim_usdt"
    spot_id = "instrument_btc_usdt"
    perp_id = "instrument_btc_usdt_perp"

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/trading/execution-batches",
            json=batch_payload(
                account_id,
                spot_id,
                perp_id,
                idempotency_key="funding-batch-manual-001",
            ),
        )

        assert response.status_code == 200
        batch = response.json()
        assert batch["status"] == "manual_intervention"
        assert batch["requiresManualIntervention"] is True
        assert batch["legs"][0]["status"] == "filled"
        assert batch["legs"][1]["status"] == "result_unknown"
        assert batch["legs"][1]["orderId"] is not None

        spot = client.get(f"/api/v1/accounts/{account_id}/positions/{spot_id}")
        perp = client.get(f"/api/v1/accounts/{account_id}/positions/{perp_id}")
        assert spot.status_code == 200
        assert spot.json()["netQuantity"] == "1"
        assert perp.status_code == 404
