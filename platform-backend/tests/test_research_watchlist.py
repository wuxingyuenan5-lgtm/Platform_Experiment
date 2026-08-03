from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.config import get_settings
from app.database_bootstrap import bootstrap_database
from app.research_watchlist_schemas import ReplaceResearchWatchlistRequest
from app.research_watchlist_service import (
    ResearchWatchlistServiceError,
    get_research_watchlist,
    replace_research_watchlist,
)
from app.schema_migrations import PLATFORM_MIGRATIONS, apply_migrations
from app.user_product_migrations import USER_PRODUCT_MIGRATIONS
from app.user_service import create_initial_ceo


def initialize_database(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        bootstrap_database(db)
        apply_migrations(db, PLATFORM_MIGRATIONS)
        apply_migrations(db, USER_PRODUCT_MIGRATIONS)
        db.commit()


@pytest.mark.integration
def test_account_watchlist_normalizes_persists_empty_and_detects_conflicts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "research-watchlist.db"
    initialize_database(database_path)
    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(database_path))

    user = create_initial_ceo(
        username="ResearchOwner",
        password="correct horse battery staple",
    )

    empty = get_research_watchlist(user.id)
    assert empty.items == []
    assert empty.row_version == 0
    assert empty.updated_at is None

    created = replace_research_watchlist(
        user_id=user.id,
        request=ReplaceResearchWatchlistRequest(
            items=[
                {"code": "SH600519", "name": " 贵州茅台 ", "group": " 核心观察 "},
                {"code": "300750.SZ", "name": "宁德时代", "group": "核心观察"},
            ],
            expectedVersion=0,
        ),
    )
    assert created.row_version == 1
    assert [item.code for item in created.items] == ["600519", "300750"]
    assert created.items[0].name == "贵州茅台"
    assert created.items[0].group == "核心观察"

    cleared = replace_research_watchlist(
        user_id=user.id,
        request=ReplaceResearchWatchlistRequest(items=[], expectedVersion=1),
    )
    assert cleared.items == []
    assert cleared.row_version == 2
    assert get_research_watchlist(user.id).items == []

    with pytest.raises(ResearchWatchlistServiceError) as conflict:
        replace_research_watchlist(
            user_id=user.id,
            request=ReplaceResearchWatchlistRequest(
                items=[{"code": "600000", "name": "浦发银行", "group": "银行"}],
                expectedVersion=1,
            ),
        )
    assert conflict.value.status_code == 409
    assert conflict.value.code == "watchlist_version_conflict"


@pytest.mark.integration
def test_account_watchlist_rejects_duplicate_codes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "research-watchlist-duplicates.db"
    initialize_database(database_path)
    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(database_path))

    user = create_initial_ceo(
        username="ResearchOwner",
        password="correct horse battery staple",
    )

    with pytest.raises(ResearchWatchlistServiceError) as duplicate:
        replace_research_watchlist(
            user_id=user.id,
            request=ReplaceResearchWatchlistRequest(
                items=[
                    {"code": "600519", "name": "贵州茅台", "group": "默认分组"},
                    {"code": "600519.SH", "name": "重复", "group": "默认分组"},
                ],
                expectedVersion=0,
            ),
        )
    assert duplicate.value.status_code == 422
    assert duplicate.value.code == "duplicate_stock_code"
