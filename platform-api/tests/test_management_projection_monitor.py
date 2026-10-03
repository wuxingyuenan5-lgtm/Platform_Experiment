import asyncio
import sqlite3
from contextlib import suppress

from app import monitor_health
from app import strategy_management_projection as projection


def test_startup_lock_failure_recovers_without_restarting_api(monkeypatch):
    calls = []

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
