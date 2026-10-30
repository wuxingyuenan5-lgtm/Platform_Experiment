"""Bounded background consumer. Requests cannot start collectors or backfill."""

from __future__ import annotations

import asyncio
import json
import logging
import multiprocessing
import time
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from contextlib import asynccontextmanager
from pathlib import Path

from app import runtime_transport
from app.config import get_settings
from app.research_write_lock import RESEARCH_DB_WRITE_LOCK
from app.strategy_research_lease import ResearchLease
from app.strategy_research_repository import (
    checkpoint,
    finish_experiment,
    invalidate_capture_status_cache,
    next_experiment,
    publish,
    recover_experiments,
    root_path,
)
from app.strategy_research_series import Deriver, stable_hash

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


def acknowledge_archive():
    """Retryable acknowledgement, only after durable catalog commit and shard verification."""
    from app.strategy_research_repository import parts

    current = checkpoint()["cursor"]
    if not current:
        return
    catalog = parts()
    if not catalog or catalog[-1]["end_cursor"] != current:
        raise ValueError("archive checkpoint has no committed shard")
    part = catalog[-1]
    import hashlib

    import pyarrow.parquet as pq

    path = root_path() / part["path"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != part["checksum"]:
        raise ValueError("archive acknowledgement checksum mismatch")
    if pq.read_metadata(path).num_rows != part["row_count"]:
        raise ValueError("archive acknowledgement row count mismatch")
    response = runtime_transport.post(
        get_settings().runtime_base_url.rstrip("/") + "/v1/market-data/archive-ack",
        json={"cursor": current, "checksum": part["checksum"]},
        timeout=5,
    )
    response.raise_for_status()


async def consume(pool):
    STATUS.update(status="waiting", error=None)
    pending = None
    deriver = await asyncio.to_thread(lambda: Deriver(json.loads(checkpoint()["state_json"])))
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
            for index, event in enumerate(batch["events"]):
                if index % 32 == 0:
                    await asyncio.sleep(0)
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
                await run_serving_job(pool, publish, pending)
                invalidate_capture_status_cache()
                pending = None
                await asyncio.to_thread(acknowledge_archive)
            await asyncio.sleep(0.25)
        except asyncio.CancelledError:
            # Unpublished work replays from the last committed cursor on restart.
            raise
        except BrokenProcessPool:
            raise
        except Exception as exc:
            STATUS.update(status="failed", error=type(exc).__name__ + ":" + str(exc))
            logging.getLogger(__name__).warning(
                "Research ingest paused: %s: %s", type(exc).__name__, str(exc)[:240]
            )
            pending = None
            LATEST.clear()
            deriver = await asyncio.to_thread(
                lambda: Deriver(json.loads(checkpoint()["state_json"]))
            )
            await asyncio.sleep(2)


def compute_job(job, storage=None):
    if storage is not None:
        get_settings().database_path = storage[0]
        get_settings().strategy_research_path = storage[1]
        get_settings().strategy_research_database_path = storage[2] if len(storage) > 2 else None
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
                        pool,
                        compute_job,
                        job,
                        (
                            get_settings().database_path,
                            str(root_path()),
                            get_settings().strategy_research_database_path,
                        ),
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


def initialize_serving_worker(database_path, archive_path, research_database_path=None):
    get_settings().database_path = database_path
    get_settings().strategy_research_path = archive_path
    get_settings().strategy_research_database_path = research_database_path


def project_serving_once():
    from app.strategy_research_projection import (
        project_candle_next,
        project_funding_basis_next,
        project_next,
    )

    return project_candle_next(), project_next(), project_funding_basis_next(500)


async def run_serving_job(pool, operation, *args):
    # Keep the existing writer lock until the child has actually finished,
    # including cancellation during API shutdown. No concurrent replacement job.
    async with RESEARCH_DB_WRITE_LOCK:
        future = asyncio.get_running_loop().run_in_executor(pool, operation, *args)
        try:
            return await asyncio.shield(future)
        except asyncio.CancelledError:
            try:
                await future
            finally:
                raise


async def projections(pool):
    while True:
        try:
            candle_progressed, progressed, basis_progressed = await run_serving_job(
                pool, project_serving_once
            )
            await asyncio.sleep(
                0.2
                if basis_progressed and not (candle_progressed or progressed)
                else (0.02 if candle_progressed or progressed else 1)
            )
        except (asyncio.CancelledError, BrokenProcessPool):
            raise
        except Exception:
            logging.getLogger(__name__).exception("Research serving projection paused")
            await asyncio.sleep(5)


async def serving():
    # CPU-heavy JSON/Parquet work must not contend with the API's Python lock.
    # This is one API-owned worker, sharing the existing durable cursor and lease.
    while True:
        pool = ProcessPoolExecutor(
            max_workers=1,
            mp_context=multiprocessing.get_context("spawn"),
            initializer=initialize_serving_worker,
            initargs=(
                str(Path(get_settings().database_path).resolve()),
                str(root_path().resolve()),
                get_settings().strategy_research_database_path,
            ),
        )
        tasks = [asyncio.create_task(consume(pool))]
        if get_settings().strategy_research_projection_enabled:
            tasks.append(asyncio.create_task(projections(pool)))
        try:
            await asyncio.gather(*tasks)
        except BrokenProcessPool:
            LATEST.clear()
            STATUS.update(
                status="failed", error="Research worker exited; recovering durable cursor"
            )
            logging.getLogger(__name__).exception("Research worker exited; restarting")
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            await asyncio.to_thread(pool.shutdown, wait=True, cancel_futures=True)
        await asyncio.sleep(2)


@asynccontextmanager
async def lifespan(_):
    settings = get_settings()
    tasks = []
    lease = None
    if settings.strategy_research_enabled and settings.strategy_research_worker_enabled:
        lease = ResearchLease(root_path())
        tasks = [
            asyncio.create_task(serving()),
            asyncio.create_task(experiments()),
        ]
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
