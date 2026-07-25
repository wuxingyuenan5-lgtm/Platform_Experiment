from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException

from app.catalog import get_instrument
from app.config import get_settings
from app.cross_spread import (
    BYBIT_ACCOUNT_ID,
    BYBIT_INSTRUMENT_ID,
    BYBIT_LEG_ROLE,
    BYBIT_SYMBOL,
    MT5_ACCOUNT_ID,
    MT5_INSTRUMENT_ID,
    MT5_LEG_ROLE,
    MT5_SYMBOL,
    STRATEGY_INSTANCE_ID,
    STRATEGY_KEY,
    _load_live_cross_spread_sizing,
    _sides_for_action,
    _validate_acceptance_quantity,
    _validate_leg_quantity,
)
from app.execution_batches import create_execution_batch
from app.order_execution_intents import register_order_execution_intent
from app.schemas import (
    BatchLegRequest,
    CreateExecutionBatchRequest,
    CrossSpreadMarketCommandRequest,
    ExecutionBatchResponse,
)


def get_bybit_catalog_tick_size() -> Decimal:
    instrument = get_instrument(BYBIT_INSTRUMENT_ID)
    if instrument.contract is None or instrument.contract.price_tick <= 0:
        raise HTTPException(
            status_code=423,
            detail="Bybit contract Tick Size is not configured",
        )
    return instrument.contract.price_tick


def submit_cross_spread_fok_command(
    request: CrossSpreadMarketCommandRequest,
    *,
    bybit_limit_price: Decimal,
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
        raise HTTPException(status_code=422, detail="Bybit FOK limit price must be positive")

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
    bybit_side, mt5_side = _sides_for_action(request.action)
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

    batch_key = idempotency_key or (
        f"cross-spread-fok:{request.action}:{request.quantity_oz}:"
        f"{bybit_limit_price}:{uuid4()}"
    )
    register_order_execution_intent(
        f"{batch_key}:{BYBIT_LEG_ROLE}",
        reduce_only=bybit_reduce_only,
    )
    register_order_execution_intent(
        f"{batch_key}:{MT5_LEG_ROLE}",
        reduce_only=mt5_reduce_only,
        position_id=mt5_position_id,
    )

    return create_execution_batch(
        CreateExecutionBatchRequest(
            idempotencyKey=batch_key,
            strategyInstanceId=STRATEGY_INSTANCE_ID,
            accountId=BYBIT_ACCOUNT_ID,
            strategyKey=STRATEGY_KEY,
            direction=request.action,
            legs=[
                BatchLegRequest(
                    role=BYBIT_LEG_ROLE,
                    accountId=BYBIT_ACCOUNT_ID,
                    instrumentId=BYBIT_INSTRUMENT_ID,
                    symbol=BYBIT_SYMBOL,
                    side=bybit_side,
                    orderType="limit",
                    quantity=request.quantity_oz,
                    price=bybit_limit_price,
                ),
                BatchLegRequest(
                    role=MT5_LEG_ROLE,
                    accountId=MT5_ACCOUNT_ID,
                    instrumentId=MT5_INSTRUMENT_ID,
                    symbol=MT5_SYMBOL,
                    side=mt5_side,
                    orderType="market",
                    quantity=mt5_lot,
                ),
            ],
        )
    )
