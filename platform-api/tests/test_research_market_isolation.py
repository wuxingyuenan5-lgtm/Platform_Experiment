import asyncio
from datetime import UTC, datetime

import pytest
from test_a_share_delivery import research_db as research_db

from app import research_a_share_refresh as cn
from app import research_a_share_repository as repo
from app import research_hk_share_refresh as hk
from app.auth import permission_for_request


class SessionTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 7, 9, tzinfo=UTC).astimezone(tz) if tz else cls(2026, 9, 7, 17)


def test_market_refresh_routes_share_research_permissions():
    for market in ("a-share", "hk-share"):
        assert (
            permission_for_request("POST", f"/api/v1/research/{market}/refresh") == "research.write"
        )
        assert (
            permission_for_request("GET", f"/api/v1/research/{market}/refresh-status")
            == "research.read"
        )


@pytest.fixture
def markets(research_db, monkeypatch):
    monkeypatch.setattr(hk, "_PROVIDER", research_db)
    monkeypatch.setattr(hk, "_LOCK", asyncio.Lock())
    monkeypatch.setattr(hk, "datetime", SessionTime)
    return research_db


def test_slow_hk_cannot_delay_cn_publication_or_change_cn_completion(markets, monkeypatch):
    original = markets.stock_daily_histories

    async def scenario():
        started, release = asyncio.Event(), asyncio.Event()

        async def histories(codes):
            if any(len(code) == 5 for code in codes):
                assert all(len(code) == 5 for code in codes)
                started.set()
                await release.wait()
            else:
                assert all(len(code) == 6 for code in codes)
            return await original(codes)

        monkeypatch.setattr(markets, "stock_daily_histories", histories)
        hk_task = asyncio.create_task(hk.refresh_hk_share_research(force=True))
        await asyncio.wait_for(started.wait(), 2)
        try:
            assert await asyncio.wait_for(cn.refresh_a_share_research(force=True), 3) == "ready"
            assert not hk_task.done()
            before = repo.read_dataset_metadata("stock_pool")
            cn_run = repo.read_refresh_status()
            release.set()
            assert await hk_task == "ready"
            assert repo.read_refresh_status() == cn_run
            assert repo.read_refresh_status("HK")["status"] == "ready"
            assert repo.read_dataset_metadata("stock_pool") == before
            pool = repo.read_stock_pool()
            assert {r["code"] for r in pool["stocks"]} == {
                "600519",
                "000858",
                "300750",
                "300308",
                "00700",
            }
            assert pool["marketStatus"]["CN"]["status"] == "ready"
            assert pool["marketStatus"]["HK"]["status"] == "ready"
        finally:
            release.set()
            await hk_task

    asyncio.run(scenario())


def test_slow_cn_cannot_delay_hk_and_late_cn_publish_keeps_hk_rows(markets, monkeypatch):
    original = markets.index_snapshots

    async def scenario():
        started, release = asyncio.Event(), asyncio.Event()

        async def indices():
            started.set()
            await release.wait()
            return await original()

        monkeypatch.setattr(markets, "index_snapshots", indices)
        cn_task = asyncio.create_task(cn.refresh_a_share_research(force=True))
        await asyncio.wait_for(started.wait(), 2)
        try:
            assert await asyncio.wait_for(hk.refresh_hk_share_research(force=True), 3) == "ready"
            assert not cn_task.done()
            before = repo.read_refresh_status("HK")
            release.set()
            assert await cn_task == "ready"
            assert repo.read_refresh_status("HK") == before
            assert (
                next(r for r in repo.read_stock_pool()["stocks"] if r["code"] == "00700")["status"]
                == "ready"
            )
        finally:
            release.set()
            await cn_task

    asyncio.run(scenario())


def test_failures_mark_only_the_owning_market_stale(markets):
    assert asyncio.run(cn.refresh_a_share_research(force=True)) == "ready"
    assert asyncio.run(hk.refresh_hk_share_research(force=True)) == "ready"
    repo.start_refresh("hk-share-failure", "2026-09-07")
    repo.finish_refresh("hk-share-failure", "error", message="HK unavailable")
    pool = repo.read_stock_pool()
    assert pool["meta"]["status"] == "ready"
    assert all(r["status"] == "ready" for r in pool["stocks"] if len(r["code"]) == 6)
    assert next(r for r in pool["stocks"] if r["code"] == "00700")["status"] == "stale"
    assert asyncio.run(hk.refresh_hk_share_research(force=True)) == "ready"
    repo.start_refresh("a-share-failure", "2026-09-07")
    repo.finish_refresh("a-share-failure", "error", message="CN unavailable")
    pool = repo.read_stock_pool()
    assert all(r["status"] == "stale" for r in pool["stocks"] if len(r["code"]) == 6)
    assert next(r for r in pool["stocks"] if r["code"] == "00700")["status"] == "ready"


def test_hk_holiday_does_not_start_collection_or_touch_cn_status(markets, monkeypatch):
    class HolidayTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 19, 9, tzinfo=UTC).astimezone(tz)

    monkeypatch.setattr(hk, "datetime", HolidayTime)
    assert asyncio.run(cn.refresh_a_share_research(force=True)) == "ready"
    before = repo.read_refresh_status()
    calls = dict(markets.calls)
    assert asyncio.run(hk.refresh_hk_share_research()) == "not_due"
    assert markets.calls == calls
    assert repo.read_refresh_status() == before
    assert repo.read_refresh_status("HK") is None


def test_completed_market_is_not_retried_due_to_other_market_failure(markets, monkeypatch):
    assert asyncio.run(cn.refresh_a_share_research(force=True)) == "ready"
    monkeypatch.setattr(cn, "datetime", SessionTime)
    monkeypatch.setattr(cn, "_scheduled_refresh_due", lambda: True)
    repo.start_refresh("hk-share-failure", "2026-09-07")
    repo.finish_refresh("hk-share-failure", "error", message="HK unavailable")
    calls = dict(markets.calls)
    assert asyncio.run(cn.refresh_a_share_research()) == "up_to_date"
    assert markets.calls == calls
    assert asyncio.run(hk.refresh_hk_share_research(force=True)) == "ready"
    repo.start_refresh("a-share-failure", "2026-09-07")
    repo.finish_refresh("a-share-failure", "error", message="CN unavailable")
    calls = dict(markets.calls)
    assert asyncio.run(hk.refresh_hk_share_research()) == "up_to_date"
    assert markets.calls == calls
