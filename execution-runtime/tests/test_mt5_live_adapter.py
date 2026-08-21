import sys
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.config import Settings, get_settings
from app.gateway_errors import GatewayConfigurationError
from app.journal import initialize_journal
from app.models import SubmitOrderCommand
from app.mt5_live_adapter import Mt5LiveAdapter


class FakeMt5:
    TRADE_ACTION_DEAL = 1
    TRADE_ACTION_PENDING = 5
    TRADE_ACTION_REMOVE = 8
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TYPE_BUY_LIMIT = 2
    ORDER_TYPE_SELL_LIMIT = 3
    ORDER_TYPE_BUY_STOP = 4
    ORDER_TIME_GTC = 0
    ORDER_FILLING_IOC = 1
    ORDER_FILLING_RETURN = 2
    TRADE_RETCODE_PLACED = 10008
    TRADE_RETCODE_DONE = 10009
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

    def symbol_info_tick(self, symbol):
        return SimpleNamespace(ask=2000.0, bid=1999.5)

    def order_check(self, request):
        return SimpleNamespace(retcode=0, comment="Done")

    def order_send(self, request):
        self.requests.append(request)
        if request["action"] == self.TRADE_ACTION_REMOVE:
            return SimpleNamespace(retcode=self.TRADE_RETCODE_DONE, comment="Canceled")
        return SimpleNamespace(
            retcode=self.TRADE_RETCODE_DONE,
            comment="Done",
            order=123,
            deal=456,
            volume=1.0,
            price=2000.0,
        )

    def orders_get(self, **kwargs):
        return (
            SimpleNamespace(
                ticket=123,
                state=self.ORDER_STATE_PLACED,
                type=self.ORDER_TYPE_BUY,
                volume_initial=1.0,
                volume_current=1.0,
                price_open=2000.0,
                time_setup=1784800000,
                time_done=0,
            ),
        )

    def history_orders_get(self, **kwargs):
        return ()

    def history_deals_get(self, *args, **kwargs):
        return (
            SimpleNamespace(
                ticket=456,
                order=123,
                position_id=789,
                type=self.DEAL_TYPE_BUY,
                symbol="XAUUSD+",
                volume=1.0,
                price=2000.0,
                commission=-1.0,
                fee=0.0,
                swap=-2.0,
                time=1784800001,
                time_msc=1784800001000,
                _asdict=lambda: {
                    "ticket": 456,
                    "order": 123,
                    "symbol": "XAUUSD+",
                    "swap": -2.0,
                    "commission": -1.0,
                },
            ),
        )

    def positions_get(self):
        return (
            SimpleNamespace(
                ticket=789,
                type=self.POSITION_TYPE_BUY,
                symbol="XAUUSD+",
                volume=1.0,
                price_open=2000.0,
                time_update=1784800002,
                time_update_msc=1784800002000,
            ),
        )

    def account_info(self):
        return SimpleNamespace(
            login=123456,
            currency="USD",
            equity=100000.0,
            margin_free=90000.0,
        )


class FakeRuntimeMt5(FakeMt5):
    def __init__(self) -> None:
        super().__init__()
        self.initialize_calls: list[dict[str, object]] = []
        self.login_calls: list[dict[str, object]] = []

    def initialize(self, **kwargs):
        self.initialize_calls.append(kwargs)
        return True

    def login(self, login, **kwargs):
        self.login_calls.append({"login": login, **kwargs})
        return True


def runtime_settings(write_enabled: bool = True) -> Settings:
    return Settings(
        environment="live",
        live_write_enabled=write_enabled,
        live_account_allowlist="account-mt5",
        live_strategy_allowlist="strategy-live",
        live_symbol_allowlist="XAUUSD+",
        live_max_order_notional="5000",
        live_max_daily_notional="10000",
        mt5_account_ids="account-mt5",
        mt5_instrument_map="XAUUSD+=instrument-xauusd",
        mt5_credential_ref="secret://environment/mt5-live-001",
        mt5_magic_number=5604001,
        mt5_check_timeout_seconds=8,
    )


def order_command() -> SubmitOrderCommand:
    return SubmitOrderCommand(
        command_id="command-mt5-1",
        platform_order_id="platform-order-mt5-1",
        strategy_instance_id="strategy-live",
        account_id="account-mt5",
        instrument_id="instrument-xauusd",
        symbol="XAUUSD+",
        side="buy",
        order_type="market",
        quantity="1",
    )


def configure_mt5_secret(monkeypatch) -> None:
    monkeypatch.setenv("VG_SECRET_MT5_LIVE_001_LOGIN", "123456")
    monkeypatch.setenv("VG_SECRET_MT5_LIVE_001_PASSWORD", "not-exposed")
    monkeypatch.setenv("VG_SECRET_MT5_LIVE_001_SERVER", "Broker-Live")


def test_mt5_live_adapter_is_readable_but_write_gated(tmp_path, monkeypatch) -> None:
    configure_mt5_secret(monkeypatch)
    get_settings().journal_path = str(tmp_path / "mt5-readonly.db")
    initialize_journal()
    adapter = Mt5LiveAdapter(runtime_settings(write_enabled=False), FakeMt5())
    assert adapter.list_positions("account-mt5")[0].net_quantity == Decimal("1.0")
    assert adapter.list_balances("account-mt5")[0].equity == Decimal("100000.0")
    with pytest.raises(GatewayConfigurationError, match="live write gate is disabled"):
        adapter.submit_order(order_command())


def test_mt5_live_adapter_sets_terminal_timeouts(tmp_path, monkeypatch) -> None:
    configure_mt5_secret(monkeypatch)
    get_settings().journal_path = str(tmp_path / "mt5-timeout.db")
    initialize_journal()
    fake_mt5 = FakeRuntimeMt5()
    monkeypatch.setitem(sys.modules, "MetaTrader5", fake_mt5)
    monkeypatch.setattr("app.mt5_live_adapter.platform.system", lambda: "Windows")

    adapter = Mt5LiveAdapter(runtime_settings(write_enabled=False))
    balance = adapter.list_balances("account-mt5")[0]

    assert balance.equity == Decimal("100000.0")
    assert fake_mt5.initialize_calls[0]["timeout"] == 8000
    assert fake_mt5.login_calls[0]["timeout"] == 8000


def test_mt5_live_adapter_maps_orders_deals_and_swap(tmp_path, monkeypatch) -> None:
    configure_mt5_secret(monkeypatch)
    get_settings().journal_path = str(tmp_path / "mt5-live.db")
    initialize_journal()
    provider = FakeMt5()
    adapter = Mt5LiveAdapter(runtime_settings(), provider)

    events = adapter.submit_order(order_command())
    assert [event.event_type for event in events] == ["order_acknowledged", "order_filled"]
    assert events[0].external_order_id == "123"
    assert provider.requests[0]["magic"] == 5604001
    assert str(provider.requests[0]["comment"]).startswith("VG-")

    snapshot = adapter.get_order(platform_order_id="platform-order-mt5-1")
    assert snapshot is not None
    assert snapshot.status == "accepted"

    fills = adapter.list_fills(platform_order_id="platform-order-mt5-1")
    assert fills[0].external_fill_id == "456"
    assert fills[0].instrument_id == "instrument-xauusd"

    economic = adapter.list_economic_events(account_id="account-mt5")
    assert {(item.event_type, item.amount) for item in economic} == {
        ("swap", Decimal("-2.0")),
        ("fee", Decimal("-1.0")),
    }

    canceled = adapter.cancel_order("123", "cancel-mt5-1", "operator request")
    assert canceled.status == "canceled"


def test_mt5_live_adapter_normalizes_ust_currency_to_usdt(tmp_path, monkeypatch) -> None:
    configure_mt5_secret(monkeypatch)
    get_settings().journal_path = str(tmp_path / "mt5-currency.db")
    initialize_journal()
    provider = FakeMt5()
    provider.account_info = lambda: SimpleNamespace(
        login=123456,
        currency="UST",
        equity=100000.0,
        margin_free=90000.0,
    )
    adapter = Mt5LiveAdapter(runtime_settings(write_enabled=False), provider)

    balance = adapter.list_balances("account-mt5")[0]

    assert balance.currency == "USDT"
