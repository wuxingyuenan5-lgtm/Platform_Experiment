from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any, cast

from app.bybit_mt5_gateway import BybitMt5Gateway
from app.config import Settings


class RecordingCoordinator:
    def __init__(self) -> None:
        self.locked = False
        self.health_checks = 0

    @contextmanager
    def acquire(self):
        self.locked = True
        try:
            yield
        finally:
            self.locked = False

    def assert_healthy(self) -> None:
        self.health_checks += 1


class RecordingAdapter:
    name = "mt5_live"

    def __init__(self, coordinator: RecordingCoordinator) -> None:
        self.coordinator = coordinator
        self.submitted_while_locked = False
        self.canceled_while_locked = False

    def submit_order(self, command):
        self.submitted_while_locked = self.coordinator.locked
        return []

    def cancel_order(self, external_order_id, idempotency_key, reason):
        self.canceled_while_locked = self.coordinator.locked
        return SimpleNamespace(status="canceled")


class UnusedBybitAdapter:
    name = "bybit_live"


def test_mt5_gateway_write_uses_snapshot_session_coordinator(monkeypatch) -> None:
    coordinator = RecordingCoordinator()
    mt5 = RecordingAdapter(coordinator)
    settings = Settings(mt5_account_ids="mt5-live-main")
    gateway = BybitMt5Gateway(
        settings=settings,
        bybit=cast(Any, UnusedBybitAdapter()),
        mt5=cast(Any, mt5),
    )
    monkeypatch.setattr("app.bybit_mt5_gateway.COORDINATOR", coordinator)

    gateway.submit_order(cast(Any, SimpleNamespace(account_id="mt5-live-main")))

    assert mt5.submitted_while_locked is True
    assert coordinator.health_checks == 1


def test_mt5_gateway_cancel_uses_snapshot_session_coordinator(monkeypatch) -> None:
    coordinator = RecordingCoordinator()
    mt5 = RecordingAdapter(coordinator)
    settings = Settings(mt5_account_ids="mt5-live-main")
    gateway = BybitMt5Gateway(
        settings=settings,
        bybit=cast(Any, UnusedBybitAdapter()),
        mt5=cast(Any, mt5),
    )
    monkeypatch.setattr("app.bybit_mt5_gateway.COORDINATOR", coordinator)
    monkeypatch.setattr(
        "app.bybit_mt5_gateway.get_order_route",
        lambda external_order_id: SimpleNamespace(adapter="mt5_live"),
    )

    response = gateway.cancel_order("123", "cancel-123", "test")

    assert response.status == "canceled"
    assert mt5.canceled_while_locked is True
    assert coordinator.health_checks == 1
