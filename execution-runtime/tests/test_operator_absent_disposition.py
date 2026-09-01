from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient

from app import main as runtime_main
from app.config import get_settings
from app.fake_gateway import FakeGateway
from app.journal import (
    claim_command,
    get_command,
    has_unresolved_command_for_account,
    initialize_journal,
    mark_command_result_unknown,
)
from app.models import (
    ExecutionEvent,
    SubmitOrderCommand,
    VenueFillHistoryPage,
    VenueOrderHistoryPage,
    VenueOrderSnapshot,
    VenuePositionSnapshot,
)

NOW = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)


def command(command_id: str, account_id: str = "bybit-live-main") -> SubmitOrderCommand:
    return SubmitOrderCommand(
        contract_name="runtime-command",
        contract_version="1.0",
        payload_version="1.0",
        command_id=command_id,
        platform_order_id=f"platform-{command_id}",
        strategy_instance_id="strategy-cross-live",
        account_id=account_id,
        instrument_id="instrument-xaut-usdt",
        symbol="XAUTUSDT",
        side="buy",
        order_type="limit",
        quantity="1",
        price="3000",
        received_at=NOW,
    )


class AbsenceGateway(FakeGateway):
    def __init__(self) -> None:
        self.complete = True
        self.order_match: VenueOrderSnapshot | None = None
        self.open_orders: list[VenueOrderSnapshot] = []
        self.positions: list[VenuePositionSnapshot] = []
        self.write_calls = 0

    def place_order(self, command: SubmitOrderCommand) -> list[ExecutionEvent]:
        self.write_calls += 1
        raise AssertionError("operator disposition must not write")

    def get_order(self, **_kwargs):
        return self.order_match

    def get_order_history(self, **kwargs):
        items = [self.order_match] if self.order_match is not None else []
        return VenueOrderHistoryPage(
            source="test",
            accountId=kwargs["account_id"],
            items=items,
            startTime=kwargs["start_time"],
            endTime=kwargs["end_time"],
            dataQualityState="complete" if self.complete else "incomplete",
        )

    def get_fill_history(self, **kwargs):
        return VenueFillHistoryPage(
            source="test",
            accountId=kwargs["account_id"],
            items=[],
            startTime=kwargs["start_time"],
            endTime=kwargs["end_time"],
            dataQualityState="complete" if self.complete else "incomplete",
        )

    def get_open_orders(self, **_kwargs):
        return self.open_orders

    def get_positions(self, account_id: str | None = None) -> list[VenuePositionSnapshot]:
        return self.positions


def seed_unknown(tmp_path: Path, *commands: SubmitOrderCommand) -> None:
    get_settings().journal_path = str(tmp_path / "operator-disposition.db")
    initialize_journal()
    for item in commands:
        assert claim_command(item)
        assert mark_command_result_unknown(item.command_id)


def request_payload(**overrides):
    payload = {
        "actor": "owner",
        "reason": "Owner confirmed no external side effect after authoritative read-only review",
        "ownerConfirmedNoExternalSideEffect": True,
        "evidenceStart": (NOW - timedelta(days=2)).isoformat(),
        "evidenceEnd": (NOW + timedelta(days=2)).isoformat(),
    }
    payload.update(overrides)
    return payload


def test_incomplete_evidence_and_non_unknown_are_rejected(tmp_path: Path) -> None:
    unknown = command("unknown-incomplete")
    completed = command("already-completed")
    seed_unknown(tmp_path, unknown, completed)
    with sqlite3.connect(get_settings().journal_path) as db:
        db.execute(
            "UPDATE runtime_commands SET status = 'completed' WHERE command_id = ?",
            (completed.command_id,),
        )
    gateway = AbsenceGateway()
    gateway.complete = False
    with TestClient(runtime_main.create_app(gateway)) as client:
        incomplete = client.post(
            f"/commands/{unknown.command_id}/resolve-absent", json=request_payload()
        )
        non_unknown = client.post(
            f"/commands/{completed.command_id}/resolve-absent", json=request_payload()
        )
    assert incomplete.status_code == 409
    assert non_unknown.status_code == 409
    record = get_command(unknown.command_id)
    assert record is not None and record.status == "result_unknown"
    assert gateway.write_calls == 0


def test_absent_disposition_is_idempotent_and_preserves_payload(tmp_path: Path) -> None:
    item = command("unknown-absent")
    seed_unknown(tmp_path, item)
    original = get_command(item.command_id)
    assert original is not None
    original_payload = original.payload
    gateway = AbsenceGateway()
    with TestClient(runtime_main.create_app(gateway)) as client:
        first = client.post(
            f"/commands/{item.command_id}/resolve-absent", json=request_payload()
        )
        second = client.post(
            f"/commands/{item.command_id}/resolve-absent", json=request_payload()
        )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    resolved = get_command(item.command_id)
    assert resolved is not None
    assert resolved.status == "resolved_absent"
    assert resolved.payload == original_payload
    with sqlite3.connect(get_settings().journal_path) as db:
        assert db.execute("SELECT COUNT(*) FROM runtime_command_dispositions").fetchone()[0] == 1
    assert gateway.write_calls == 0


def test_disposition_releases_only_corresponding_account_blocker(tmp_path: Path) -> None:
    target = command("unknown-target", "bybit-live-main")
    other = command("unknown-other", "bybit-other")
    seed_unknown(tmp_path, target, other)
    gateway = AbsenceGateway()
    with TestClient(runtime_main.create_app(gateway)) as client:
        response = client.post(
            f"/commands/{target.command_id}/resolve-absent", json=request_payload()
        )
    assert response.status_code == 200
    assert has_unresolved_command_for_account("bybit-live-main") is False
    assert has_unresolved_command_for_account("bybit-other") is True


def test_current_position_prevents_absent_disposition(tmp_path: Path) -> None:
    item = command("unknown-position")
    seed_unknown(tmp_path, item)
    gateway = AbsenceGateway()
    gateway.positions = [
        VenuePositionSnapshot(
            source="test",
            externalPositionId="position-1",
            accountId=item.account_id,
            instrumentId=item.instrument_id,
            instrumentType="perpetual",
            category="linear",
            symbol=item.symbol,
            netQuantity=Decimal("1"),
            currency="USDT",
            asOf=NOW,
        )
    ]
    with TestClient(runtime_main.create_app(gateway)) as client:
        response = client.post(
            f"/commands/{item.command_id}/resolve-absent", json=request_payload()
        )
    assert response.status_code == 409
    record = get_command(item.command_id)
    assert record is not None and record.status == "result_unknown"
