import asyncio
from contextlib import nullcontext
from datetime import UTC, datetime

import pytest

from app import research_a_share_refresh
from app.research_a_share_refresh import _scheduled_refresh_due


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
    # Monday 15:05 Shanghai is eligible.
    assert _scheduled_refresh_due(datetime(2026, 9, 7, 7, 5, tzinfo=UTC)) is True
    # Friday 15:05 is not eligible when the exchange calendar marks a holiday.
    assert _scheduled_refresh_due(datetime(2026, 9, 25, 7, 5, tzinfo=UTC)) is False


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
