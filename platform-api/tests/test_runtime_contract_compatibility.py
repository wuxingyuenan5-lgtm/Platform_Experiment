from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.runtime_contracts import (
    RuntimeExecutionEventV1,
    RuntimeSubmitOrderCommandV1,
    runtime_contract_signature,
)

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "docs" / "contracts" / "runtime-v1.json"
GOLDEN = ROOT / "docs" / "contracts" / "runtime-v1-golden.json"


def test_platform_runtime_contract_matches_canonical_snapshot() -> None:
    expected = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert runtime_contract_signature() == expected


def test_runtime_command_serializes_explicit_contract_versions() -> None:
    command = RuntimeSubmitOrderCommandV1(
        command_id="command-contract-001",
        platform_order_id="order-contract-001",
        strategy_instance_id="strategy-contract-001",
        account_id="account-contract-001",
        instrument_id="instrument-contract-001",
        symbol="BTCUSDT",
        side="buy",
        order_type="limit",
        quantity="1",
        price="100",
    )

    payload = command.model_dump(mode="json")
    assert payload["contract_name"] == "runtime-command"
    assert payload["contract_version"] == "1.0"
    assert payload["payload_version"] == "1.0"


def test_incompatible_runtime_event_version_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RuntimeExecutionEventV1.model_validate(
            {
                "contract_name": "runtime-event",
                "contract_version": "2.0",
                "payload_version": "1.0",
                "event_id": "event-contract-001",
                "command_id": "command-contract-001",
                "platform_order_id": "order-contract-001",
                "event_type": "order_acknowledged",
                "occurred_at": "2026-07-24T00:00:00+00:00",
            }
        )


def test_platform_command_and_event_match_bidirectional_golden_payloads() -> None:
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    command = RuntimeSubmitOrderCommandV1.model_validate(golden["command"])
    event = RuntimeExecutionEventV1.model_validate(golden["event"])

    assert command.model_dump(mode="json") == golden["command"]
    assert event.model_dump(mode="json") == golden["event"]
    assert command.model_dump(mode="json")["quantity"] == "1.25000001"
    assert event.model_dump(mode="json")["fill_quantity"] == "1.25000001"


@pytest.mark.parametrize("field", ["contract_version", "payload_version"])
def test_incompatible_platform_command_versions_are_rejected(field: str) -> None:
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))["command"]
    golden[field] = "2.0"
    with pytest.raises(ValidationError):
        RuntimeSubmitOrderCommandV1.model_validate(golden)


@pytest.mark.parametrize("field", ["contract_version", "payload_version"])
def test_incompatible_platform_event_versions_are_rejected(field: str) -> None:
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))["event"]
    golden[field] = "2.0"
    with pytest.raises(ValidationError):
        RuntimeExecutionEventV1.model_validate(golden)
