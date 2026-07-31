from __future__ import annotations

import asyncio
import math
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from app.research_provider_normalization import as_decimal as _decimal
from app.research_provider_normalization import as_non_negative_integer as _integer
from app.research_provider_normalization import first_present as _pick
from app.research_provider_normalization import frame_records as _records

AkshareLoader = Callable[[], Any]


class StockAkshareResearchProvider:
    def __init__(self, *, akshare_loader: AkshareLoader) -> None:
        self._akshare = akshare_loader

    async def stock_financials(self, code: str) -> dict[str, Any]:
        def load() -> dict[str, Any]:
            frame = self._akshare().stock_financial_abstract_ths(
                symbol=code,
                indicator="按报告期",
            )
            rows = _records(frame)
            if not rows:
                return {}
            row = rows[-1]
            return {
                "period": _pick(row, "报告期"),
                "revenue": _pick(row, "营业总收入"),
                "revenueYoy": _pick(row, "营业总收入同比增长率"),
                "netProfit": _pick(row, "净利润"),
                "netProfitYoy": _pick(row, "净利润同比增长率"),
                "eps": _pick(row, "基本每股收益"),
                "bvps": _pick(row, "每股净资产"),
                "roe": _pick(row, "净资产收益率"),
                "grossMargin": _pick(row, "销售毛利率"),
                "netMargin": _pick(row, "销售净利率"),
                "operatingCashFlowPerShare": _pick(row, "每股经营现金流"),
            }

        return await asyncio.to_thread(load)

    async def stock_forecast(self, code: str, price: Decimal | None) -> dict[str, Any]:
        def load() -> dict[str, Any]:
            rows = _records(
                self._akshare().stock_profit_forecast_ths(
                    symbol=code,
                    indicator="预测年报每股收益",
                )
            )
            forecasts = []
            for row in rows:
                forecasts.append(
                    {
                        "year": str(_pick(row, "年度") or ""),
                        "meanEps": _decimal(_pick(row, "均值")),
                        "institutionCount": _integer(_pick(row, "预测机构数")),
                    }
                )
            valid = [item for item in forecasts if item["meanEps"] and item["meanEps"] > 0]
            forward_pe = None
            growth_pct = None
            peg = None
            digest_years = None
            if price is not None and valid:
                forward_pe = price / valid[0]["meanEps"]
                if len(valid) >= 2:
                    growth = valid[1]["meanEps"] / valid[0]["meanEps"] - Decimal("1")
                    growth_pct = growth * Decimal("100")
                    if growth > 0:
                        peg = forward_pe / growth_pct
                        target_pe = Decimal("30")
                        if forward_pe <= target_pe:
                            digest_years = Decimal("0")
                        else:
                            digest_years = Decimal(
                                str(
                                    math.log(float(forward_pe / target_pe))
                                    / math.log(float(1 + growth))
                                )
                            )
            return {
                "forecasts": forecasts,
                "forwardPe": forward_pe,
                "growthPct": growth_pct,
                "peg": peg,
                "digestYears": digest_years,
                "analystCount": max(
                    (item["institutionCount"] for item in forecasts),
                    default=0,
                ),
            }

        return await asyncio.to_thread(load)

    async def stock_valuation_percentile(self, code: str) -> dict[str, Any]:
        def quantile(values: list[Decimal], ratio: float) -> Decimal:
            index = ratio * (len(values) - 1)
            low = int(index)
            high = min(low + 1, len(values) - 1)
            fraction = Decimal(str(index - low))
            return values[low] * (Decimal("1") - fraction) + values[high] * fraction

        def load() -> dict[str, Any]:
            metrics: dict[str, Any] = {}
            for key, indicator in (("peTtm", "市盈率(TTM)"), ("pb", "市净率")):
                try:
                    frame = self._akshare().stock_zh_valuation_baidu(
                        symbol=code,
                        indicator=indicator,
                        period="近五年",
                    )
                    rows = _records(frame)
                    values = [
                        item
                        for item in (_decimal(list(row.values())[-1]) for row in rows)
                        if item is not None
                    ]
                    if not values:
                        continue
                    current = values[-1]
                    ordered = sorted(values)
                    below = sum(1 for item in ordered if item < current)
                    metrics[key] = {
                        "current": current,
                        "percentile": Decimal(below)
                        / Decimal(max(len(ordered) - 1, 1))
                        * Decimal("100"),
                        "min": ordered[0],
                        "max": ordered[-1],
                        "p20": quantile(ordered, 0.2),
                        "p50": quantile(ordered, 0.5),
                        "p80": quantile(ordered, 0.8),
                        "observations": len(ordered),
                    }
                except Exception:
                    continue
            return {"period": "近5年", "metrics": metrics}

        return await asyncio.to_thread(load)

    async def stock_news(self, code: str, limit: int = 20) -> list[dict[str, Any]]:
        def load() -> list[dict[str, Any]]:
            rows = _records(self._akshare().stock_news_em(symbol=code))[:limit]
            return [
                {
                    "title": _pick(row, "新闻标题", "标题"),
                    "content": _pick(row, "新闻内容", "内容"),
                    "publishedAt": _pick(row, "发布时间", "日期"),
                    "source": _pick(row, "文章来源", "来源"),
                    "url": _pick(row, "新闻链接", "链接"),
                }
                for row in rows
            ]

        return await asyncio.to_thread(load)
