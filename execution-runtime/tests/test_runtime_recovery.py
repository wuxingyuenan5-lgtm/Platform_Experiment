from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main as runtime_main
from app.config import get_settings
from app.fake_gateway import FakeGateway
from app.gateway_errors import GatewayResultUnknownError
from app.journal import get_command, get_events
from app.models import ExecutionEvent, SubmitOrderCommand, VenueFillSnapshot, VenueOrderSnapshot

COMMAND_ID = "recovery-command-001"
ORDER_ID = "recovery-order-001"
EXTERNAL_ID = "venue-order-001"
NOW = datetime(2026, 8, 2, 12, 0, tzinfo=UTC)


def command_payload() -> dict[str, object]:
    return {
        "contract_name": "runtime-command",
        "contract_version": "1.0",
        "payload_version": "1.0",
        "command_id": COMMAND_ID,
        "platform_order_id": ORDER_ID,
        "strategy_instance_id": "strategy-001",
        "account_id": "account_sim_usdt",
        "instrument_id": "instrument_btc_usdt",
        "symbol": "BTCUSDT",
        "side": "buy",
        "order_type": "limit",
        "quantity": "1.25000001",
        "price": "100.12345678",
        "received_at": NOW.isoformat(),
    }


def order_snapshot(status: str, *, platform_order_id: str = ORDER_ID) -> VenueOrderSnapshot:
    filled = Decimal("1.25000001") if status == "filled" else Decimal("0")
    return VenueOrderSnapshot(
        source="test",
        externalOrderId=EXTERNAL_ID,
        platformOrderId=platform_order_id,
        commandId=COMMAND_ID,
        accountId="account_sim_usdt",
        instrumentId="instrument_btc_usdt",
        symbol="BTCUSDT",
        side="buy",
        orderType="limit",
        quantity=Decimal("1.25000001"),
        price=Decimal("100.12345678"),
        status=status,
        filledQuantity=filled,
        remainingQuantity=Decimal("0") if status == "filled" else Decimal("1.25000001"),
        averageFillPrice=Decimal("100.12345678") if status == "filled" else None,
        rejectReason="venue rejected" if status == "rejected" else None,
        occurredAt=NOW,
        asOf=NOW,
    )


def fill_snapshot() -> VenueFillSnapshot:
    return VenueFillSnapshot(
        source="test",
        externalFillId="venue-fill-001",
        externalOrderId=EXTERNAL_ID,
        platformOrderId=ORDER_ID,
        commandId=COMMAND_ID,
        accountId="account_sim_usdt",
        instrumentId="instrument_btc_usdt",
        symbol="BTCUSDT",
        side="buy",
        quantity=Decimal("1.25000001"),
        price=Decimal("100.12345678"),
        currency="USDT",
        occurredAt=NOW,
    )


class RecoveryGateway(FakeGateway):
    def __init__(self) -> None:
        self.submit_calls = 0
        self.order: VenueOrderSnapshot | None = None
        self.fills: list[VenueFillSnapshot] = []
        self.query_error: Exception | None = None

    def submit_order(self, _command: SubmitOrderCommand) -> list[ExecutionEvent]:
        self.submit_calls += 1
        raise GatewayResultUnknownError("venue outcome is unknown")

    def get_order(self, **_kwargs: object) -> VenueOrderSnapshot | None:
        if self.query_error is not None:
            raise self.query_error
        return self.order

    def list_fills(self, **_kwargs: object) -> list[VenueFillSnapshot]:
        if self.query_error is not None:
            raise self.query_error
        return self.fills


def command_status() -> str:
    record = get_command(COMMAND_ID)
    assert record is not None
    return record.status


def create_unknown_command(tmp_path: Path, gateway: RecoveryGateway) -> None:
    get_settings().journal_path = str(tmp_path / "runtime-recovery.db")
    with TestClient(runtime_main.create_app(gateway)) as client:
        response = client.post("/commands/orders", json=command_payload())
    assert response.status_code == 502
    record = get_command(COMMAND_ID)
    assert record is not None
    assert record.status == "result_unknown"
    assert record.payload["contract_version"] == "1.0"


@pytest.mark.parametrize(
    ("venue_status", "expected_types"),
    [
        ("accepted", ["order_acknowledged"]),
        ("rejected", ["order_rejected"]),
        ("filled", ["order_acknowledged", "order_filled"]),
    ],
)
def test_result_unknown_recovers_from_venue_facts(
    tmp_path: Path,
    venue_status: str,
    expected_types: list[str],
) -> None:
    gateway = RecoveryGateway()
    create_unknown_command(tmp_path, gateway)
    gateway.order = order_snapshot(venue_status)
    gateway.fills = [fill_snapshot()] if venue_status == "filled" else []

    with TestClient(runtime_main.create_app(gateway)) as client:
        first = client.post(f"/commands/{COMMAND_ID}/recover")
        second = client.post(f"/commands/{COMMAND_ID}/recover")

    assert first.status_code == 200
    assert [event["event_type"] for event in first.json()] == expected_types
    assert second.json() == first.json()
    assert gateway.submit_calls == 1
    assert len(get_events(COMMAND_ID)) == len(expected_types)
    if venue_status == "filled":
        fill = first.json()[1]
        assert fill["fill_quantity"] == "1.25000001"
        assert fill["fill_price"] == "100.12345678"


def test_recovery_remains_unknown_when_venue_has_no_order(tmp_path: Path) -> None:
    gateway = RecoveryGateway()
    create_unknown_command(tmp_path, gateway)

    with TestClient(runtime_main.create_app(gateway)) as client:
        response = client.post(f"/commands/{COMMAND_ID}/recover")

    assert response.status_code == 200
    assert response.json() == []
    assert command_status() == "result_unknown"


def test_recovery_timeout_remains_result_unknown(tmp_path: Path) -> None:
    gateway = RecoveryGateway()
    create_unknown_command(tmp_path, gateway)
    gateway.query_error = TimeoutError("venue timed out")

    with TestClient(runtime_main.create_app(gateway)) as client:
        response = client.post(f"/commands/{COMMAND_ID}/recover")

    assert response.status_code == 200
    assert response.json() == []
    assert command_status() == "result_unknown"


def test_runtime_restart_can_recover_without_resubmitting(tmp_path: Path) -> None:
    first_gateway = RecoveryGateway()
    create_unknown_command(tmp_path, first_gateway)

    recovery_gateway = RecoveryGateway()
    recovery_gateway.order = order_snapshot("filled")
    recovery_gateway.fills = [fill_snapshot()]
    with TestClient(runtime_main.create_app(recovery_gateway)) as client:
        response = client.post(f"/commands/{COMMAND_ID}/recover")

    assert response.status_code == 200
    assert recovery_gateway.submit_calls == 0
    assert command_status() == "completed"


def test_wrong_platform_order_id_cannot_pollute_journal(tmp_path: Path) -> None:
    gateway = RecoveryGateway()
    create_unknown_command(tmp_path, gateway)
    gateway.order = order_snapshot("filled", platform_order_id="different-order")

    with TestClient(runtime_main.create_app(gateway)) as client:
        response = client.post(f"/commands/{COMMAND_ID}/recover")

    assert response.status_code == 502
    assert get_events(COMMAND_ID) == []
    assert command_status() == "result_unknown"


def test_stale_processing_command_can_recover_without_submission(tmp_path: Path) -> None:
    from app.journal import claim_command
    from app.runtime_contracts import RuntimeSubmitOrderCommandV1

    get_settings().journal_path = str(tmp_path / "stale-processing.db")
    gateway = RecoveryGateway()
    command = RuntimeSubmitOrderCommandV1.model_validate(command_payload())
    with TestClient(runtime_main.create_app(gateway)):
        assert claim_command(command) is True
    gateway.order = order_snapshot("accepted")

    with TestClient(runtime_main.create_app(gateway)) as client:
        response = client.post(f"/commands/{COMMAND_ID}/recover")

    assert response.status_code == 200
    assert [event["event_type"] for event in response.json()] == ["order_acknowledged"]
    assert gateway.submit_calls == 0
