from __future__ import annotations

from decimal import Decimal

import pytest

from app.bybit_fill_confirming_adapter import (
    CROSS_SPREAD_STRATEGY_INSTANCE_ID,
    BybitFillConfirmingAdapter,
)
from app.config import Settings, get_settings
from app.gateway_errors import GatewayResultUnknownError
from app.journal import initialize_journal
from app.models import SubmitOrderCommand
from app.strict_live_acceptance_adapters import StrictBybitAcceptanceAdapter


class FakeBybitConfirmationClient:
    def __init__(self, order_rows: list[dict[str, object]]) -> None:
        self.order_rows = order_rows
        self.query_index = 0
        self.place_calls: list[dict[str, object]] = []

    def get_tickers(self, **kwargs):
        return {"retCode": 0, "result": {"list": [{"markPrice": "1000"}]}}

    def place_order(self, **kwargs):
        self.place_calls.append(kwargs)
        return {
            "retCode": 0,
            "result": {"orderId": "BYBIT-ORDER-CONFIRM", "orderLinkId": kwargs["orderLinkId"]},
        }

    def get_open_orders(self, **kwargs):
        row = self.order_rows[min(self.query_index, len(self.order_rows) - 1)]
        self.query_index += 1
        return {"retCode": 0, "result": {"list": [row]}}

    def get_order_history(self, **kwargs):
        return {"retCode": 0, "result": {"list": []}}

    def get_instruments_info(self, **kwargs):
        return {
            "retCode": 0,
            "result": {
                "list": [
                    {
                        "symbol": "XAUTUSDT",
                        "status": "Trading",
                        "lotSizeFilter": {
                            "minOrderQty": "1",
                            "qtyStep": "1",
                            "maxMktOrderQty": "1000",
                        },
                    }
                ]
            },
        }

    def get_api_key_information(self):
        return {
            "retCode": 0,
            "result": {
                "readOnly": 0,
                "ips": ["127.0.0.1"],
                "permissions": {"ContractTrade": ["Order", "Position"]},
            },
        }

    def get_positions(self, **kwargs):
        return {"retCode": 0, "result": {"list": []}}


class ExplodingBybitConfirmationClient(FakeBybitConfirmationClient):
    def __init__(self) -> None:
        super().__init__([order_row("New", filled_quantity="0", average_price="")])

    def place_order(self, **kwargs):
        raise RuntimeError("position check timed out")


def runtime_settings() -> Settings:
    return Settings(
        environment="live",
        live_write_enabled=True,
        live_account_allowlist="account-bybit",
        live_strategy_allowlist=(
            f"strategy-live,{CROSS_SPREAD_STRATEGY_INSTANCE_ID}"
        ),
        live_symbol_allowlist="XAUTUSDT",
        live_max_order_notional="200000",
        live_max_daily_notional="500000",
        bybit_account_ids="account-bybit",
        bybit_instrument_map="XAUTUSDT=instrument-xaut",
        bybit_fill_confirmation_timeout_seconds=0.02,
        bybit_fill_confirmation_poll_seconds=0,
    )


def order_command(suffix: str) -> SubmitOrderCommand:
    return SubmitOrderCommand(
        command_id=f"command-bybit-confirm-{suffix}",
        platform_order_id=f"platform-order-bybit-confirm-{suffix}",
        strategy_instance_id="strategy-live",
        account_id="account-bybit",
        instrument_id="instrument-xaut",
        symbol="XAUTUSDT",
        side="buy",
        order_type="market",
        quantity="100",
    )


def fok_order_command(suffix: str) -> SubmitOrderCommand:
    return SubmitOrderCommand(
        command_id=f"command-bybit-fok-{suffix}",
        platform_order_id=f"platform-order-bybit-fok-{suffix}",
        strategy_instance_id=CROSS_SPREAD_STRATEGY_INSTANCE_ID,
        account_id="account-bybit",
        instrument_id="instrument-xaut",
        symbol="XAUTUSDT",
        side="buy",
        order_type="limit",
        quantity="100",
        price="1001.5",
    )


def single_postonly_attempt_command(suffix: str) -> SubmitOrderCommand:
    return SubmitOrderCommand(
        command_id=f"command-bybit-single-postonly-{suffix}",
        platform_order_id=f"platform-order-bybit-single-postonly-{suffix}",
        strategy_instance_id="strategy-live",
        account_id="account-bybit",
        instrument_id="instrument-xaut",
        symbol="XAUTUSDT",
        side="buy",
        order_type="limit",
        execution_policy="post_only_single_attempt",
        quantity="100",
        price="1001.5",
    )


def order_row(
    status: str,
    *,
    filled_quantity: str,
    average_price: str,
    order_type: str = "Market",
) -> dict[str, object]:
    return {
        "orderId": "BYBIT-ORDER-CONFIRM",
        "symbol": "XAUTUSDT",
        "side": "Buy",
        "orderType": order_type,
        "qty": "100",
        "price": "1001.5" if order_type == "Limit" else "0",
        "orderStatus": status,
        "cumExecQty": filled_quantity,
        "avgPrice": average_price,
        "createdTime": "1784800000000",
        "updatedTime": "1784800001000",
    }


def initialize_runtime_store(tmp_path, name: str) -> None:
    get_settings().journal_path = str(tmp_path / name)
    initialize_journal()


def test_market_order_emits_fill_only_after_confirmed_terminal_fill(tmp_path) -> None:
    initialize_runtime_store(tmp_path, "bybit-confirmed-fill.db")
    client = FakeBybitConfirmationClient(
        [
            order_row("New", filled_quantity="0", average_price=""),
            order_row("Filled", filled_quantity="100", average_price="1001.25"),
        ]
    )
    adapter = BybitFillConfirmingAdapter(runtime_settings(), client)

    events = adapter.submit_order(order_command("full"))

    assert [event.event_type for event in events] == ["order_acknowledged", "order_filled"]
    assert events[1].event_id == "BYBIT-FILL-BYBIT-ORDER-CONFIRM"
    assert events[1].fill_quantity == Decimal("100")
    assert events[1].fill_price == Decimal("1001.25")


def test_terminal_partial_fill_emits_only_confirmed_quantity(tmp_path) -> None:
    initialize_runtime_store(tmp_path, "bybit-terminal-partial.db")
    client = FakeBybitConfirmationClient(
        [order_row("Canceled", filled_quantity="40", average_price="1002")]
    )
    adapter = BybitFillConfirmingAdapter(runtime_settings(), client)

    events = adapter.submit_order(order_command("partial"))

    assert [event.event_type for event in events] == ["order_acknowledged", "order_filled"]
    assert events[1].fill_quantity == Decimal("40")
    assert events[1].reason is not None
    assert "terminal partial fill" in events[1].reason


def test_unresolved_market_order_times_out_without_a_fill_event(tmp_path) -> None:
    initialize_runtime_store(tmp_path, "bybit-confirm-timeout.db")
    client = FakeBybitConfirmationClient(
        [order_row("New", filled_quantity="0", average_price="")]
    )
    settings = runtime_settings()
    settings.bybit_fill_confirmation_timeout_seconds = 0
    adapter = BybitFillConfirmingAdapter(settings, client)

    events = adapter.submit_order(order_command("timeout"))

    assert [event.event_type for event in events] == ["order_acknowledged"]
    assert events[0].reason == "Bybit market-order fill confirmation timed out"


def test_cross_spread_limit_uses_fok_and_emits_only_full_fill(tmp_path) -> None:
    initialize_runtime_store(tmp_path, "bybit-fok-full.db")
    client = FakeBybitConfirmationClient(
        [order_row("Filled", filled_quantity="100", average_price="1001.4", order_type="Limit")]
    )
    adapter = BybitFillConfirmingAdapter(runtime_settings(), client)

    events = adapter.submit_order(fok_order_command("full"))

    assert client.place_calls[0]["timeInForce"] == "FOK"
    assert client.place_calls[0]["price"] == "1001.5"
    assert [event.event_type for event in events] == ["order_acknowledged", "order_filled"]
    assert events[1].fill_quantity == Decimal("100")


def test_single_postonly_attempt_uses_maker_tif_without_runtime_chase(tmp_path) -> None:
    initialize_runtime_store(tmp_path, "bybit-single-postonly-confirming.db")
    client = FakeBybitConfirmationClient(
        [order_row("New", filled_quantity="0", average_price="", order_type="Limit")]
    )
    adapter = BybitFillConfirmingAdapter(runtime_settings(), client)

    events = adapter.submit_order(single_postonly_attempt_command("funding"))

    assert client.place_calls[0]["timeInForce"] == "PostOnly"
    assert client.place_calls[0]["price"] == "1001.5"
    assert len(client.place_calls) == 1
    assert [event.event_type for event in events] == ["order_acknowledged"]


def test_strict_acceptance_path_preserves_postonly_single_attempt_without_runtime_chase(
    tmp_path,
) -> None:
    initialize_runtime_store(tmp_path, "bybit-single-postonly-strict.db")
    client = FakeBybitConfirmationClient(
        [order_row("New", filled_quantity="0", average_price="", order_type="Limit")]
    )
    adapter = StrictBybitAcceptanceAdapter(runtime_settings(), client)

    events = adapter.submit_order(single_postonly_attempt_command("strict"))

    assert client.place_calls[0]["timeInForce"] == "PostOnly"
    assert client.place_calls[0]["price"] == "1001.5"
    assert len(client.place_calls) == 1
    assert [event.event_type for event in events] == ["order_acknowledged"]


def test_cross_spread_fok_no_fill_rejects_without_fill_event(tmp_path) -> None:
    initialize_runtime_store(tmp_path, "bybit-fok-no-fill.db")
    client = FakeBybitConfirmationClient(
        [order_row("Canceled", filled_quantity="0", average_price="", order_type="Limit")]
    )
    adapter = BybitFillConfirmingAdapter(runtime_settings(), client)

    events = adapter.submit_order(fok_order_command("no-fill"))

    assert [event.event_type for event in events] == [
        "order_acknowledged",
        "order_rejected",
    ]
    assert events[1].reason == "Bybit FOK limit order was not filled"


def test_cross_spread_fok_partial_fill_never_emits_fill_event(tmp_path) -> None:
    initialize_runtime_store(tmp_path, "bybit-fok-partial.db")
    client = FakeBybitConfirmationClient(
        [order_row("Canceled", filled_quantity="40", average_price="1001.4", order_type="Limit")]
    )
    adapter = BybitFillConfirmingAdapter(runtime_settings(), client)

    events = adapter.submit_order(fok_order_command("partial"))

    assert [event.event_type for event in events] == ["order_acknowledged"]
    assert events[0].reason is not None
    assert "terminal partial fill" in events[0].reason
    assert "MT5 hedge was not submitted" in events[0].reason


def test_market_acknowledgement_preserves_underlying_place_order_error(tmp_path) -> None:
    initialize_runtime_store(tmp_path, "bybit-confirm-place-order-error.db")
    adapter = BybitFillConfirmingAdapter(runtime_settings(), ExplodingBybitConfirmationClient())

    with pytest.raises(
        GatewayResultUnknownError,
        match="Bybit place_order result is unknown: RuntimeError: position check timed out",
    ):
        adapter.submit_order(order_command("explode"))
