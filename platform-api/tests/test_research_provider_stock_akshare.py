from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any

import pytest

from app.research_provider_stock_akshare import StockAkshareResearchProvider

pytestmark = pytest.mark.unit


class _Frame:
    empty = False

    def __init__(self, records: list[dict[str, Any]]) -> None:
        self._records = records

    def to_dict(self, orient: str) -> list[dict[str, Any]]:
        assert orient == "records"
        return self._records


class _Akshare:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def stock_financial_abstract_ths(self, **kwargs: Any) -> _Frame:
        self.calls.append(("stock_financial_abstract_ths", kwargs))
        return _Frame(
            [
                {"报告期": "2025-12-31", "营业总收入": 80},
                {
                    "报告期": "2026-06-30",
                    "营业总收入": 100,
                    "营业总收入同比增长率": 12.5,
                    "净利润": 20,
                    "净利润同比增长率": 15.5,
                    "基本每股收益": 1.2,
                    "每股净资产": 8.8,
                    "净资产收益率": 13.6,
                    "销售毛利率": 42.1,
                    "销售净利率": 20.0,
                    "每股经营现金流": 1.5,
                },
            ]
        )

    def stock_profit_forecast_ths(self, **kwargs: Any) -> _Frame:
        self.calls.append(("stock_profit_forecast_ths", kwargs))
        return _Frame(
            [
                {"年度": "2027", "均值": "2", "预测机构数": "8"},
                {"年度": "2028", "均值": "3", "预测机构数": "12"},
            ]
        )

    def stock_zh_valuation_baidu(self, **kwargs: Any) -> _Frame:
        self.calls.append(("stock_zh_valuation_baidu", kwargs))
        if kwargs["indicator"] == "市净率":
            raise RuntimeError("pb unavailable")
        return _Frame(
            [
                {"date": "2026-01-01", "value": "10"},
                {"date": "2026-02-01", "value": "20"},
                {"date": "2026-03-01", "value": "30"},
            ]
        )

    def stock_news_em(self, **kwargs: Any) -> _Frame:
        self.calls.append(("stock_news_em", kwargs))
        return _Frame(
            [
                {
                    "新闻标题": "新闻一",
                    "新闻内容": "内容一",
                    "发布时间": "2026-07-31 09:00:00",
                    "文章来源": "来源一",
                    "新闻链接": "https://example.com/1",
                },
                {
                    "标题": "新闻二",
                    "内容": "内容二",
                    "日期": "2026-07-31 08:00:00",
                    "来源": "来源二",
                    "链接": "https://example.com/2",
                },
                {"新闻标题": "新闻三"},
            ]
        )


def _provider() -> tuple[StockAkshareResearchProvider, _Akshare]:
    akshare = _Akshare()
    return StockAkshareResearchProvider(akshare_loader=lambda: akshare), akshare


def test_financials_preserve_latest_row_mapping_and_call_contract() -> None:
    provider, akshare = _provider()

    result = asyncio.run(provider.stock_financials("600000"))

    assert result == {
        "period": "2026-06-30",
        "revenue": 100,
        "revenueYoy": 12.5,
        "netProfit": 20,
        "netProfitYoy": 15.5,
        "eps": 1.2,
        "bvps": 8.8,
        "roe": 13.6,
        "grossMargin": 42.1,
        "netMargin": 20.0,
        "operatingCashFlowPerShare": 1.5,
    }
    assert akshare.calls == [
        (
            "stock_financial_abstract_ths",
            {"symbol": "600000", "indicator": "按报告期"},
        )
    ]


def test_forecast_preserves_order_valuation_and_analyst_count() -> None:
    provider, akshare = _provider()

    result = asyncio.run(provider.stock_forecast("600000", Decimal("20")))

    assert result["forecasts"] == [
        {"year": "2027", "meanEps": Decimal("2"), "institutionCount": 8},
        {"year": "2028", "meanEps": Decimal("3"), "institutionCount": 12},
    ]
    assert result["forwardPe"] == Decimal("10")
    assert result["growthPct"] == Decimal("50.0")
    assert result["peg"] == Decimal("0.2")
    assert result["digestYears"] == Decimal("0")
    assert result["analystCount"] == 12
    assert akshare.calls == [
        (
            "stock_profit_forecast_ths",
            {"symbol": "600000", "indicator": "预测年报每股收益"},
        )
    ]


def test_valuation_preserves_quantiles_and_metric_failure_isolation() -> None:
    provider, akshare = _provider()

    result = asyncio.run(provider.stock_valuation_percentile("600000"))

    assert result["period"] == "近5年"
    assert set(result["metrics"]) == {"peTtm"}
    metric = result["metrics"]["peTtm"]
    assert metric == {
        "current": Decimal("30"),
        "percentile": Decimal("100"),
        "min": Decimal("10"),
        "max": Decimal("30"),
        "p20": Decimal("14.0"),
        "p50": Decimal("20.0"),
        "p80": Decimal("26.0"),
        "observations": 3,
    }
    assert akshare.calls == [
        (
            "stock_zh_valuation_baidu",
            {"symbol": "600000", "indicator": "市盈率(TTM)", "period": "近五年"},
        ),
        (
            "stock_zh_valuation_baidu",
            {"symbol": "600000", "indicator": "市净率", "period": "近五年"},
        ),
    ]


def test_news_preserves_limit_and_fallback_field_mapping() -> None:
    provider, akshare = _provider()

    result = asyncio.run(provider.stock_news("600000", limit=2))

    assert result == [
        {
            "title": "新闻一",
            "content": "内容一",
            "publishedAt": "2026-07-31 09:00:00",
            "source": "来源一",
            "url": "https://example.com/1",
        },
        {
            "title": "新闻二",
            "content": "内容二",
            "publishedAt": "2026-07-31 08:00:00",
            "source": "来源二",
            "url": "https://example.com/2",
        },
    ]
    assert akshare.calls == [("stock_news_em", {"symbol": "600000"})]
