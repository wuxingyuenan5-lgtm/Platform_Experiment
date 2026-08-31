from types import SimpleNamespace
from typing import Any, cast

from app.bybit_mt5_gateway import BybitMt5Gateway
from app.config import Settings


class RecordingAdapter:
    name = "mt5_live"

    def __init__(self) -> None:
        self.submitted_account_id = None
        self.canceled = False

    def submit_order(self, command):
        self.submitted_account_id = command.account_id
        return []

    def cancel_order(self, external_order_id, idempotency_key, reason):
        self.canceled = True
        return SimpleNamespace(status="canceled")


class UnusedBybitAdapter:
    name = "bybit_live"


def test_mt5_gateway_write_routes_to_bound_account_adapter() -> None:
    mt5 = RecordingAdapter()
    settings = Settings(mt5_account_ids="mt5-live-main")
    gateway = BybitMt5Gateway(
        settings=settings,
        bybit=cast(Any, UnusedBybitAdapter()),
        mt5=cast(Any, mt5),
    )
    gateway.submit_order(cast(Any, SimpleNamespace(account_id="mt5-live-main")))

    assert mt5.submitted_account_id == "mt5-live-main"


def test_mt5_gateway_cancel_routes_by_persisted_account(monkeypatch) -> None:
    mt5 = RecordingAdapter()
    settings = Settings(mt5_account_ids="mt5-live-main")
    gateway = BybitMt5Gateway(
        settings=settings,
        bybit=cast(Any, UnusedBybitAdapter()),
        mt5=cast(Any, mt5),
    )
    monkeypatch.setattr(
        "app.bybit_mt5_gateway.get_order_route",
        lambda external_order_id: SimpleNamespace(
            adapter="mt5_live", account_id="mt5-live-main"
        ),
    )

    response = gateway.cancel_order("123", "cancel-123", "test")

    assert response.status == "canceled"
    assert mt5.canceled is True
