from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import httpx
from fastapi import HTTPException

from app.config import get_settings
from app.database import connection
from app.execution_batches import create_execution_batch
from app.market_data import list_cross_spread_market_history, save_cross_spread_market_snapshot
from app.schemas import (
    BatchLegRequest,
    CreateExecutionBatchRequest,
    CrossSpreadHistoryPointResponse,
    CrossSpreadMarketCommandRequest,
    CrossSpreadSnapshotResponse,
    ExecutionBatchResponse,
)

STRATEGY_INSTANCE_ID = "strategy_cross_venue_spread_instance_default"
STRATEGY_KEY = "cross_venue_spread"
BYBIT_ACCOUNT_ID = "account_crypto_test"
MT5_ACCOUNT_ID = "account_mt5_demo"
BYBIT_INSTRUMENT_ID = "instrument_xau_usdt_perp"
MT5_INSTRUMENT_ID = "instrument_xau_usd"
BYBIT_SYMBOL = "XAUTUSDT"
MT5_SYMBOL = "XAUUSD+"


def get_cross_spread_snapshot() -> CrossSpreadSnapshotResponse:
    settings = get_settings()
    try:
        response = httpx.get(
            f"{settings.runtime_base_url}/gateway/cross-spread/snapshot",
            timeout=max(settings.runtime_timeout_seconds, 20.0),
        )
        if response.status_code >= 400:
            raise httpx.HTTPStatusError(
                "Execution runtime returned an error",
                request=response.request,
                response=response,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Execution runtime is unavailable") from exc
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
) -> ExecutionBatchResponse:
    settings = get_settings()
    if not settings.live_trading_enabled:
        raise HTTPException(
            status_code=403,
            detail="Live cross-spread execution is disabled",
        )

    bybit_side, mt5_side = _sides_for_action(request.action)
    sizing = _load_cross_spread_sizing()
    _validate_leg_quantity(
        request.quantity_oz,
        minimum=sizing["bybit_min"],
        step=sizing["bybit_step"],
        label=BYBIT_SYMBOL,
    )
    mt5_lot = request.quantity_oz / sizing["mt5_multiplier"]
    _validate_leg_quantity(
        mt5_lot,
        minimum=sizing["mt5_min"],
        step=sizing["mt5_step"],
        label=MT5_SYMBOL,
    )
    return create_execution_batch(
        CreateExecutionBatchRequest(
            idempotencyKey=f"cross-spread:{request.action}:{request.quantity_oz}:{uuid4()}",
            strategyInstanceId=STRATEGY_INSTANCE_ID,
            accountId=BYBIT_ACCOUNT_ID,
            strategyKey=STRATEGY_KEY,
            direction=request.action,
            legs=[
                BatchLegRequest(
                    role="bybit_leg",
                    accountId=BYBIT_ACCOUNT_ID,
                    instrumentId=BYBIT_INSTRUMENT_ID,
                    symbol=BYBIT_SYMBOL,
                    side=bybit_side,
                    orderType="market",
                    quantity=request.quantity_oz,
                ),
                BatchLegRequest(
                    role="mt5_leg",
                    accountId=MT5_ACCOUNT_ID,
                    instrumentId=MT5_INSTRUMENT_ID,
                    symbol=MT5_SYMBOL,
                    side=mt5_side,
                    orderType="market",
                    quantity=mt5_lot.quantize(sizing["mt5_step"]),
                ),
            ],
        )
    )


def _sides_for_action(action: str) -> tuple[str, str]:
    if action in {"OPEN_LONG", "CLOSE_SHORT"}:
        return "buy", "sell"
    return "sell", "buy"


def _load_cross_spread_sizing() -> dict[str, Decimal]:
    with connection() as db:
        rows = db.execute(
            """
            SELECT instrument_id, min_order_quantity, quantity_step, contract_multiplier
            FROM contract_specifications
            WHERE instrument_id IN (?, ?)
            """,
            (BYBIT_INSTRUMENT_ID, MT5_INSTRUMENT_ID),
        ).fetchall()
    specs = {row["instrument_id"]: row for row in rows}
    if BYBIT_INSTRUMENT_ID not in specs or MT5_INSTRUMENT_ID not in specs:
        raise HTTPException(status_code=422, detail="Cross-spread contract specification is missing")
    bybit = specs[BYBIT_INSTRUMENT_ID]
    mt5 = specs[MT5_INSTRUMENT_ID]
    return {
        "bybit_min": Decimal(bybit["min_order_quantity"]),
        "bybit_step": Decimal(bybit["quantity_step"]),
        "mt5_min": Decimal(mt5["min_order_quantity"]),
        "mt5_step": Decimal(mt5["quantity_step"]),
        "mt5_multiplier": Decimal(mt5["contract_multiplier"]),
    }


def _validate_leg_quantity(
    quantity: Decimal,
    *,
    minimum: Decimal,
    step: Decimal,
    label: str,
) -> None:
    if quantity < minimum:
        raise HTTPException(status_code=422, detail=f"{label} quantity is below contract minimum")
    steps = (quantity - minimum) / step
    if steps != steps.to_integral_value():
        raise HTTPException(status_code=422, detail=f"{label} quantity does not match contract step")
