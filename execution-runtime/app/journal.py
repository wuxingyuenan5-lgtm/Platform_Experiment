from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

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


def command_exists(command_id: str) -> bool:
    with connection() as db:
        row = db.execute(
            "SELECT command_id FROM runtime_commands WHERE command_id = ?",
            (command_id,),
        ).fetchone()
    return row is not None


def claim_command(command: SubmitOrderCommand) -> bool:
    """Atomically claim a command before any external gateway side effect.

    Exactly one caller can insert the command row. Other callers must not call the gateway and
    should either return persisted events or report that the first execution is still processing.
    """

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
    """Backward-compatible wrapper for tests and callers that do not need claim ownership."""

    claim_command(command)


def save_command_events(command: SubmitOrderCommand, events: list[ExecutionEvent]) -> None:
    now = command.received_at.isoformat()
    status = "completed"
    if any(event.event_type == "order_rejected" for event in events):
        status = "rejected"

    with connection() as db:
        for sequence, event in enumerate(events, start=1):
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
                    sequence,
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
