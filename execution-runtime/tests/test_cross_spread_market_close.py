from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.bybit_fill_confirming_adapter import BybitFillConfirmingAdapter
from app.config import Settings, get_settings
from app.gateway_errors import GatewayRequestRejectedError
from app.journal import initialize_journal
from app.models import SubmitOrderCommand
from app.mt5_position_closing_adapter import Mt5PositionClosingAdapter


class FakeBybitCloseClient:
    def __init__(self, positions: list[dict[str, object]]) -> None:
        self.positions = positions
        self.place_calls: list[dict[str, object]] = []

    def get_tickers(self, **kwargs):
        return {"retCode": 0, "result": {"list": [{"markPrice": "1000"}]}}

    def get_positions(self, **kwargs):
        return {"retCode": 0, "result": {"list": self.positions}}

    def place_order(self, **kwargs):
        self.place_calls.append(kwargs)
        return {"retCode": 0, "result": {"orderId": "BYBIT-CLOSE-1"}}

    def get_open_orders(self, **kwargs):
        return {
            "retCode": 0,
            "result": {
                "list": [
                    {
                        "orderId": "BYBIT-CLOSE-1",
                        "symbol": "XAUTUSDT",
                        "side": "Sell",
                        "orderType": "Market",
                        "qty": "40",
                        "price": "0",
                        "orderStatus": "Filled",
                        "cumExecQty": "40",
                        "avgPrice": "1001",
                        "createdTime": "1784800000000",
                        "updatedTime": "1784800001000",
                    }
                ]
            },
        }

    def get_order_history(self, **kwargs):
        return {"retCode": 0, "result": {"list": []}}


def runtime_settings() -> Settings:
    return Settings(
        environment="live",
        live_write_enabled=True,
        live_account_allowlist="account-bybit,account-mt5",
        live_strategy_allowlist="strategy-live",
        live_symbol_allowlist="XAUTUSDT,XAUUSD+",
        live_max_order_notional="200000",
        live_max_daily_notional="500000",
        bybit_account_ids="account-bybit",
        bybit_instrument_map="XAUTUSDT=instrument-xaut",
        bybit_fill_confirmation_timeout_seconds=0.02,
        bybit_fill_confirmation_poll_seconds=0,
        mt5_account_ids="account-mt5",
        mt5_instrument_map="XAUUSD+=instrument-xauusd",
    )


def initialize_runtime_store(tmp_path, name: str) -> None:
    get_settings().journal_path = str(tmp_path / name)
    initialize_journal()


def close_command(
    *,
    side: str,
    quantity: str,
    position_id: str | None = None,
) -> SubmitOrderCommand:
    return SubmitOrderCommand(
        command_id=f"command-{side}-{quantity}",
        platform_order_id=f"platform-{side}-{quantity}",
        strategy_instance_id="strategy-live",
        account_id="account-bybit",
        instrument_id="instrument-xaut",
        symbol="XAUTUSDT",
        side=side,
        order_type="market",
        quantity=quantity,
        reduce_only=True,
        position_id=position_id,
    )


def test_bybit_close_sets_reduce_only_and_matching_position_idx(tmp_path) -> None:
    initialize_runtime_store(tmp_path, "bybit-close.db")
    client = FakeBybitCloseClient(
        [{"symbol": "XAUTUSDT", "side": "Buy", "size": "100", "positionIdx": 1}]
    )
    adapter = BybitFillConfirmingAdapter(runtime_settings(), client)

    events = adapter.submit_order(close_command(side="sell", quantity="40"))

    assert [event.event_type for event in events] == ["order_acknowledged", "order_filled"]
    assert client.place_calls[0]["reduceOnly"] is True
    assert client.place_calls[0]["positionIdx"] == 1


def test_bybit_close_rejects_wrong_side_or_oversized_position(tmp_path) -> None:
    initialize_runtime_store(tmp_path, "bybit-close-rejected.db")
    wrong_side = BybitFillConfirmingAdapter(
        runtime_settings(),
        FakeBybitCloseClient(
            [{"symbol": "XAUTUSDT", "side": "Sell", "size": "100", "positionIdx": 2}]
        ),
    )
    with pytest.raises(GatewayRequestRejectedError, match="exactly one matching"):
        wrong_side.submit_order(close_command(side="sell", quantity="40"))

    oversized = BybitFillConfirmingAdapter(
        runtime_settings(),
        FakeBybitCloseClient(
            [{"symbol": "XAUTUSDT", "side": "Buy", "size": "20", "positionIdx": 1}]
        ),
    )
    with pytest.raises(GatewayRequestRejectedError, match="exceeds"):
        oversized.submit_order(close_command(side="sell", quantity="40"))


class FakeMt5:
    TRADE_ACTION_DEAL = 1
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TIME_GTC = 0
    ORDER_FILLING_IOC = 1
    POSITION_TYPE_SELL = 1

    def __init__(self, position) -> None:
        self.position = position

    def positions_get(self, *, ticket: int):
        if ticket != int(self.position.ticket):
            return ()
        return (self.position,)


def mt5_command(*, side: str, quantity: str, position_id: str) -> SubmitOrderCommand:
    return SubmitOrderCommand(
        command_id=f"mt5-command-{side}-{quantity}",
        platform_order_id=f"mt5-platform-{side}-{quantity}",
        strategy_instance_id="strategy-live",
        account_id="account-mt5",
        instrument_id="instrument-xauusd",
        symbol="XAUUSD+",
        side=side,
        order_type="market",
        quantity=quantity,
        reduce_only=True,
        position_id=position_id,
    )


def test_mt5_close_binds_position_ticket_and_rejects_reverse_or_oversized() -> None:
    position = SimpleNamespace(ticket=778899, symbol="XAUUSD+", type=1, volume=Decimal("1"))
    mt5 = FakeMt5(position)
    adapter = Mt5PositionClosingAdapter(runtime_settings(), provider=mt5)

    request = adapter._build_order_request(
        mt5,
        mt5_command(side="buy", quantity="0.4", position_id="778899"),
        Decimal("2500"),
        "close-test",
    )
    assert request["position"] == 778899
    assert request["type"] == mt5.ORDER_TYPE_BUY

    with pytest.raises(GatewayRequestRejectedError, match="would not close"):
        adapter._build_order_request(
            mt5,
            mt5_command(side="sell", quantity="0.4", position_id="778899"),
            Decimal("2500"),
            "close-test",
        )

    with pytest.raises(GatewayRequestRejectedError, match="exceeds"):
        adapter._build_order_request(
            mt5,
            mt5_command(side="buy", quantity="1.1", position_id="778899"),
            Decimal("2500"),
            "close-test",
        )
