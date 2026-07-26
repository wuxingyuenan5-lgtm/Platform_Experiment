from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from queue import Empty, Queue
from threading import Lock
from typing import Any, Protocol

from app.bybit_postonly_chase import PrivateChaseEvent
from app.config import Settings
from app.secret_resolver import resolve_secret_reference


class PrivateEventSource(Protocol):
    def start(self) -> None: ...

    def next_event(self, timeout_seconds: float) -> PrivateChaseEvent | None: ...

    def close(self) -> None: ...


class BybitPrivateEventParser:
    def __init__(self, *, symbol: str, order_link_prefix: str) -> None:
        if not order_link_prefix:
            raise ValueError("Bybit private stream Order Link prefix is required")
        self.symbol = symbol.upper()
        self.order_link_prefix = order_link_prefix
        self._sequence = 0
        self._lock = Lock()

    def parse(self, message: dict[str, object]) -> list[PrivateChaseEvent]:
        topic = str(message.get("topic") or "")
        rows = message.get("data")
        if not isinstance(rows, list):
            raise ValueError("Bybit private stream payload has no data list")
        events: list[PrivateChaseEvent] = []
        for raw in rows:
            if not isinstance(raw, dict):
                raise ValueError("Bybit private stream row is invalid")
            row = {str(key): value for key, value in raw.items()}
            if str(row.get("symbol") or "").upper() != self.symbol:
                continue
            order_link_id = str(row.get("orderLinkId") or "")
            if not order_link_id.startswith(self.order_link_prefix):
                continue
            if topic == "execution":
                events.append(self._execution_event(row))
            elif topic == "order":
                events.append(self._order_event(row))
        return events

    def disconnect_event(self, reason: str) -> PrivateChaseEvent:
        return PrivateChaseEvent(
            event_id=f"disconnect:{self._next_sequence()}",
            sequence=self._sequence,
            occurred_at=datetime.now(UTC),
            kind="disconnect",
            reason=reason,
        )

    def _execution_event(self, row: dict[str, object]) -> PrivateChaseEvent:
        external_order_id = str(row.get("orderId") or "")
        execution_id = str(row.get("execId") or "")
        if not external_order_id or not execution_id:
            raise ValueError("Bybit private execution identity is missing")
        sequence = self._next_sequence()
        return PrivateChaseEvent(
            event_id=f"execution:{execution_id}",
            sequence=sequence,
            occurred_at=_millis(row.get("execTime")),
            kind="execution",
            external_order_id=external_order_id,
            execution_quantity=_positive_decimal(row.get("execQty"), "execution quantity"),
            execution_price=_positive_decimal(row.get("execPrice"), "execution price"),
        )

    def _order_event(self, row: dict[str, object]) -> PrivateChaseEvent:
        external_order_id = str(row.get("orderId") or "")
        raw_status = str(row.get("orderStatus") or "")
        status = _ORDER_STATUS_MAP.get(raw_status)
        if not external_order_id or status is None:
            raise ValueError("Bybit private order identity or status is invalid")
        updated_time = str(row.get("updatedTime") or row.get("createdTime") or "0")
        sequence = self._next_sequence()
        event_id = ":".join(
            (
                "order",
                external_order_id,
                raw_status,
                updated_time,
                str(row.get("cumExecQty") or "0"),
            )
        )
        return PrivateChaseEvent(
            event_id=event_id,
            sequence=sequence,
            occurred_at=_millis(updated_time),
            kind="order",
            external_order_id=external_order_id,
            order_status=status,
            reason=str(row.get("rejectReason") or row.get("cancelType") or "") or None,
        )

    def _next_sequence(self) -> int:
        with self._lock:
            self._sequence += 1
            return self._sequence


class BybitPrivateEventSource:
    def __init__(
        self,
        settings: Settings,
        *,
        symbol: str,
        order_link_prefix: str,
        websocket_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.settings = settings
        self.parser = BybitPrivateEventParser(
            symbol=symbol,
            order_link_prefix=order_link_prefix,
        )
        self._queue: Queue[PrivateChaseEvent] = Queue()
        self._websocket_factory = websocket_factory
        self._websocket: Any | None = None
        self._closed = False
        self._healthy = False

    def start(self) -> None:
        if not self.settings.bybit_postonly_chase_enabled:
            raise ValueError("Bybit PostOnly Chase private stream is disabled")
        if self._websocket is not None:
            return
        factory = self._websocket_factory or _default_websocket_factory
        secret = resolve_secret_reference(
            self.settings.bybit_credential_ref,
            required_fields=("API_KEY", "SECRET"),
        )
        try:
            websocket = factory(
                testnet=False,
                demo=self.settings.bybit_demo_mode,
                channel_type="private",
                api_key=secret["API_KEY"],
                api_secret=secret["SECRET"],
            )
            websocket.order_stream(self._handle_message)
            websocket.execution_stream(self._handle_message)
        except Exception as exc:
            self._healthy = False
            self._queue.put(self.parser.disconnect_event("Private stream startup failed"))
            raise RuntimeError("Bybit private stream startup failed") from exc
        self._websocket = websocket
        self._healthy = True

    def next_event(self, timeout_seconds: float) -> PrivateChaseEvent | None:
        if timeout_seconds <= 0:
            raise ValueError("Private event timeout must be positive")
        try:
            return self._queue.get(timeout=timeout_seconds)
        except Empty:
            if not self._connection_is_healthy():
                self._healthy = False
                return self.parser.disconnect_event("Private stream disconnected")
            return None

    def close(self) -> None:
        self._closed = True
        self._healthy = False
        websocket = self._websocket
        self._websocket = None
        if websocket is not None and hasattr(websocket, "exit"):
            websocket.exit()

    def _handle_message(self, message: dict[str, object]) -> None:
        if self._closed:
            return
        try:
            events = self.parser.parse(message)
        except Exception:
            self._healthy = False
            self._queue.put(self.parser.disconnect_event("Private stream payload is invalid"))
            return
        for event in events:
            self._queue.put(event)

    def _connection_is_healthy(self) -> bool:
        if self._closed or not self._healthy or self._websocket is None:
            return False
        checker = getattr(self._websocket, "is_connected", None)
        if callable(checker):
            try:
                return bool(checker())
            except Exception:
                return False
        manager = getattr(self._websocket, "ws", None)
        socket = getattr(manager, "sock", None)
        connected = getattr(socket, "connected", None)
        if connected is not None:
            return bool(connected)
        return True


def _default_websocket_factory(**kwargs: object) -> Any:
    try:
        from pybit.unified_trading import WebSocket
    except ImportError as exc:
        raise RuntimeError("Bybit private stream requires the optional pybit dependency") from exc
    return WebSocket(**kwargs)


def _positive_decimal(value: object, label: str) -> Decimal:
    result = Decimal(str(value or "0"))
    if result <= 0:
        raise ValueError(f"Bybit private {label} must be positive")
    return result


def _millis(value: object) -> datetime:
    timestamp = Decimal(str(value or "0"))
    if timestamp <= 0:
        return datetime.now(UTC)
    return datetime.fromtimestamp(float(timestamp / Decimal("1000")), tz=UTC)


_ORDER_STATUS_MAP = {
    "New": "new",
    "PartiallyFilled": "partially_filled",
    "Filled": "filled",
    "PendingCancel": "cancel_pending",
    "Cancelled": "canceled",
    "Canceled": "canceled",
    "Rejected": "rejected",
}
