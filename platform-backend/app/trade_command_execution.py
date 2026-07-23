from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import httpx
from fastapi import HTTPException

from app.config import get_settings
from app.database import connection
from app.schemas import CreateOrderRequest, OrderResponse
from app.security import enforce_order_safety
from app.trading import (
    apply_execution_events,
    decimal_text,
    get_order_response,
    mark_order_result_unknown,
    now_iso,
)


def submit_trade_command_order(
    request: CreateOrderRequest,
    *,
    strategy_instance_id: str,
    command_id: str,
    reduce_only: bool = False,
) -> OrderResponse:
    """Create an Order and preserve Strategy identity across the Runtime boundary."""

    settings = get_settings()
    order_id = str(uuid4())
    created_at = now_iso()

    if request.order_type == "limit" and request.price is None:
        raise HTTPException(status_code=422, detail="Limit orders require price")

    enforce_order_safety(
        request.account_id,
        request.instrument_id,
        request.quantity,
        request.price,
    )

    with connection() as db:
        db.execute(
            """
            INSERT INTO orders (
                id, command_id, account_id, instrument_id, symbol, side,
                order_type, quantity, price, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order_id,
                command_id,
                request.account_id,
                request.instrument_id,
                request.symbol,
                request.side,
                request.order_type,
                decimal_text(request.quantity),
                decimal_text(request.price) if request.price is not None else None,
                "processing",
                created_at,
                created_at,
            ),
        )

    command = {
        "command_id": command_id,
        "platform_order_id": order_id,
        "strategy_instance_id": strategy_instance_id,
        "account_id": request.account_id,
        "instrument_id": request.instrument_id,
        "symbol": request.symbol,
        "side": request.side,
        "order_type": request.order_type,
        "quantity": decimal_text(request.quantity),
        "price": decimal_text(request.price) if request.price is not None else None,
        "reduce_only": reduce_only,
    }

    try:
        response = httpx.post(
            f"{settings.runtime_base_url}/commands/orders",
            json=command,
            timeout=settings.runtime_timeout_seconds,
        )
        response.raise_for_status()
        events = response.json()
    except httpx.HTTPError:
        mark_order_result_unknown(order_id)
        return get_order_response(order_id)

    apply_execution_events(
        order_id,
        request,
        events,
        expected_command_id=command_id,
    )
    return get_order_response(order_id)


def estimated_order_notional(request: CreateOrderRequest) -> Decimal | None:
    if request.price is None:
        return None
    return request.quantity * request.price
