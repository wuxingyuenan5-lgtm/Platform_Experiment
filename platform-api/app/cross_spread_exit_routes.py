from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Query

from app.config import get_settings
from app.cross_spread import get_cross_spread_trading_rules
from app.cross_spread_exit_repository import list_exit_plans, update_exit_plan_settings
from app.cross_spread_exit_schemas import (
    CrossSpreadCloseResult,
    CrossSpreadExitEvaluationResponse,
    CrossSpreadExitPlanResponse,
    CrossSpreadExitPlanUpdateRequest,
    CrossSpreadMarketCloseRequest,
    CrossSpreadMarketOpenRequest,
    CrossSpreadOpenResult,
    CrossSpreadPendingOpenTriggerResponse,
)
from app.cross_spread_open_trigger_repository import list_pending_open_triggers
from app.cross_spread_synthetic_service import (
    close_cross_spread_market,
    evaluate_cross_spread_exit_plans,
    open_cross_spread_market,
    run_cross_spread_exit_monitor,
)
from app.schemas import CrossSpreadTradingRulesResponse

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


@router.get(
    "/open-triggers",
    response_model=list[CrossSpreadPendingOpenTriggerResponse],
    tags=["trading"],
)
def open_triggers() -> list[CrossSpreadPendingOpenTriggerResponse]:
    return [
        CrossSpreadPendingOpenTriggerResponse(
            triggerId=row["id"], direction=row["direction"], quantityOz=row["quantity_oz"],
            limitSpread=row["limit_spread"], limitStrategy=row["limit_strategy"],
            status=row["status"], createdAt=row["created_at"],
        )
        for row in list_pending_open_triggers()
    ]


@router.get(
    "/trading-rules",
    response_model=CrossSpreadTradingRulesResponse,
    tags=["trading"],
)
def trading_rules() -> CrossSpreadTradingRulesResponse:
    return get_cross_spread_trading_rules()


@router.patch(
    "/exit-plans/{plan_id}",
    response_model=CrossSpreadExitPlanResponse,
    tags=["trading"],
)
def update_exit_plan(
    plan_id: str,
    request: CrossSpreadExitPlanUpdateRequest,
) -> CrossSpreadExitPlanResponse:
    return update_exit_plan_settings(
        plan_id,
        take_profit_spread=request.take_profit_spread,
        stop_loss_spread=request.stop_loss_spread,
        take_profit_execution_mode=request.take_profit_execution_mode,
        stop_loss_execution_mode=request.stop_loss_execution_mode,
        take_profit_limit_strategy=request.take_profit_limit_strategy,
        stop_loss_limit_strategy=request.stop_loss_limit_strategy,
        update_take_profit="take_profit_spread" in request.model_fields_set,
        update_stop_loss="stop_loss_spread" in request.model_fields_set,
        update_take_profit_execution_mode="take_profit_execution_mode" in request.model_fields_set,
        update_stop_loss_execution_mode="stop_loss_execution_mode" in request.model_fields_set,
        update_take_profit_limit_strategy="take_profit_limit_strategy" in request.model_fields_set,
        update_stop_loss_limit_strategy="stop_loss_limit_strategy" in request.model_fields_set,
        take_profit_max_adverse_spread=request.take_profit_max_adverse_spread,
        stop_loss_max_adverse_spread=request.stop_loss_max_adverse_spread,
        update_take_profit_max_adverse_spread="take_profit_max_adverse_spread"
        in request.model_fields_set,
        update_stop_loss_max_adverse_spread="stop_loss_max_adverse_spread"
        in request.model_fields_set,
    )


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
        limit_spread=request.limit_spread,
        limit_strategy=request.limit_strategy,
        idempotency_key=request.idempotency_key,
        quantity_oz=request.quantity_oz,
        max_adverse_spread=request.max_adverse_spread,
    )


@router.post(
    "/exit-plans/evaluate",
    response_model=CrossSpreadExitEvaluationResponse,
    tags=["trading"],
)
def evaluate_market_exit_plans() -> CrossSpreadExitEvaluationResponse:
    return evaluate_cross_spread_exit_plans()
