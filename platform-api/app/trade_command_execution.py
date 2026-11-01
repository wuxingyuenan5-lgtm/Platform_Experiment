from __future__ import annotations

from decimal import Decimal
from typing import Literal
from uuid import uuid4

import httpx
from fastapi import HTTPException

from app import runtime_transport
from app.catalog import get_instrument
from app.config import get_settings
from app.database import connection
from app.execution_steps import BLOCKED
from app.execution_steps import FAILED
from app.execution_steps import PASSED
from app.execution_steps import StepRecorder
from app.execution_steps import active_recorder
from app.order_execution_intents import ExecutionPolicy
from app.runtime_contracts import (
    CrossSpreadGuardV1,
    RuntimeExecutionEventV1,
    RuntimeSubmitOrderCommandV1,
)
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


def _runtime_error_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict) and payload.get("detail"):
        return str(payload["detail"])
    text = response.text.strip()
    if text:
        return text
    return f"HTTP {response.status_code}"


def submit_order_through_runtime(
    request: CreateOrderRequest,
    *,
    mode: SubmissionMode,
    strategy_instance_id: str | None = None,
    command_id: str | None = None,
    reduce_only: bool = False,
    position_id: str | None = None,
    execution_policy: ExecutionPolicy = "default",
    cross_spread_guard: CrossSpreadGuardV1 | dict[str, object] | None = None,
    recorder: StepRecorder | None = None,
) -> OrderResponse:
    """Create one local Order and submit it through the selected Runtime contract mode."""

    steps = recorder if recorder is not None else active_recorder() or StepRecorder()

    if mode == "v1":
        if strategy_instance_id is None or command_id is None:
            raise ValueError("V1 order submission requires Strategy and Command identity")
        resolved_command_id = command_id
    else:
        resolved_command_id = command_id or str(uuid4())
    steps.bind(command_id=resolved_command_id)

    with steps.step(
        "ORDER_REQUEST_VALIDATED",
        payload={
            "mode": mode,
            "accountId": request.account_id,
            "instrumentId": request.instrument_id,
            "symbol": request.symbol,
            "side": request.side,
            "orderType": request.order_type,
            "quantity": request.quantity,
            "price": request.price,
            "reduceOnly": reduce_only,
            "executionPolicy": execution_policy,
            "positionId": position_id,
        },
    ):
        if position_id is not None and not reduce_only:
            raise ValueError("A close position target requires reduce-only execution")
        if execution_policy != "default" and request.order_type != "limit":
            raise ValueError("FOK and PostOnly Chase policies require a limit order")

    settings = get_settings()
    instrument_type = get_instrument(request.instrument_id).instrument_type
    order_id = str(uuid4())
    created_at = now_iso()

    with steps.step("ORDER_REQUEST_NORMALIZED", payload={"orderType": request.order_type}):
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
            recorder=steps,
        )
    else:
        enforce_order_safety(
            request.account_id,
            request.instrument_id,
            request.quantity,
            request.price,
            recorder=steps,
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

    steps.bind(order_id=order_id)
    steps.record(
        "ORDER_LOCAL_CREATED",
        payload={
            "orderId": order_id,
            "commandId": resolved_command_id,
            "accountId": request.account_id,
            "symbol": request.symbol,
            "side": request.side,
            "orderType": request.order_type,
            "quantity": decimal_text(request.quantity),
            "price": decimal_text(request.price) if request.price is not None else None,
            "reduceOnly": reduce_only,
        },
    )

    if mode == "v1":
        command_payload = RuntimeSubmitOrderCommandV1(
            command_id=resolved_command_id,
            platform_order_id=order_id,
            strategy_instance_id=strategy_instance_id,
            account_id=request.account_id,
            instrument_id=request.instrument_id,
            instrument_type=instrument_type,
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            execution_policy=execution_policy,
            quantity=request.quantity,
            price=request.price,
            reduce_only=reduce_only,
            position_id=position_id,
            cross_spread_guard=(
                CrossSpreadGuardV1.model_validate(cross_spread_guard)
                if cross_spread_guard is not None
                else None
            ),
        ).model_dump(mode="json")
    else:
        command_payload = {
            "command_id": resolved_command_id,
            "platform_order_id": order_id,
            "account_id": request.account_id,
            "instrument_id": request.instrument_id,
            "instrument_type": instrument_type,
            "symbol": request.symbol,
            "side": request.side,
            "order_type": request.order_type,
            "quantity": decimal_text(request.quantity),
            "price": decimal_text(request.price) if request.price is not None else None,
        }

    steps.record(
        "ORDER_DISPATCH_STARTED",
        payload={
            "runtimeBaseUrl": settings.runtime_base_url,
            "commandId": resolved_command_id,
            "mode": mode,
            "executionPolicy": execution_policy,
            "reduceOnly": reduce_only,
        },
    )
    try:
        response = runtime_transport.post(
            f"{settings.runtime_base_url}/commands/orders",
            json=command_payload,
            timeout=settings.runtime_timeout_seconds,
        )
        response.raise_for_status()
        if mode == "v1":
            events = [
                event.model_dump(mode="json")
                for event in (
                    RuntimeExecutionEventV1.model_validate(item) for item in response.json()
                )
            ]
        else:
            events = response.json()
    except httpx.HTTPStatusError as exc:
        mark_order_result_unknown(order_id)
        detail = _runtime_error_detail(exc.response)
        steps.record(
            "ORDER_DISPATCH_REJECTED",
            BLOCKED,
            reason_code="RUNTIME_REJECTED",
            reason_detail=detail,
            status_code=exc.response.status_code,
            payload={"commandId": resolved_command_id},
        )
        raise HTTPException(status_code=502, detail=detail) from exc
    except httpx.HTTPError as exc:
        mark_order_result_unknown(order_id)
        steps.record(
            "ORDER_DISPATCH_REJECTED",
            FAILED,
            reason_code="RUNTIME_UNAVAILABLE",
            reason_detail=f"{exc.__class__.__name__}: {exc}",
            payload={"commandId": resolved_command_id},
        )
        order = get_order_response(order_id)
        _record_order_final(steps, order, reason_detail="Dispatch outcome is unknown")
        return order
    except (ValueError, TypeError) as exc:
        # A malformed/partial HTTP body is not evidence that dispatch failed.
        mark_order_result_unknown(order_id)
        steps.record(
            "ORDER_DISPATCH_REJECTED",
            FAILED,
            reason_code="RUNTIME_RESPONSE_MALFORMED",
            reason_detail=f"{exc.__class__.__name__}: {exc}",
            payload={"commandId": resolved_command_id},
        )
        order = get_order_response(order_id)
        _record_order_final(steps, order, reason_detail="Dispatch outcome is unknown")
        return order
    except Exception as exc:
        mark_order_result_unknown(order_id)
        steps.record(
            "ORDER_DISPATCH_REJECTED",
            FAILED,
            reason_code="RUNTIME_UNAVAILABLE",
            reason_detail=f"{exc.__class__.__name__}: {exc}",
            payload={"commandId": resolved_command_id},
        )
        raise

    try:
        apply_execution_events(
            order_id,
            request,
            events,
            expected_command_id=resolved_command_id,
        )
    except Exception as exc:
        # This includes projection transaction failures after the venue acted.
        mark_order_result_unknown(order_id)
        steps.record(
            "ORDER_EVENTS_APPLIED",
            FAILED,
            reason_code="EVENT_PROJECTION_FAILED",
            reason_detail=f"{exc.__class__.__name__}: {exc}",
            payload={"commandId": resolved_command_id},
        )
        raise
    steps.record(
        "ORDER_EVENTS_APPLIED",
        payload={
            "eventCount": len(events),
            "eventTypes": ",".join(
                sorted({str(event.get("eventType") or event.get("type")) for event in events})
            ),
        },
    )
    order = get_order_response(order_id)
    _record_order_final(steps, order, reason_detail=None)
    return order


def _record_order_final(
    steps: StepRecorder,
    order: OrderResponse,
    *,
    reason_detail: str | None,
) -> None:
    status = str(order.status)
    if status == "filled":
        steps.record("ORDER_FINAL", PASSED, payload={"orderId": order.order_id, "status": status})
        return
    if status in {"rejected", "canceled", "failed", "expired"}:
        steps.record(
            "ORDER_FINAL",
            FAILED,
            reason_code="ORDER_REJECTED_BY_VENUE",
            reason_detail=reason_detail or f"Order finished with status {status}",
            payload={"orderId": order.order_id, "status": status},
        )
        return
    steps.record(
        "ORDER_FINAL",
        BLOCKED,
        reason_code="ORDER_NOT_FILLED",
        reason_detail=reason_detail or f"Order finished with status {status}",
        payload={"orderId": order.order_id, "status": status},
    )


def submit_trade_command_order(
    request: CreateOrderRequest,
    *,
    strategy_instance_id: str,
    command_id: str,
    reduce_only: bool = False,
    position_id: str | None = None,
    execution_policy: ExecutionPolicy = "default",
    cross_spread_guard: CrossSpreadGuardV1 | dict[str, object] | None = None,
    recorder: StepRecorder | None = None,
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
        cross_spread_guard=cross_spread_guard,
        recorder=recorder,
    )


def estimated_order_notional(request: CreateOrderRequest) -> Decimal | None:
    if request.price is None:
        return None
    return request.quantity * request.price
