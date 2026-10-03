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


def test_market_catalog_reads_all_pages_through_same_public_reader():
    calls = []

    def read(method, **params):
        calls.append((method, params))
        return {
            "retCode": 0,
            "result": {
                "category": params["category"],
                "list": [market_row(params["category"])],
                "nextPageCursor": "",
            },
        }

    reader = BybitMarketData(read)
    try:
        markets = reader.markets("spot")
        assert len(markets) == 1
        assert markets[0]["id"] == "XAUTUSDT"
        assert calls[0][0] == "get_instruments_info"
        assert calls[0][1]["category"] == "spot"
    finally:
        reader.close()


def test_market_catalog_is_cached_for_the_ttl():
    calls = []

    def read(method, **params):
        calls.append((method, params))
        return {
            "retCode": 0,
            "result": {
                "category": params["category"],
                "list": [market_row(params["category"])],
                "nextPageCursor": "",
            },
        }

    reader = BybitMarketData(read)
    try:
        first = reader.markets("spot")
        second = reader.markets("spot")
        assert first == second
        assert len(calls) == 1
    finally:
        reader.close()


def test_independent_ticker_network_reads_do_not_hold_parser_lock():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    barrier = Barrier(2, timeout=2)

    def read(method, **params):
        category = params["category"]
        if method == "get_tickers":
            barrier.wait()
            return {"time": 1788832800123, "result": {"category": category, "list": [
                {"symbol": "XAUTUSDT", "bid1Price": "3500.1", "ask1Price": "3500.2"}
            ]}}
        rows = [] if params.get("status") == "PreLaunch" else [market_row(category)]
        return {"result": {"category": category, "list": rows, "nextPageCursor": ""}}

    reader = BybitMarketData(read)
    try:
        reader.market("spot", "XAUTUSDT")
        reader.market("linear", "XAUTUSDT")
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(reader.ticker, category, "XAUTUSDT")
                    for category in ("spot", "linear")]
            results = [job.result() for job in jobs]
        assert [result[0]["spot"] for result in results] == [True, False]
        assert all(result[1]["bid"] == "3500.1" for result in results)
        assert all(result[3]["time"] == 1788832800123 for result in results)
    finally:
        reader.close()
