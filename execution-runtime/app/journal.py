from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from app.config import get_settings
from app.models import ExecutionEvent, SubmitOrderCommand

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS runtime_commands (
    command_id TEXT PRIMARY KEY,
    platform_order_id TEXT NOT NULL,
    command_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runtime_events (
    event_id TEXT PRIMARY KEY,
    command_id TEXT NOT NULL,
    platform_order_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(command_id) REFERENCES runtime_commands(command_id)
);

CREATE INDEX IF NOT EXISTS idx_runtime_events_command
ON runtime_events(command_id, sequence);
"""


class RuntimeCommandRecord(BaseModel):
    command_id: str
    platform_order_id: str
    account_id: str
    instrument_id: str
    symbol: str
    status: str
    payload: dict[str, object]
    command: SubmitOrderCommand
    created_at: datetime
    updated_at: datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def journal_path() -> Path:
    path = Path(get_settings().journal_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    db = sqlite3.connect(journal_path())
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def initialize_journal() -> None:
    with connection() as db:
        db.executescript(SCHEMA_SQL)


def get_events(command_id: str) -> list[ExecutionEvent]:
    with connection() as db:
        rows = db.execute(
            """
            SELECT payload_json
            FROM runtime_events
            WHERE command_id = ?
            ORDER BY sequence
            """,
            (command_id,),
        ).fetchall()
    return [ExecutionEvent.model_validate_json(row["payload_json"]) for row in rows]


def get_command(command_id: str) -> RuntimeCommandRecord | None:
    with connection() as db:
        row = db.execute(
            """
            SELECT command_id, platform_order_id, payload_json, status,
                   created_at, updated_at
            FROM runtime_commands
            WHERE command_id = ?
            """,
            (command_id,),
        ).fetchone()
    if row is None:
        return None
    command = SubmitOrderCommand.model_validate_json(row["payload_json"])
    return RuntimeCommandRecord(
        command_id=row["command_id"],
        platform_order_id=row["platform_order_id"],
        account_id=command.account_id,
        instrument_id=command.instrument_id,
        symbol=command.symbol,
        status=row["status"],
        payload=json.loads(row["payload_json"]),
        command=command,
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def command_exists(command_id: str) -> bool:
    return get_command(command_id) is not None


def claim_command(command: SubmitOrderCommand) -> bool:
    """Atomically claim a command before any external gateway side effect."""

    now = command.received_at.isoformat()
    payload = command.model_dump_json(by_alias=True)
    with connection() as db:
        cursor = db.execute(
            """
            INSERT OR IGNORE INTO runtime_commands (
                command_id, platform_order_id, command_type, payload_json,
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                command.command_id,
                command.platform_order_id,
                "submit_order",
                payload,
                "processing",
                now,
                now,
            ),
        )
        return cursor.rowcount == 1


def save_command_started(command: SubmitOrderCommand) -> None:
    claim_command(command)


def mark_command_result_unknown(command_id: str) -> bool:
    """Atomically preserve an uncertain command without changing its payload."""

    with connection() as db:
        cursor = db.execute(
            """
            UPDATE runtime_commands
            SET status = 'result_unknown', updated_at = ?
            WHERE command_id = ? AND status IN ('processing', 'result_unknown')
            """,
            (utc_now().isoformat(), command_id),
        )
    return cursor.rowcount == 1


def save_command_events(command: SubmitOrderCommand, events: list[ExecutionEvent]) -> None:
    now = utc_now().isoformat()
    status = (
        "rejected"
        if any(event.event_type == "order_rejected" for event in events)
        else "completed"
    )

    with connection() as db:
        next_sequence_row = db.execute(
            """
            SELECT COALESCE(MAX(sequence), 0) + 1 AS value
            FROM runtime_events
            WHERE command_id = ?
            """,
            (command.command_id,),
        ).fetchone()
        next_sequence = int(next_sequence_row["value"])
        for offset, event in enumerate(events):
            db.execute(
                """
                INSERT OR IGNORE INTO runtime_events (
                    event_id, command_id, platform_order_id, sequence, event_type,
                    payload_json, occurred_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.command_id,
                    event.platform_order_id,
                    next_sequence + offset,
                    event.event_type,
                    event.model_dump_json(by_alias=True),
                    event.occurred_at.isoformat(),
                    now,
                ),
            )
        db.execute(
            """
            UPDATE runtime_commands
            SET status = ?, updated_at = ?
            WHERE command_id = ?
            """,
            (status, now, command.command_id),
        )


def journal_status() -> dict[str, object]:
    with connection() as db:
        command_count = db.execute("SELECT COUNT(*) AS count FROM runtime_commands").fetchone()
        event_count = db.execute("SELECT COUNT(*) AS count FROM runtime_events").fetchone()
        latest = db.execute(
            """
            SELECT command_id, status, updated_at
            FROM runtime_commands
            ORDER BY updated_at DESC
            LIMIT 1
            """
        ).fetchone()
    return {
        "status": "available",
        "commandCount": command_count["count"],
        "eventCount": event_count["count"],
        "latestCommand": dict(latest) if latest is not None else None,
    }
