from __future__ import annotations

from decimal import Decimal

import pytest

from app.bybit_acceptance_adapter import BybitAcceptanceAdapter
from app.config import Settings, get_settings
from app.gateway_errors import GatewayConfigurationError


class AccountClient:
    def __init__(self):
        self.wallet_reads = 0
        self.pages = []
        self.repeat_cursor = False

    def get_wallet_balance(self, **kwargs):
        self.wallet_reads += 1
        return {
            "retCode": 0,
            "result": {
                "list": [
                    {
                        "totalEquity": "1000",
                        "totalWalletBalance": "990",
                        "totalAvailableBalance": "495",
                        "totalInitialMargin": "505",
                        "coin": [
                            {
                                "coin": "USDT",
                                "equity": "1000",
                                "usdValue": "990",
                                "walletBalance": "1000",
                                "locked": "100",
                                "totalOrderIM": "0",
                                "totalPositionIM": "0",
                                "bonus": "0",
                                "spotBorrow": "0",
                                "availableToWithdraw": "999999",
                            }
                        ],
                    }
                ]
            },
        }

    def get_account_info(self):
        return {"retCode": 0, "result": {"marginMode": "REGULAR_MARGIN"}}

    def get_asset_overview(self, **kwargs):
        assert kwargs == {"valuationCurrency": "USD"}
        return {
            "retCode": 0,
            "result": {
                "totalEquity": "5000",
                "list": [
                    {
                        "accountType": "UnifiedTradingAccount",
                        "totalEquity": "1000",
                        "valuationCurrency": "USD",
                        "categories": [{"category": "stocks", "equity": "100"}],
                    },
                    {"accountType": "Earn", "totalEquity": "500", "valuationCurrency": "USD"},
                    {"accountType": "TradFi", "totalEquity": "3500", "valuationCurrency": "USD"},
                ],
            },
        }

    def get_positions(self, **kwargs):
        return {"retCode": 0, "result": {"list": []}}

    def get_open_orders(self, **kwargs):
        assert kwargs["limit"] <= 50
        self.pages.append(kwargs.get("cursor"))
        second = kwargs.get("cursor") is not None
        return {
            "retCode": 0,
            "result": {
                "nextPageCursor": "page-2" if not second or self.repeat_cursor else "",
                "list": [
                    {
                        "symbol": "BTCUSDT",
                        "orderId": "2" if second else "1",
                        "side": "Buy",
                        "qty": "1",
                        "price": "100",
                        "orderStatus": "New",
                        "createdTime": "1788797000000",
                        "updatedTime": "1788797000000",
                    }
                ],
            },
        }

    def get_order_history(self, **kwargs):
        assert kwargs["limit"] <= 50
        assert kwargs["endTime"] - kwargs["startTime"] <= 7 * 86400000
        return {"retCode": 0, "result": {"list": []}}

    def get_executions(self, **kwargs):
        assert kwargs["limit"] <= 100
        return {
            "retCode": 0,
            "result": {
                "list": [
                    {
                        "execType": "Funding",
                        "execId": "funding-1",
                        "execQty": "1",
                        "execPrice": "100",
                    },
                    {
                        "execType": "Trade",
                        "execId": "trade-1",
                        "orderId": "3",
                        "symbol": "BTCUSDT",
                        "side": "Buy",
                        "execQty": "1",
                        "execPrice": "100",
                        "execFee": "0.001",
                        "feeCurrency": "BTC",
                        "execTime": "1788797000000",
                    },
                ]
            },
        }

    def get_transaction_log(self, **kwargs):
        assert "category" not in kwargs
        return {"retCode": 0, "result": {"list": []}}


@pytest.fixture
def adapter(tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "journal_path", str(tmp_path / "journal.db"))
    return BybitAcceptanceAdapter(
        Settings(
            _env_file=None,
            bybit_account_ids="account",
            bybit_category="linear",
            bybit_instrument_map="BTCUSDT=btc",
        ),
        AccountClient(),
    )


def test_currency_and_asset_scope_stay_separate_and_wallet_is_read_once(adapter):
    snapshot = adapter.get_account_snapshot("account")
    risk = snapshot.account_risk
    assert risk.currency == "USD"
    assert risk.equity == Decimal("1000")
    assert risk.wallet_balance == Decimal("990")
    assert risk.total_assets == Decimal("5000")
    assert risk.asset_scope == "unified_trading"
    assert len(risk.asset_breakdown) == 3
    assert snapshot.balances[0].available_balance == Decimal("500")
    assert snapshot.balances[0].currency == "USDT"
    assert adapter._injected_client.wallet_reads == 1
    assert adapter._injected_client.pages == [None, "page-2"]
    assert len(snapshot.orders) == 2
    assert [fill.external_fill_id for fill in snapshot.fills] == ["trade-1"]
    assert snapshot.fills[0].currency == "BTC"
    assert "credentialRef" not in snapshot.identity


def test_missing_coin_cash_evidence_is_unknown_and_zero_remains_zero(adapter):
    coin = adapter._injected_client.get_wallet_balance()["result"]["list"][0]["coin"][0]
    coin["walletBalance"] = "100"
    assert adapter._available_balance(coin, account_available=Decimal("495")) == 0
    del coin["usdValue"]
    coin["locked"] = "0"
    assert adapter._available_balance(coin, account_available=Decimal("495")) is None
    del coin["totalOrderIM"]
    assert adapter._available_balance(coin, account_available=Decimal("495")) is None


def test_overview_failure_does_not_replace_trading_equity_with_zero(adapter, monkeypatch):
    monkeypatch.setattr(
        adapter._injected_client, "get_asset_overview", lambda **kwargs: {"retCode": 10005}
    )
    risk = adapter.get_account_risk("account", include_asset_overview=True)
    assert risk.equity == Decimal("1000")
    assert risk.total_assets is None
    assert risk.asset_overview_quality == "unavailable"


def test_repeated_page_cursor_fails_instead_of_returning_truncated_holdings(adapter):
    adapter._injected_client.repeat_cursor = True
    with pytest.raises(GatewayConfigurationError, match="pagination"):
        adapter.get_account_snapshot("account")
