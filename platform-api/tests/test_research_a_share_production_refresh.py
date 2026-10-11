import asyncio
from contextlib import nullcontext
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app import research_a_share_refresh
from app.research_a_share_refresh import _daily_market_archive_row, _scheduled_refresh_due


def test_daily_archive_keeps_limit_pool_on_matching_all_a_date_only() -> None:
    rows = [
        SimpleNamespace(return_pct=Decimal("1"), turnover_yuan=Decimal("100")),
        SimpleNamespace(return_pct=Decimal("-1"), turnover_yuan=Decimal("50")),
    ]
    emotion = SimpleNamespace(
        trade_date=datetime(2026, 10, 9).date(), limit_up_count=72, limit_down_count=11
    )
    all_a = _daily_market_archive_row("all_a", "2026-10-09", rows, emotion)
    sh_sz = _daily_market_archive_row("sh_sz_a", "2026-10-09", rows, emotion)
    stale = _daily_market_archive_row("all_a", "2026-10-10", rows, emotion)

    assert (all_a["limit_up"], all_a["limit_down"], all_a["quality_status"]) == (
        72,
        11,
        "ready",
    )
    assert (sh_sz["limit_up"], sh_sz["limit_down"], sh_sz["quality_status"]) == (
        None,
        None,
        "ready",
    )
    assert (stale["limit_up"], stale["limit_down"], stale["quality_status"]) == (
        None,
        None,
        "partial",
    )


def test_scheduled_a_share_refresh_requires_completed_china_session(monkeypatch) -> None:
    monkeypatch.setattr(research_a_share_refresh, "read_only_connection", lambda: nullcontext(None))
    monkeypatch.setattr(
        research_a_share_refresh,
        "calendar_snapshot",
        lambda _db, _today: {"days": ["2026-09-07", "2026-09-24"]},
    )
    # 2026-09-06 is Sunday in Asia/Shanghai.
    assert _scheduled_refresh_due(datetime(2026, 9, 6, 8, tzinfo=UTC)) is False
    # Monday 15:04 Shanghai is not a completed daily close.
    assert _scheduled_refresh_due(datetime(2026, 9, 7, 7, 4, tzinfo=UTC)) is False
    # Monday 15:09 Shanghai is not yet eligible; the owned daily trigger is 15:10.
    assert _scheduled_refresh_due(datetime(2026, 9, 7, 7, 9, tzinfo=UTC)) is False
    assert _scheduled_refresh_due(datetime(2026, 9, 7, 7, 10, tzinfo=UTC)) is True
    # Friday 15:10 is not eligible when the exchange calendar marks a holiday.
    assert _scheduled_refresh_due(datetime(2026, 9, 25, 7, 10, tzinfo=UTC)) is False


def test_periodic_worker_retries_after_unexpected_refresh_exception(monkeypatch) -> None:
    calls = 0
    sleeps = 0

    async def refresh() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("transient database failure")
        raise asyncio.CancelledError

    async def sleep(_: float) -> None:
        nonlocal sleeps
        sleeps += 1

    monkeypatch.setattr(research_a_share_refresh, "refresh_a_share_research", refresh)
    monkeypatch.setattr(research_a_share_refresh.asyncio, "sleep", sleep)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(research_a_share_refresh._run_periodic(900))

    assert calls == 2
    assert sleeps == 1
