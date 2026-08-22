from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection
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
                    "occurred_at": "2026-07-20T10:00:00+00:00",
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
                    "occurred_at": "2026-07-20T10:00:01+00:00",
                    "reason": None,
                },
            ]

    return FakeResponse()


def funding_run_payload() -> dict[str, object]:
    return {
        "idempotencyKey": "funding-run-001",
        "direction": "open_carry",
        "reason": "v1_smoke_test",
        "legs": [
            {
                "role": "spot",
                "accountId": "account_sim_usdt",
                "instrumentId": "instrument_btc_usdt",
                "symbol": "BTCUSDT",
                "side": "buy",
                "orderType": "limit",
                "quantity": "0.01",
                "price": "65000",
            },
            {
                "role": "perp",
                "accountId": "account_sim_usdt",
                "instrumentId": "instrument_btc_usdt_perp",
                "symbol": "BTCUSDT-PERP",
                "side": "sell",
                "orderType": "limit",
                "quantity": "0.01",
                "price": "65100",
            },
        ],
    }


def test_strategy_run_creates_idempotent_hedged_batch(
    monkeypatch,
    tmp_path: Path,
) -> None:
    get_settings().database_path = str(tmp_path / "strategy-run.db")
    monkeypatch.setattr(
        "app.trade_command_execution.httpx.post",
        lambda *args, **kwargs: filled_runtime_response(kwargs["json"]),
    )

    with TestClient(app) as client:
        url = "/api/v1/strategies/instances/strategy_funding_arbitrage_instance_default/runs"
        first = client.post(url, json=funding_run_payload())
        second = client.post(url, json=funding_run_payload())

        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json() == first.json()
        assert first.json()["status"] == "completed"
        assert first.json()["executionBatch"]["status"] == "hedged"
        assert first.json()["strategyKey"] == "funding_arbitrage"

        with connection() as db:
            instruction = db.execute(
                "SELECT execution_plan_json FROM strategy_runs WHERE id = ?",
                (first.json()["strategyRunId"],),
            ).fetchone()
            linked_batch = db.execute(
                "SELECT strategy_instruction_id FROM execution_batches WHERE id = ?",
                (first.json()["executionBatchId"],),
            ).fetchone()
        assert instruction["execution_plan_json"] is not None
        assert linked_batch["strategy_instruction_id"] == first.json()["strategyRunId"]

        runs = client.get(url)
        assert runs.status_code == 200
        assert len(runs.json()) == 1


def test_strategy_run_rejects_non_closed_loop_strategy(tmp_path: Path) -> None:
    get_settings().database_path = str(tmp_path / "strategy-run-reject.db")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/strategies/instances/strategy_home_abroad_spread_instance_default/runs",
            json=funding_run_payload(),
        )

        assert response.status_code == 422
