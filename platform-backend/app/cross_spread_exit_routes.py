from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Query

from app.config import get_settings
from app.cross_spread_exit_repository import list_exit_plans
from app.cross_spread_exit_schemas import (
    CrossSpreadCloseResult,
    CrossSpreadExitEvaluationResponse,
    CrossSpreadExitPlanResponse,
    CrossSpreadMarketCloseRequest,
    CrossSpreadMarketOpenRequest,
    CrossSpreadOpenResult,
)
from app.cross_spread_exit_service import (
    close_cross_spread_market,
    evaluate_cross_spread_exit_plans,
    open_cross_spread_market,
    run_cross_spread_exit_monitor,
)

settings = get_settings()


@asynccontextmanager
async def cross_spread_exit_lifespan(_: FastAPI) -> AsyncIterator[None]:
    task: asyncio.Task[None] | None = None
    if settings.cross_spread_exit_monitor_enabled:
        task = asyncio.create_task(run_cross_spread_exit_monitor())
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


router = APIRouter(
    prefix=f"{settings.api_prefix}/trading/cross-spread",
    lifespan=cross_spread_exit_lifespan,
)


@router.post(
    "/lifecycle/open",
    response_model=CrossSpreadOpenResult,
    tags=["trading"],
)
def open_market_lifecycle(request: CrossSpreadMarketOpenRequest) -> CrossSpreadOpenResult:
    return open_cross_spread_market(request)


@router.get(
    "/exit-plans",
    response_model=list[CrossSpreadExitPlanResponse],
    tags=["trading"],
)
def exit_plans(
    status: str | None = Query(default=None),
) -> list[CrossSpreadExitPlanResponse]:
    return list_exit_plans(status=status)


@router.post(
    "/exit-plans/{plan_id}/close",
    response_model=CrossSpreadCloseResult,
    tags=["trading"],
)
def close_market_lifecycle(
    plan_id: str,
    request: CrossSpreadMarketCloseRequest,
) -> CrossSpreadCloseResult:
    return close_cross_spread_market(
        plan_id,
        execution_mode=request.execution_mode,
    )


@router.post(
    "/exit-plans/evaluate",
    response_model=CrossSpreadExitEvaluationResponse,
    tags=["trading"],
)
def evaluate_market_exit_plans() -> CrossSpreadExitEvaluationResponse:
    return evaluate_cross_spread_exit_plans()
