from __future__ import annotations

from threading import Event, Thread
from types import SimpleNamespace

import pytest

from app.bybit_live_adapter import BybitLiveAdapter
from app.bybit_mt5_gateway import BybitMt5Gateway
from app.config import Settings
from app.mt5_read_coordinator import COORDINATOR, with_mt5_read_session
from app.strict_live_acceptance_adapters import StrictMt5AcceptanceAdapter


class FakeScopedBybitClient:
    def __init__(self) -> None:
        self.categories: list[str] = []

    def get_wallet_balance(self, **kwargs):
        return {
            "retCode": 0,
            "result": {
                "list": [
                    {"coin": [{"coin": "USDT", "equity": "100", "walletBalance": "100"}]}
                ]
            },
        }

    def get_positions(self, **kwargs):
        self.categories.append(f"positions:{kwargs['category']}")
        symbol = "BTCUSDT" if kwargs["category"] == "spot" else "BTCUSDT"
        return {
            "retCode": 0,
            "result": {
                "list": [
                    {
                        "symbol": symbol,
                        "side": "Buy",
                        "size": "1",
                        "updatedTime": "1784800000000",
                    }
                ]
            },
        }

    def get_open_orders(self, **kwargs):
        self.categories.append(f"open:{kwargs['category']}")
        return {"retCode": 0, "result": {"list": []}}

    def get_order_history(self, **kwargs):
        self.categories.append(f"history:{kwargs['category']}")
        return {"retCode": 0, "result": {"list": []}}

    def get_executions(self, **kwargs):
        self.categories.append(f"fills:{kwargs['category']}")
        return {"retCode": 0, "result": {"list": []}}


class FakeMt5SnapshotProvider:
    POSITION_TYPE_BUY = 0
    POSITION_TYPE_SELL = 1
    ORDER_STATE_PLACED = 1
    ORDER_TYPE_BUY = 0
    DEAL_TYPE_BUY = 0

    def __init__(self, *, fail_restore: bool = False, mismatch_after_login: bool = False) -> None:
        self.fail_restore = fail_restore
        self.mismatch_after_login = mismatch_after_login
        self.current_login = "111111"
        self.current_server = "Broker-Main"
        self.login_calls: list[tuple[str, str]] = []

    def initialize(self, **kwargs):
        return True

    def login(self, login, **kwargs):
        login_text = str(login)
        server = str(kwargs["server"])
        self.login_calls.append((login_text, server))
        if self.fail_restore and login_text == "111111":
            return False
        self.current_login = "999999" if self.mismatch_after_login else login_text
        self.current_server = server
        return True

    def last_error(self):
        return (0, "ok")

    def account_info(self):
        return SimpleNamespace(
            login=int(self.current_login),
            server=self.current_server,
            currency="USD",
            balance=1000.0,
            equity=1001.0,
            profit=1.0,
            margin=10.0,
            margin_free=991.0,
            margin_level=100.0,
            margin_so_call=80.0,
            margin_so_so=50.0,
            margin_so_mode=0,
            leverage=100,
            margin_mode=2,
            trade_allowed=True,
        )

    def terminal_info(self):
        return SimpleNamespace(trade_allowed=True)

    def positions_get(self):
        return (
            SimpleNamespace(
                ticket=1,
                type=self.POSITION_TYPE_BUY,
                symbol="XAUUSD+",
                volume=0.01,
                price_open=2400.0,
                price_current=2401.0,
                profit=1.0,
                time_update=1784800000,
                time_update_msc=1784800000000,
            ),
        )

    def orders_get(self):
        return (
            SimpleNamespace(
                ticket=2,
                state=self.ORDER_STATE_PLACED,
                type=self.ORDER_TYPE_BUY,
                symbol="XAUUSD+",
                volume_initial=0.01,
                volume_current=0.01,
                price_open=2400.0,
                time_setup=1784800000,
                time_done=0,
            ),
        )

    def history_orders_get(self, *args, **kwargs):
        return ()

    def history_deals_get(self, *args, **kwargs):
        return (
            SimpleNamespace(
                ticket=3,
                order=2,
                type=self.DEAL_TYPE_BUY,
                symbol="XAUUSD+",
                volume=0.01,
                price=2400.5,
                commission=-0.1,
                fee=0.0,
                time=1784800001,
                time_msc=1784800001000,
            ),
        )


def configure_mt5_refs(monkeypatch) -> None:
    monkeypatch.setenv("VG_RUNTIME_LIVE_WRITE_ENABLED", "false")
    monkeypatch.setenv("VG_SECRET_MT5_MAIN_LOGIN", "111111")
    monkeypatch.setenv("VG_SECRET_MT5_MAIN_PASSWORD", "main-pass")
    monkeypatch.setenv("VG_SECRET_MT5_MAIN_SERVER", "Broker-Main")
    monkeypatch.setenv("VG_SECRET_MT5_SHORT_A_LOGIN", "222222")
    monkeypatch.setenv("VG_SECRET_MT5_SHORT_A_PASSWORD", "short-pass")
    monkeypatch.setenv("VG_SECRET_MT5_SHORT_A_SERVER", "Broker-Short")


def test_bybit_account_snapshot_uses_scoped_categories() -> None:
    client = FakeScopedBybitClient()
    adapter = BybitLiveAdapter(
        Settings(
            bybit_account_ids="bybit-live-main",
            bybit_instrument_map="BTCUSDT=instrument_btc",
            bybit_account_category_scopes="bybit-live-main=spot|linear",
        ),
        client,
    )

    snapshot = adapter.get_account_snapshot("bybit-live-main")

    assert snapshot.venue == "bybit"
    assert set(client.categories) >= {
        "positions:linear",
        "open:spot",
        "open:linear",
        "fills:spot",
        "fills:linear",
    }
    assert "positions:spot" not in client.categories


def test_mt5_instrument_query_does_not_forward_bybit_scope_arguments(monkeypatch) -> None:
    calls: list[dict[str, str]] = []

    class Mt5InstrumentAdapter:
        def get_instrument_specification(self, *, account_id: str, symbol: str):
            calls.append({"account_id": account_id, "symbol": symbol})
            return SimpleNamespace(symbol=symbol)

    settings = Settings(mt5_account_ids="mt5-live-main")
    gateway = BybitMt5Gateway(settings=settings)
    gateway.mt5 = Mt5InstrumentAdapter()
    gateway._injected_mt5 = gateway.mt5
    result = gateway.get_instrument_specification(
        account_id="mt5-live-main",
        symbol="XAUUSD.s",
        instrument_type="mt5_contract",
        category="mt5",
    )

    assert result.symbol == "XAUUSD.s"
    assert calls == [{"account_id": "mt5-live-main", "symbol": "XAUUSD.s"}]


def test_mt5_account_snapshot_switches_once_and_restores_primary(monkeypatch) -> None:
    COORDINATOR.clear_restore_failure()
    configure_mt5_refs(monkeypatch)
    provider = FakeMt5SnapshotProvider()
    gateway = BybitMt5Gateway(
        Settings(
            mt5_account_ids="mt5-live-main,account_mt5_short_term_a",
            mt5_account_credential_refs=(
                "mt5-live-main=secret://environment/mt5-main,"
                "account_mt5_short_term_a=secret://environment/mt5-short-a"
            ),
            mt5_primary_account_id="mt5-live-main",
            mt5_instrument_map="XAUUSD+=instrument_xau_usd",
        ),
        bybit=None,
        mt5=None,
    )
    gateway.mt5 = StrictMt5AcceptanceAdapter(gateway.settings, provider)
    gateway._injected_mt5 = gateway.mt5

    snapshot = gateway.get_account_snapshot("account_mt5_short_term_a")

    assert snapshot.venue == "mt5"
    assert provider.login_calls == [("222222", "Broker-Short"), ("111111", "Broker-Main")]


def test_mt5_explicit_risk_read_uses_fixed_account_worker(monkeypatch) -> None:
    COORDINATOR.clear_restore_failure()
    configure_mt5_refs(monkeypatch)
    provider = FakeMt5SnapshotProvider()
    provider.current_login = "222222"
    provider.current_server = "Broker-Short"
    settings = Settings(
        mt5_account_ids="mt5-live-main,account_mt5_short_term_a",
        mt5_account_credential_refs=(
            "mt5-live-main=secret://environment/mt5-main,"
            "account_mt5_short_term_a=secret://environment/mt5-short-a"
        ),
        mt5_primary_account_id="mt5-live-main",
        mt5_instrument_map="XAUUSD+=instrument_xau_usd",
    )
    gateway = BybitMt5Gateway(settings=settings)
    gateway.mt5 = StrictMt5AcceptanceAdapter(settings, provider)
    gateway._injected_mt5 = gateway.mt5

    risk = gateway.get_account_risk("account_mt5_short_term_a")

    assert risk.account_id == "account_mt5_short_term_a"
    assert provider.login_calls == []


def test_mt5_primary_risk_read_does_not_relogin_current_primary(monkeypatch) -> None:
    COORDINATOR.clear_restore_failure()
    configure_mt5_refs(monkeypatch)
    provider = FakeMt5SnapshotProvider()
    settings = Settings(
        mt5_account_ids="mt5-live-main,account_mt5_short_term_a",
        mt5_account_credential_refs=(
            "mt5-live-main=secret://environment/mt5-main,"
            "account_mt5_short_term_a=secret://environment/mt5-short-a"
        ),
        mt5_primary_account_id="mt5-live-main",
        mt5_instrument_map="XAUUSD+=instrument_xau_usd",
    )
    gateway = BybitMt5Gateway(settings=settings)
    gateway.mt5 = StrictMt5AcceptanceAdapter(settings, provider)
    gateway._injected_mt5 = gateway.mt5

    risk = gateway.get_account_risk("mt5-live-main")

    assert risk.account_id == "mt5-live-main"
    assert provider.login_calls == []


def test_mt5_non_primary_session_is_paused_while_live_write_is_enabled(monkeypatch) -> None:
    COORDINATOR.clear_restore_failure()
    configure_mt5_refs(monkeypatch)
    provider = FakeMt5SnapshotProvider()
    settings = Settings(
        live_write_enabled=True,
        mt5_account_ids="mt5-live-main,account_mt5_short_term_a",
        mt5_account_credential_refs=(
            "mt5-live-main=secret://environment/mt5-main,"
            "account_mt5_short_term_a=secret://environment/mt5-short-a"
        ),
        mt5_primary_account_id="mt5-live-main",
        mt5_instrument_map="XAUUSD+=instrument_xau_usd",
    )
    gateway = BybitMt5Gateway(settings=settings)
    gateway.mt5 = StrictMt5AcceptanceAdapter(settings, provider)
    gateway._injected_mt5 = gateway.mt5

    with pytest.raises(Exception, match="MT5_NON_PRIMARY_SESSION_PAUSED"):
        gateway.get_account_snapshot("account_mt5_short_term_a")

    assert provider.login_calls == []


def test_mt5_restore_failure_fail_closes_readiness(monkeypatch) -> None:
    COORDINATOR.clear_restore_failure()
    configure_mt5_refs(monkeypatch)
    provider = FakeMt5SnapshotProvider(fail_restore=True)
    settings = Settings(
        mt5_account_ids="mt5-live-main,account_mt5_short_term_a",
        mt5_account_credential_refs=(
            "mt5-live-main=secret://environment/mt5-main,"
            "account_mt5_short_term_a=secret://environment/mt5-short-a"
        ),
        mt5_primary_account_id="mt5-live-main",
        mt5_instrument_map="XAUUSD+=instrument_xau_usd",
    )
    gateway = BybitMt5Gateway(settings=settings)
    gateway.mt5 = StrictMt5AcceptanceAdapter(settings, provider)
    gateway._injected_mt5 = gateway.mt5

    with pytest.raises(Exception, match="restore failed"):
        gateway.get_account_snapshot("account_mt5_short_term_a")

    capability = gateway.mt5.capability()
    assert "MT5_PRIMARY_RESTORE_FAILED" in capability.missing_requirements


def test_mt5_restore_failure_blocks_until_primary_identity_recovers(monkeypatch) -> None:
    COORDINATOR.clear_restore_failure()
    configure_mt5_refs(monkeypatch)

    class CoordinatedProvider(FakeMt5SnapshotProvider):
        def __init__(self) -> None:
            super().__init__(fail_restore=True)
            self.target_started = Event()
            self.release_target = Event()
            self.callback_entered = Event()
            self.callback_calls = 0

        def login(self, login, **kwargs):
            login_text = str(login)
            if login_text == "222222":
                self.target_started.set()
                self.release_target.wait(timeout=5)
            return super().login(login, **kwargs)

    provider = CoordinatedProvider()
    settings = Settings(
        mt5_account_ids="mt5-live-main,account_mt5_short_term_a",
        mt5_account_credential_refs=(
            "mt5-live-main=secret://environment/mt5-main,"
            "account_mt5_short_term_a=secret://environment/mt5-short-a"
        ),
        mt5_primary_account_id="mt5-live-main",
        mt5_instrument_map="XAUUSD+=instrument_xau_usd",
    )

    errors: dict[str, str] = {}

    def worker(name: str) -> None:
        try:
            with_mt5_read_session(
                mt5=provider,
                settings=settings,
                account_id="account_mt5_short_term_a",
                callback=lambda _session: _callback(provider),
            )
        except Exception as exc:  # noqa: BLE001
            errors[name] = str(exc)

    def _callback(current_provider: CoordinatedProvider) -> str:
        current_provider.callback_calls += 1
        current_provider.callback_entered.set()
        return "ok"

    thread_a = Thread(target=worker, args=("A",), daemon=True)
    thread_b = Thread(target=worker, args=("B",), daemon=True)
    thread_a.start()
    assert provider.target_started.wait(timeout=5)
    thread_b.start()
    provider.release_target.set()
    thread_a.join(timeout=5)
    thread_b.join(timeout=5)

    assert provider.callback_calls == 1
    assert provider.callback_entered.is_set()
    assert provider.login_calls == [
        ("222222", "Broker-Short"),
        ("111111", "Broker-Main"),
        ("111111", "Broker-Main"),
    ]
    assert "restore failed" in errors["A"]
    assert "MT5 login failed" in errors["B"]

    provider.fail_restore = False
    recovered = with_mt5_read_session(
        mt5=provider,
        settings=settings,
        account_id="account_mt5_short_term_a",
        callback=lambda _session: "recovered",
    )
    assert recovered == "recovered"
    assert provider.login_calls == [
        ("222222", "Broker-Short"),
        ("111111", "Broker-Main"),
        ("111111", "Broker-Main"),
        ("111111", "Broker-Main"),
        ("222222", "Broker-Short"),
        ("111111", "Broker-Main"),
    ]


def test_mt5_callback_exception_still_restores_primary(monkeypatch) -> None:
    COORDINATOR.clear_restore_failure()
    configure_mt5_refs(monkeypatch)
    provider = FakeMt5SnapshotProvider()
    settings = Settings(
        mt5_account_ids="mt5-live-main,account_mt5_short_term_a",
        mt5_account_credential_refs=(
            "mt5-live-main=secret://environment/mt5-main,"
            "account_mt5_short_term_a=secret://environment/mt5-short-a"
        ),
        mt5_primary_account_id="mt5-live-main",
        mt5_instrument_map="XAUUSD+=instrument_xau_usd",
    )

    callback_calls = 0

    def raising_callback(_session):
        nonlocal callback_calls
        callback_calls += 1
        raise RuntimeError("boom")

    with pytest.raises(Exception, match="snapshot failed"):
        with_mt5_read_session(
            mt5=provider,
            settings=settings,
            account_id="account_mt5_short_term_a",
            callback=raising_callback,
        )

    assert callback_calls == 1
    assert provider.login_calls == [("222222", "Broker-Short"), ("111111", "Broker-Main")]


def test_mt5_identity_mismatch_still_restores_primary(monkeypatch) -> None:
    COORDINATOR.clear_restore_failure()
    configure_mt5_refs(monkeypatch)

    class TargetMismatchProvider(FakeMt5SnapshotProvider):
        def login(self, login, **kwargs):
            result = super().login(login, **kwargs)
            if str(login) == "222222":
                self.current_login = "999999"
            return result

    provider = TargetMismatchProvider()
    settings = Settings(
        mt5_account_ids="mt5-live-main,account_mt5_short_term_a",
        mt5_account_credential_refs=(
            "mt5-live-main=secret://environment/mt5-main,"
            "account_mt5_short_term_a=secret://environment/mt5-short-a"
        ),
        mt5_primary_account_id="mt5-live-main",
        mt5_instrument_map="XAUUSD+=instrument_xau_usd",
    )

    with pytest.raises(Exception, match="identity mismatch"):
        with_mt5_read_session(
            mt5=provider,
            settings=settings,
            account_id="account_mt5_short_term_a",
            callback=lambda _session: "unexpected",
        )

    assert provider.login_calls == [("222222", "Broker-Short"), ("111111", "Broker-Main")]


def test_mt5_account_snapshot_keeps_unmapped_symbols_for_readonly_monitoring(monkeypatch) -> None:
    COORDINATOR.clear_restore_failure()
    configure_mt5_refs(monkeypatch)
    provider = FakeMt5SnapshotProvider()
    gateway = BybitMt5Gateway(
        Settings(
            mt5_account_ids="mt5-live-main,account_mt5_short_term_a",
            mt5_account_credential_refs=(
                "mt5-live-main=secret://environment/mt5-main,"
                "account_mt5_short_term_a=secret://environment/mt5-short-a"
            ),
            mt5_primary_account_id="mt5-live-main",
            mt5_instrument_map="",
        ),
        bybit=None,
        mt5=None,
    )
    gateway.mt5 = StrictMt5AcceptanceAdapter(gateway.settings, provider)
    gateway._injected_mt5 = gateway.mt5

    snapshot = gateway.get_account_snapshot("account_mt5_short_term_a")

    assert snapshot.data_quality_state == "external_unmapped"
    assert snapshot.warnings == ["read_only_monitoring_unmapped:XAUUSD+"]
    assert snapshot.positions[0].symbol == "XAUUSD+"
    assert snapshot.positions[0].instrument_id.startswith(
        "monitor:mt5:account_mt5_short_term_a:"
    )
    assert snapshot.positions[0].data_quality_state == "external_unmapped"
    assert snapshot.orders[0].instrument_id == snapshot.positions[0].instrument_id
    assert snapshot.orders[0].data_quality_state == "external_unmapped"
    assert snapshot.fills[0].instrument_id == snapshot.positions[0].instrument_id
    assert snapshot.fills[0].data_quality_state == "external_unmapped"


def test_mt5_unmapped_monitoring_identity_is_stable_and_account_scoped(monkeypatch) -> None:
    COORDINATOR.clear_restore_failure()
    configure_mt5_refs(monkeypatch)
    provider = FakeMt5SnapshotProvider()
    gateway = BybitMt5Gateway(
        Settings(
            mt5_account_ids="mt5-live-main,account_mt5_short_term_a",
            mt5_account_credential_refs=(
                "mt5-live-main=secret://environment/mt5-main,"
                "account_mt5_short_term_a=secret://environment/mt5-short-a"
            ),
            mt5_primary_account_id="mt5-live-main",
            mt5_instrument_map="",
        ),
        bybit=None,
        mt5=None,
    )
    gateway.mt5 = StrictMt5AcceptanceAdapter(gateway.settings, provider)
    gateway._injected_mt5 = gateway.mt5

    first = gateway.get_account_snapshot("account_mt5_short_term_a")
    second = gateway.get_account_snapshot("account_mt5_short_term_a")
    main = gateway.get_account_snapshot("mt5-live-main")

    assert first.positions[0].instrument_id == second.positions[0].instrument_id
    assert first.orders[0].instrument_id == second.orders[0].instrument_id
    assert first.fills[0].instrument_id == second.fills[0].instrument_id
    assert first.positions[0].instrument_id != main.positions[0].instrument_id


def test_mt5_account_snapshot_reports_real_zero_when_positions_and_orders_are_empty(
    monkeypatch,
) -> None:
    COORDINATOR.clear_restore_failure()
    configure_mt5_refs(monkeypatch)

    class EmptyProvider(FakeMt5SnapshotProvider):
        def positions_get(self):
            return ()

        def orders_get(self):
            return ()

        def history_deals_get(self, *args, **kwargs):
            return ()

    provider = EmptyProvider()
    gateway = BybitMt5Gateway(
        Settings(
            mt5_account_ids="mt5-live-main,account_mt5_short_term_a",
            mt5_account_credential_refs=(
                "mt5-live-main=secret://environment/mt5-main,"
                "account_mt5_short_term_a=secret://environment/mt5-short-a"
            ),
            mt5_primary_account_id="mt5-live-main",
            mt5_instrument_map="",
        ),
        bybit=None,
        mt5=None,
    )
    gateway.mt5 = StrictMt5AcceptanceAdapter(gateway.settings, provider)
    gateway._injected_mt5 = gateway.mt5

    snapshot = gateway.get_account_snapshot("account_mt5_short_term_a")

    assert snapshot.positions == []
    assert snapshot.orders == []
    assert snapshot.fills == []
    assert snapshot.data_quality_state == "complete"
