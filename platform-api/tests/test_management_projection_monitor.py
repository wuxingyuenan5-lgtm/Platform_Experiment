import asyncio
import sqlite3
import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from concurrent.futures import Future
from concurrent.futures.process import BrokenProcessPool
from contextlib import suppress

from app import monitor_health
from app import strategy_management_projection as projection


def test_startup_prepares_unbound_strategy_snapshot_before_first_request():
    from app.database import connection, initialize_database

    initialize_database()
    instance = "strategy_short_term_w_instance_default"
    projection.prepare_keys()
    with connection() as db:
        keys = db.execute(
            "SELECT kind FROM strategy_management_projection "
            "WHERE strategy_instance_id=? AND account_id=''", (instance,),
        ).fetchall()
        total = db.execute("SELECT COUNT(*) FROM strategy_management_projection").fetchone()[0]
    assert {row["kind"] for row in keys} == {"pnl", "summary"}
    # No request is needed to enqueue this unbound instance. Drain one startup pass.
    for _ in range(total):
        assert projection.refresh_one()
    result = projection.read_projection(instance, kind="summary")
    assert result.account_id is None
    assert result.sync_status == "unbound"
    assert result.data_quality_state == "unbound"


def test_startup_lock_failure_recovers_without_restarting_api(monkeypatch):
    calls = []
    # Exercise the monitor's retry sequence with local injected failures.
    # Real spawn/database isolation is covered separately below.
    monkeypatch.setattr(projection, "ProcessPoolExecutor", lambda **_: ThreadPoolExecutor(max_workers=1))

    async def scenario():
        ready = asyncio.Event()
        loop = asyncio.get_running_loop()

        def prepare():
            calls.append("prepare")
            if calls.count("prepare") == 1:
                raise sqlite3.OperationalError("database is locked")
            assert monitor_health.snapshot(
                "management_projection", enabled=True, deadline=120
            )["error"] == "OperationalError"

        def refresh():
            calls.append("refresh")
            if calls.count("refresh") == 2:
                loop.call_soon_threadsafe(ready.set)
            return True, False

        monkeypatch.setattr(projection, "prepare_keys", prepare)
        monkeypatch.setattr(projection, "refresh_and_check", refresh)
        task = asyncio.create_task(projection.run_management_projection_monitor())
        try:
            await asyncio.wait_for(ready.wait(), timeout=4)
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    asyncio.run(scenario())
    assert calls == ["prepare", "prepare", "refresh", "refresh"]


def test_projection_spawn_uses_isolated_database_and_publishes():
    from app.database import connection, initialize_database
    from app.config import get_settings

    initialize_database()
    projection.prepare_keys()
    with connection() as db:
        count = db.execute("SELECT count(*) FROM strategy_management_projection WHERE payload_json IS NOT NULL").fetchone()[0]
    assert count == 0
    with ProcessPoolExecutor(
        max_workers=1,
        mp_context=multiprocessing.get_context("spawn"),
        initializer=projection.initialize_projection_worker,
        initargs=(get_settings().database_path,),
    ) as pool:
        assert pool.submit(os.getpid).result(timeout=20) != os.getpid()
        assert pool.submit(projection.refresh_and_check).result(timeout=20) == (True, False)
    with connection() as db:
        rows = db.execute("SELECT payload_json,error_code FROM strategy_management_projection WHERE payload_json IS NOT NULL").fetchall()
    assert len(rows) == 1 and rows[0]["error_code"] is None


def test_exited_projection_worker_is_replaced_before_retry(monkeypatch):
    pools = []
    class ExitedPool:
        def submit(self, *_):
            future = Future()
            future.set_exception(BrokenProcessPool("worker exited"))
            return future
        def shutdown(self, **_):
            self.closed = True

    def create_pool(**_):
        if not pools:
            pool = ExitedPool()
        else:
            assert pools[0].closed
            pool = ThreadPoolExecutor(max_workers=1)
        pools.append(pool)
        return pool

    async def scenario():
        ready = asyncio.Event()
        loop = asyncio.get_running_loop()
        def refresh():
            loop.call_soon_threadsafe(ready.set)
            return False, False
        monkeypatch.setattr(projection, "ProcessPoolExecutor", create_pool)
        monkeypatch.setattr(projection, "prepare_keys", lambda: None)
        monkeypatch.setattr(projection, "refresh_and_check", refresh)
        task = asyncio.create_task(projection.run_management_projection_monitor())
        try:
            await asyncio.wait_for(ready.wait(), timeout=4)
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
    asyncio.run(scenario())
    assert len(pools) == 2
