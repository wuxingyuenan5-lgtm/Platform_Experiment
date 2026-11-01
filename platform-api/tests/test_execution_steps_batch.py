"""Batch level execution timeline: batch stages plus one order trace per leg."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from app import runtime_transport
from app.config import get_settings
from app.database import connection, initialize_database
from app.execution_batches import create_execution_batch
from app.execution_steps import StepRecorder, list_execution_steps
from app.schemas import CreateExecutionBatchRequest

STRATEGY = "strategy_funding_arbitrage_instance_default"
ACCOUNT = "account_sim_usdt"


def _filled_response(command: dict[str, object]):
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
                    "fill_price": command.get("price") or "100",
                    "fill_quantity": command["quantity"],
                    "occurred_at": "2026-07-19T10:00:01+00:00",
                    "reason": None,
                },
            ]

    return FakeResponse()


def _payload(*, live: bool) -> dict[str, object]:
    return {
        "idempotencyKey": f"p0-batch-steps-{uuid4()}",
        "strategyInstanceId": STRATEGY,
        "accountId": ACCOUNT,
        "strategyKey": "funding_arbitrage",
        "direction": "open",
        "legs": [
            {
                "role": "perp",
                "instrumentId": "instrument_btc_usdt_perp",
                "symbol": "BTCUSDT",
                "side": "sell",
                "orderType": "limit",
                "quantity": "1",
                "price": "100",
            },
            {
                "role": "spot",
                "instrumentId": "instrument_btc_usdt",
                "symbol": "BTCUSDT",
                "side": "buy",
                "orderType": "limit",
                "quantity": "1",
                "price": "100",
            },
        ],
    }


@pytest.fixture
def batch_environment(monkeypatch, tmp_path):
    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "batch-steps.db"))
    monkeypatch.setattr(settings, "live_trading_enabled", False)
    initialize_database()
    monkeypatch.setattr(
        runtime_transport,
        "post",
        lambda url, *, json, timeout=None, **kwargs: _filled_response(json),
    )
    return settings


def test_completed_batch_records_batch_and_both_order_traces(batch_environment) -> None:
    recorder = StepRecorder()
    batch = create_execution_batch(
        CreateExecutionBatchRequest.model_validate(_payload(live=False)),
        recorder=recorder,
    )
    assert batch.status == "hedged"

    timeline = list_execution_steps(trace_id=recorder.trace_id)
    steps = timeline["steps"]
    assert steps[0]["stage"] == "BATCH_REQUEST_VALIDATED"
    assert steps[-1]["stage"] == "BATCH_FINAL"
    assert steps[-1]["status"] == "passed"
    assert timeline["summary"]["outcome"] == "passed"
    assert [step["sequence"] for step in steps] == list(range(1, len(steps) + 1))

    final_orders = [step for step in steps if step["stage"] == "ORDER_FINAL"]
    assert len(final_orders) == 2
    assert len({step["orderId"] for step in final_orders}) == 2
    assert all(step["orderId"] for step in final_orders)
    assert {step["batchId"] for step in steps if step["batchId"]} == {batch.batch_id}

    stages = {step["stage"] for step in steps}
    assert {"BATCH_RESOURCES_CLAIMED", "BATCH_LEG_RESULT", "BATCH_RISK_SETTLED"} <= stages


def test_live_gate_rejection_stops_before_any_order(batch_environment) -> None:
    with connection() as db:
        db.execute("UPDATE accounts SET environment='live',status='active' WHERE id=?", (ACCOUNT,))

    recorder = StepRecorder()
    with pytest.raises(Exception) as caught:
        create_execution_batch(
            CreateExecutionBatchRequest.model_validate(_payload(live=True)),
            recorder=recorder,
        )
    assert "Live trading is disabled" in str(getattr(caught.value, "detail", caught.value))

    timeline = list_execution_steps(trace_id=recorder.trace_id)
    assert timeline["summary"]["outcome"] == "blocked"
    assert timeline["summary"]["blockedReasonCode"] == "LIVE_TRADING_DISABLED"
    assert timeline["summary"]["blockedStage"] == "GATE_LIVE_SWITCH_FINAL"
    stages = [step["stage"] for step in timeline["steps"]]
    assert "ORDER_LOCAL_CREATED" not in stages
    assert "BATCH_FINAL" not in stages


def test_replayed_batch_keeps_one_trace(batch_environment) -> None:
    key_payload = _payload(live=False)
    first = StepRecorder()
    created = create_execution_batch(
        CreateExecutionBatchRequest.model_validate(key_payload), recorder=first
    )

    second = StepRecorder()
    replayed = create_execution_batch(
        CreateExecutionBatchRequest.model_validate(key_payload), recorder=second
    )
    assert replayed.batch_id == created.batch_id

    timeline = list_execution_steps(trace_id=second.trace_id)
    stages = [step["stage"] for step in timeline["steps"]]
    assert "BATCH_IDEMPOTENCY_CHECKED" in stages
    assert "BATCH_FINAL" in stages
    assert Decimal(str(timeline["summary"]["stepCount"])) > 0
