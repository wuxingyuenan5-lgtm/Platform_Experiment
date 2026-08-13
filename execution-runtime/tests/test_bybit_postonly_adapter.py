from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.bybit_fill_confirming_adapter import (
    CROSS_SPREAD_STRATEGY_INSTANCE_ID,
    BybitFillConfirmingAdapter,
)
from app.bybit_postonly_chase import PrivateChaseEvent
from app.config import Settings, get_settings
from app.gateway_errors import GatewayRequestRejectedError
from app.journal import initialize_journal
from app.models import SubmitOrderCommand

NOW = datetime(2026, 7, 26, tzinfo=UTC)


class FakePrivateSource:
    def __init__(self, events: list[PrivateChaseEvent | None]) -> None:
        self.events = list(events)
        self.started = False
        self.closed = False
        self.timeouts: list[float] = []

    def start(self) -> None:
        self.started = True

    def next_event(self, timeout_seconds: float) -> PrivateChaseEvent | None:
        assert timeout_seconds > 0
        self.timeouts.append(timeout_seconds)
        return self.events.pop(0) if self.events else None

    def close(self) -> None:
        self.closed = True


class FakePostOnlyClient:
    def __init__(self, *, terminal_row: dict[str, object] | None = None) -> None:
        self.place_calls: list[dict[str, object]] = []
        self.amend_calls: list[dict[str, object]] = []
        self.cancel_calls: list[dict[str, object]] = []
        self.ticker_calls = 0
        self.terminal_row = terminal_row

    def get_tickers(self, **kwargs):
        self.ticker_calls += 1
        return {
            "retCode": 0,
            "result": {
                "list": [
                    {
                        "bid1Price": "2500.0",
                        "ask1Price": "2500.1",
                        "markPrice": "2500.05",
                    }
                ]
            },
        }

    def get_instruments_info(self, **kwargs):
        return {
            "retCode": 0,
            "result": {"list": [{"priceFilter": {"tickSize": "0.1"}}]},
        }

    def place_order(self, **kwargs):
        self.place_calls.append(kwargs)
        index = len(self.place_calls)
        return {
            "retCode": 0,
            "result": {
                "orderId": f"POSTONLY-{index}",
                "orderLinkId": kwargs["orderLinkId"],
            },
        }

    def amend_order(self, **kwargs):
        self.amend_calls.append(kwargs)
        return {"retCode": 0, "result": {}}

    def cancel_order(self, **kwargs):
        self.cancel_calls.append(kwargs)
        return {"retCode": 0, "result": {}}

    def get_open_orders(self, **kwargs):
        if self.terminal_row is None:
            return {"retCode": 0, "result": {"list": []}}
        return {"retCode": 0, "result": {"list": [self.terminal_row]}}

    def get_order_history(self, **kwargs):
        if self.terminal_row is None:
            return {"retCode": 0, "result": {"list": []}}
        return {"retCode": 0, "result": {"list": [self.terminal_row]}}


def runtime_settings(*, enabled: bool = True) -> Settings:
    return Settings(
        _env_file=None,
        environment="live",
        live_write_enabled=True,
        live_account_allowlist="account-bybit",
        live_strategy_allowlist=CROSS_SPREAD_STRATEGY_INSTANCE_ID,
        live_symbol_allowlist="XAUTUSDT",
        live_max_order_notional="200000",
        live_max_daily_notional="500000",
        bybit_account_ids="account-bybit",
        bybit_instrument_map="XAUTUSDT=instrument-xaut",
        bybit_postonly_chase_enabled=enabled,
        bybit_postonly_chase_ttl_seconds=1,
        bybit_postonly_chase_min_amend_ticks=2,
        bybit_postonly_chase_max_mutations=2,
        bybit_postonly_chase_rest_reconcile_seconds=0.001,
    )


def command(suffix: str) -> SubmitOrderCommand:
    return SubmitOrderCommand(
        command_id=f"command-postonly-{suffix}",
        platform_order_id=f"platform-postonly-{suffix}",
        strategy_instance_id=CROSS_SPREAD_STRATEGY_INSTANCE_ID,
        account_id="account-bybit",
        instrument_id="instrument-xaut",
        symbol="XAUTUSDT",
        side="buy",
        order_type="limit",
        execution_policy="post_only_chase",
        quantity="1",
        price="2500.5",
    )


def initialize_runtime_store(tmp_path, name: str) -> None:
    get_settings().journal_path = str(tmp_path / name)
    initialize_journal()


def test_postonly_disabled_rejects_before_place(tmp_path) -> None:
    initialize_runtime_store(tmp_path, "postonly-disabled.db")
    client = FakePostOnlyClient()
    source = FakePrivateSource([])
    adapter = BybitFillConfirmingAdapter(
        runtime_settings(enabled=False),
        client,
        private_source_factory=lambda _symbol, _prefix: source,
    )

    with pytest.raises(GatewayRequestRejectedError, match="disabled"):
        adapter.submit_order(command("disabled"))

    assert client.place_calls == []
    assert source.started is False


def test_postonly_adapter_reevaluates_quotes_at_configured_cadence(tmp_path) -> None:
    initialize_runtime_store(tmp_path, "postonly-cadence.db")
    source = FakePrivateSource(
        [
            None,
            PrivateChaseEvent(
                event_id="disconnect-after-reevaluation",
                sequence=1,
                occurred_at=NOW,
                kind="disconnect",
            ),
        ]
    )
    client = FakePostOnlyClient()
    settings = runtime_settings()
    adapter = BybitFillConfirmingAdapter(
        settings,
        client,
        private_source_factory=lambda _symbol, _prefix: source,
    )

    events = adapter.submit_order(command("cadence"))

    assert source.timeouts == [1.0, 1.0]
    assert client.ticker_calls == 2
    assert settings.bybit_postonly_chase_cooldown_seconds == 1.0
    assert [event.event_type for event in events] == ["order_acknowledged"]


def test_postonly_exact_full_fill_emits_one_fill(tmp_path) -> None:
    initialize_runtime_store(tmp_path, "postonly-full.db")
    source = FakePrivateSource(
        [
            PrivateChaseEvent(
                event_id="order-new",
                sequence=1,
                occurred_at=NOW,
                kind="order",
                external_order_id="POSTONLY-1",
                order_status="new",
            ),
            PrivateChaseEvent(
                event_id="execution:EXEC-1",
                sequence=2,
                occurred_at=NOW,
                kind="execution",
                external_order_id="POSTONLY-1",
                execution_quantity=Decimal("1"),
                execution_price=Decimal("2500"),
            ),
        ]
    )
    client = FakePostOnlyClient()
    adapter = BybitFillConfirmingAdapter(
        runtime_settings(),
        client,
        private_source_factory=lambda _symbol, _prefix: source,
    )

    events = adapter.submit_order(command("full"))

    assert client.place_calls[0]["timeInForce"] == "PostOnly"
    assert client.place_calls[0]["price"] == "2500.0"
    assert [event.event_type for event in events] == [
        "order_acknowledged",
        "order_filled",
    ]
    assert events[1].fill_quantity == Decimal("1")
    assert events[1].fill_price == Decimal("2500")
    assert source.closed is True


def test_duplicate_partial_execution_does_not_duplicate_total(tmp_path) -> None:
    initialize_runtime_store(tmp_path, "postonly-duplicate.db")
    duplicate = PrivateChaseEvent(
        event_id="execution:EXEC-1",
        sequence=1,
        occurred_at=NOW,
        kind="execution",
        external_order_id="POSTONLY-1",
        execution_quantity=Decimal("0.4"),
        execution_price=Decimal("2500"),
    )
    source = FakePrivateSource(
        [
            duplicate,
            duplicate,
            PrivateChaseEvent(
                event_id="execution:EXEC-2",
                sequence=2,
                occurred_at=NOW,
                kind="execution",
                external_order_id="POSTONLY-1",
                execution_quantity=Decimal("0.6"),
                execution_price=Decimal("2500.2"),
            ),
        ]
    )
    adapter = BybitFillConfirmingAdapter(
        runtime_settings(),
        FakePostOnlyClient(),
        private_source_factory=lambda _symbol, _prefix: source,
    )

    events = adapter.submit_order(command("duplicate"))

    assert [event.event_type for event in events] == [
        "order_acknowledged",
        "order_filled",
    ]
    assert events[1].fill_quantity == Decimal("1.0")
    assert events[1].fill_price == Decimal("2500.12")


def test_partial_fill_then_cancel_never_emits_fill(tmp_path) -> None:
    initialize_runtime_store(tmp_path, "postonly-partial-cancel.db")
    source = FakePrivateSource(
        [
            PrivateChaseEvent(
                event_id="execution:EXEC-PARTIAL",
                sequence=1,
                occurred_at=NOW,
                kind="execution",
                external_order_id="POSTONLY-1",
                execution_quantity=Decimal("0.4"),
                execution_price=Decimal("2500"),
            ),
            PrivateChaseEvent(
                event_id="order-canceled",
                sequence=2,
                occurred_at=NOW,
                kind="order",
                external_order_id="POSTONLY-1",
                order_status="canceled",
            ),
        ]
    )
    terminal = {
        "orderId": "POSTONLY-1",
        "symbol": "XAUTUSDT",
        "side": "Buy",
        "orderType": "Limit",
        "qty": "1",
        "price": "2500",
        "orderStatus": "Cancelled",
        "cumExecQty": "0.4",
        "avgPrice": "2500",
        "createdTime": "1785000000000",
        "updatedTime": "1785000001000",
    }
    adapter = BybitFillConfirmingAdapter(
        runtime_settings(),
        FakePostOnlyClient(terminal_row=terminal),
        private_source_factory=lambda _symbol, _prefix: source,
    )

    events = adapter.submit_order(command("partial-cancel"))

    assert [event.event_type for event in events] == ["order_acknowledged"]
    assert events[0].reason is not None
    assert "MT5 was not submitted" in events[0].reason
    assert "0.4" in events[0].reason
