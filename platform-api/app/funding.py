"""Funding-carry strategy market commands (local closed loop).

The funding carry uses a CEO-specified perpetual-short plus spot-long pair on
one Bybit account. The execution batch places the perpetual leg first and only
releases the spot hedge after an authoritative perpetual fill is confirmed
(see execution_batches.resize_funding_spot_hedge). This module is the thin
strategy adapter for the shared two-leg execution foundation.
"""

from __future__ import annotations

from typing import Literal
from uuid import uuid4

from fastapi import HTTPException

from app.config import get_settings
from app.database import connection
from app.execution_batches import create_execution_batch
from app.execution_schemas import (
    BatchLegRequest,
    CreateExecutionBatchRequest,
    ExecutionBatchResponse,
    FundingMarketCommandRequest,
)
from app.order_execution_intents import register_order_execution_intent
from app.strategies.domain import StrategyInstructionAction

STRATEGY_INSTANCE_ID = "strategy_funding_arbitrage_instance_default"
STRATEGY_KEY = "funding_arbitrage"
ACCOUNT_ID = "account_sim_usdt"
PERPETUAL_LEG_ROLE = "perpetual_leg"
SPOT_LEG_ROLE = "spot_leg"
PHASE_2_CAPABILITY_MESSAGE = (
    "Funding controlled-live execution requires Phase 2 post-only "
    "chase and authoritative incremental release"
)


def _sides_for_action(action: str) -> tuple[Literal["buy", "sell"], Literal["buy", "sell"]]:
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
    if _is_simulation_execution():
        return
    raise HTTPException(status_code=423, detail=PHASE_2_CAPABILITY_MESSAGE)


def _is_simulation_execution() -> bool:
    """Allow the legacy Market path only for an authoritative simulation account."""
    if get_settings().default_trading_environment.strip().lower() != "simulation":
        return False
    with connection() as db:
        account = db.execute(
            "SELECT environment FROM accounts WHERE id = ?", (ACCOUNT_ID,)
        ).fetchone()
    return account is not None and account["environment"] == "simulation"


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
    normalized_spot_symbol = _normalize_spot_symbol(request.spot_symbol)
    batch_key = request.idempotency_key or (
        f"funding:{request.action}:{request.perpetual_symbol}:{normalized_spot_symbol}:"
        f"{format(request.quantity, 'f')}:{uuid4()}"
    )
    if request.action == "OPEN_SHORT_PERP_LONG_SPOT":
        from app.strategies.instruction_service import (
            CreateStrategyInstructionRequest,
            create_instruction,
            execute_instruction,
        )

        instruction = create_instruction(
            STRATEGY_INSTANCE_ID,
            CreateStrategyInstructionRequest(
                idempotencyKey=batch_key,
                action=StrategyInstructionAction.OPEN,
                parameters={
                    "perpetualSymbol": request.perpetual_symbol,
                    "perpetualQuantity": request.quantity,
                    "spotSymbol": normalized_spot_symbol,
                    "spotQuantity": request.quantity,
                },
                reason="legacy funding market-command bridge",
            ),
            requested_by=get_settings().development_user_id,
        )
        return execute_instruction(str(instruction["instructionId"]))

    perpetual_side, spot_side = _sides_for_action(request.action)
    is_close = request.action.startswith("CLOSE_")
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
                    instrumentId=_resolve_instrument_id(
                        symbol=request.perpetual_symbol,
                        instrument_type="crypto_perp",
                    ),
                    symbol=request.perpetual_symbol,
                    side=perpetual_side,
                    orderType="market",
                    quantity=request.quantity,
                ),
                BatchLegRequest(
                    role=SPOT_LEG_ROLE,
                    accountId=ACCOUNT_ID,
                    instrumentId=_resolve_instrument_id(
                        symbol=normalized_spot_symbol,
                        instrument_type="crypto_spot",
                    ),
                    symbol=normalized_spot_symbol,
                    side=spot_side,
                    orderType="market",
                    quantity=request.quantity,
                ),
            ],
        )
    )


def _normalize_spot_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if normalized.endswith(("USDT", "USDC", "USD")):
        return normalized
    return f"{normalized}USDT"


def _resolve_instrument_id(*, symbol: str, instrument_type: str) -> str:
    with connection() as db:
        venue = db.execute("SELECT venue_id FROM accounts WHERE id = ?", (ACCOUNT_ID,)).fetchone()
        if venue is None:
            raise HTTPException(status_code=422, detail="Funding account venue is unavailable")
        rows = db.execute(
            """
            SELECT i.id
            FROM instrument_mappings m
            JOIN instruments i ON i.id = m.instrument_id
            JOIN contract_specifications cs ON cs.instrument_id = i.id
            WHERE m.venue_id = ? AND m.status = 'active'
              AND i.instrument_type = ? AND cs.data_quality_state = 'complete'
              AND upper(m.external_symbol) = upper(?)
            """,
            (venue["venue_id"], instrument_type, symbol),
        ).fetchall()
    if len(rows) != 1:
        raise HTTPException(
            status_code=422,
            detail=f"Funding {instrument_type} instrument mapping is unavailable or ambiguous",
        )
    return str(rows[0]["id"])
