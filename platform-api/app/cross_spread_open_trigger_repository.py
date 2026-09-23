from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.database import connection


def _now() -> str:
    return datetime.now(UTC).isoformat()


def create_open_trigger(
    *, idempotency_key: str, direction: str, quantity_oz: str, limit_spread: str,
    limit_strategy: str, request_json: str
) -> dict:
    existing = find_open_trigger_by_idempotency(idempotency_key)
    if existing is not None:
        return existing
    now = _now()
    trigger_id = str(uuid4())
    with connection() as db:
        db.execute(
            "INSERT INTO cross_spread_open_triggers "
            "(id,idempotency_key,direction,quantity_oz,limit_spread,limit_strategy,"
            "request_json,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (trigger_id, idempotency_key, direction, quantity_oz, limit_spread,
             limit_strategy, request_json, now, now),
        )
    return get_open_trigger(trigger_id)


def get_open_trigger(trigger_id: str) -> dict:
    with connection() as db:
        row = db.execute(
            "SELECT * FROM cross_spread_open_triggers WHERE id=?", (trigger_id,)
        ).fetchone()
    if row is None:
        raise KeyError(trigger_id)
    return dict(row)


def find_open_trigger_by_idempotency(idempotency_key: str) -> dict | None:
    with connection() as db:
        row = db.execute(
            "SELECT * FROM cross_spread_open_triggers WHERE idempotency_key=?", (idempotency_key,)
        ).fetchone()
    return dict(row) if row is not None else None


def list_pending_open_triggers() -> list[dict]:
    with connection() as db:
        rows = db.execute(
            "SELECT * FROM cross_spread_open_triggers "
            "WHERE status='pending' ORDER BY created_at"
        ).fetchall()
    return [dict(row) for row in rows]


def claim_open_trigger(trigger_id: str) -> bool:
    with connection() as db:
        cur = db.execute(
            "UPDATE cross_spread_open_triggers SET status='triggered', triggered_at=?, "
            "updated_at=? WHERE id=? AND status='pending'",
            (_now(), _now(), trigger_id),
        )
    return cur.rowcount == 1


def finish_open_trigger(
    trigger_id: str, *, execution_batch_id: str | None = None,
    failure_reason: str | None = None
) -> None:
    with connection() as db:
        db.execute(
            "UPDATE cross_spread_open_triggers SET status=?, execution_batch_id=?, "
            "failure_reason=?, updated_at=? WHERE id=?",
            ("completed" if execution_batch_id else "failed", execution_batch_id,
             failure_reason, _now(), trigger_id),
        )
