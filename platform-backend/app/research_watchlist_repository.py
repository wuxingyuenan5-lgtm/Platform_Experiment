from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4


class ConcurrentWatchlistUpdateError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class WatchlistItemRecord:
    security_code: str
    security_name: str
    group: str


@dataclass(frozen=True, slots=True)
class WatchlistRecord:
    market: str
    version: int
    updated_at: str | None
    items: tuple[WatchlistItemRecord, ...]


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def get_watchlist(db: sqlite3.Connection, *, user_id: str, market: str) -> WatchlistRecord:
    header = db.execute(
        """
        SELECT version, updated_at
        FROM user_research_watchlists
        WHERE user_id = ? AND market = ?
        """,
        (user_id, market),
    ).fetchone()
    if header is None:
        return WatchlistRecord(market=market, version=0, updated_at=None, items=())

    rows = db.execute(
        """
        SELECT security_code, security_name, group_name
        FROM user_research_watchlist_items
        WHERE user_id = ? AND market = ?
        ORDER BY sort_order, security_code
        """,
        (user_id, market),
    ).fetchall()
    return WatchlistRecord(
        market=market,
        version=int(header["version"]),
        updated_at=str(header["updated_at"]),
        items=tuple(
            WatchlistItemRecord(
                security_code=str(row["security_code"]),
                security_name=str(row["security_name"]),
                group=str(row["group_name"]),
            )
            for row in rows
        ),
    )


def replace_watchlist(
    db: sqlite3.Connection,
    *,
    user_id: str,
    market: str,
    expected_version: int,
    items: tuple[WatchlistItemRecord, ...],
    now: str | None = None,
) -> WatchlistRecord:
    timestamp = now or utc_now_iso()
    if not db.in_transaction:
        db.execute("BEGIN IMMEDIATE")

    current = db.execute(
        """
        SELECT version
        FROM user_research_watchlists
        WHERE user_id = ? AND market = ?
        """,
        (user_id, market),
    ).fetchone()
    current_version = int(current["version"]) if current is not None else 0
    if current_version != expected_version:
        raise ConcurrentWatchlistUpdateError(
            f"watchlist version changed from {expected_version} to {current_version}"
        )

    next_version = current_version + 1
    if current is None:
        db.execute(
            """
            INSERT INTO user_research_watchlists (
                user_id, market, version, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, market, next_version, timestamp, timestamp),
        )
    else:
        db.execute(
            """
            UPDATE user_research_watchlists
            SET version = ?, updated_at = ?
            WHERE user_id = ? AND market = ? AND version = ?
            """,
            (next_version, timestamp, user_id, market, current_version),
        )

    db.execute(
        "DELETE FROM user_research_watchlist_items WHERE user_id = ? AND market = ?",
        (user_id, market),
    )
    for sort_order, item in enumerate(items):
        db.execute(
            """
            INSERT INTO user_research_watchlist_items (
                id, user_id, market, security_code, security_name,
                group_name, sort_order, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                user_id,
                market,
                item.security_code,
                item.security_name,
                item.group,
                sort_order,
                timestamp,
                timestamp,
            ),
        )

    return get_watchlist(db, user_id=user_id, market=market)
