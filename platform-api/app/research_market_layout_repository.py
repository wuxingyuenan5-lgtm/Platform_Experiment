"""Per-account display preferences. Market facts never enter this table."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.database_connection import connection
from app.research_watchlist_repository import ResearchWatchlistConcurrentUpdateError


def read_layout(user_id: str, market_id: str) -> dict[str, Any]:
    with connection() as db:
        row = db.execute(
            "SELECT groups_json,row_version,updated_at FROM user_research_market_layouts "
            "WHERE user_id=? AND market_id=?",
            (user_id, market_id),
        ).fetchone()
    if row is None:
        return {"groups": None, "rowVersion": 0, "updatedAt": None}
    return {
        "groups": json.loads(row["groups_json"]),
        "rowVersion": row["row_version"],
        "updatedAt": row["updated_at"],
    }


def replace_layout(
    user_id: str,
    market_id: str,
    groups: list[dict[str, Any]] | None,
    expected_version: int,
) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat()
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT row_version FROM user_research_market_layouts WHERE user_id=? AND market_id=?",
            (user_id, market_id),
        ).fetchone()
        version = row["row_version"] if row else 0
        if version != expected_version:
            raise ResearchWatchlistConcurrentUpdateError("Market layout version changed")
        db.execute(
            "INSERT INTO user_research_market_layouts VALUES (?,?,?,?,?) "
            "ON CONFLICT(user_id,market_id) DO UPDATE SET groups_json=excluded.groups_json,"
            "row_version=excluded.row_version,updated_at=excluded.updated_at",
            (user_id, market_id, json.dumps(groups, ensure_ascii=False), version + 1, now),
        )
    return {"groups": groups, "rowVersion": version + 1, "updatedAt": now}
