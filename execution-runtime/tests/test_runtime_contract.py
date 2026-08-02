from __future__ import annotations

import json
from pathlib import Path

import pytest

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.runtime_contracts import runtime_contract_signature

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "docs" / "contracts" / "runtime-v1.json"


def order_payload() -> dict[str, object]:
    return {
        "command_id": "command-contract-001",
        "platform_order_id": "order-contract-001",
        "strategy_instance_id": "strategy-contract-001",
        "account_id": "account_sim_usdt",
        "instrument_id": "instrument_btc_usdt",
        "symbol": "BTCUSDT",
        "side": "buy",
        "order_type": "limit",
        "quantity": "1",
        "price": "100",
    }


def test_runtime_contract_matches_canonical_snapshot() -> None:
    expected = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert runtime_contract_signature() == expected


def test_legacy_omitted_version_defaults_to_v1_and_response_is_explicit(tmp_path: Path) -> None:
    get_settings().journal_path = str(tmp_path / "contract-journal.db")

    with TestClient(app) as client:
        response = client.post("/commands/orders", json=order_payload())

    assert response.status_code == 200
    for event in response.json():
        assert event["contract_name"] == "runtime-event"
        assert event["contract_version"] == "1.0"
        assert event["payload_version"] == "1.0"


def test_incompatible_command_version_is_rejected_before_gateway(tmp_path: Path) -> None:
    get_settings().journal_path = str(tmp_path / "rejected-contract-journal.db")
    payload = order_payload()
    payload.update(
        {
            "contract_name": "runtime-command",
            "contract_version": "2.0",
            "payload_version": "1.0",
        }
    )

    with TestClient(app) as client:
        response = client.post("/commands/orders", json=payload)

    assert response.status_code == 422

GOLDEN = ROOT / "docs" / "contracts" / "runtime-v1-golden.json"


def test_runtime_command_and_event_match_bidirectional_golden_payloads() -> None:
    from app.runtime_contracts import RuntimeExecutionEventV1, RuntimeSubmitOrderCommandV1

    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    command = RuntimeSubmitOrderCommandV1.model_validate(golden["command"])
    event = RuntimeExecutionEventV1.model_validate(golden["event"])

    assert command.model_dump(mode="json") == golden["command"]
    assert event.model_dump(mode="json") == golden["event"]
    assert isinstance(command.model_dump(mode="json")["quantity"], str)
    assert isinstance(event.model_dump(mode="json")["fill_price"], str)


@pytest.mark.parametrize("field", ["contract_version", "payload_version"])
def test_incompatible_command_versions_are_rejected(field: str, tmp_path: Path) -> None:
    get_settings().journal_path = str(tmp_path / f"rejected-{field}-journal.db")
    payload = order_payload()
    payload.update(
        {
            "contract_name": "runtime-command",
            "contract_version": "1.0",
            "payload_version": "1.0",
            field: "2.0",
        }
    )

    with TestClient(app) as client:
        response = client.post("/commands/orders", json=payload)

    assert response.status_code == 422
