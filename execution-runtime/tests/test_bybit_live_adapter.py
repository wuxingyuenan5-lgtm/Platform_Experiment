from decimal import Decimal

import pytest

from app.bybit_live_adapter import BybitLiveAdapter
from app.config import Settings, get_settings
from app.gateway_errors import (
    GatewayConfigurationError,
    GatewayRequestRejectedError,
    GatewayResultUnknownError,
)
from app.journal import initialize_journal
from app.models import SubmitOrderCommand


class FakeBybitClient:
    def __init__(self) -> None:
        self.place_calls: list[dict[str, object]] = []

    def get_tickers(self, **kwargs):
        return {"retCode": 0, "result": {"list": [{"markPrice": "1000"}]}}

    def place_order(self, **kwargs):
        self.place_calls.append(kwargs)
        return {
            "retCode": 0,
            "result": {"orderId": "BYBIT-ORDER-1", "orderLinkId": kwargs["orderLinkId"]},
        }

    def get_open_orders(self, **kwargs):
        return {
            "retCode": 0,
            "result": {
                "list": [
                    {
                        "orderId": "BYBIT-ORDER-1",
                        "orderLinkId": kwargs.get("orderLinkId", ""),
                        "symbol": "XAUTUSDT",
                        "side": "Buy",
                        "orderType": "Market",
                        "qty": "1",
                        "price": "0",
                        "orderStatus": "New",
                        "cumExecQty": "0",
                        "avgPrice": "",
                        "createdTime": "1784800000000",
                        "updatedTime": "1784800001000",
                    }
                ]
            },
        }

    def get_order_history(self, **kwargs):
        return {"retCode": 0, "result": {"list": []}}

    def get_executions(self, **kwargs):
        return {
            "retCode": 0,
            "result": {
                "list": [
                    {
                        "execId": "EXEC-1",
                        "orderId": "BYBIT-ORDER-1",
                        "symbol": "XAUTUSDT",
                        "side": "Buy",
                        "execQty": "1",
                        "execPrice": "1001",
                        "execFee": "0.1",
                        "feeCurrency": "USDT",
                        "execTime": "1784800002000",
                    }
                ]
            },
        }

    def get_positions(self, **kwargs):
        return {
            "retCode": 0,
            "result": {
                "list": [
                    {
                        "symbol": "XAUTUSDT",
                        "side": "Buy",
                        "size": "1",
                        "avgPrice": "1001",
                        "updatedTime": "1784800003000",
                    }
                ]
            },
        }

    def get_wallet_balance(self, **kwargs):
        return {
            "retCode": 0,
            "result": {
                "list": [
                    {
                        "coin": [
                            {
                                "coin": "USDT",
                                "equity": "10000",
                                "walletBalance": "10000",
                                "availableToWithdraw": "9000",
                            }
                        ]
                    }
                ]
            },
        }

    def get_transaction_log(self, **kwargs):
        return {
            "retCode": 0,
            "result": {
                "list": [
                    {
                        "id": "TX-1",
                        "symbol": "XAUTUSDT",
                        "funding": "5",
                        "fee": "0.2",
                        "currency": "USDT",
                        "transactionTime": "1784800004000",
                    }
                ]
            },
        }

    def cancel_order(self, **kwargs):
        return {"retCode": 0, "result": {"orderId": kwargs["orderId"]}}


class FakeUnifiedBalanceClient(FakeBybitClient):
    def get_wallet_balance(self, **kwargs):
        return {
            "retCode": 0,
            "result": {
                "list": [
                    {
                        "totalAvailableBalance": "888.5",
                        "coin": [
                            {
                                "coin": "USDT",
                                "equity": "1000",
                                "walletBalance": "1000",
                                "availableToWithdraw": "",
                            }
                        ],
                    }
                ]
            },
        }


class ExplodingBybitClient(FakeBybitClient):
    def place_order(self, **kwargs):
        raise RuntimeError("timestamp outside venue tolerance")


class TracingBybitClient(FakeBybitClient):
    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = label
        self.calls: list[tuple[str, dict[str, object]]] = []

    def get_wallet_balance(self, **kwargs):
        self.calls.append(("get_wallet_balance", kwargs))
        return super().get_wallet_balance(**kwargs)

    def get_executions(self, **kwargs):
        self.calls.append(("get_executions", kwargs))
        return super().get_executions(**kwargs)


def runtime_settings(write_enabled: bool = True) -> Settings:
    return Settings(
        environment="live",
        live_write_enabled=write_enabled,
        live_account_allowlist="account-bybit",
        live_strategy_allowlist="strategy-live",
        live_symbol_allowlist="XAUTUSDT",
        live_max_order_notional="2000",
        live_max_daily_notional="5000",
        bybit_account_ids="account-bybit",
        bybit_instrument_map="XAUTUSDT=instrument-xaut",
        bybit_category="linear",
        bybit_settle_coin="USDT",
    )


def order_command(
    *,
    order_type: str = "market",
    execution_policy: str = "default",
    price: str | None = None,
) -> SubmitOrderCommand:
    return SubmitOrderCommand(
        command_id="command-bybit-1",
        platform_order_id="platform-order-bybit-1",
        strategy_instance_id="strategy-live",
        account_id="account-bybit",
        instrument_id="instrument-xaut",
        symbol="XAUTUSDT",
        side="buy",
        order_type=order_type,
        execution_policy=execution_policy,
        quantity="1",
        price=price,
    )


def test_bybit_live_adapter_is_readable_but_write_gated(tmp_path) -> None:
    get_settings().journal_path = str(tmp_path / "bybit-readonly.db")
    initialize_journal()
    adapter = BybitLiveAdapter(runtime_settings(write_enabled=False), FakeBybitClient())
    assert adapter.list_positions("account-bybit")[0].net_quantity == Decimal("1")
    assert adapter.list_balances("account-bybit")[0].equity == Decimal("10000")
    with pytest.raises(GatewayConfigurationError, match="live write gate is disabled"):
        adapter.submit_order(order_command())


def test_bybit_live_adapter_uses_unified_available_balance(tmp_path) -> None:
    get_settings().journal_path = str(tmp_path / "bybit-unified-balance.db")
    initialize_journal()
    adapter = BybitLiveAdapter(runtime_settings(write_enabled=False), FakeUnifiedBalanceClient())

    balance = adapter.list_balances("account-bybit")[0]

    assert balance.equity == Decimal("1000")
    assert balance.available_balance == Decimal("888.5")


def test_bybit_live_adapter_maps_order_fills_and_economic_events(tmp_path) -> None:
    get_settings().journal_path = str(tmp_path / "bybit-live.db")
    initialize_journal()
    client = FakeBybitClient()
    adapter = BybitLiveAdapter(runtime_settings(), client)

    events = adapter.submit_order(order_command())
    assert events[0].event_type == "order_acknowledged"
    assert events[0].external_order_id == "BYBIT-ORDER-1"
    assert len(client.place_calls) == 1
    assert client.place_calls[0]["orderLinkId"].startswith("VG")

    snapshot = adapter.get_order(platform_order_id="platform-order-bybit-1")
    assert snapshot is not None
    assert snapshot.account_id == "account-bybit"
    assert snapshot.status == "accepted"

    fills = adapter.list_fills(platform_order_id="platform-order-bybit-1")
    assert fills[0].external_fill_id == "EXEC-1"
    assert fills[0].instrument_id == "instrument-xaut"

    economic = adapter.list_economic_events(account_id="account-bybit")
    assert {(item.event_type, item.amount) for item in economic} == {
        ("funding", Decimal("5")),
        ("fee", Decimal("-0.2")),
    }

    canceled = adapter.cancel_order("BYBIT-ORDER-1", "cancel-key-1", "operator request")
    assert canceled.status == "canceled"


def test_bybit_live_adapter_sends_postonly_time_in_force_for_single_attempt(tmp_path) -> None:
    get_settings().journal_path = str(tmp_path / "bybit-single-postonly.db")
    initialize_journal()
    client = FakeBybitClient()
    adapter = BybitLiveAdapter(runtime_settings(), client)

    adapter.submit_order(
        order_command(
            order_type="limit",
            execution_policy="post_only_single_attempt",
            price="1000",
        )
    )

    assert client.place_calls[0]["timeInForce"] == "PostOnly"


def test_bybit_live_adapter_preserves_underlying_place_order_error(tmp_path) -> None:
    get_settings().journal_path = str(tmp_path / "bybit-place-order-error.db")
    initialize_journal()
    adapter = BybitLiveAdapter(runtime_settings(), ExplodingBybitClient())

    with pytest.raises(
        GatewayResultUnknownError,
        match="Bybit place_order result is unknown: RuntimeError: timestamp outside venue tolerance",
    ):
        adapter.submit_order(order_command())


def test_bybit_account_credential_mapping_isolated_with_legacy_fallback() -> None:
    settings = Settings(
        bybit_credential_ref="secret://environment/bybit-default",
        bybit_account_ids="account-funding,account-bottom",
        bybit_account_credential_refs=(
            "account-funding=secret://environment/bybit-funding,"
            "account-bottom=secret://environment/bybit-bottom"
        ),
    )

    assert settings.bybit_credential_for_account("account-funding") == "secret://environment/bybit-funding"
    assert settings.bybit_credential_for_account("account-bottom") == "secret://environment/bybit-bottom"
    assert settings.bybit_credential_for_account("legacy-account") == "secret://environment/bybit-default"


def test_bybit_read_only_account_rejects_submit_before_client_call(tmp_path) -> None:
    get_settings().journal_path = str(tmp_path / "bybit-read-only-account.db")
    initialize_journal()
    client = FakeBybitClient()
    settings = runtime_settings()
    settings.bybit_read_only_account_ids = "account-bybit"
    adapter = BybitLiveAdapter(settings, client)

    with pytest.raises(GatewayRequestRejectedError, match="configured read-only"):
        adapter.submit_order(order_command())
    assert client.place_calls == []


def test_bybit_live_adapter_routes_multi_account_reads_to_explicit_client(tmp_path) -> None:
    get_settings().journal_path = str(tmp_path / "bybit-multi-client.db")
    initialize_journal()

    class MultiClientAdapter(BybitLiveAdapter):
        def __init__(self, settings: Settings, clients: dict[str, TracingBybitClient]) -> None:
            super().__init__(settings, None)
            self._clients = clients

        def _client(self, account_id: str | None = None):
            if account_id is None:
                raise AssertionError("multi-account reads must pass account_id explicitly")
            return self._clients[account_id]

    funding_client = TracingBybitClient("funding")
    bottom_client = TracingBybitClient("bottom")
    adapter = MultiClientAdapter(
        Settings(
            environment="live",
            bybit_account_ids="bybit-live-main,account_bybit_bottom_fishing",
            bybit_account_credential_refs=(
                "bybit-live-main=secret://environment/bybit-live-001,"
                "account_bybit_bottom_fishing=secret://environment/bybit-bottom-fishing"
            ),
            bybit_instrument_map="XAUTUSDT=instrument-xaut",
            bybit_category="linear",
            bybit_settle_coin="USDT",
        ),
        {
            "bybit-live-main": funding_client,
            "account_bybit_bottom_fishing": bottom_client,
        },
    )

    balances = adapter.list_balances("bybit-live-main")
    fills = adapter.list_fills(account_id="account_bybit_bottom_fishing")

    assert balances[0].account_id == "bybit-live-main"
    assert fills[0].account_id == "account_bybit_bottom_fishing"
    assert {name for name, _ in funding_client.calls} == {"get_wallet_balance"}
    assert {name for name, _ in bottom_client.calls} == {"get_executions"}
