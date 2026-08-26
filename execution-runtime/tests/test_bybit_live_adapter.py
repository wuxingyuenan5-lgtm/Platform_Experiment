from decimal import Decimal

import pytest

from app.bybit_acceptance_adapter import BybitAcceptanceAdapter
from app.bybit_live_adapter import BybitLiveAdapter
from app.bybit_mt5_gateway import BybitMt5Gateway
from app.config import Settings, get_settings
from app.gateway_errors import (
    GatewayConfigurationError,
    GatewayRequestRejectedError,
    GatewayResultUnknownError,
)
from app.journal import initialize_journal
from app.models import InternalCapitalTransferStepCommand, SubmitOrderCommand


class FakeBybitClient:
    def __init__(self) -> None:
        self.place_calls: list[dict[str, object]] = []
        self.ticker_calls: list[dict[str, object]] = []
        self.instrument_calls: list[dict[str, object]] = []

    def get_tickers(self, **kwargs):
        self.ticker_calls.append(kwargs)
        return {
            "retCode": 0,
            "result": {
                "list": [
                    {
                        "markPrice": "1000",
                        "bid1Price": "999.5",
                        "ask1Price": "1000.5",
                        "lastPrice": "1000",
                        "fundingRate": "0.0001",
                        "nextFundingTime": "1784800004000",
                    }
                ]
            },
        }

    def get_instruments_info(self, **kwargs):
        self.instrument_calls.append(kwargs)
        return {
            "retCode": 0,
            "result": {
                "list": [
                    {
                        "symbol": kwargs["symbol"],
                        "status": "Trading",
                        "priceFilter": {"tickSize": "0.1"},
                        "lotSizeFilter": {
                            "minOrderQty": "0.001",
                            "qtyStep": "0.001",
                            "maxMktOrderQty": "10",
                        },
                    }
                ]
            },
        }

    def get_api_key_information(self, **kwargs):
        return {
            "retCode": 0,
            "result": {
                "readOnly": 0,
                "ips": ["127.0.0.1"],
                "permissions": {"ContractTrade": ["Order", "Position"]},
            },
        }

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


class FakeTradFiTransferClient(FakeBybitClient):
    def __init__(self, *, permission: bool = True, create_status: str = "SUCCESS") -> None:
        super().__init__()
        self.permission = permission
        self.create_status = create_status
        self.balance_calls: list[dict[str, object]] = []
        self.transfer_calls: list[dict[str, object]] = []
        self.records: dict[str, dict[str, object]] = {}

    def get_api_key_information(self, **kwargs):
        wallet = ["AccountTransfer"] if self.permission else []
        return {
            "retCode": 0,
            "result": {
                "readOnly": 0,
                "permissions": {"Wallet": wallet},
            },
        }

    def get_coin_balance(self, **kwargs):
        self.balance_calls.append(kwargs)
        return {
            "retCode": 0,
            "result": {"balance": {"transferBalance": "350.125"}},
        }

    def get_internal_transfer_records(self, **kwargs):
        row = self.records.get(str(kwargs["transferId"]))
        return {"retCode": 0, "result": {"list": [row] if row is not None else []}}

    def create_internal_transfer(self, **kwargs):
        self.transfer_calls.append(kwargs)
        row = {"transferId": kwargs["transferId"], "status": self.create_status}
        self.records[str(kwargs["transferId"])] = row
        return {"retCode": 0, "result": row}


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


def tradfi_settings(*, write_enabled: bool = True) -> Settings:
    return Settings(
        environment="live",
        live_write_enabled=write_enabled,
        live_account_allowlist="bybit-live-main,mt5-live-main",
        bybit_account_ids="bybit-live-main",
        mt5_account_ids="mt5-live-main",
        bybit_instrument_map="XAUTUSDT=instrument-xaut",
        tradfi_transfer_account_pairs="bybit-live-main=mt5-live-main",
    )


def transfer_command(
    *,
    direction: str = "bybit_to_mt5",
    key: str = "tradfi-transfer-1",
) -> InternalCapitalTransferStepCommand:
    bybit_to_mt5 = direction == "bybit_to_mt5"
    return InternalCapitalTransferStepCommand(
        idempotencyKey=key,
        sourceAccountId="bybit-live-main" if bybit_to_mt5 else "mt5-live-main",
        destinationAccountId="mt5-live-main" if bybit_to_mt5 else "bybit-live-main",
        sourceCurrency="USDT",
        destinationCurrency="USDT",
        amount="300",
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


def test_tradfi_transfer_readiness_requires_wallet_account_transfer_permission() -> None:
    client = FakeTradFiTransferClient(permission=False)
    gateway = BybitMt5Gateway(
        tradfi_settings(write_enabled=False),
        bybit=BybitLiveAdapter(tradfi_settings(write_enabled=False), client),
        mt5=object(),
    )

    readiness = gateway.get_internal_capital_transfer_readiness(
        source_account_id="bybit-live-main",
        destination_account_id="mt5-live-main",
        currency="USDT",
    )

    assert readiness.ready is False
    assert readiness.reason == "BYBIT_WALLET_ACCOUNT_TRANSFER_PERMISSION_REQUIRED"
    assert client.balance_calls == []


def test_tradfi_transfer_readiness_uses_explicit_account_mapping() -> None:
    client = FakeTradFiTransferClient()
    settings = tradfi_settings(write_enabled=False)
    gateway = BybitMt5Gateway(
        settings,
        bybit=BybitLiveAdapter(settings, client),
        mt5=object(),
    )

    forward = gateway.get_internal_capital_transfer_readiness(
        source_account_id="bybit-live-main",
        destination_account_id="mt5-live-main",
        currency="USDT",
    )
    reverse = gateway.get_internal_capital_transfer_readiness(
        source_account_id="mt5-live-main",
        destination_account_id="bybit-live-main",
        currency="USDT",
    )
    unmapped = gateway.get_internal_capital_transfer_readiness(
        source_account_id="bybit-live-main",
        destination_account_id="display-name-is-not-identity",
        currency="USDT",
    )

    assert forward.ready is True
    assert forward.transferable_balance == Decimal("350.125")
    assert forward.from_account_type == "UNIFIED"
    assert forward.to_account_type == "TradFi"
    assert reverse.ready is True
    assert reverse.from_account_type == "TradFi"
    assert reverse.to_account_type == "UNIFIED"
    assert unmapped.ready is False
    assert "explicitly mapped" in str(unmapped.reason)
    assert client.balance_calls == [
        {"accountType": "UNIFIED", "toAccountType": "TradFi", "coin": "USDT"},
        {"accountType": "TradFi", "toAccountType": "UNIFIED", "coin": "USDT"},
    ]


def test_tradfi_transfer_posts_once_and_replay_queries_same_identity() -> None:
    client = FakeTradFiTransferClient()
    settings = tradfi_settings()
    gateway = BybitMt5Gateway(
        settings,
        bybit=BybitLiveAdapter(settings, client),
        mt5=object(),
    )
    command = transfer_command()

    first = gateway.transfer_internal_capital(command)
    replay = gateway.transfer_internal_capital(command)

    assert first.status == replay.status == "completed"
    assert first.external_transfer_id == replay.external_transfer_id
    assert len(client.transfer_calls) == 1
    assert client.transfer_calls[0] == {
        "transferId": first.external_transfer_id,
        "coin": "USDT",
        "amount": "300",
        "fromAccountType": "UNIFIED",
        "toAccountType": "TradFi",
    }


def test_tradfi_pending_is_result_unknown_and_live_write_remains_gated() -> None:
    pending_client = FakeTradFiTransferClient(create_status="PENDING")
    settings = tradfi_settings()
    gateway = BybitMt5Gateway(
        settings,
        bybit=BybitLiveAdapter(settings, pending_client),
        mt5=object(),
    )

    result = gateway.transfer_internal_capital(transfer_command(key="pending-transfer"))

    assert result.status == "result_unknown"
    assert len(pending_client.transfer_calls) == 1
    pending_client.records[result.external_transfer_id]["status"] = "SUCCESS"
    reconciled = gateway.query_internal_capital_transfer(
        transfer_command(key="pending-transfer"),
        external_transfer_id=result.external_transfer_id,
    )
    assert reconciled.status == "completed"
    assert len(pending_client.transfer_calls) == 1

    blocked_settings = tradfi_settings(write_enabled=False)
    blocked_client = FakeTradFiTransferClient()
    blocked_gateway = BybitMt5Gateway(
        blocked_settings,
        bybit=BybitLiveAdapter(blocked_settings, blocked_client),
        mt5=object(),
    )
    with pytest.raises(GatewayConfigurationError, match="live write gate is disabled"):
        blocked_gateway.transfer_internal_capital(transfer_command(key="blocked-transfer"))
    assert blocked_client.transfer_calls == []


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


def test_bybit_live_adapter_quote_and_spec_use_explicit_category_scope(tmp_path) -> None:
    get_settings().journal_path = str(tmp_path / "bybit-explicit-scope.db")
    initialize_journal()
    client = FakeBybitClient()
    adapter = BybitLiveAdapter(
        Settings(
            environment="live",
            bybit_account_ids="bybit-live-main",
            bybit_account_category_scopes="bybit-live-main=spot|linear",
            bybit_instrument_map=(
                "BTCUSDT|SPOT=instrument_btc_spot,"
                "BTCUSDT|LINEAR=instrument_btc_perp"
            ),
            bybit_category="linear",
            bybit_settle_coin="USDT",
        ),
        client,
    )

    spot_quote = adapter.get_market_quote(
        account_id="bybit-live-main",
        symbol="BTCUSDT",
        instrument_type="crypto_spot",
        category="spot",
    )

    acceptance = BybitAcceptanceAdapter(adapter.settings, client)
    perp_spec = acceptance.get_instrument_specification(
        account_id="bybit-live-main",
        symbol="BTCUSDT",
        instrument_type="crypto_perp",
        category="linear",
    )

    assert spot_quote.category == "spot"
    assert spot_quote.instrument_type == "crypto_spot"
    assert spot_quote.funding_rate is None
    assert client.ticker_calls[-1]["category"] == "spot"
    assert perp_spec.category == "linear"
    assert perp_spec.instrument_type == "crypto_perp"
    assert perp_spec.price_tick == Decimal("0.1")
    assert perp_spec.contract_multiplier == Decimal("1")
    assert client.instrument_calls[-1]["category"] == "linear"
