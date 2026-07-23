from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import httpx
from fastapi import HTTPException

from app.config import get_settings
from app.database import connection
from app.schemas import CreateOrderRequest, OrderResponse
from app.security import enforce_order_safety


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def decimal_text(value: Decimal) -> str:
    return format(value, "f")


def submit_order(request: CreateOrderRequest, command_id: str | None = None) -> OrderResponse:
    settings = get_settings()
    order_id = str(uuid4())
    command_id = command_id or str(uuid4())
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


def reconcile_order(order_id: str) -> OrderResponse:
    """Recover an uncertain order from Runtime Journal without resubmitting it."""

    row = get_order_row(order_id)
    if row["status"] != "result_unknown":
        return order_response_from_row(row)

    settings = get_settings()
    try:
        response = httpx.get(
            f"{settings.runtime_base_url}/commands/{row['command_id']}/events",
            timeout=settings.runtime_timeout_seconds,
        )
        if response.status_code == 404:
            return order_response_from_row(row)
        response.raise_for_status()
        events = response.json()
    except httpx.HTTPError:
        return order_response_from_row(row)

    if not events:
        return order_response_from_row(row)

    request = request_from_order_row(row)
    apply_execution_events(
        order_id,
        request,
        events,
        expected_command_id=row["command_id"],
    )
    synchronize_trade_command_status(row["command_id"], order_id)
    return get_order_response(order_id)


def mark_order_result_unknown(order_id: str) -> None:
    with connection() as db:
        db.execute(
            "UPDATE orders SET status = ?, updated_at = ? WHERE id = ?",
            ("result_unknown", now_iso(), order_id),
        )


def apply_execution_events(
    order_id: str,
    request: CreateOrderRequest,
    events: list[dict[str, object]],
    *,
    expected_command_id: str,
) -> None:
    for event in events:
        validate_execution_event(
            event,
            expected_command_id=expected_command_id,
            expected_order_id=order_id,
        )
        event_type = str(event["event_type"])
        occurred_at = str(event["occurred_at"])
        external_order_id = event.get("external_order_id")

        if event_type == "order_acknowledged":
            with connection() as db:
                db.execute(
                    """
                    UPDATE orders
                    SET status = ?, external_order_id = ?, updated_at = ?
                    WHERE id = ? AND status != 'filled'
                    """,
                    ("acknowledged", external_order_id, occurred_at, order_id),
                )
        elif event_type == "order_rejected":
            with connection() as db:
                db.execute(
                    """
                    UPDATE orders SET status = ?, updated_at = ?
                    WHERE id = ? AND status != 'filled'
                    """,
                    ("rejected", occurred_at, order_id),
                )
        elif event_type == "order_filled":
            fill_price = Decimal(str(event["fill_price"]))
            fill_quantity = Decimal(str(event["fill_quantity"]))
            fill_id = str(event["event_id"])
            record_fill_and_update_projections(
                fill_id=fill_id,
                order_id=order_id,
                request=request,
                fill_price=fill_price,
                fill_quantity=fill_quantity,
                occurred_at=occurred_at,
            )


def validate_execution_event(
    event: dict[str, object],
    *,
    expected_command_id: str,
    expected_order_id: str,
) -> None:
    if str(event.get("command_id")) != expected_command_id:
        raise HTTPException(status_code=502, detail="Runtime event command mismatch")
    if str(event.get("platform_order_id")) != expected_order_id:
        raise HTTPException(status_code=502, detail="Runtime event order mismatch")
    if event.get("event_id") is None or event.get("occurred_at") is None:
        raise HTTPException(status_code=502, detail="Runtime event is incomplete")


def record_fill_and_update_projections(
    *,
    fill_id: str,
    order_id: str,
    request: CreateOrderRequest,
    fill_price: Decimal,
    fill_quantity: Decimal,
    occurred_at: str,
) -> bool:
    signed_fill = fill_quantity if request.side == "buy" else -fill_quantity

    with connection() as db:
        cursor = db.execute(
            """
            INSERT OR IGNORE INTO fills (
                id, order_id, account_id, instrument_id, side, quantity, price, occurred_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fill_id,
                order_id,
                request.account_id,
                request.instrument_id,
                request.side,
                decimal_text(fill_quantity),
                decimal_text(fill_price),
                occurred_at,
            ),
        )
        if cursor.rowcount == 0:
            return False

        current = db.execute(
            """
            SELECT net_quantity, average_price FROM positions
            WHERE account_id = ? AND instrument_id = ?
            """,
            (request.account_id, request.instrument_id),
        ).fetchone()

        old_quantity = Decimal(current["net_quantity"]) if current else Decimal("0")
        old_average = (
            Decimal(current["average_price"])
            if current and current["average_price"] is not None
            else None
        )
        new_quantity, new_average, realized_pnl = calculate_position_update(
            old_quantity=old_quantity,
            old_average=old_average,
            signed_fill=signed_fill,
            fill_price=fill_price,
        )

        db.execute(
            """
            INSERT INTO positions (
                account_id, instrument_id, net_quantity, average_price, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(account_id, instrument_id) DO UPDATE SET
                net_quantity = excluded.net_quantity,
                average_price = excluded.average_price,
                updated_at = excluded.updated_at
            """,
            (
                request.account_id,
                request.instrument_id,
                decimal_text(new_quantity),
                decimal_text(new_average) if new_average is not None else None,
                occurred_at,
            ),
        )

        db.execute(
            "UPDATE orders SET status = ?, updated_at = ? WHERE id = ?",
            ("filled", occurred_at, order_id),
        )

        db.execute(
            """
            INSERT INTO economic_events (
                id, event_type, account_id, instrument_id, order_id,
                amount, currency, occurred_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"trade-fill:{fill_id}",
                "trade_fill",
                request.account_id,
                request.instrument_id,
                order_id,
                decimal_text(realized_pnl),
                "USD",
                occurred_at,
            ),
        )

        pnl = db.execute(
            """
            SELECT realized_pnl, trading_pnl, fees FROM pnl_results
            WHERE account_id = ? AND instrument_id = ?
            """,
            (request.account_id, request.instrument_id),
        ).fetchone()
        previous_realized = Decimal(pnl["realized_pnl"]) if pnl else Decimal("0")
        previous_trading = Decimal(pnl["trading_pnl"]) if pnl else Decimal("0")
        previous_fees = Decimal(pnl["fees"]) if pnl else Decimal("0")

        db.execute(
            """
            INSERT INTO pnl_results (
                account_id, instrument_id, realized_pnl, trading_pnl, fees, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(account_id, instrument_id) DO UPDATE SET
                realized_pnl = excluded.realized_pnl,
                trading_pnl = excluded.trading_pnl,
                fees = excluded.fees,
                updated_at = excluded.updated_at
            """,
            (
                request.account_id,
                request.instrument_id,
                decimal_text(previous_realized + realized_pnl),
                decimal_text(previous_trading + realized_pnl),
                decimal_text(previous_fees),
                occurred_at,
            ),
        )
    return True


def get_order_row(order_id: str):
    with connection() as db:
        row = db.execute(
            """
            SELECT id, command_id, account_id, instrument_id, symbol, side,
                   order_type, quantity, price, status, external_order_id
            FROM orders
            WHERE id = ?
            """,
            (order_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return row


def request_from_order_row(row) -> CreateOrderRequest:
    return CreateOrderRequest(
        accountId=row["account_id"],
        instrumentId=row["instrument_id"],
        symbol=row["symbol"],
        side=row["side"],
        orderType=row["order_type"],
        quantity=Decimal(row["quantity"]),
        price=Decimal(row["price"]) if row["price"] is not None else None,
    )


def get_order_response(order_id: str) -> OrderResponse:
    return order_response_from_row(get_order_row(order_id))


def order_response_from_row(row) -> OrderResponse:
    return OrderResponse(
        orderId=row["id"],
        commandId=row["command_id"],
        status=row["status"],
        externalOrderId=row["external_order_id"],
    )


def synchronize_trade_command_status(command_id: str, order_id: str) -> None:
    with connection() as db:
        row = db.execute("SELECT status FROM orders WHERE id = ?", (order_id,)).fetchone()
        if row is not None:
            db.execute(
                "UPDATE trade_commands SET status = ?, updated_at = ? WHERE id = ?",
                (row["status"], now_iso(), command_id),
            )


def calculate_position_update(
    *,
    old_quantity: Decimal,
    old_average: Decimal | None,
    signed_fill: Decimal,
    fill_price: Decimal,
) -> tuple[Decimal, Decimal | None, Decimal]:
    if old_quantity == 0 or old_quantity * signed_fill > 0:
        new_quantity = old_quantity + signed_fill
        old_notional = abs(old_quantity) * (old_average or Decimal("0"))
        new_notional = abs(signed_fill) * fill_price
        new_average = (old_notional + new_notional) / abs(new_quantity)
        return new_quantity, new_average, Decimal("0")

    closing_quantity = min(abs(old_quantity), abs(signed_fill))
    direction = Decimal("1") if old_quantity > 0 else Decimal("-1")
    realized_pnl = closing_quantity * (fill_price - (old_average or fill_price)) * direction
    new_quantity = old_quantity + signed_fill

    if new_quantity == 0:
        return new_quantity, None, realized_pnl
    if old_quantity * new_quantity > 0:
        return new_quantity, old_average, realized_pnl
    return new_quantity, fill_price, realized_pnl
