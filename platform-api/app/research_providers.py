from __future__ import annotations

import asyncio
import math
from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx

from app.research_data_schemas import (
    AShareBreadthSnapshot,
    AShareIndexSnapshot,
    AShareTurnoverStock,
    MacroExpectationEvent,
    ShenwanMembership,
    ShortTermEmotionSnapshot,
)
from app.research_provider_a_share import AShareResearchProvider
from app.research_provider_errors import ResearchProviderError
from app.research_provider_macro import MacroResearchProvider
from app.research_provider_normalization import as_decimal as _decimal
from app.research_provider_normalization import as_non_negative_integer as _integer
from app.research_provider_normalization import first_present as _pick
from app.research_provider_normalization import frame_records as _records
from app.research_provider_normalization import percentage_change as _pct_change

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/150.0 Safari/537.36"
)
EASTMONEY_DATACENTER_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
TENCENT_QUOTE_URL = "https://qt.gtimg.cn/q="



def _akshare() -> Any:
    try:
        import akshare as ak
    except ImportError as exc:  # pragma: no cover - protected by dependency installation
        raise ResearchProviderError("akshare_dependency_missing") from exc
    return ak



class FreeResearchProvider:
    """Free-source adapters used only by the research domain.

    The provider normalizes third-party fields before they cross the Platform API boundary. It never
    supplies execution-authoritative quotes and never imports Venue or Broker SDKs.
    """

    def __init__(self, *, timeout_seconds: float = 20.0) -> None:
        self._timeout_seconds = timeout_seconds
        self._a_share = AShareResearchProvider(
            timeout_seconds=timeout_seconds,
            user_agent=USER_AGENT,
            akshare_loader=_akshare,
        )
        self._macro = MacroResearchProvider(
            timeout_seconds=timeout_seconds,
            user_agent=USER_AGENT,
        )

    async def a_share_spot(self) -> list[AShareTurnoverStock]:
        return await self._a_share.a_share_spot()

    async def market_activity(self) -> AShareBreadthSnapshot:
        return await self._a_share.market_activity()

    async def index_snapshots(self) -> list[AShareIndexSnapshot]:
        return await self._a_share.index_snapshots()



    async def shenwan_memberships(self) -> list[ShenwanMembership]:
        return await self._a_share.shenwan_memberships()

    async def short_term_emotion(self) -> ShortTermEmotionSnapshot:
        return await self._a_share.short_term_emotion()


    async def stock_quote(self, code: str) -> dict[str, Any]:
        prefix = "sh" if code.startswith(("6", "9", "5")) else ("bj" if code.startswith("8") else "sz")
        async with httpx.AsyncClient(timeout=self._timeout_seconds, trust_env=False) as client:
            response = await client.get(
                TENCENT_QUOTE_URL + prefix + code,
                headers={"User-Agent": USER_AGENT},
            )
            response.raise_for_status()
        text = response.content.decode("gbk", errors="ignore")
        if '"' not in text:
            raise ResearchProviderError("tencent_quote_empty")
        values = text.split('"', 2)[1].split("~")
        if len(values) < 53:
            raise ResearchProviderError("tencent_quote_malformed")

        def number(index: int) -> Decimal | None:
            return _decimal(values[index] if index < len(values) else None)

        return {
            "name": values[1],
            "code": code,
            "price": number(3),
            "lastClose": number(4),
            "open": number(5),
            "changeAmount": number(31),
            "changePct": number(32),
            "high": number(33),
            "low": number(34),
            "turnoverYuan": (number(37) * Decimal("10000")) if number(37) is not None else None,
            "turnoverPct": number(38),
            "peTtm": number(39),
            "amplitudePct": number(43),
            "marketCapYuan": (number(44) * Decimal("100000000")) if number(44) is not None else None,
            "floatMarketCapYuan": (number(45) * Decimal("100000000")) if number(45) is not None else None,
            "pb": number(46),
            "limitUp": number(47),
            "limitDown": number(48),
            "volumeRatio": number(49),
            "peStatic": number(52),
        }

    async def stock_financials(self, code: str) -> dict[str, Any]:
        def load() -> dict[str, Any]:
            frame = _akshare().stock_financial_abstract_ths(symbol=code, indicator="按报告期")
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
                _akshare().stock_profit_forecast_ths(
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
                                str(math.log(float(forward_pe / target_pe)) / math.log(float(1 + growth)))
                            )
            return {
                "forecasts": forecasts,
                "forwardPe": forward_pe,
                "growthPct": growth_pct,
                "peg": peg,
                "digestYears": digest_years,
                "analystCount": max((item["institutionCount"] for item in forecasts), default=0),
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
                    frame = _akshare().stock_zh_valuation_baidu(
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
                        "percentile": Decimal(below) / Decimal(max(len(ordered) - 1, 1)) * Decimal("100"),
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
            rows = _records(_akshare().stock_news_em(symbol=code))[:limit]
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

    async def stock_reports(self, code: str, limit: int = 30) -> list[dict[str, Any]]:
        params = {
            "industryCode": "*",
            "pageSize": str(limit),
            "industry": "*",
            "rating": "*",
            "ratingChange": "*",
            "beginTime": "2000-01-01",
            "endTime": "2035-01-01",
            "pageNo": "1",
            "qType": "0",
            "code": code,
        }
        async with httpx.AsyncClient(timeout=self._timeout_seconds, trust_env=False) as client:
            response = await client.get(
                "https://reportapi.eastmoney.com/report/list",
                params=params,
                headers={"User-Agent": USER_AGENT, "Referer": "https://data.eastmoney.com/"},
            )
            response.raise_for_status()
            rows = response.json().get("data") or []
        return [
            {
                "title": row.get("title"),
                "organization": row.get("orgSName") or row.get("orgName"),
                "author": row.get("researcher"),
                "rating": row.get("emRatingName") or row.get("rating"),
                "publishedAt": row.get("publishDate"),
                "pdfUrl": (
                    f"https://pdf.dfcfw.com/pdf/H3_{row.get('infoCode')}_1.pdf"
                    if row.get("infoCode")
                    else None
                ),
            }
            for row in rows[:limit]
        ]

    async def stock_announcements(self, code: str, limit: int = 20) -> list[dict[str, Any]]:
        params = {
            "sr": -1,
            "page_size": limit,
            "page_index": 1,
            "ann_type": "A",
            "client_source": "web",
            "stock_list": code,
            "f_node": 0,
            "s_node": 0,
        }
        async with httpx.AsyncClient(timeout=self._timeout_seconds, trust_env=False) as client:
            response = await client.get(
                "https://np-anotice-stock.eastmoney.com/api/security/ann",
                params=params,
                headers={"User-Agent": USER_AGENT},
            )
            response.raise_for_status()
            rows = ((response.json().get("data") or {}).get("list") or [])
        output = []
        for row in rows:
            columns = [
                item.get("column_name")
                for item in row.get("columns") or []
                if item.get("column_name")
            ]
            article_code = row.get("art_code")
            output.append(
                {
                    "date": str(row.get("notice_date") or "")[:10],
                    "title": row.get("title"),
                    "type": columns[0] if columns else None,
                    "url": (
                        f"https://data.eastmoney.com/notices/detail/{code}/{article_code}.html"
                        if article_code
                        else None
                    ),
                }
            )
        return output

    async def datacenter_rows(
        self,
        *,
        report_name: str,
        filter_value: str,
        page_size: int = 30,
        sort_columns: str = "",
        sort_types: str = "-1",
    ) -> list[dict[str, Any]]:
        params = {
            "reportName": report_name,
            "columns": "ALL",
            "filter": filter_value,
            "pageNumber": "1",
            "pageSize": str(page_size),
            "sortColumns": sort_columns,
            "sortTypes": sort_types,
            "source": "WEB",
            "client": "WEB",
        }
        async with httpx.AsyncClient(timeout=self._timeout_seconds, trust_env=False) as client:
            response = await client.get(
                EASTMONEY_DATACENTER_URL,
                params=params,
                headers={"User-Agent": USER_AGENT},
            )
            response.raise_for_status()
            result = response.json().get("result") or {}
        return result.get("data") or []

    async def stock_margin(self, code: str) -> list[dict[str, Any]]:
        rows = await self.datacenter_rows(
            report_name="RPTA_WEB_RZRQ_GGMX",
            filter_value=f'(SCODE="{code}")',
            sort_columns="DATE",
        )
        return [
            {
                "date": str(row.get("DATE") or "")[:10],
                "financingBalance": row.get("RZYE"),
                "financingBuy": row.get("RZMRE"),
                "financingRepay": row.get("RZCHE"),
                "securitiesBalance": row.get("RQYE"),
                "securitiesSell": row.get("RQMCL"),
                "totalBalance": row.get("RZRQYE"),
            }
            for row in rows
        ]

    async def stock_block_trades(self, code: str) -> list[dict[str, Any]]:
        rows = await self.datacenter_rows(
            report_name="RPT_DATA_BLOCKTRADE",
            filter_value=f'(SECURITY_CODE="{code}")',
            page_size=20,
            sort_columns="TRADE_DATE",
        )
        output = []
        for row in rows:
            close = _decimal(row.get("CLOSE_PRICE"))
            deal = _decimal(row.get("DEAL_PRICE"))
            output.append(
                {
                    "date": str(row.get("TRADE_DATE") or "")[:10],
                    "price": deal,
                    "close": close,
                    "premiumPct": _pct_change(deal, close),
                    "volume": row.get("DEAL_VOLUME"),
                    "amount": row.get("DEAL_AMT"),
                    "buyer": row.get("BUYER_NAME"),
                    "seller": row.get("SELLER_NAME"),
                }
            )
        return output

    async def stock_holders(self, code: str) -> list[dict[str, Any]]:
        rows = await self.datacenter_rows(
            report_name="RPT_HOLDERNUMLATEST",
            filter_value=f'(SECURITY_CODE="{code}")',
            page_size=12,
            sort_columns="END_DATE",
        )
        return [
            {
                "date": str(row.get("END_DATE") or "")[:10],
                "holderCount": row.get("HOLDER_NUM"),
                "changePct": row.get("HOLDER_NUM_RATIO"),
                "averageFreeShares": row.get("AVG_FREE_SHARES"),
            }
            for row in rows
        ]

    async def stock_dividends(self, code: str) -> list[dict[str, Any]]:
        rows = await self.datacenter_rows(
            report_name="RPT_SHAREBONUS_DET",
            filter_value=f'(SECURITY_CODE="{code}")',
            page_size=20,
            sort_columns="EX_DIVIDEND_DATE",
        )
        return [
            {
                "date": str(row.get("EX_DIVIDEND_DATE") or "")[:10],
                "pretaxBonusRmb": row.get("PRETAX_BONUS_RMB"),
                "transferRatio": row.get("TRANSFER_RATIO"),
                "bonusRatio": row.get("BONUS_RATIO"),
                "progress": row.get("ASSIGN_PROGRESS"),
            }
            for row in rows
        ]

    async def stock_fund_flow(self, code: str) -> dict[str, Any]:
        market_code = 1 if code.startswith("6") else 0
        params = {
            "secid": f"{market_code}.{code}",
            "fields1": "f1,f2,f3,f7",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
            "lmt": "120",
        }
        async with httpx.AsyncClient(timeout=self._timeout_seconds, trust_env=False) as client:
            response = await client.get(
                "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get",
                params=params,
                headers={"User-Agent": USER_AGENT, "Referer": "https://quote.eastmoney.com/"},
            )
            response.raise_for_status()
            lines = (response.json().get("data") or {}).get("klines") or []
        rows = []
        for line in lines:
            parts = str(line).split(",")
            if len(parts) < 6:
                continue
            rows.append(
                {
                    "date": parts[0],
                    "mainNet": _decimal(parts[1]) or Decimal("0"),
                    "smallNet": _decimal(parts[2]) or Decimal("0"),
                    "mediumNet": _decimal(parts[3]) or Decimal("0"),
                    "largeNet": _decimal(parts[4]) or Decimal("0"),
                    "superNet": _decimal(parts[5]) or Decimal("0"),
                }
            )
        return {
            "history": rows,
            "mainNet20d": sum((item["mainNet"] for item in rows[-20:]), Decimal("0")),
        }

    async def stock_dragon_tiger(self, code: str) -> dict[str, Any]:
        end = date.today()
        start = end - timedelta(days=45)
        rows = await self.datacenter_rows(
            report_name="RPT_DAILYBILLBOARD_DETAILSNEW",
            filter_value=(
                f"(TRADE_DATE>='{start.isoformat()}')(TRADE_DATE<='{end.isoformat()}')"
                f'(SECURITY_CODE="{code}")'
            ),
            page_size=50,
            sort_columns="TRADE_DATE",
        )
        records = [
            {
                "date": str(row.get("TRADE_DATE") or "")[:10],
                "reason": row.get("EXPLANATION"),
                "netBuyYuan": row.get("BILLBOARD_NET_AMT"),
                "turnoverPct": row.get("TURNOVERRATE"),
            }
            for row in rows
        ]
        seats: dict[str, list[dict[str, Any]]] = {"buy": [], "sell": []}
        if records:
            latest = records[0]["date"]
            for side, report, sort_column in (
                ("buy", "RPT_BILLBOARD_DAILYDETAILSBUY", "BUY"),
                ("sell", "RPT_BILLBOARD_DAILYDETAILSSELL", "SELL"),
            ):
                details = await self.datacenter_rows(
                    report_name=report,
                    filter_value=f"(TRADE_DATE='{latest}')(SECURITY_CODE=\"{code}\")",
                    page_size=10,
                    sort_columns=sort_column,
                )
                seats[side] = [
                    {
                        "name": row.get("OPERATEDEPT_NAME"),
                        "buyYuan": row.get("BUY"),
                        "sellYuan": row.get("SELL"),
                        "netYuan": row.get("NET"),
                    }
                    for row in details[:5]
                ]
        return {"records": records, "seats": seats}

    async def stock_lockup(self, code: str) -> dict[str, Any]:
        today = date.today()
        end = today + timedelta(days=90)
        history_rows, upcoming_rows = await asyncio.gather(
            self.datacenter_rows(
                report_name="RPT_LIFT_STAGE",
                filter_value=f'(SECURITY_CODE="{code}")',
                page_size=15,
                sort_columns="FREE_DATE",
            ),
            self.datacenter_rows(
                report_name="RPT_LIFT_STAGE",
                filter_value=(
                    f'(SECURITY_CODE="{code}")(FREE_DATE>=\'{today.isoformat()}\')'
                    f"(FREE_DATE<='{end.isoformat()}')"
                ),
                page_size=20,
                sort_columns="FREE_DATE",
                sort_types="1",
            ),
        )

        def normalize(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
            return [
                {
                    "date": str(row.get("FREE_DATE") or "")[:10],
                    "type": row.get("FREE_SHARES_TYPE"),
                    "shares": row.get("FREE_SHARES"),
                    "availableShares": row.get("ABLE_FREE_SHARES"),
                    "ratioPct": row.get("FREE_RATIO"),
                }
                for row in rows
            ]

        return {"history": normalize(history_rows), "upcoming": normalize(upcoming_rows)}

    async def stock_investor_qa(self, code: str, limit: int = 30) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self._timeout_seconds, trust_env=False) as client:
            lookup = await client.post(
                "https://irm.cninfo.com.cn/newircs/index/queryKeyboardInfo",
                data={"keyWord": code},
                headers={"User-Agent": USER_AGENT},
            )
            lookup.raise_for_status()
            matches = lookup.json().get("data") or []
            if not matches:
                return []
            org_id = matches[0].get("secid")
            response = await client.post(
                "https://irm.cninfo.com.cn/newircs/company/question",
                params={
                    "_t": 1,
                    "stockcode": code,
                    "orgId": org_id,
                    "pageSize": limit,
                    "pageNum": 1,
                    "keyWord": "",
                    "startDay": "",
                    "endDay": "",
                },
                headers={"User-Agent": USER_AGENT},
            )
            response.raise_for_status()
            rows = response.json().get("rows") or []
        output = []
        for row in rows:
            timestamp = row.get("pubDate")
            asked_at = None
            if isinstance(timestamp, (int, float)):
                asked_at = datetime.fromtimestamp(timestamp / 1000, tz=UTC).isoformat()
            output.append(
                {
                    "company": row.get("companyShortName"),
                    "question": row.get("mainContent"),
                    "answer": row.get("attachedContent"),
                    "answerer": row.get("attachedAuthor"),
                    "askedAt": asked_at,
                }
            )
        return output

    async def macro_expectation_events(
        self, limit: int = 12
    ) -> list[MacroExpectationEvent]:
        return await self._macro.macro_expectation_events(limit=limit)
