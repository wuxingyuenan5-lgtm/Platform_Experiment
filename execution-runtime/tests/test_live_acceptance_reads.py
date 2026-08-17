from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.bybit_acceptance_adapter import BybitAcceptanceAdapter
from app.config import Settings, get_settings
from app.gateway_errors import GatewayRequestRejectedError
from app.journal import initialize_journal
from app.models import SubmitOrderCommand
from app.mt5_acceptance_adapter import Mt5AcceptanceAdapter
from app.strict_live_acceptance_adapters import StrictMt5AcceptanceAdapter


class AcceptanceBybitClient:
    def get_open_orders(self, **kwargs):
        return {
            "retCode": 0,
            "result": {
                "list": [
                    {
                        "orderId": "BYBIT-EXTERNAL-1",
                        "orderLinkId": "manual-order",
                        "symbol": "XAUTUSDT",
                        "side": "Buy",
                        "orderType": "Market",
                        "qty": "1",
                        "price": "0",
                        "orderStatus": "Filled",
                        "cumExecQty": "1",
                        "avgPrice": "2400",
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
                        "execId": "BYBIT-EXEC-1",
                        "orderId": "BYBIT-EXTERNAL-1",
                        "symbol": "XAUTUSDT",
                        "side": "Buy",
                        "execQty": "1",
                        "execPrice": "2400",
                        "execFee": "0.1",
                        "feeCurrency": "USDT",
                        "execTime": "1784800001000",
                    }
                ]
            },
        }

    def get_instruments_info(self, **kwargs):
        return {
            "retCode": 0,
            "result": {
                "list": [
                    {
                        "symbol": "XAUTUSDT",
                        "status": "Trading",
                        "lotSizeFilter": {
                            "minOrderQty": "0.001",
                            "qtyStep": "0.001",
                            "maxMktOrderQty": "10",
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
                "ips": ["203.0.113.10"],
                "permissions": {
                    "ContractTrade": ["Order", "Position"],
                },
            },
        }


class AcceptanceMt5:
    TRADE_ACTION_DEAL = 1
    TRADE_ACTION_PENDING = 5
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TYPE_BUY_LIMIT = 2
    ORDER_TYPE_SELL_LIMIT = 3
    ORDER_TYPE_BUY_STOP = 4
    ORDER_TIME_GTC = 0
    ORDER_FILLING_IOC = 1
    ORDER_FILLING_RETURN = 2
    TRADE_RETCODE_DONE = 10009
    TRADE_RETCODE_PLACED = 10008
    TRADE_RETCODE_DONE_PARTIAL = 10010
    ORDER_STATE_STARTED = 0
    ORDER_STATE_PLACED = 1
    ORDER_STATE_CANCELED = 2
    ORDER_STATE_PARTIAL = 3
    ORDER_STATE_FILLED = 4
    ORDER_STATE_REJECTED = 5
    ORDER_STATE_EXPIRED = 6
    ORDER_STATE_REQUEST_ADD = 7
    DEAL_TYPE_BUY = 0
    DEAL_TYPE_SELL = 1
    POSITION_TYPE_BUY = 0
    POSITION_TYPE_SELL = 1

    def __init__(self) -> None:
        self.requests: list[dict[str, object]] = []

    def last_error(self):
        return (0, "ok")

    def symbol_info(self, symbol):
        return SimpleNamespace(
            select=True,
            visible=True,
            volume_min=0.01,
            volume_step=0.01,
            volume_max=100.0,
            trade_contract_size=100.0,
            trade_mode=4,
            filling_mode=1,
        )

    def symbol_info_tick(self, symbol):
        return SimpleNamespace(ask=2400.0, bid=2399.5)

    def account_info(self):
        return SimpleNamespace(
            login=123456,
            currency="USD",
            equity=1000.0,
            margin_free=900.0,
            trade_allowed=True,
        )

    def terminal_info(self):
        return SimpleNamespace(trade_allowed=True)

    def orders_get(self, **kwargs):
        return ()

    def history_orders_get(self, *args, **kwargs):
        return ()

    def history_deals_get(self, *args, **kwargs):
        return (
            SimpleNamespace(
                ticket=456,
                order=123,
                position_id=789,
                type=self.DEAL_TYPE_BUY,
                symbol="XAUUSD+",
                volume=0.01,
                price=2400.0,
                commission=-0.1,
                fee=0.0,
                swap=0.0,
                time=1784800001,
                time_msc=1784800001000,
                comment="manual-deal",
            ),
        )

    def positions_get(self, **kwargs):
        return ()

    def order_check(self, request):
        return SimpleNamespace(retcode=0, comment="Done")

    def order_send(self, request):
        self.requests.append(request)
        return SimpleNamespace(
            retcode=self.TRADE_RETCODE_DONE,
            comment="Done",
            order=123,
            deal=456,
            volume=request["volume"],
            price=request["price"],
        )


def bybit_settings() -> Settings:
    return Settings(
        environment="live",
        bybit_account_ids="account-bybit",
        bybit_instrument_map="XAUTUSDT=instrument-xaut",
        bybit_category="linear",
        bybit_settle_coin="USDT",
    )


def mt5_settings(**overrides) -> Settings:
    values = dict(
        environment="live",
        live_write_enabled=True,
        live_account_allowlist="account-mt5",
        live_strategy_allowlist="strategy-live",
        live_symbol_allowlist="XAUUSD+",
        live_max_order_notional="100",
        live_max_daily_notional="500",
        live_acceptance_max_order_quantity="1",
        mt5_account_ids="account-mt5",
        mt5_instrument_map="XAUUSD+=instrument-xauusd",
    )
    values.update(overrides)
    return Settings(**values)


def configure_mt5_secret(monkeypatch) -> None:
    monkeypatch.setenv("VG_SECRET_MT5_LIVE_001_LOGIN", "123456")
    monkeypatch.setenv("VG_SECRET_MT5_LIVE_001_PASSWORD", "not-exposed")
    monkeypatch.setenv("VG_SECRET_MT5_LIVE_001_SERVER", "Broker-Live")


def mt5_command(quantity: str) -> SubmitOrderCommand:
    return SubmitOrderCommand(
        command_id=f"command-mt5-{quantity}",
        platform_order_id=f"platform-mt5-{quantity}",
        strategy_instance_id="strategy-live",
        account_id="account-mt5",
        instrument_id="instrument-xauusd",
        symbol="XAUUSD+",
        side="buy",
        order_type="market",
        quantity=quantity,
    )


def test_bybit_external_order_and_fill_are_readable_without_route(tmp_path) -> None:
    get_settings().journal_path = str(tmp_path / "bybit-acceptance.db")
    initialize_journal()
    adapter = BybitAcceptanceAdapter(bybit_settings(), AcceptanceBybitClient())

    snapshot = adapter.get_order(external_order_id="BYBIT-EXTERNAL-1")
    assert snapshot is not None
    assert snapshot.status == "filled"
    assert snapshot.platform_order_id == "external:bybit_live:BYBIT-EXTERNAL-1"
    assert snapshot.data_quality_state == "external_only"

    listed = adapter.list_orders(account_id="account-bybit")
    assert [item.external_order_id for item in listed] == ["BYBIT-EXTERNAL-1"]
    fills = adapter.list_fills(external_order_id="BYBIT-EXTERNAL-1")
    assert fills[0].external_fill_id == "BYBIT-EXEC-1"
    assert fills[0].data_quality_state == "external_only"


def test_bybit_specification_includes_access_and_quantity_evidence(tmp_path) -> None:
    get_settings().journal_path = str(tmp_path / "bybit-spec.db")
    initialize_journal()
    adapter = BybitAcceptanceAdapter(bybit_settings(), AcceptanceBybitClient())

    specification = adapter.get_instrument_specification(
        account_id="account-bybit",
        symbol="XAUTUSDT",
    )
    assert specification.min_quantity == Decimal("0.001")
    assert specification.quantity_step == Decimal("0.001")
    assert specification.max_market_quantity == Decimal("10")
    assert specification.access_checks["ipBound"] is True
    assert specification.access_checks["orderPermission"] is True


def test_mt5_deal_ticket_resolves_to_filled_order_without_route(
    tmp_path,
    monkeypatch,
) -> None:
    configure_mt5_secret(monkeypatch)
    get_settings().journal_path = str(tmp_path / "mt5-acceptance.db")
    initialize_journal()
    adapter = Mt5AcceptanceAdapter(mt5_settings(), AcceptanceMt5())

    snapshot = adapter.get_order(external_order_id="456")
    assert snapshot is not None
    assert snapshot.external_order_id == "123"
    assert snapshot.status == "filled"
    assert snapshot.filled_quantity == Decimal("0.01")
    assert snapshot.data_quality_state == "external_only"

    fills = adapter.list_fills(external_order_id="123")
    assert fills[0].external_fill_id == "456"
    assert fills[0].external_order_id == "123"


def test_mt5_runtime_cap_converts_lots_to_ounces(tmp_path, monkeypatch) -> None:
    configure_mt5_secret(monkeypatch)
    get_settings().journal_path = str(tmp_path / "mt5-cap.db")
    initialize_journal()
    provider = AcceptanceMt5()
    adapter = StrictMt5AcceptanceAdapter(mt5_settings(), provider)

    events = adapter.submit_order(mt5_command("0.01"))
    assert [event.event_type for event in events] == [
        "order_acknowledged",
        "order_filled",
    ]
    assert provider.requests[0]["volume"] == 0.01

    with pytest.raises(GatewayRequestRejectedError, match="one-ounce limit"):
        adapter.submit_order(mt5_command("0.02"))


def test_mt5_legacy_one_ounce_cap_is_disabled_by_default(tmp_path, monkeypatch) -> None:
    configure_mt5_secret(monkeypatch)
    get_settings().journal_path = str(tmp_path / "mt5-nocap.db")
    initialize_journal()
    provider = AcceptanceMt5()
    adapter = StrictMt5AcceptanceAdapter(
        mt5_settings(live_acceptance_max_order_quantity="0"), provider
    )
    events = adapter.submit_order(mt5_command("0.02"))
    assert [event.event_type for event in events] == [
        "order_acknowledged",
        "order_filled",
    ]
    assert provider.requests[0]["volume"] == 0.02
