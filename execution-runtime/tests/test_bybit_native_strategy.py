from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.bybit_fill_confirming_adapter import BybitFillConfirmingAdapter
from app.bybit_native_strategy import (
    create_chase_order,
    get_strategy,
    list_strategy_orders,
    stop_strategy,
)
from app.gateway_errors import GatewayRequestRejectedError, GatewayResultUnknownError


class Client:
    def __init__(self, responses):
        self.endpoint = "https://api.bybit.com"
        self.responses = list(responses)
        self.calls = []

    def _submit_request(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_native_chase_uses_strategy_endpoint_and_returns_strategy_identity() -> None:
    client = Client([{"retCode": 0, "result": {"strategyId": "s-1"}}])
    assert (
        create_chase_order(
            client,
            category="UTA_USDT",
            symbol="xauusdt",
            side="Buy",
            size="1",
            reduce_only=False,
            max_chase_price="2500",
        )
        == "s-1"
    )
    assert client.calls[0]["path"] == "https://api.bybit.com/v5/strategy/create"
    assert client.calls[0]["query"]["strategyType"] == "chaseOrder"
    assert client.calls[0]["query"]["maxChasePrice"] == "2500"


def test_native_strategy_stop_and_list_use_strategy_id() -> None:
    client = Client(
        [
            {"retCode": 0, "result": {"strategyId": "s-1"}},
            {"retCode": 0, "result": {"list": [{"orderId": "o-1"}]}},
        ]
    )
    assert stop_strategy(client, "s-1") == "s-1"
    assert list_strategy_orders(client, strategy_id="s-1", symbol="BTCUSDT") == [{"orderId": "o-1"}]
    assert client.calls[0]["path"] == "https://api.bybit.com/v5/strategy/stop"
    assert client.calls[1]["path"] == "https://api.bybit.com/v5/strategy/order-list"


@pytest.mark.parametrize("code", [60062, 60074])
@pytest.mark.parametrize("sdk_exception", [False, True])
def test_stop_race_allows_reconciliation_without_retry(code, sdk_exception) -> None:
    from pybit.exceptions import InvalidRequestError

    response = (InvalidRequestError("", "already stopped", code, "", {})
                if sdk_exception else {"retCode": code, "retMsg": "already stopped"})
    client = Client([response])
    assert stop_strategy(client, "s-1") == "s-1"
    assert len(client.calls) == 1


def test_get_strategy_follows_pages_and_rejects_repeated_cursor() -> None:
    client = Client(
        [
            {"retCode": 0, "result": {"list": [{"strategyId": "other"}], "nextCursor": "c1"}},
            {"retCode": 0, "result": {"list": [{"strategyId": "s-1"}], "nextCursor": ""}},
        ]
    )
    assert get_strategy(client, "s-1") == {"strategyId": "s-1"}
    assert client.calls[1]["query"]["cursor"] == "c1"

    repeated = Client(
        [
            {"retCode": 0, "result": {"list": [], "nextCursor": "c1"}},
            {"retCode": 0, "result": {"list": [], "nextCursor": "c1"}},
        ]
    )
    with pytest.raises(GatewayResultUnknownError, match="repeated cursor"):
        get_strategy(repeated, "s-1")


@pytest.mark.parametrize("response", [TimeoutError("timeout"), {"retCode": 10001, "retMsg": "bad"}])
def test_native_strategy_failures_are_fail_closed(response) -> None:
    client = Client([response])
    with pytest.raises((GatewayResultUnknownError, GatewayRequestRejectedError)):
        stop_strategy(client, "s-1")


def test_cross_guard_uses_cross_bid_ask_direction_and_requires_native_freshness() -> None:
    adapter = object.__new__(BybitFillConfirmingAdapter)
    adapter.settings = SimpleNamespace(bybit_postonly_chase_event_timeout_seconds=2)
    adapter._command_category = lambda _: "linear"
    now = datetime.now(UTC)
    mt5 = SimpleNamespace(
        account_id="m",
        symbol="X",
        bid=Decimal("100"),
        ask=Decimal("101"),
        mid=Decimal("100.5"),
        source_as_of=now,
        as_of=now,
        raw_payload={
            "accountTradeAllowed": True,
            "accountExpertTradeAllowed": True,
            "pythonTradeAllowed": True,
            "symbolVisible": True,
            "terminalTradeAllowed": True,
            "tradeMode": 4,
        },
    )
    bybit = SimpleNamespace(
        account_id="b",
        raw_payload={},
        symbol="BTCUSDT",
        bid=Decimal("101"),
        ask=Decimal("102"),
        mid=Decimal("101.5"),
        source_as_of=now,
        as_of=now,
    )
    adapter.market_quote_reader = lambda **_: mt5
    adapter.get_market_quote = lambda **_: bybit
    command = SimpleNamespace(
        cross_spread_guard=SimpleNamespace(
            target_spread=Decimal("2"),
            max_adverse_spread=Decimal("1"),
            mt5_account_id="m",
            mt5_symbol="X",
            mt5_close=False,
            mt5_min_quantity=Decimal("0.1"),
            mt5_quantity_step=Decimal("0.1"),
            mt5_contract_multiplier=Decimal("1"),
        ),
        side="buy",
        account_id="b",
        symbol="BTCUSDT",
        instrument_type="crypto_perp",
    )
    assert adapter._cross_guard_allows(command)
    mt5.source_as_of = None
    assert not adapter._cross_guard_allows(command)
