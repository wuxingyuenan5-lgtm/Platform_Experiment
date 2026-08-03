from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.gateway import ExecutionGateway
from app.gateway_errors import (
    GatewayConfigurationError,
    GatewayQueryUnsupportedError,
    GatewayRequestRejectedError,
    GatewayResultUnknownError,
)
from app.journal import (
    RuntimeCommandRecord,
    get_command,
    get_events,
    mark_command_result_unknown,
    save_command_events,
)
from app.models import ExecutionEvent, VenueFillSnapshot, VenueOrderSnapshot

PROCESSING_STALE_AFTER = timedelta(seconds=30)


class RecoveryCommandNotFoundError(LookupError):
    pass


class RecoveryCommandNotReadyError(RuntimeError):
    pass


class RecoveryEvidenceMismatchError(RuntimeError):
    pass


def _event_id(command_id: str, event_type: str, external_id: str) -> str:
    return f"RECOVERY-{command_id}-{event_type}-{external_id}"


def _validate_order(record: RuntimeCommandRecord, order: VenueOrderSnapshot) -> None:
    expected = (
        record.platform_order_id,
        record.command_id,
        record.account_id,
        record.instrument_id,
        record.symbol.upper(),
    )
    actual = (
        order.platform_order_id,
        order.command_id,
        order.account_id,
        order.instrument_id,
        order.symbol.upper(),
    )
    if actual != expected:
        raise RecoveryEvidenceMismatchError("Venue order identity does not match Runtime command")
    command = record.command
    if order.side != command.side or order.order_type != command.order_type:
        raise RecoveryEvidenceMismatchError(
            "Venue order execution terms do not match Runtime command"
        )
    if order.quantity != command.quantity:
        raise RecoveryEvidenceMismatchError("Venue order quantity does not match Runtime command")
    if command.order_type == "limit" and order.price != command.price:
        raise RecoveryEvidenceMismatchError("Venue order price does not match Runtime command")
    if order.reduce_only is not None and order.reduce_only != command.reduce_only:
        raise RecoveryEvidenceMismatchError(
            "Venue order reduce-only flag does not match Runtime command"
        )
    if order.position_id is not None and order.position_id != command.position_id:
        raise RecoveryEvidenceMismatchError(
            "Venue order position identity does not match Runtime command"
        )
    if order.filled_quantity < 0 or order.remaining_quantity < 0:
        raise RecoveryEvidenceMismatchError("Venue order quantities are invalid")
    if order.filled_quantity > order.quantity:
        raise RecoveryEvidenceMismatchError("Venue filled quantity exceeds order quantity")


def _validate_fill(
    record: RuntimeCommandRecord,
    order: VenueOrderSnapshot,
    fill: VenueFillSnapshot,
) -> None:
    if (
        fill.platform_order_id != record.platform_order_id
        or fill.command_id != record.command_id
        or fill.account_id != record.account_id
        or fill.instrument_id != record.instrument_id
        or fill.symbol.upper() != record.symbol.upper()
        or fill.external_order_id != order.external_order_id
        or fill.side != record.command.side
    ):
        raise RecoveryEvidenceMismatchError("Venue fill identity does not match Runtime command")
    if fill.quantity <= 0 or fill.price <= 0:
        raise RecoveryEvidenceMismatchError("Venue fill quantity or price is invalid")


def _ack_event(record: RuntimeCommandRecord, order: VenueOrderSnapshot) -> ExecutionEvent:
    return ExecutionEvent(
        event_id=_event_id(record.command_id, "ack", order.external_order_id),
        command_id=record.command_id,
        platform_order_id=record.platform_order_id,
        event_type="order_acknowledged",
        external_order_id=order.external_order_id,
        occurred_at=order.occurred_at,
    )


def _fill_events(
    record: RuntimeCommandRecord,
    order: VenueOrderSnapshot,
    fills: list[VenueFillSnapshot],
) -> list[ExecutionEvent]:
    events: list[ExecutionEvent] = []
    for fill in sorted(fills, key=lambda item: (item.occurred_at, item.external_fill_id)):
        _validate_fill(record, order, fill)
        events.append(
            ExecutionEvent(
                event_id=_event_id(record.command_id, "fill", fill.external_fill_id),
                command_id=record.command_id,
                platform_order_id=record.platform_order_id,
                event_type="order_filled",
                external_order_id=fill.external_order_id,
                fill_price=fill.price,
                fill_quantity=fill.quantity,
                occurred_at=fill.occurred_at,
            )
        )
    if events:
        total_quantity = sum((event.fill_quantity or 0 for event in events), start=0)
        if total_quantity != order.filled_quantity:
            raise RecoveryEvidenceMismatchError(
                "Venue fill facts do not match the order filled quantity"
            )
        return events
    if order.filled_quantity > 0 and order.average_fill_price is not None:
        return [
            ExecutionEvent(
                event_id=_event_id(record.command_id, "fill", order.external_order_id),
                command_id=record.command_id,
                platform_order_id=record.platform_order_id,
                event_type="order_filled",
                external_order_id=order.external_order_id,
                fill_price=order.average_fill_price,
                fill_quantity=order.filled_quantity,
                occurred_at=order.occurred_at,
            )
        ]
    return []


def _events_from_venue(
    record: RuntimeCommandRecord,
    gateway: ExecutionGateway,
    order: VenueOrderSnapshot,
) -> list[ExecutionEvent]:
    _validate_order(record, order)
    if order.status == "unknown":
        return []
    if order.status in {"rejected", "canceled"}:
        if order.filled_quantity > 0:
            raise RecoveryEvidenceMismatchError(
                "Canceled or rejected Venue order has fills that cannot be represented safely"
            )
        reason = order.reject_reason or order.cancel_reason or f"Venue order is {order.status}"
        return [
            ExecutionEvent(
                event_id=_event_id(record.command_id, "reject", order.external_order_id),
                command_id=record.command_id,
                platform_order_id=record.platform_order_id,
                event_type="order_rejected",
                external_order_id=order.external_order_id,
                occurred_at=order.occurred_at,
                reason=reason,
            )
        ]

    events = [_ack_event(record, order)]
    if order.status in {"partially_filled", "filled"}:
        fills = gateway.list_fills(
            account_id=record.account_id,
            platform_order_id=record.platform_order_id,
            external_order_id=order.external_order_id,
        )
        events.extend(_fill_events(record, order, fills))
        if order.status == "filled" and len(events) == 1:
            return []
    return events


def recover_command(
    command_id: str,
    *,
    gateway: ExecutionGateway,
    now: datetime | None = None,
) -> list[ExecutionEvent]:
    """Recover one uncertain command from venue facts without resubmitting it."""

    record = get_command(command_id)
    if record is None:
        raise RecoveryCommandNotFoundError(command_id)
    persisted = get_events(command_id)
    if record.status in {"completed", "rejected"}:
        return persisted

    current_time = now or datetime.now(UTC)
    if record.status == "processing":
        if current_time - record.updated_at < PROCESSING_STALE_AFTER:
            raise RecoveryCommandNotReadyError(command_id)
        mark_command_result_unknown(command_id)
    elif record.status != "result_unknown":
        raise RecoveryCommandNotReadyError(command_id)

    try:
        order = gateway.get_order(platform_order_id=record.platform_order_id)
        if order is None:
            return []
        events = _events_from_venue(record, gateway, order)
    except (
        GatewayConfigurationError,
        GatewayQueryUnsupportedError,
        GatewayRequestRejectedError,
        GatewayResultUnknownError,
        TimeoutError,
    ):
        return []

    if not events:
        mark_command_result_unknown(command_id)
        return []
    save_command_events(record.command, events)
    return get_events(command_id)
