"""Advance persisted Funding instructions through their existing bounded state machine."""

from __future__ import annotations

import asyncio
import logging

from app.database import connection
from app.strategies.instruction_service import execute_instruction

LOGGER = logging.getLogger(__name__)
INSTANCE_ID = "strategy_funding_arbitrage_instance_default"


def pending_instruction_ids() -> list[str]:
    with connection() as db:
        return [
            str(row[0])
            for row in db.execute(
                "SELECT id FROM strategy_runs WHERE strategy_instance_id=? "
                "AND execution_plan_json IS NOT NULL AND execution_batch_id IS NOT NULL "
                "AND status IN ('accepted','executing','reconciling') ORDER BY created_at,id",
                (INSTANCE_ID,),
            )
        ]


async def run_funding_instruction_monitor(stop: asyncio.Event) -> None:
    failures: dict[str, str] = {}
    while not stop.is_set():
        for instruction_id in await asyncio.to_thread(pending_instruction_ids):
            if stop.is_set():
                return
            try:
                # This is a state-machine tick, never a reconstructed request.
                # Existing gates, attempt claims, TTL and unknown-result rules apply.
                await asyncio.to_thread(execute_instruction, instruction_id)
                failures.pop(instruction_id, None)
            except Exception as exc:
                kind = type(exc).__name__
                if failures.get(instruction_id) != kind:
                    LOGGER.warning("Funding instruction %s paused: %s", instruction_id, kind)
                    failures[instruction_id] = kind
        try:
            await asyncio.wait_for(stop.wait(), timeout=1.0)
        except TimeoutError:
            pass
