from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.config import get_settings
from app.database_bootstrap import bootstrap_database
from app.research_watchlist_schemas import ReplaceResearchWatchlistRequest
from app.research_watchlist_service import (
    ResearchWatchlistServiceError,
    get_user_a_share_watchlist,
    replace_user_a_share_watchlist,
)
from app.schema_migrations import PLATFORM_MIGRATIONS, apply_migrations
from app.user_product_migrations import USER_PRODUCT_MIGRATIONS

USER_ID = "watchlist-user"


def initialize_database(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        bootstrap_database(db)
        apply_migrations(db, PLATFORM_MIGRATIONS)
        apply_migrations(db, USER_PRODUCT_MIGRATIONS)
        db.execute(
            """
            INSERT INTO users (
                id, username, username_normalized, password_hash,
                display_name, role_code, lifecycle_status,
                registered_at, approved_at, password_changed_at,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                USER_ID,
                "WatchlistUser",
                "watchlistuser",
                "test-password-hash",
                "Watchlist User",
                "employee",
                "active",
                "2026-07-30T00:00:00+00:00",
                "2026-07-30T00:00:00+00:00",
                "2026-07-30T00:00:00+00:00",
                "2026-07-30T00:00:00+00:00",
                "2026-07-30T00:00:00+00:00",
            ),
        )
        db.commit()


@pytest.mark.integration
def test_watchlist_persists_order_and_deliberate_empty_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "watchlist.db"
    initialize_database(database_path)
    monkeypatch.setattr(get_settings(), "database_path", str(database_path))

    initial = get_user_a_share_watchlist(USER_ID)
    assert initial.version == 0
    assert initial.items == []

    saved = replace_user_a_share_watchlist(
        USER_ID,
        ReplaceResearchWatchlistRequest(
            expectedVersion=0,
            items=[
                {
                    "securityCode": "600519",
                    "securityName": "贵州茅台",
                    "group": "核心观察",
                },
                {
                    "securityCode": "300750",
                    "securityName": "宁德时代",
                    "group": "核心观察",
                },
            ],
        ),
    )
    assert saved.version == 1
    assert [item.security_code for item in saved.items] == ["600519", "300750"]

    emptied = replace_user_a_share_watchlist(
        USER_ID,
        ReplaceResearchWatchlistRequest(expectedVersion=1, items=[]),
    )
    assert emptied.version == 2
    assert emptied.items == []

    reloaded = get_user_a_share_watchlist(USER_ID)
    assert reloaded.version == 2
    assert reloaded.items == []


@pytest.mark.integration
def test_watchlist_rejects_stale_version(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "watchlist-conflict.db"
    initialize_database(database_path)
    monkeypatch.setattr(get_settings(), "database_path", str(database_path))

    replace_user_a_share_watchlist(
        USER_ID,
        ReplaceResearchWatchlistRequest(expectedVersion=0, items=[]),
    )

    with pytest.raises(ResearchWatchlistServiceError) as conflict:
        replace_user_a_share_watchlist(
            USER_ID,
            ReplaceResearchWatchlistRequest(expectedVersion=0, items=[]),
        )

    assert conflict.value.status_code == 409
    assert conflict.value.code == "watchlist_version_conflict"
