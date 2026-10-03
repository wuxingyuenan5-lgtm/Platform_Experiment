from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.journal import claim_command, initialize_journal
from app.main import create_app
from app.models import ExecutionEvent, SubmitOrderCommand


def build_command() -> SubmitOrderCommand:
    return SubmitOrderCommand(
        command_id="command-atomic-001",
        platform_order_id="order-atomic-001",
        account_id="account-sim",
        instrument_id="instrument-btc",
        symbol="BTCUSDT",
        side="buy",
        order_type="market",
        quantity="0.01",
    )


def test_only_one_caller_can_claim_a_runtime_command(tmp_path: Path) -> None:
    get_settings().journal_path = str(tmp_path / "claim.db")
    initialize_journal()
    command = build_command()

    assert claim_command(command) is True
    assert claim_command(command) is False


def test_duplicate_http_command_reuses_events_without_second_gateway_call(
    tmp_path: Path,
) -> None:
    get_settings().journal_path = str(tmp_path / "http-claim.db")

    class CountingGateway:
        name = "counting"

        def __init__(self) -> None:
            self.calls = 0

        def place_order(self, command: SubmitOrderCommand) -> list[ExecutionEvent]:
            self.calls += 1
            return [
                ExecutionEvent(
                    command_id=command.command_id,
                    platform_order_id=command.platform_order_id,
                    event_type="order_acknowledged",
                    external_order_id="external-atomic-001",
                )
            ]

    gateway = CountingGateway()
    payload = build_command().model_dump(mode="json")

    with TestClient(create_app(gateway)) as client:
        first = client.post("/commands/orders", json=payload)
        second = client.post("/commands/orders", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()
    assert gateway.calls == 1


@pytest.mark.parametrize("changes", [
    {"quantity": "0.02"}, {"account_id": "other-account"},
    {"platform_order_id": "other-order"}, {"reduce_only": True},
    {"symbol": "ETHUSDT"}, {"side": "sell"},
])
def test_command_identity_rejects_changed_execution_payload(tmp_path, changes):
    get_settings().journal_path = str(tmp_path / "claim-conflict.db")

    class CountingGateway:
        name = "counting"
        calls = 0

        def place_order(self, command):
            self.calls += 1
            return [ExecutionEvent(
                command_id=command.command_id, platform_order_id=command.platform_order_id,
                event_type="order_acknowledged", external_order_id="original-order",
            )]

    gateway = CountingGateway()
    payload = build_command().model_dump(mode="json")
    payload.pop("received_at")
    with TestClient(create_app(gateway)) as client:
        first = client.post("/commands/orders", json=payload)
        assert first.status_code == 200
        conflict = client.post("/commands/orders", json={**payload, **changes})
        assert conflict.status_code == 409
        # A freshly generated receive time and equivalent Decimal are a valid replay.
        replay = client.post("/commands/orders", json={**payload, "quantity": "0.010"})
        assert replay.status_code == 200
        assert replay.json() == first.json()
    assert gateway.calls == 1
