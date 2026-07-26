from __future__ import annotations

import app.bybit_private_stream as private_stream
from app.config import Settings


class FakeDisconnectedWebSocket:
    def __init__(self) -> None:
        self.order_callback = None
        self.execution_callback = None
        self.closed = False

    def order_stream(self, callback) -> None:
        self.order_callback = callback

    def execution_stream(self, callback) -> None:
        self.execution_callback = callback

    def is_connected(self) -> bool:
        return False

    def exit(self) -> None:
        self.closed = True


def test_private_source_emits_disconnect_when_socket_is_unhealthy(monkeypatch) -> None:
    websocket = FakeDisconnectedWebSocket()
    monkeypatch.setattr(
        private_stream,
        "resolve_secret_reference",
        lambda *_args, **_kwargs: {"API_KEY": "test", "SECRET": "test"},
    )
    source = private_stream.BybitPrivateEventSource(
        Settings(bybit_postonly_chase_enabled=True),
        symbol="XAUTUSDT",
        order_link_prefix="VGP-CHASE",
        websocket_factory=lambda **_kwargs: websocket,
    )

    source.start()
    event = source.next_event(0.001)

    assert event is not None
    assert event.kind == "disconnect"
    assert event.reason == "Private stream disconnected"
    source.close()
    assert websocket.closed is True


def test_invalid_private_payload_marks_source_unhealthy(monkeypatch) -> None:
    websocket = FakeDisconnectedWebSocket()
    monkeypatch.setattr(
        private_stream,
        "resolve_secret_reference",
        lambda *_args, **_kwargs: {"API_KEY": "test", "SECRET": "test"},
    )
    source = private_stream.BybitPrivateEventSource(
        Settings(bybit_postonly_chase_enabled=True),
        symbol="XAUTUSDT",
        order_link_prefix="VGP-CHASE",
        websocket_factory=lambda **_kwargs: websocket,
    )

    source.start()
    assert websocket.order_callback is not None
    websocket.order_callback({"topic": "order", "data": "invalid"})
    event = source.next_event(0.001)

    assert event is not None
    assert event.kind == "disconnect"
    assert event.reason == "Private stream payload is invalid"
