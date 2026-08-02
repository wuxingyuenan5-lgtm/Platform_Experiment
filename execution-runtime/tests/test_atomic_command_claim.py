from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.journal import claim_command, initialize_journal
from app.main import app, create_app
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

        def submit_order(self, command: SubmitOrderCommand) -> list[ExecutionEvent]:
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
