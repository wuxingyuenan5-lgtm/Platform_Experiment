"""Funding-carry strategy market commands (local closed loop).

The funding carry uses a CEO-specified perpetual-short plus spot-long pair on
one Bybit account. The execution batch places the perpetual leg first and only
releases the spot hedge after an authoritative perpetual fill is confirmed
(see execution_batches.resize_funding_spot_hedge). This module is the thin
strategy adapter for the shared two-leg execution foundation.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException

from app.config import get_settings
from app.execution_batches import create_execution_batch
from app.execution_schemas import (
    BatchLegRequest,
    CreateExecutionBatchRequest,
    ExecutionBatchResponse,
    FundingMarketCommandRequest,
)
from app.order_execution_intents import register_order_execution_intent

STRATEGY_INSTANCE_ID = "strategy_funding_arbitrage_instance_default"
STRATEGY_KEY = "funding_arbitrage"
ACCOUNT_ID = "account_sim_usdt"
PERPETUAL_LEG_ROLE = "perpetual_leg"
SPOT_LEG_ROLE = "spot_leg"
PHASE_2_CAPABILITY_MESSAGE = (
    "Funding controlled-live execution requires Phase 2 post-only "
    "chase and authoritative incremental release"
)


def _sides_for_action(action: str) -> tuple[str, str]:
    if action == "OPEN_SHORT_PERP_LONG_SPOT":
        return "sell", "buy"
    if action == "CLOSE_SHORT_PERP_LONG_SPOT":
        return "buy", "sell"
    raise HTTPException(
        status_code=422,
        detail=f"Unsupported funding action: {action}",
    )


def _funding_execution_gate_allows_write() -> bool:
    return bool(get_settings().live_trading_enabled)


def assert_funding_controlled_live_capability() -> None:
    """Fail closed until the approved funding execution policy exists.

    The legacy endpoint currently constructs two market orders.  It must never
    be treated as controlled-live funding execution while PostOnly Chase and
    deduplicated incremental hedge release remain unimplemented.
    """
    raise HTTPException(status_code=423, detail=PHASE_2_CAPABILITY_MESSAGE)


def submit_funding_market_command(
    request: FundingMarketCommandRequest,
) -> ExecutionBatchResponse:
    if not _funding_execution_gate_allows_write():
        raise HTTPException(
            status_code=403,
            detail="Live funding execution is disabled",
        )
    assert_funding_controlled_live_capability()
    if request.quantity <= 0:
        raise HTTPException(
            status_code=422,
            detail="Funding instruction quantity must be positive",
        )
    if request.perpetual_symbol == request.spot_symbol:
        raise HTTPException(
            status_code=422,
            detail="Perpetual and spot symbols must differ",
        )

    perpetual_side, spot_side = _sides_for_action(request.action)
    is_close = request.action.startswith("CLOSE_")
    batch_key = request.idempotency_key or (
        f"funding:{request.action}:{request.perpetual_symbol}:{request.spot_symbol}:"
        f"{format(request.quantity, 'f')}:{uuid4()}"
    )
    register_order_execution_intent(
        f"{batch_key}:{PERPETUAL_LEG_ROLE}",
        reduce_only=is_close,
    )
    register_order_execution_intent(
        f"{batch_key}:{SPOT_LEG_ROLE}",
        reduce_only=is_close,
    )
    return create_execution_batch(
        CreateExecutionBatchRequest(
            idempotencyKey=batch_key,
            strategyInstanceId=STRATEGY_INSTANCE_ID,
            accountId=ACCOUNT_ID,
            strategyKey=STRATEGY_KEY,
            direction=request.action,
            legs=[
                BatchLegRequest(
                    role=PERPETUAL_LEG_ROLE,
                    accountId=ACCOUNT_ID,
                    instrumentId=f"instrument_{request.perpetual_symbol.lower()}",
                    symbol=request.perpetual_symbol,
                    side=perpetual_side,
                    orderType="market",
                    quantity=request.quantity,
                ),
                BatchLegRequest(
                    role=SPOT_LEG_ROLE,
                    accountId=ACCOUNT_ID,
                    instrumentId=f"instrument_{request.spot_symbol.lower()}",
                    symbol=request.spot_symbol,
                    side=spot_side,
                    orderType="market",
                    quantity=request.quantity,
                ),
            ],
        )
    )
