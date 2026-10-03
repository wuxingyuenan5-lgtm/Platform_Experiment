import asyncio
import sqlite3

from app import monitor_health
from app.strategies import funding_runner
from app.strategies.funding_runner import run_funding_instruction_monitor


def test_database_read_failure_does_not_kill_funding_progress(monkeypatch):
    calls = []

    async def scenario():
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()

        def pending():
            calls.append("read")
            if calls.count("read") == 1:
                raise sqlite3.OperationalError("database is locked")
            assert (
                monitor_health.snapshot(
                    "funding_runner",
                    enabled=True,
                    deadline=60,
                )["error"]
                == "OperationalError"
            )
            return ["original-instruction"]

        def execute(instruction_id):
            calls.append(instruction_id)
            loop.call_soon_threadsafe(stop.set)

        monkeypatch.setattr(funding_runner, "pending_instruction_ids", pending)
        monkeypatch.setattr(funding_runner, "execute_instruction", execute)
        await asyncio.wait_for(run_funding_instruction_monitor(stop), timeout=4)

    asyncio.run(scenario())
    assert calls == ["read", "read", "original-instruction"]
    assert (
        monitor_health.snapshot("funding_runner", enabled=True, deadline=60)["status"] == "healthy"
    )


def test_instruction_failure_does_not_stop_other_instructions(monkeypatch):
    calls = []

    async def scenario():
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        monkeypatch.setattr(funding_runner, "pending_instruction_ids", lambda: ["bad", "good"])

        def execute(instruction_id):
            calls.append(instruction_id)
            if instruction_id == "bad":
                raise RuntimeError("unavailable")
            loop.call_soon_threadsafe(stop.set)

        monkeypatch.setattr(funding_runner, "execute_instruction", execute)
        await asyncio.wait_for(run_funding_instruction_monitor(stop), timeout=4)

    asyncio.run(scenario())
    assert calls == ["bad", "good"]
    assert (
        monitor_health.snapshot("funding_runner", enabled=True, deadline=60)["status"] == "degraded"
    )
