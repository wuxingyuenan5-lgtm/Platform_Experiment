from decimal import Decimal
from types import SimpleNamespace

from app.bybit_mt5_gateway import BybitMt5Gateway
from app.config import Settings


class RecordingAdapter:
    name = "recording"

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def get_account_risk(self, account_id: str):
        self.calls.append(("risk", account_id))
        return SimpleNamespace(account_id=account_id)

    def get_account_snapshot(self, account_id: str):
        self.calls.append(("snapshot", account_id))
        return SimpleNamespace(account_id=account_id)

    def capability(self):
        self.calls.append(("capability", "mt5-live-main"))
        return SimpleNamespace(operational=True)

    def get_instrument_specification(self, **kwargs):
        self.calls.append(("specification", kwargs["account_id"]))
        return SimpleNamespace(symbol=kwargs["symbol"])

    def get_market_quote(self, **kwargs):
        self.calls.append(("quote", kwargs["account_id"]))
        return SimpleNamespace(symbol=kwargs["symbol"], bid=Decimal("100"))

    def estimate_order_margin(self, **kwargs):
        self.calls.append(("margin", kwargs["account_id"]))
        return SimpleNamespace(estimated_initial_margin=Decimal("5"))


def live_settings() -> Settings:
    return Settings(
        gateway_name="live",
        bybit_account_ids="bybit-live-main",
        mt5_account_ids="mt5-live-main",
        live_account_allowlist="bybit-live-main,mt5-live-main",
    )


def test_live_warmup_connects_allowed_accounts_before_first_order() -> None:
    bybit = RecordingAdapter()
    mt5 = RecordingAdapter()
    gateway = BybitMt5Gateway(settings=live_settings(), bybit=bybit, mt5=mt5)

    gateway.warm_live_execution()

    assert bybit.calls == [("risk", "bybit-live-main")]
    assert mt5.calls == [("capability", "mt5-live-main")]


def test_execution_reads_are_reused_within_the_short_admission_window() -> None:
    bybit = RecordingAdapter()
    mt5 = RecordingAdapter()
    gateway = BybitMt5Gateway(settings=live_settings(), bybit=bybit, mt5=mt5)

    for _ in range(2):
        gateway.get_instrument_specification(
            account_id="bybit-live-main",
            symbol="XAUTUSDT",
            instrument_type="crypto_perp",
            category="linear",
        )
        gateway.get_market_quote(
            account_id="bybit-live-main",
            symbol="XAUTUSDT",
            instrument_type="crypto_perp",
            category="linear",
        )
        gateway.estimate_order_margin(
            account_id="bybit-live-main",
            symbol="XAUTUSDT",
            side="sell",
            quantity=Decimal("1"),
            reference_price=Decimal("4400"),
        )

    assert bybit.calls == [
        ("specification", "bybit-live-main"),
        ("quote", "bybit-live-main"),
        ("margin", "bybit-live-main"),
    ]
