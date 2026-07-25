from __future__ import annotations

from decimal import Decimal
from typing import Literal
from uuid import uuid4

import httpx
from fastapi import HTTPException
from pydantic import ValidationError

from app.config import get_settings
from app.database import connection
from app.order_execution_intents import ExecutionPolicy
from app.runtime_contracts import RuntimeExecutionEventV1, RuntimeSubmitOrderCommandV1
from app.schemas import CreateOrderRequest, OrderResponse
from app.security import enforce_order_safety
from app.trading import (
    apply_execution_events,
    decimal_text,
    get_order_response,
    mark_order_result_unknown,
    now_iso,
)

SubmissionMode = Literal["legacy", "v1"]


def submit_order_through_runtime(
    request: CreateOrderRequest,
    *,
    mode: SubmissionMode,
    strategy_instance_id: str | None = None,
    command_id: str | None = None,
    reduce_only: bool = False,
    position_id: str | None = None,
    execution_policy: ExecutionPolicy = "default",
) -> OrderResponse:
    """Create one local Order and submit it through the selected Runtime contract mode."""

    if mode == "v1":
        if strategy_instance_id is None or command_id is None:
            raise ValueError("V1 order submission requires Strategy and Command identity")
        resolved_command_id = command_id
    else:
        resolved_command_id = command_id or str(uuid4())

    if position_id is not None and not reduce_only:
        raise ValueError("A close position target requires reduce-only execution")
    if execution_policy != "default" and request.order_type != "limit":
        raise ValueError("FOK and PostOnly Chase policies require a limit order")

    settings = get_settings()
    order_id = str(uuid4())
    created_at = now_iso()

    if request.order_type == "limit" and request.price is None:
        raise HTTPException(status_code=422, detail="Limit orders require price")

    if mode == "v1":
        enforce_order_safety(
            request.account_id,
            request.instrument_id,
            request.quantity,
            request.price,
            strategy_instance_id=strategy_instance_id,
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            command_id=resolved_command_id,
        )
    else:
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
                resolved_command_id,
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

    if mode == "v1":
        command_payload = RuntimeSubmitOrderCommandV1(
            command_id=resolved_command_id,
            platform_order_id=order_id,
            strategy_instance_id=strategy_instance_id,
            account_id=request.account_id,
            instrument_id=request.instrument_id,
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            execution_policy=execution_policy,
            quantity=request.quantity,
            price=request.price,
            reduce_only=reduce_only,
            position_id=position_id,
        ).model_dump(mode="json")
    else:
        command_payload = {
            "command_id": resolved_command_id,
            "platform_order_id": order_id,
            "account_id": request.account_id,
            "instrument_id": request.instrument_id,
            "symbol": request.symbol,
            "side": request.side,
            "order_type": request.order_type,
            "quantity": decimal_text(request.quantity),
            "price": decimal_text(request.price) if request.price is not None else None,
        }

    try:
        response = httpx.post(
            f"{settings.runtime_base_url}/commands/orders",
            json=command_payload,
            timeout=settings.runtime_timeout_seconds,
        )
        response.raise_for_status()
        if mode == "v1":
            events = [
                event.model_dump(mode="json")
                for event in (
                    RuntimeExecutionEventV1.model_validate(item)
                    for item in response.json()
                )
            ]
        else:
            events = response.json()
    except httpx.HTTPError:
        mark_order_result_unknown(order_id)
        return get_order_response(order_id)
    except (ValidationError, TypeError):
        if mode != "v1":
            raise
        mark_order_result_unknown(order_id)
        return get_order_response(order_id)

    apply_execution_events(
        order_id,
        request,
        events,
        expected_command_id=resolved_command_id,
    )
    return get_order_response(order_id)


def submit_trade_command_order(
    request: CreateOrderRequest,
    *,
    strategy_instance_id: str,
    command_id: str,
    reduce_only: bool = False,
    position_id: str | None = None,
    execution_policy: ExecutionPolicy = "default",
) -> OrderResponse:
    """Submit through the authoritative versioned Runtime contract."""

    return submit_order_through_runtime(
        request,
        mode="v1",
        strategy_instance_id=strategy_instance_id,
        command_id=command_id,
        reduce_only=reduce_only,
        position_id=position_id,
        execution_policy=execution_policy,
    )


def estimated_order_notional(request: CreateOrderRequest) -> Decimal | None:
    if request.price is None:
        return None
    return request.quantity * request.price
