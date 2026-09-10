from copy import deepcopy
from decimal import Decimal

import pytest

from app.bybit_market_data import BybitMarketData
from app.gateway_errors import GatewayConfigurationError


def market_row(category="spot"):
    lot = (
        {"basePrecision": "0.000001", "minOrderQty": "0.000001", "minOrderAmt": "5"}
        if category == "spot"
        else {"qtyStep": "0.001", "minOrderQty": "0.001", "minNotionalValue": "10"}
    )
    return {
        "symbol": "XAUTUSDT",
        "baseCoin": "XAUT",
        "quoteCoin": "USDT",
        "settleCoin": "USDT",
        "status": "Trading",
        "contractType": "LinearPerpetual",
        "marginTrading": "none",
        "priceFilter": {"tickSize": "0.0000000001"},
        "lotSizeFilter": {**lot, "maxOrderQty": "500", "maxMarketOrderQty": "120"},
    }


def test_ccxt_separates_markets_preserves_decimal_strings_and_keeps_native_evidence():
    calls = []

    def read(method, **params):
        calls.append((method, params))
        rows = [] if params.get("status") == "PreLaunch" else [market_row(params["category"])]
        return {
            "retCode": 0,
            "result": {"category": params["category"], "list": rows, "nextPageCursor": ""},
        }

    reader = BybitMarketData(read)
    try:
        spot = reader.market("spot", "XAUTUSDT")
        perp = reader.market("linear", "XAUTUSDT")
        assert spot["symbol"] == "XAUT/USDT"
        assert perp["symbol"] == "XAUT/USDT:USDT"
        assert spot["precision"]["amount"] == "0.000001"
        assert perp["precision"]["amount"] == "0.001"
        assert spot["precision"]["price"] == "0.0000000001"
        assert spot["limits"]["cost"]["min"] == "5"
        assert perp["limits"]["cost"]["min"] == "10"
        assert perp["linear"] is True
        assert spot["info"] == market_row("spot")
        assert spot["info"]["lotSizeFilter"]["maxMarketOrderQty"] == "120"
        assert reader.market("spot", "XAUTUSDT") is spot
        assert len(calls) == 3
    finally:
        reader.close()


def test_quote_and_funding_use_exact_strings_and_preserve_source_timestamp():
    raw = {
        "retCode": 0,
        "time": 1788832800123,
        "result": {
            "category": "linear",
            "list": [
                {
                    "symbol": "XAUTUSDT",
                    "bid1Price": "3500.1234567891",
                    "ask1Price": "3500.1234567892",
                    "lastPrice": "3500.1234567891",
                    "fundingRate": "0.000012345678901234",
                    "nextFundingTime": "1788854400000",
                }
            ],
        },
    }

    def read(method, **params):
        if method == "get_tickers":
            return deepcopy(raw)
        return {"retCode": 0, "result": {"category": "linear", "list": [market_row("linear")]}}

    reader = BybitMarketData(read)
    try:
        _, ticker, funding, receipt = reader.ticker("linear", "XAUTUSDT")
        assert ticker["bid"] == "3500.1234567891"
        assert Decimal(ticker["ask"]) - Decimal(ticker["bid"]) == Decimal("0.0000000001")
        assert funding["fundingRate"] == "0.000012345678901234"
        assert funding["fundingTimestamp"] == 1788854400000
        assert receipt == raw
    finally:
        reader.close()


def test_ccxt_market_reader_rejects_writes_and_wrong_categories():
    calls = []
    reader = BybitMarketData(
        lambda *args, **kwargs: calls.append(args) or {"result": {"category": "inverse"}}
    )
    with pytest.raises(GatewayConfigurationError, match="cannot issue"):
        reader._request("v5/order/create", "private", "POST", {})
    assert calls == []
    with pytest.raises(GatewayConfigurationError, match="category mismatch"):
        reader.market("spot", "XAUTUSDT")
    reader.close()


def test_repeated_market_cursor_is_bounded_and_never_cached_as_success():
    calls = []

    def read(method, **params):
        calls.append(params)
        return {
            "retCode": 0,
            "result": {
                "category": "linear",
                "list": [market_row("linear")],
                "nextPageCursor": "stuck",
            },
        }

    reader = BybitMarketData(read)
    with pytest.raises(GatewayConfigurationError, match="did not converge"):
        reader.market("linear", "XAUTUSDT")
    assert len(calls) == 3
    assert not reader._markets
    reader.close()
