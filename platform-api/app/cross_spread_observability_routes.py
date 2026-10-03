import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import APIRouter, FastAPI, Query

from app.config import get_settings
from app.cross_spread import get_cross_spread_snapshot
from app.cross_spread_observability_schemas import CrossSpreadObservabilityResponse
from app.cross_spread_observability_service import get_cross_spread_observability

settings = get_settings()


async def run_market_snapshot_monitor() -> None:
    while True:
        await asyncio.sleep(settings.cross_spread_market_snapshot_interval_seconds)
        try:
            await asyncio.to_thread(get_cross_spread_snapshot, record_history=True)
        except Exception:
            # A temporary Runtime or venue read failure must not stop future sampling.
            continue


@asynccontextmanager
async def market_snapshot_lifespan(_: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(run_market_snapshot_monitor())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


router = APIRouter(
    prefix=f"{settings.api_prefix}/trading/cross-spread",
    lifespan=market_snapshot_lifespan,
)


@router.get(
    "/observability",
    response_model=CrossSpreadObservabilityResponse,
    tags=["trading"],
)
def cross_spread_observability(
    history_hours: int = Query(default=24, alias="historyHours", ge=1, le=168),
    limit: int = Query(default=20, ge=1, le=100),
    mode: Literal["fast", "audit"] = Query(default="audit"),
) -> CrossSpreadObservabilityResponse:
    return get_cross_spread_observability(
        history_hours=history_hours,
        limit=limit,
        mode=mode,
    )
