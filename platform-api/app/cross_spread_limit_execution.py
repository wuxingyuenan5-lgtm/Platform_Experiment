from __future__ import annotations

from decimal import Decimal
from typing import Literal

from fastapi import HTTPException

from app.catalog import get_instrument
from app.config import get_settings
from app.cross_spread import (
    BYBIT_INSTRUMENT_ID,
    BYBIT_SYMBOL,
    MT5_SYMBOL,
    STRATEGY_INSTANCE_ID,
    _load_live_cross_spread_sizing,
    _validate_acceptance_quantity,
    _validate_leg_quantity,
)
from app.schemas import CrossSpreadMarketCommandRequest, ExecutionBatchResponse
from app.strategies.domain import StrategyInstructionAction
from app.strategies.instruction_service import (
    CreateStrategyInstructionRequest,
    create_instruction,
    execute_instruction,
)

LimitStrategy = Literal["fok", "post_only_chase"]


def get_bybit_catalog_tick_size() -> Decimal:
    instrument = get_instrument(BYBIT_INSTRUMENT_ID)
    if instrument.contract is None or instrument.contract.price_tick <= 0:
        raise HTTPException(
            status_code=423,
            detail="Bybit contract Tick Size is not configured",
        )
    return instrument.contract.price_tick


def submit_cross_spread_limit_command(
    request: CrossSpreadMarketCommandRequest,
    *,
    bybit_limit_price: Decimal,
    limit_strategy: LimitStrategy,
    idempotency_key: str | None = None,
    bybit_reduce_only: bool = False,
    mt5_reduce_only: bool = False,
    mt5_position_id: str | None = None,
) -> ExecutionBatchResponse:
    settings = get_settings()
    if not settings.live_trading_enabled:
        raise HTTPException(
            status_code=403,
            detail="Live cross-spread execution is disabled",
        )
    if bybit_limit_price <= 0:
        raise HTTPException(status_code=422, detail="Bybit Limit price must be positive")
    if limit_strategy not in {"fok", "post_only_chase"}:
        raise HTTPException(status_code=422, detail="Unsupported cross-spread Limit strategy")

    is_close = request.action.startswith("CLOSE_")
    if is_close and not (
        bybit_reduce_only and mt5_reduce_only and mt5_position_id is not None
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "Cross-spread close requires reduce-only venue intents "
                "and an MT5 Position Ticket"
            ),
        )
    if not is_close and (
        bybit_reduce_only or mt5_reduce_only or mt5_position_id is not None
    ):
        raise HTTPException(
            status_code=422,
            detail="Open cross-spread commands cannot carry close-position intent",
        )

    _validate_acceptance_quantity(request.quantity_oz)
    sizing = _load_live_cross_spread_sizing()
    _validate_leg_quantity(
        request.quantity_oz,
        minimum=sizing.bybit_min,
        step=sizing.bybit_step,
        maximum=sizing.bybit_max,
        label=BYBIT_SYMBOL,
    )
    mt5_lot = request.quantity_oz / sizing.mt5_multiplier
    _validate_leg_quantity(
        mt5_lot,
        minimum=sizing.mt5_min,
        step=sizing.mt5_step,
        maximum=sizing.mt5_max,
        label=MT5_SYMBOL,
    )
    if mt5_lot * sizing.mt5_multiplier != request.quantity_oz:
        raise HTTPException(
            status_code=422,
            detail="Requested ounces do not map exactly to the current MT5 contract size",
        )

    batch_key = idempotency_key or request.idempotency_key
    if batch_key is None:
        raise HTTPException(
            status_code=422,
            detail="Cross-spread execution requires a stable idempotencyKey",
        )
    instruction = create_instruction(
        STRATEGY_INSTANCE_ID,
        CreateStrategyInstructionRequest(
            idempotencyKey=batch_key,
            action=(
                StrategyInstructionAction.CLOSE
                if is_close
                else StrategyInstructionAction.OPEN
            ),
            parameters={
                "action": request.action,
                "quantityOz": request.quantity_oz,
                "bybitReduceOnly": bybit_reduce_only,
                "mt5ReduceOnly": mt5_reduce_only,
                "mt5PositionId": mt5_position_id,
                "executionPolicy": limit_strategy,
                "bybitLimitPrice": bybit_limit_price,
            },
            reason="cross spread limit command",
        ),
        requested_by="cross_spread_command",
    )
    return execute_instruction(str(instruction["instructionId"]))


def submit_cross_spread_fok_command(
    request: CrossSpreadMarketCommandRequest,
    *,
    bybit_limit_price: Decimal,
    idempotency_key: str | None = None,
    bybit_reduce_only: bool = False,
    mt5_reduce_only: bool = False,
    mt5_position_id: str | None = None,
) -> ExecutionBatchResponse:
    return submit_cross_spread_limit_command(
        request,
        bybit_limit_price=bybit_limit_price,
        limit_strategy="fok",
        idempotency_key=idempotency_key,
        bybit_reduce_only=bybit_reduce_only,
        mt5_reduce_only=mt5_reduce_only,
        mt5_position_id=mt5_position_id,
    )


def submit_cross_spread_postonly_command(
    request: CrossSpreadMarketCommandRequest,
    *,
    bybit_limit_price: Decimal,
    idempotency_key: str | None = None,
    bybit_reduce_only: bool = False,
    mt5_reduce_only: bool = False,
    mt5_position_id: str | None = None,
) -> ExecutionBatchResponse:
    return submit_cross_spread_limit_command(
        request,
        bybit_limit_price=bybit_limit_price,
        limit_strategy="post_only_chase",
        idempotency_key=idempotency_key,
        bybit_reduce_only=bybit_reduce_only,
        mt5_reduce_only=mt5_reduce_only,
        mt5_position_id=mt5_position_id,
    )
