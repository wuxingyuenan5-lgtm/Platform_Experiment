from datetime import UTC
from decimal import Decimal
from types import SimpleNamespace

from app.config import Settings
from app.mt5_live_adapter import Mt5LiveAdapter


class FakeMt5MarketData:
    def terminal_info(self):
        return SimpleNamespace(connected=True)

    def account_info(self):
        return SimpleNamespace(login=123, server="offline", currency="EUR")

    def symbol_info_tick(self, symbol):
        return SimpleNamespace(bid=4040.1, ask=4040.4, last=4040.2)

    def symbol_info(self, symbol):
        return SimpleNamespace(
            swap_long=-78.29,
            swap_short=29.49,
            swap_mode=1,
            swap_rollover3days=3,
            trade_contract_size=100.0,
            currency_base="XAU",
            currency_profit="USD",
        )


def test_mt5_worker_quote_exposes_swap_and_instrument_currency_without_reconnecting(monkeypatch):
    adapter = Mt5LiveAdapter(Settings(_env_file=None, mt5_account_ids="mt5-1"))
    mt5 = FakeMt5MarketData()
    monkeypatch.setattr(adapter, "_connect", lambda: mt5)
    monkeypatch.setattr(
        "app.mt5_symbol_resolver.resolve_mt5_symbol", lambda **_: SimpleNamespace(symbol="XAUUSD+")
    )
    quote = adapter.get_market_quote(account_id="mt5-1", symbol="XAUUSD+")
    assert quote.bid == Decimal("4040.1")
    assert quote.currency == "USD"
    assert quote.raw_payload["swap_long"] == "-78.29"
    assert quote.raw_payload["swap_short"] == "29.49"
    assert quote.raw_payload["swap_mode"] == "1"
    assert quote.raw_payload["swap_rollover3days"] == "3"
    assert quote.raw_payload["trade_contract_size"] == "100.0"
    assert quote.as_of.tzinfo == UTC
