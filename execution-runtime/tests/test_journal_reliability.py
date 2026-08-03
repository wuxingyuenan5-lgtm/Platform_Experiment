from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.journal import (
    JournalEventConflictError,
    claim_command,
    connection,
    get_command,
    get_events,
    initialize_journal,
    save_command_events,
)
from app.main import create_app
from app.models import ExecutionEvent, SubmitOrderCommand


def build_command() -> SubmitOrderCommand:
    return SubmitOrderCommand(
        command_id="command-journal-001",
        platform_order_id="order-journal-001",
        account_id="account-sim",
        instrument_id="instrument-btc",
        symbol="BTCUSDT",
        side="buy",
        order_type="limit",
        quantity="1.25",
        price="100.50",
    )


def build_events() -> list[ExecutionEvent]:
    occurred_at = datetime(2026, 8, 2, 12, 0, tzinfo=UTC)
    return [
        ExecutionEvent(
            event_id="event-journal-ack-001",
            command_id="command-journal-001",
            platform_order_id="order-journal-001",
            event_type="order_acknowledged",
            external_order_id="external-journal-001",
            occurred_at=occurred_at,
        ),
        ExecutionEvent(
            event_id="event-journal-fill-001",
            command_id="command-journal-001",
            platform_order_id="order-journal-001",
            event_type="order_filled",
            external_order_id="external-journal-001",
            fill_price="100.50",
            fill_quantity="1.25",
            occurred_at=occurred_at,
        ),
    ]


def test_concurrent_identical_event_batches_are_idempotent_and_ordered(tmp_path: Path) -> None:
    get_settings().journal_path = str(tmp_path / "concurrent-events.db")
    initialize_journal()
    command = build_command()
    assert claim_command(command) is True

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(save_command_events, command, build_events()) for _ in range(2)]
        for future in futures:
            future.result()

    assert [event.event_id for event in get_events(command.command_id)] == [
        "event-journal-ack-001",
        "event-journal-fill-001",
    ]
    with connection() as db:
        sequences = [
            row["sequence"]
            for row in db.execute(
                "SELECT sequence FROM runtime_events WHERE command_id = ? ORDER BY sequence",
                (command.command_id,),
            ).fetchall()
        ]
    assert sequences == [1, 2]


def test_conflicting_duplicate_event_identity_fails_closed(tmp_path: Path) -> None:
    get_settings().journal_path = str(tmp_path / "event-conflict.db")
    initialize_journal()
    command = build_command()
    assert claim_command(command) is True
    save_command_events(command, build_events())

    conflicting = build_events()
    conflicting[1] = conflicting[1].model_copy(update={"fill_quantity": Decimal("1.00")})
    with pytest.raises(JournalEventConflictError):
        save_command_events(command, conflicting)

    assert get_events(command.command_id)[1].fill_quantity == build_events()[1].fill_quantity


def test_empty_gateway_evidence_leaves_command_result_unknown(tmp_path: Path) -> None:
    get_settings().journal_path = str(tmp_path / "empty-evidence.db")

    class EmptyGateway:
        name = "empty"

        def submit_order(self, _command: SubmitOrderCommand) -> list[ExecutionEvent]:
            return []

    command = build_command()
    with TestClient(create_app(EmptyGateway())) as client:
        response = client.post("/commands/orders", json=command.model_dump(mode="json"))

    assert response.status_code == 502
    record = get_command(command.command_id)
    assert record is not None
    assert record.status == "result_unknown"
    assert get_events(command.command_id) == []


def test_journal_status_exposes_bounded_recovery_diagnostics(tmp_path: Path) -> None:
    from datetime import timedelta

    from app.journal import journal_status, mark_command_result_unknown

    get_settings().journal_path = str(tmp_path / "journal-status.db")
    initialize_journal()
    command = build_command().model_copy(
        update={"received_at": datetime(2026, 8, 2, 11, 59, tzinfo=UTC)}
    )
    assert claim_command(command) is True
    assert mark_command_result_unknown(command.command_id) is True

    status = journal_status(now=datetime.now(UTC) + timedelta(seconds=5))

    assert status["commandStatusCounts"] == {"result_unknown": 1}
    assert status["resultUnknownCount"] == 1
    assert status["oldestResultUnknownAt"] is not None
    assert status["oldestResultUnknownAgeSeconds"] >= 5
    assert status["staleProcessingCount"] == 0
