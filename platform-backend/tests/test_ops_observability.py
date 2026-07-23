from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_reconciliation_summary_reports_unknown_orders_and_manual_batches(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "ops-reconciliation.db")

    call_count = 0

    def runtime_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return filled_runtime_response(kwargs["json"])
        raise httpx.ConnectError("runtime unavailable")

    monkeypatch.setattr("app.trading.httpx.post", runtime_post)

    payload = {
        "strategyInstanceId": "strategy_funding_arbitrage_instance_default",
        "strategyKey": "funding_arbitrage",
        "direction": "manual_intervention_case",
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
                "symbol": "BTCUSDT-PERP",
                "side": "sell",
                "orderType": "limit",
                "quantity": "0.01",
                "price": "65100",
            },
        ],
    }

    with TestClient(app) as client:
        batch = client.post("/api/v1/trading/execution-batches", json=payload)
        assert batch.status_code == 200
        assert batch.json()["status"] == "manual_intervention"

        summary = client.get("/api/v1/ops/reconciliation-summary")
        assert summary.status_code == 200
        body = summary.json()
        assert body["manualInterventionBatchCount"] == 1
        assert body["resultUnknownOrderCount"] == 1
        assert body["status"] == "action_required"
        assert body["issues"][0]["issueType"] == "manual_intervention_batch"


def test_audit_events_are_queryable_after_trade_command(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "ops-audit.db")

    payload = {
        "idempotencyKey": "audit-command-001",
        "strategyInstanceId": "strategy_funding_arbitrage_instance_default",
        "accountId": "account_sim_usdt",
        "instrumentId": "instrument_btc_usdt",
        "symbol": "BTCUSDT",
        "side": "buy",
        "orderType": "limit",
        "quantity": "1",
        "price": "100",
    }

    with TestClient(app) as client:
        command = client.post("/api/v1/trading/commands", json=payload)
        assert command.status_code == 200

        events = client.get("/api/v1/ops/audit-events?subjectType=trade_command")
        assert events.status_code == 200
        body = events.json()
        assert len(body) == 1
        assert body[0]["eventType"] == "trade_command_created"
        assert body[0]["subjectId"] == command.json()["tradeCommandId"]


def filled_runtime_response(command: dict[str, object]) -> object:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict[str, object]]:
            return [
                {
                    "event_id": f"ack-{command['platform_order_id']}",
                    "command_id": command["command_id"],
                    "platform_order_id": command["platform_order_id"],
                    "event_type": "order_acknowledged",
                    "external_order_id": f"fake-{command['platform_order_id']}",
                    "fill_price": None,
                    "fill_quantity": None,
                    "occurred_at": "2026-07-20T12:00:00+00:00",
                    "reason": None,
                },
                {
                    "event_id": f"fill-{command['platform_order_id']}",
                    "command_id": command["command_id"],
                    "platform_order_id": command["platform_order_id"],
                    "event_type": "order_filled",
                    "external_order_id": f"fake-{command['platform_order_id']}",
                    "fill_price": command["price"] or "100",
                    "fill_quantity": command["quantity"],
                    "occurred_at": "2026-07-20T12:00:01+00:00",
                    "reason": None,
                },
            ]

    return FakeResponse()
