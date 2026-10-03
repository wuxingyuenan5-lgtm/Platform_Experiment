"""Serving-worker isolation and lifecycle, using only synthetic research data."""

import asyncio
import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from threading import Event

from test_strategy_research import event

from app import strategy_research_ingest as ingest
from app.config import get_settings
from app.database import initialize_database
from app.strategy_research_projection import read_projection
from app.strategy_research_repository import checkpoint, publish


def test_spawned_serving_worker_publishes_and_resumes_original_cursor(tmp_path):
    settings = get_settings()
    settings.strategy_research_path = str(tmp_path / "archive")
    settings.strategy_research_min_free_bytes = 0
    initialize_database()
    storage = (settings.database_path, settings.strategy_research_path)
    batch = {"schemaVersion": "market-events.v1", "after": None,
             "nextCursor": "2", "events": [event(1), event(2, category="spot")]}
    with ProcessPoolExecutor(
        max_workers=1, mp_context=multiprocessing.get_context("spawn"),
        initializer=ingest.initialize_serving_worker, initargs=storage,
    ) as pool:
        assert pool.submit(os.getpid).result(timeout=15) != os.getpid()
        pool.submit(publish, batch).result(timeout=15)
        assert pool.submit(ingest.project_serving_once).result(timeout=15)[1]
    assert checkpoint()["cursor"] == "2"
    expected = read_projection("spread_all", "funding-btc")
    assert expected
    with ProcessPoolExecutor(
        max_workers=1, mp_context=multiprocessing.get_context("spawn"),
        initializer=ingest.initialize_serving_worker, initargs=storage,
    ) as pool:
        assert not any(pool.submit(ingest.project_serving_once).result(timeout=15))
    assert checkpoint()["cursor"] == "2"
    assert read_projection("spread_all", "funding-btc") == expected


def test_cancelled_job_holds_writer_lock_until_worker_finishes(monkeypatch):
    entered, release = Event(), Event()

    def operation():
        entered.set()
        assert release.wait(3)
        return "durable"

    async def exercise():
        lock = asyncio.Lock()
        monkeypatch.setattr(ingest, "RESEARCH_DB_WRITE_LOCK", lock)
        with ThreadPoolExecutor(max_workers=1) as pool:
            task = asyncio.create_task(ingest.run_serving_job(pool, operation))
            assert await asyncio.to_thread(entered.wait, 3)
            task.cancel()
            await asyncio.sleep(0)
            assert lock.locked()
            assert not task.done()
            release.set()
            result = await asyncio.gather(task, return_exceptions=True)
            assert isinstance(result[0], asyncio.CancelledError)
            assert not lock.locked()

    asyncio.run(exercise())


def test_serving_replaces_broken_pool_and_closes_both_generations(monkeypatch):
    pools = []
    get_settings().strategy_research_projection_enabled = False

    class Pool:
        def __init__(self, **kwargs):
            self.closed = False
            pools.append(self)

        def shutdown(self, **kwargs):
            self.closed = True

    async def exercise():
        restarted = asyncio.Event()

        async def consume(pool):
            if len(pools) == 1:
                raise BrokenProcessPool("isolated worker stopped")
            restarted.set()
            await asyncio.Event().wait()

        monkeypatch.setattr(ingest, "ProcessPoolExecutor", Pool)
        monkeypatch.setattr(ingest, "consume", consume)
        task = asyncio.create_task(ingest.serving())
        await asyncio.wait_for(restarted.wait(), timeout=4)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    asyncio.run(exercise())
    assert len(pools) == 2
    assert all(pool.closed for pool in pools)
