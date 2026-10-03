from decimal import Decimal

import pytest

from app.bybit_mt5_gateway import BybitMt5Gateway
from app.config import Settings, get_settings
from app.gateway_errors import GatewayConfigurationError, GatewayRequestRejectedError
from app.journal import initialize_journal, save_command_started
from app.live_route_store import record_order_route
from app.models import SubmitOrderCommand
from app.strict_live_acceptance_adapters import StrictBybitAcceptanceAdapter


class MarketClient:
    def __init__(self):
        self.calls = []
        self.orders = {}
        self.spot_permission = True

    def get_api_key_information(self):
        return {
            "retCode": 0,
            "result": {
                "readOnly": 0,
                "ips": ["203.0.113.1"],
                "permissions": {
                    "ContractTrade": ["Order", "Position"],
                    "Spot": ["SpotTrade"] if self.spot_permission else [],
                },
            },
        }

    def get_instruments_info(self, **query):
        self.calls.append(("spec", query))
        spot = query["category"] == "spot"
        return {
            "retCode": 0,
            "result": {
                "category": query["category"],
                "list": [
                    {
                        "symbol": "BTCUSDT",
                        "status": "Trading",
                        "baseCoin": "BTC",
                        "quoteCoin": "USDT",
                        "settleCoin": "USDT",
                        "contractType": "LinearPerpetual",
                        "priceFilter": {"tickSize": "0.1"},
                        "lotSizeFilter": {
                            "basePrecision": "0.000001",
                            "quotePrecision": "0.1",
                            "qtyStep": "0.001",
                            "minOrderQty": "0.000001" if spot else "0.001",
                            "maxMktOrderQty": "100",
                            "minOrderAmt": "1",
                        },
                    }
                ],
            },
        }

    def get_tickers(self, **query):
        self.calls.append(("quote", query))
        return {"retCode": 0, "result": {"list": [{"lastPrice": "79000"}]}}

    def place_order(self, **payload):
        self.calls.append(("place", payload))
        order_id = f"{payload['category']}-{payload['side']}"
        self.orders[order_id] = payload
        return {"retCode": 0, "result": {"orderId": order_id}}

    def get_open_orders(self, **query):
        self.calls.append(("order", query))
        order_id = query["orderId"]
        order = self.orders.get(order_id)
        if not order or order["category"] != query["category"]:
            return {"retCode": 0, "result": {"list": []}}
        return {
            "retCode": 0,
            "result": {
                "list": [
                    {
                        **order,
                        "orderId": order_id,
                        "orderStatus": "Filled",
                        "cumExecQty": order["qty"],
                        "avgPrice": "79000",
                        "createdTime": "1784800000000",
                        "updatedTime": "1784800001000",
                    }
                ]
            },
        }

    def get_order_history(self, **query):
        return self.get_open_orders(**query)

    def get_executions(self, **query):
        self.calls.append(("fills", query))
        order_id = query["orderId"]
        order = self.orders[order_id]
        assert order["category"] == query["category"]
        return {
            "retCode": 0,
            "result": {
                "list": [
                    {
                        "execId": f"fill-{order_id}",
                        "orderId": order_id,
                        "symbol": "BTCUSDT",
                        "side": order["side"],
                        "execQty": order["qty"],
                        "execPrice": "79000",
                        "execFee": "0.000001" if query["category"] == "spot" else "0.043",
                        "feeCurrency": "BTC" if query["category"] == "spot" else "USDT",
                        "execTime": "1784800001000",
                    }
                ]
            },
        }


@pytest.fixture
def routed(tmp_path, monkeypatch):
    get_settings().journal_path = str(tmp_path / "market-identity.db")
    initialize_journal()
    settings = Settings(
        environment="live",
        live_write_enabled=True,
        live_account_allowlist="funding",
        bybit_account_ids="funding,monitor",
        bybit_instrument_map="BTCUSDT|SPOT=btc-spot,BTCUSDT|LINEAR=btc-perp",
    )
    clients = {"funding": MarketClient(), "monitor": MarketClient()}
    adapter = StrictBybitAcceptanceAdapter(settings)
    monkeypatch.setattr(adapter, "_client", lambda account_id: clients[account_id])
    return BybitMt5Gateway(settings, bybit=adapter, mt5=object()), adapter, clients


def command(instrument_type="crypto_perp", side="sell"):
    return SubmitOrderCommand(
        command_id="command",
        platform_order_id="platform-order",
        strategy_instance_id="funding",
        account_id="funding",
        instrument_id="btc-spot" if instrument_type == "crypto_spot" else "btc-perp",
        instrument_type=instrument_type,
        symbol="BTCUSDT",
        side=side,
        quantity="0.001",
    )


@pytest.mark.parametrize("identity", ["platform_order_id", "external_order_id"])
def test_order_fill_query_uses_persisted_account_without_caller_account_id(routed, identity):
    gateway, adapter, clients = routed
    order = command()
    save_command_started(order)
    record_order_route(order, adapter.name, "link", "linear-Sell")
    clients["funding"].orders["linear-Sell"] = {
        "category": "linear",
        "side": "Sell",
        "qty": "0.001",
    }
    value = "platform-order" if identity == "platform_order_id" else "linear-Sell"
    for reader in (gateway, adapter):
        fills = reader.list_fills(**{identity: value})
        assert len(fills) == 1
        assert fills[0].account_id == "funding"
        assert fills[0].quantity == Decimal("0.001")
        assert fills[0].platform_order_id == "platform-order"
    assert clients["monitor"].calls == []
    before = list(clients["funding"].calls)
    with pytest.raises(GatewayConfigurationError, match="different account"):
        gateway.list_fills(account_id="monitor", platform_order_id="platform-order")
    assert clients["funding"].calls == before
    assert clients["monitor"].calls == []


@pytest.mark.parametrize(
    "instrument_type,side",
    [
        ("crypto_spot", "buy"),
        ("crypto_spot", "sell"),
        ("crypto_perp", "sell"),
    ],
)
def test_submit_confirmation_and_native_fills_keep_same_market_after_restart(
    routed, instrument_type, side
):
    gateway, adapter, clients = routed
    order = command(instrument_type, side)
    save_command_started(order)
    events = gateway.submit_order(order)
    assert [event.event_type for event in events] == ["order_acknowledged", "order_filled"]
    category = "spot" if instrument_type == "crypto_spot" else "linear"
    payload = next(query for method, query in clients["funding"].calls if method == "place")
    assert payload["category"] == category
    assert payload["qty"] == "0.001"
    if category == "spot":
        assert payload["marketUnit"] == "baseCoin"
        assert payload["isLeverage"] == 0
        assert "reduceOnly" not in payload and "positionIdx" not in payload
    else:
        assert payload["reduceOnly"] is False
        assert "marketUnit" not in payload
    # A newly constructed reader must recover category from the journal, not process state.
    restored = StrictBybitAcceptanceAdapter(adapter.settings, clients["funding"])
    fills = restored.list_fills(platform_order_id=order.platform_order_id)
    assert fills[0].instrument_id == order.instrument_id
    assert fills[0].currency == ("BTC" if category == "spot" else "USDT")
    assert all(query["category"] == category for _, query in clients["funding"].calls)
    assert clients["monitor"].calls == []


def test_spot_permission_is_checked_before_submit(routed):
    gateway, _, clients = routed
    clients["funding"].spot_permission = False
    with pytest.raises(GatewayRequestRejectedError, match="Order permission"):
        gateway.submit_order(command("crypto_spot", "buy"))
    assert not any(method == "place" for method, _ in clients["funding"].calls)


def test_missing_route_does_not_query_an_arbitrary_account(routed):
    gateway, adapter, clients = routed
    assert gateway.list_fills(platform_order_id="absent") == []
    assert adapter.list_fills(platform_order_id="absent") == []
    with pytest.raises(GatewayConfigurationError, match="explicit accountId"):
        adapter.list_fills()
    assert all(not client.calls for client in clients.values())


def test_position_identity_uses_account_and_persisted_market_without_a_static_symbol_map(routed):
    _, adapter, _ = routed
    adapter.settings.bybit_instrument_map = "XAUTUSDT=gold"
    for kind, identity in [("crypto_spot", "spot"), ("crypto_perp", "perp")]:
        order = command(kind).model_copy(
            update={
                "command_id": identity,
                "platform_order_id": identity,
            }
        )
        save_command_started(order)
        record_order_route(order, adapter.name, identity, identity)
    for category, kind, expected in [
        ("spot", "crypto_spot", "btc-spot"),
        ("linear", "crypto_perp", "btc-perp"),
    ]:
        assert (
            adapter._instrument_id_for_symbol(
                account_id="funding",
                symbol="BTCUSDT",
                instrument_type=kind,
                category=category,
            )
            == expected
        )
        assert adapter._instrument_id_for_symbol(
            account_id="monitor",
            symbol="BTCUSDT",
            instrument_type=kind,
            category=category,
        ).startswith("monitor:bybit:monitor:")


def test_concurrent_specs_share_only_inflight_permission_read(routed, monkeypatch):
    from concurrent.futures import Future, ThreadPoolExecutor
    from threading import Event

    _, adapter, clients = routed
    client = clients["funding"]
    for category in ("spot", "linear"):
        adapter._market_data("funding").market(category, "BTCUSDT")
    entered, joined, release = Event(), Event(), Event()
    original = client.get_api_key_information
    calls = []

    class ObservedFuture(Future):
        def result(self, timeout=None):
            joined.set()
            return super().result(timeout)

    def blocked_read():
        calls.append(1)
        entered.set()
        assert release.wait(3)
        return original()

    monkeypatch.setattr("app.bybit_acceptance_adapter.Future", ObservedFuture)
    monkeypatch.setattr(client, "get_api_key_information", blocked_read)

    def spec(category):
        return adapter.get_instrument_specification(
            account_id="funding", symbol="BTCUSDT", category=category,
            instrument_type="crypto_spot" if category == "spot" else "crypto_perp",
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(spec, "spot")
        assert entered.wait(3)
        second = pool.submit(spec, "linear")
        assert joined.wait(3)
        release.set()
        assert first.result().access_checks["orderPermission"] is True
        assert second.result().access_checks["orderPermission"] is True
    assert len(calls) == 1
    client.spot_permission = False
    assert spec("spot").access_checks["orderPermission"] is False
    assert len(calls) == 2
    assert adapter._permission_reads == {}


def test_permission_read_failure_does_not_survive_next_check(routed, monkeypatch):
    _, adapter, clients = routed
    client = clients["funding"]
    original = client.get_api_key_information
    monkeypatch.setattr(client, "get_api_key_information", lambda: {"retCode": 10003})
    with pytest.raises(GatewayRequestRejectedError):
        adapter._api_key_readiness("funding")
    assert adapter._permission_reads == {}
    monkeypatch.setattr(client, "get_api_key_information", original)
    assert adapter._api_key_readiness("funding")["retCode"] == 0
