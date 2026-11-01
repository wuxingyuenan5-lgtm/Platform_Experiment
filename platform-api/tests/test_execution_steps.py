"""Execution step timeline: every safety gate leaves one ordered row."""

from __future__ import annotations

from decimal import Decimal

import httpx
import pytest

from app.config import get_settings
from app.database import connection, initialize_database
from app.execution_steps import (
    PASSED,
    StepRecorder,
    list_execution_steps,
)
from app.security import enforce_order_safety

STRATEGY = "strategy_funding_arbitrage_instance_default"
ACCOUNT = "account_sim_usdt"


@pytest.fixture
def live_order_environment(monkeypatch, tmp_path):
    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "execution-steps.db"))
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "auth_mode", "development")
    monkeypatch.setattr(settings, "live_trading_enabled", True)
    initialize_database()

    def native_specification(url, *, params, **kwargs):
        return httpx.Response(
            200,
            request=httpx.Request("GET", url),
            json={
                "accountId": params["accountId"],
                "symbol": "BTCUSDT",
                "instrumentType": params["instrumentType"],
                "category": params["category"],
                "dataQualityState": "complete",
                "status": "Trading",
                "minQuantity": "0.001",
                "quantityStep": "0.001",
                "priceTick": "0.01",
            },
        )

    monkeypatch.setattr("app.runtime_transport.get", native_specification)
    with connection() as db:
        db.execute("UPDATE accounts SET environment='live',status='active' WHERE id=?", (ACCOUNT,))
        db.execute(
            "UPDATE strategy_account_bindings SET status='active',capability='trade_and_read' "
            "WHERE strategy_instance_id=? AND account_id=?",
            (STRATEGY, ACCOUNT),
        )
    return settings


def _admit(recorder: StepRecorder, quantity: str = "0.01") -> None:
    enforce_order_safety(
        ACCOUNT,
        "instrument_btc_usdt",
        Decimal(quantity),
        None,
        strategy_instance_id=STRATEGY,
        symbol="BTCUSDT",
        side="buy",
        order_type="market",
        command_id="execution-step-command",
        recorder=recorder,
    )


def test_successful_admission_records_every_gate(live_order_environment) -> None:
    recorder = StepRecorder()
    _admit(recorder)

    timeline = list_execution_steps(trace_id=recorder.trace_id)
    stages = [step["stage"] for step in timeline["steps"]]
    assert stages == [
        "GATE_ACCOUNT_LOOKUP",
        "GATE_ACCOUNT_ELIGIBLE",
        "GATE_CREDENTIAL_REFERENCE",
        "GATE_INSTRUMENT_LOOKUP",
        "GATE_CONTRACT_SPEC",
        "GATE_LIVE_SWITCH",
        "GATE_NATIVE_SPEC",
        "GATE_MIN_QUANTITY",
        "GATE_QUANTITY_STEP",
        "GATE_PRICE_TICK",
        "GATE_LIVE_SWITCH_FINAL",
        "GATE_LIVE_IDENTITY",
        "GATE_ACCOUNT_LOOKUP",
        "GATE_LIVE_SWITCH_FINAL",
        "GATE_RESIDUAL_EXPOSURE",
        "GATE_STRATEGY_BINDING",
        "GATE_RECONCILIATION",
    ]
    assert {step["status"] for step in timeline["steps"]} == {PASSED}
    assert [step["sequence"] for step in timeline["steps"]] == list(
        range(1, len(stages) + 1)
    )
    assert timeline["summary"]["outcome"] == "in_progress"


def test_blocked_gate_is_recorded_with_reason(live_order_environment) -> None:
    live_order_environment.live_trading_enabled = False
    recorder = StepRecorder()
    with pytest.raises(Exception) as caught:
        _admit(recorder)
    assert "Live trading is disabled" in str(getattr(caught.value, "detail", caught.value))

    timeline = list_execution_steps(trace_id=recorder.trace_id)
    blocked = [step for step in timeline["steps"] if step["status"] == "blocked"]
    assert len(blocked) == 1
    assert blocked[0]["stage"] == "GATE_LIVE_SWITCH"
    assert blocked[0]["reasonCode"] == "LIVE_TRADING_DISABLED"
    assert blocked[0]["reasonLabel"] == "实盘总开关未开启"
    assert timeline["summary"]["outcome"] == "blocked"
    assert timeline["summary"]["blockedStage"] == "GATE_LIVE_SWITCH"


def test_quantity_gate_reports_the_exact_stage(live_order_environment) -> None:
    recorder = StepRecorder()
    with pytest.raises(Exception):
        _admit(recorder, quantity="0.0001")

    timeline = list_execution_steps(trace_id=recorder.trace_id)
    blocked = [step for step in timeline["steps"] if step["status"] == "blocked"]
    assert len(blocked) == 1
    assert blocked[0]["stage"] == "GATE_MIN_QUANTITY"
    assert blocked[0]["reasonCode"] == "QUANTITY_BELOW_MINIMUM"
    assert timeline["steps"][-1]["stage"] == "GATE_MIN_QUANTITY"


def test_timeline_requires_one_selector() -> None:
    with pytest.raises(Exception) as caught:
        list_execution_steps()
    assert "traceId, batchId or orderId" in str(caught.value)


def test_recorder_never_breaks_the_call_when_storage_is_missing(monkeypatch, tmp_path):
    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "empty.db"))
    recorder = StepRecorder()
    recorder.record("ORDER_REQUEST_VALIDATED")  # table absent: must stay silent
    assert recorder.trace_id.startswith("trc_")


def test_child_recorder_keeps_the_trace_and_adds_the_order(live_order_environment) -> None:
    parent = StepRecorder()
    parent.bind(batch_id="batch-1")
    child = parent.child(order_id="order-1", command_id="command-1")
    child.record("ORDER_LOCAL_CREATED")

    timeline = list_execution_steps(trace_id=parent.trace_id)
    assert timeline["steps"][0]["orderId"] == "order-1"
    assert timeline["steps"][0]["batchId"] == "batch-1"
    assert timeline["steps"][0]["commandId"] == "command-1"

    by_order = list_execution_steps(order_id="order-1")
    assert by_order["matchedBy"] == "orderId"
    assert len(by_order["steps"]) == 1
