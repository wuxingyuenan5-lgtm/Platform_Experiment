"""Bounded background consumer. Requests cannot start collectors or backfill."""

from __future__ import annotations

import asyncio
import json
import logging
import multiprocessing
import time
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager

from app import runtime_transport
from app.config import get_settings
from app.strategy_research_lease import ResearchLease
from app.strategy_research_repository import (
    checkpoint,
    finish_experiment,
    next_experiment,
    publish,
    recover_experiments,
    root_path,
)
from app.strategy_research_series import Deriver, stable_hash
from app.research_write_lock import RESEARCH_DB_WRITE_LOCK

WORKER_STOP = None


def initialize_worker(stop):
    global WORKER_STOP
    WORKER_STOP = stop


LATEST = {}
STATUS = {"status": "disabled", "error": None}


def fetch_batch(after, limit=1000):
    settings = get_settings()
    params = {"limit": str(limit)}
    if after:
        params["after"] = after
    response = runtime_transport.get(
        settings.runtime_base_url.rstrip("/") + "/v1/market-data/events", params=params, timeout=3
    )
    response.raise_for_status()
    return response.json()


async def consume():
    STATUS.update(status="waiting", error=None)
    pending = None
    deriver = Deriver(json.loads(checkpoint()["state_json"]))
    started = time.monotonic()
    while True:
        try:
            after = (
                pending["nextCursor"]
                if pending
                else await asyncio.to_thread(lambda: checkpoint()["cursor"])
            )
            batch = await asyncio.to_thread(fetch_batch, after)
            STATUS.update(
                status=batch.get("capture", {}).get("status", "unknown"),
                runtime=batch.get("capture", {}),
                error=None,
            )
            for event in batch["events"]:
                for derived in deriver.consume(event):
                    if derived["kind"] == "spread":
                        LATEST[derived["pairId"]] = derived
            if batch["events"]:
                if pending:
                    pending["events"].extend(batch["events"])
                    pending["nextCursor"] = batch["nextCursor"]
                    pending["capture"] = batch["capture"]
                else:
                    pending, started = batch, time.monotonic()
            if pending and (len(pending["events"]) >= 5000 or time.monotonic() - started >= 60):
                async with RESEARCH_DB_WRITE_LOCK:
                    await asyncio.to_thread(publish, pending)
                pending = None
            await asyncio.sleep(0.25)
        except asyncio.CancelledError:
            # Unpublished work replays from the last committed cursor on restart.
            raise
        except Exception as exc:
            STATUS.update(status="failed", error=type(exc).__name__ + ":" + str(exc))
            logging.getLogger(__name__).warning(
                "Research ingest paused: %s: %s", type(exc).__name__, str(exc)[:240]
            )
            pending = None
            LATEST.clear()
            deriver = Deriver(json.loads(checkpoint()["state_json"]))
            await asyncio.sleep(2)


def compute_job(job, storage=None):
    if storage is not None:
        get_settings().database_path = storage[0]
        get_settings().strategy_research_path = storage[1]
    from app.strategy_research_experiments import run_experiment
    from app.strategy_research_repository import experiment_cancelled, parts, read_rows

    params = json.loads(job["parameters_json"])
    rows = read_rows(
        pair=params["pairId"],
        kind="spread",
        start=params["from"],
        end=params["cutoff"],
        part_ids=json.loads(job["parts_json"]),
    )
    ids = json.loads(job["parts_json"])
    params["_indications"] = read_rows(
        kind="funding_indication", part_ids=ids, end=params["cutoff"]
    )
    params["_settlements"] = read_rows(
        kind="funding_settlement", part_ids=ids, end=params["cutoff"]
    )
    params["_dataVersion"] = stable_hash([p["checksum"] for p in parts() if p["part_id"] in ids])
    params["_cancelled"] = lambda: (
        (WORKER_STOP is not None and WORKER_STOP.is_set()) or experiment_cancelled(job["run_id"])
    )
    return run_experiment(rows, params)


async def experiments():
    await asyncio.to_thread(recover_experiments)
    context = multiprocessing.get_context("spawn")
    stop = context.Event()
    with ProcessPoolExecutor(
        max_workers=1, mp_context=context, initializer=initialize_worker, initargs=(stop,)
    ) as pool:
        try:
            while True:
                job = await asyncio.to_thread(next_experiment)
                if job is None:
                    await asyncio.sleep(1)
                    continue
                try:
                    result = await asyncio.get_running_loop().run_in_executor(
                        pool, compute_job, job, (get_settings().database_path, str(root_path()))
                    )
                    await asyncio.to_thread(finish_experiment, job["run_id"], result)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    await asyncio.to_thread(
                        finish_experiment,
                        job["run_id"],
                        None,
                        type(exc).__name__ + ":" + str(exc)[:400],
                    )
        finally:
            stop.set()


async def projections():
    from app.strategy_research_projection import project_candle_next, project_next

    while True:
        try:
            async with RESEARCH_DB_WRITE_LOCK:
                candle_progressed = await asyncio.to_thread(project_candle_next)
                progressed = await asyncio.to_thread(project_next)
            await asyncio.sleep(0.02 if candle_progressed or progressed else 1)
        except asyncio.CancelledError:
            raise
        except Exception:
            logging.getLogger(__name__).exception("Research serving projection paused")
            await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(_):
    settings = get_settings()
    tasks = []
    lease = None
    if settings.strategy_research_enabled and settings.strategy_research_worker_enabled:
        lease = ResearchLease(root_path())
        tasks = [
            asyncio.create_task(consume()),
            asyncio.create_task(experiments()),
        ]
        if settings.strategy_research_projection_enabled:
            tasks.append(asyncio.create_task(projections()))
    try:
        yield
    finally:
        for task in tasks:
            task.cancel()
        for task in tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        if lease:
            lease.close()
