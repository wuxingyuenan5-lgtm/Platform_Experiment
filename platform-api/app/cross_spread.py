from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

import httpx
from fastapi import HTTPException

from app.config import get_settings
from app.cross_spread_live_read_client import (
    CrossSpreadLiveReadError,
    LiveInstrumentSpecification,
    get_instrument_specification,
)
from app.execution_batches import create_execution_batch
from app.market_data import list_cross_spread_market_history, save_cross_spread_market_snapshot
from app.order_execution_intents import register_order_execution_intent
from app.schemas import (
    BatchLegRequest,
    CreateExecutionBatchRequest,
    CreateTradeCommandRequest,
    CrossSpreadHistoryPointResponse,
    CrossSpreadMarketCommandRequest,
    CrossSpreadSnapshotResponse,
    ExecutionBatchResponse,
    TradeCommandResponse,
)
from app.trade_commands import create_trade_command

STRATEGY_INSTANCE_ID = "strategy_cross_venue_spread_instance_default"
STRATEGY_KEY = "cross_venue_spread"
BYBIT_ACCOUNT_ID = "account_crypto_test"
MT5_ACCOUNT_ID = "account_mt5_demo"
BYBIT_INSTRUMENT_ID = "instrument_xau_usdt_perp"
MT5_INSTRUMENT_ID = "instrument_xau_usd"
BYBIT_SYMBOL = "XAUTUSDT"
MT5_SYMBOL = "XAUUSD.s"
BYBIT_LEG_ROLE = "bybit_leg"
MT5_LEG_ROLE = "mt5_leg"


@dataclass(frozen=True, slots=True)
class CrossSpreadLiveSizing:
    bybit_min: Decimal
    bybit_step: Decimal
    bybit_max: Decimal | None
    mt5_min: Decimal
    mt5_step: Decimal
    mt5_max: Decimal | None
    mt5_multiplier: Decimal


def get_cross_spread_snapshot() -> CrossSpreadSnapshotResponse:
    settings = get_settings()
    try:
        response = httpx.get(
            f"{settings.runtime_base_url}/gateway/cross-spread/snapshot",
            timeout=max(settings.runtime_timeout_seconds, 20.0),
        )
        if response.status_code >= 400:
            raise httpx.HTTPStatusError(
                "Platform Execution Runtime returned an error",
                request=response.request,
                response=response,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Platform Execution Runtime is unavailable",
        ) from exc
    snapshot = CrossSpreadSnapshotResponse.model_validate(response.json())
    save_cross_spread_market_snapshot(
        snapshot,
        strategy_key=STRATEGY_KEY,
        strategy_instance_id=STRATEGY_INSTANCE_ID,
    )
    return snapshot


def get_cross_spread_history(limit: int = 200) -> list[CrossSpreadHistoryPointResponse]:
    return list_cross_spread_market_history(strategy_key=STRATEGY_KEY, limit=limit)


def submit_cross_spread_market_command(
    request: CrossSpreadMarketCommandRequest,
    *,
    idempotency_key: str | None = None,
    bybit_reduce_only: bool = False,
    mt5_reduce_only: bool = False,
    mt5_position_id: str | None = None,
) -> ExecutionBatchResponse:
    settings = get_settings()
    if not _cross_spread_execution_gate_allows_simulation(settings):
        raise HTTPException(
            status_code=403,
            detail="Live cross-spread execution is disabled",
        )

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
        f"cross-spread:{request.action}:{request.quantity_oz}:{uuid4()}"
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
                    orderType="market",
                    quantity=request.quantity_oz,
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


def submit_bybit_definitive_failure_rollback(
    *,
    open_batch_id: str,
    open_action: str,
    quantity_oz: Decimal,
) -> TradeCommandResponse:
    settings = get_settings()
    if not settings.cross_spread_definitive_failure_rollback_enabled:
        raise HTTPException(
            status_code=423,
            detail="Cross-spread rollback capability is disabled",
        )
    _validate_acceptance_quantity(quantity_oz)
    bybit = _load_live_bybit_specification()
    _validate_leg_quantity(
        quantity_oz,
        minimum=bybit.min_quantity,
        step=bybit.quantity_step,
        maximum=bybit.max_market_quantity,
        label=BYBIT_SYMBOL,
    )
    idempotency_key = f"cross-spread-rollback:{open_batch_id}:bybit"
    register_order_execution_intent(idempotency_key, reduce_only=True)
    return create_trade_command(
        CreateTradeCommandRequest(
            idempotencyKey=idempotency_key,
            strategyInstanceId=STRATEGY_INSTANCE_ID,
            accountId=BYBIT_ACCOUNT_ID,
            instrumentId=BYBIT_INSTRUMENT_ID,
            symbol=BYBIT_SYMBOL,
            side="sell" if open_action == "OPEN_LONG" else "buy",
            orderType="market",
            quantity=quantity_oz,
            price=None,
        )
    )


def _cross_spread_execution_gate_allows_simulation(settings) -> bool:
    return bool(settings.live_trading_enabled)


def _sides_for_action(action: str) -> tuple[str, str]:
    if action in {"OPEN_LONG", "CLOSE_SHORT"}:
        return "buy", "sell"
    return "sell", "buy"


def _validate_acceptance_quantity(quantity_oz: Decimal) -> None:
    maximum = get_settings().cross_spread_acceptance_max_quantity_oz
    if maximum <= 0:
        raise HTTPException(
            status_code=423,
            detail="Cross-spread acceptance maximum quantity is not configured",
        )
    if quantity_oz > maximum:
        raise HTTPException(
            status_code=422,
            detail=(
                "Cross-spread acceptance quantity is temporarily capped at "
                f"{maximum} oz"
            ),
        )


def _load_live_bybit_specification() -> LiveInstrumentSpecification:
    try:
        bybit = get_instrument_specification(
            account_id=BYBIT_ACCOUNT_ID,
            symbol=BYBIT_SYMBOL,
        )
    except CrossSpreadLiveReadError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    _validate_bybit_live_specification(bybit)
    return bybit


def _load_live_cross_spread_sizing() -> CrossSpreadLiveSizing:
    settings = get_settings()
    if (
        _cross_spread_execution_gate_allows_simulation(settings)
        and not settings.live_trading_enabled
    ):
        return CrossSpreadLiveSizing(
            bybit_min=Decimal("0.001"),
            bybit_step=Decimal("0.001"),
            bybit_max=Decimal("10"),
            mt5_min=Decimal("0.01"),
            mt5_step=Decimal("0.01"),
            mt5_max=Decimal("100"),
            mt5_multiplier=Decimal("100"),
        )

    bybit = _load_live_bybit_specification()
    try:
        mt5 = get_instrument_specification(
            account_id=MT5_ACCOUNT_ID,
            symbol=MT5_SYMBOL,
        )
    except CrossSpreadLiveReadError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    _validate_mt5_live_specification(mt5)
    return CrossSpreadLiveSizing(
        bybit_min=bybit.min_quantity,
        bybit_step=bybit.quantity_step,
        bybit_max=bybit.max_market_quantity,
        mt5_min=mt5.min_quantity,
        mt5_step=mt5.quantity_step,
        mt5_max=mt5.max_market_quantity,
        mt5_multiplier=mt5.contract_size,
    )


def _validate_bybit_live_specification(
    specification: LiveInstrumentSpecification,
) -> None:
    checks = specification.access_checks
    if specification.status.lower() not in {"trading", "available"}:
        raise HTTPException(
            status_code=423,
            detail="Bybit instrument is not currently trading",
        )
    if checks.get("readOnly") is True:
        raise HTTPException(status_code=423, detail="Bybit API key is read-only")
    if checks.get("ipBound") is not True:
        raise HTTPException(
            status_code=423,
            detail="Bybit API key must be bound to a fixed IP",
        )
    if checks.get("orderPermission") is not True:
        raise HTTPException(
            status_code=423,
            detail="Bybit API key lacks Order permission",
        )
    if checks.get("positionPermission") is not True:
        raise HTTPException(
            status_code=423,
            detail="Bybit API key lacks Position permission",
        )


def _validate_mt5_live_specification(
    specification: LiveInstrumentSpecification,
) -> None:
    checks = specification.access_checks
    if specification.status not in {"available", "selected"}:
        raise HTTPException(
            status_code=423,
            detail="MT5 symbol is not available for trading",
        )
    if checks.get("accountLoginMatched") is not True:
        raise HTTPException(
            status_code=423,
            detail="MT5 connected login does not match configuration",
        )
    if checks.get("accountTradeAllowed") is not True:
        raise HTTPException(
            status_code=423,
            detail="MT5 account does not allow trading",
        )
    if checks.get("terminalTradeAllowed") is not True:
        raise HTTPException(
            status_code=423,
            detail="MT5 Terminal does not allow trading",
        )


def _validate_leg_quantity(
    quantity: Decimal,
    *,
    minimum: Decimal,
    step: Decimal,
    maximum: Decimal | None,
    label: str,
) -> None:
    if minimum <= 0 or step <= 0:
        raise HTTPException(
            status_code=422,
            detail=f"{label} contract specification is invalid",
        )
    if quantity < minimum:
        raise HTTPException(
            status_code=422,
            detail=f"{label} quantity is below contract minimum",
        )
    if maximum is not None and maximum > 0 and quantity > maximum:
        raise HTTPException(
            status_code=422,
            detail=f"{label} quantity exceeds market maximum",
        )
    steps = (quantity - minimum) / step
    if steps != steps.to_integral_value():
        raise HTTPException(
            status_code=422,
            detail=f"{label} quantity does not match current contract step",
        )
