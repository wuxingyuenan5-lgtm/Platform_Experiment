from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass


class ResearchWatchlistConcurrentUpdateError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ResearchWatchlistRecord:
    user_id: str
    items_json: str
    row_version: int
    created_at: str
    updated_at: str


def get_research_watchlist(
    db: sqlite3.Connection,
    *,
    user_id: str,
) -> ResearchWatchlistRecord | None:
    row = db.execute(
        """
        SELECT user_id, items_json, row_version, created_at, updated_at
        FROM user_research_watchlists
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()
    if row is None:
        return None
    return ResearchWatchlistRecord(
        user_id=str(row["user_id"]),
        items_json=str(row["items_json"]),
        row_version=int(row["row_version"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def replace_research_watchlist(
    db: sqlite3.Connection,
    *,
    user_id: str,
    items: list[dict[str, str]],
    expected_version: int,
    now: str,
) -> ResearchWatchlistRecord:
    payload = json.dumps(items, ensure_ascii=False, separators=(",", ":"))
    current = get_research_watchlist(db, user_id=user_id)

    if current is None:
        if expected_version != 0:
            raise ResearchWatchlistConcurrentUpdateError("Research watchlist version changed")
        db.execute(
            """
            INSERT INTO user_research_watchlists (
                user_id, items_json, row_version, created_at, updated_at
            ) VALUES (?, ?, 1, ?, ?)
            """,
            (user_id, payload, now, now),
        )
    else:
        if current.row_version != expected_version:
            raise ResearchWatchlistConcurrentUpdateError("Research watchlist version changed")
        cursor = db.execute(
            """
            UPDATE user_research_watchlists
            SET items_json = ?,
                row_version = row_version + 1,
                updated_at = ?
            WHERE user_id = ? AND row_version = ?
            """,
            (payload, now, user_id, expected_version),
        )
        if cursor.rowcount != 1:
            raise ResearchWatchlistConcurrentUpdateError("Research watchlist version changed")

    updated = get_research_watchlist(db, user_id=user_id)
    if updated is None:
        raise RuntimeError("Research watchlist did not persist")
    return updated


__all__ = [
    "ResearchWatchlistConcurrentUpdateError",
    "ResearchWatchlistRecord",
    "get_research_watchlist",
    "replace_research_watchlist",
]
