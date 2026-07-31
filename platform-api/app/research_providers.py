from __future__ import annotations

import asyncio
import math
from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx

from app.a_share_research_policy import annualized_volatility_20
from app.research_data_schemas import (
    AShareBreadthSnapshot,
    AShareIndexSnapshot,
    AShareTurnoverStock,
    EmotionLadderRow,
    EmotionStockRow,
    MacroExpectationEvent,
    ShenwanMembership,
    ShortTermEmotionSnapshot,
)
from app.research_provider_errors import ResearchProviderError
from app.research_provider_macro import MacroResearchProvider
from app.research_provider_normalization import as_date as _date
from app.research_provider_normalization import as_decimal as _decimal
from app.research_provider_normalization import as_non_negative_integer as _integer
from app.research_provider_normalization import closest_prior_close as _closest_prior
from app.research_provider_normalization import first_present as _pick
from app.research_provider_normalization import frame_records as _records
from app.research_provider_normalization import percentage_change as _pct_change
from app.research_provider_normalization import trend_marker as _trend

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/150.0 Safari/537.36"
)
EASTMONEY_DATACENTER_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"
TENCENT_QUOTE_URL = "https://qt.gtimg.cn/q="

INDEX_DEFINITIONS: tuple[tuple[str, str, str], ...] = (
    ("000001", "上证指数", "sh000001"),
    ("000300", "沪深300", "csi000300"),
    ("000016", "上证50", "sh000016"),
    ("399673", "创业板50", "sz399673"),
    ("000688", "科创50", "sh000688"),
    ("000905", "中证500", "csi000905"),
    ("932000", "中证2000", "csi932000"),
    ("930050", "中证A50", "csi930050"),
)


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
        self._macro = MacroResearchProvider(
            timeout_seconds=timeout_seconds,
            user_agent=USER_AGENT,
        )

    async def a_share_spot(self) -> list[AShareTurnoverStock]:
        def load() -> list[AShareTurnoverStock]:
            frame = _akshare().stock_zh_a_spot_em()
            result: list[AShareTurnoverStock] = []
            for row in _records(frame):
                code = str(_pick(row, "代码", "证券代码") or "").zfill(6)
                name = str(_pick(row, "名称", "证券简称") or "").strip()
                turnover = _decimal(_pick(row, "成交额", "成交金额"))
                if len(code) != 6 or not name or turnover is None:
                    continue
                result.append(
                    AShareTurnoverStock(
                        security_code=code,
                        security_name=name,
                        turnover_yuan=max(turnover, Decimal("0")),
                        return_pct=_decimal(_pick(row, "涨跌幅")),
                    )
                )
            return result

        return await asyncio.to_thread(load)

    async def market_activity(self) -> AShareBreadthSnapshot:
        def load() -> AShareBreadthSnapshot:
            frame = _akshare().stock_market_activity_legu()
            records = _records(frame)
            values: dict[str, Any] = {}
            for row in records:
                row_values = list(row.values())
                if len(row_values) >= 2:
                    values[str(row_values[0]).strip()] = row_values[1]
            from app.a_share_research_policy import classify_market_breadth, classify_speculation

            up = _integer(values.get("上涨"))
            down = _integer(values.get("下跌"))
            real_limit_up = _integer(values.get("真实涨停"))
            trade_date = _date(values.get("统计日期"))
            activity_value = values.get("活跃度")
            activity = _decimal(str(activity_value).replace("%", ""))
            return AShareBreadthSnapshot(
                up=up,
                down=down,
                flat=_integer(values.get("平盘")),
                limit_up=_integer(values.get("涨停")),
                real_limit_up=real_limit_up,
                limit_down=_integer(values.get("跌停")),
                real_limit_down=_integer(values.get("真实跌停")),
                activity_pct=activity,
                breadth_state=classify_market_breadth(up, down),
                speculation_state=classify_speculation(real_limit_up),
                trade_date=trade_date,
            )

        return await asyncio.to_thread(load)

    async def index_snapshots(self) -> list[AShareIndexSnapshot]:
        tasks = [self._index_snapshot(code, name, symbol) for code, name, symbol in INDEX_DEFINITIONS]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        snapshots = [item for item in results if isinstance(item, AShareIndexSnapshot)]
        if not snapshots:
            raise ResearchProviderError("a_share_index_history_unavailable")
        return snapshots

    async def _index_snapshot(self, code: str, name: str, symbol: str) -> AShareIndexSnapshot:
        def load() -> AShareIndexSnapshot:
            frame = _akshare().stock_zh_index_daily_em(symbol=symbol)
            history: list[dict[str, Any]] = []
            for row in _records(frame)[-280:]:
                observed = _date(_pick(row, "date", "日期"))
                close = _decimal(_pick(row, "close", "收盘"))
                if observed is None or close is None or close <= 0:
                    continue
                history.append(
                    {
                        "date": observed,
                        "close": close,
                        "amount": _decimal(_pick(row, "amount", "成交额")),
                    }
                )
            history.sort(key=lambda item: item["date"])
            if len(history) < 2:
                raise ResearchProviderError(f"index_history_empty:{code}")
            latest = history[-1]
            closes = [item["close"] for item in history]
            current = latest["close"]
            latest_date = latest["date"]
            year_start = date(latest_date.year, 1, 1)
            quarter_month = ((latest_date.month - 1) // 3) * 3 + 1
            quarter_start = date(latest_date.year, quarter_month, 1)
            high_52 = max(closes[-252:]) if closes else None
            one_hour = self._intraday_signal(code)
            return AShareIndexSnapshot(
                code=code,
                name=name,
                source_symbol=symbol,
                close=current,
                turnover_yuan=latest["amount"],
                volatility_20_pct=annualized_volatility_20(closes),
                return_1d_pct=_pct_change(current, closes[-2]),
                return_1w_pct=_pct_change(current, closes[-6] if len(closes) >= 6 else closes[0]),
                return_1m_pct=_pct_change(current, closes[-22] if len(closes) >= 22 else closes[0]),
                return_1y_pct=_pct_change(current, closes[-253] if len(closes) >= 253 else closes[0]),
                return_ytd_pct=_pct_change(current, _closest_prior(history, year_start)),
                return_qtd_pct=_pct_change(current, _closest_prior(history, quarter_start)),
                distance_52w_high_pct=_pct_change(current, high_52),
                signal_1h=one_hour,
                signal_daily=_trend(current, closes[-2]),
                signal_3d=_trend(current, closes[-4] if len(closes) >= 4 else closes[0]),
                signal_weekly=_trend(current, closes[-6] if len(closes) >= 6 else closes[0]),
                spark=closes[-30:],
            )

        return await asyncio.to_thread(load)

    @staticmethod
    def _intraday_signal(code: str) -> str | None:
        try:
            end = datetime.now().strftime("%Y-%m-%d 15:00:00")
            start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d 09:30:00")
            frame = _akshare().index_zh_a_hist_min_em(
                symbol=code,
                period="60",
                start_date=start,
                end_date=end,
            )
            rows = _records(frame)
            if len(rows) < 2:
                return None
            current = _decimal(_pick(rows[-1], "收盘", "close"))
            previous = _decimal(_pick(rows[-2], "收盘", "close"))
            return _trend(current, previous)
        except Exception:
            return None

    async def shenwan_memberships(self) -> list[ShenwanMembership]:
        def load() -> list[ShenwanMembership]:
            ak = _akshare()
            frame = ak.stock_industry_clf_hist_sw()
            records = _records(frame)
            l1_code_by_name: dict[str, str] = {}
            l2_code_by_name: dict[str, str] = {}
            try:
                for row in _records(ak.sw_index_first_info()):
                    name = str(_pick(row, "行业名称") or "").strip()
                    code = str(_pick(row, "行业代码") or "").replace(".SI", "")
                    if name and code:
                        l1_code_by_name[name] = code
                for row in _records(ak.sw_index_second_info()):
                    name = str(_pick(row, "行业名称") or "").strip()
                    code = str(_pick(row, "行业代码") or "").replace(".SI", "")
                    if name and code:
                        l2_code_by_name[name] = code
            except Exception:
                pass

            result: dict[str, ShenwanMembership] = {}
            today = date.today()
            version = f"akshare-sw-{today.isoformat()}"
            for row in records:
                code = str(
                    _pick(row, "股票代码", "证券代码", "代码", "stock_code") or ""
                ).strip()[-6:]
                l1_name = str(
                    _pick(row, "申万一级行业名称", "申万一级", "一级行业名称", "一级行业")
                    or ""
                ).strip()
                l2_name = str(
                    _pick(row, "申万二级行业名称", "申万二级", "二级行业名称", "二级行业")
                    or ""
                ).strip()
                l1_code = str(
                    _pick(row, "申万一级行业代码", "一级行业代码")
                    or l1_code_by_name.get(l1_name, "")
                ).replace(".SI", "")
                l2_code = str(
                    _pick(row, "申万二级行业代码", "二级行业代码")
                    or l2_code_by_name.get(l2_name, "")
                ).replace(".SI", "")
                if len(code) != 6 or not l1_name or not l2_name or not l1_code or not l2_code:
                    continue
                effective = _date(_pick(row, "纳入时间", "开始日期", "变动日期")) or today
                result[code] = ShenwanMembership(
                    security_code=code,
                    sw_l1_code=l1_code,
                    sw_l1_name=l1_name,
                    sw_l2_code=l2_code,
                    sw_l2_name=l2_name,
                    classification_version=version,
                    effective_from=effective,
                )
            if not result:
                raise ResearchProviderError("shenwan_membership_empty")
            return sorted(result.values(), key=lambda item: item.security_code)

        return await asyncio.to_thread(load)

    async def short_term_emotion(self) -> ShortTermEmotionSnapshot:
        selected_date: date | None = None
        pools: dict[str, list[dict[str, Any]]] = {}
        for offset in range(0, 8):
            candidate = date.today() - timedelta(days=offset)
            date_text = candidate.strftime("%Y%m%d")
            zt, zb, dt, previous = await asyncio.gather(
                self._limit_pool("getTopicZTPool", date_text, "fbt:asc"),
                self._limit_pool("getTopicZBPool", date_text, "zttj:desc"),
                self._limit_pool("getTopicDTPool", date_text, "fund:asc"),
                self._limit_pool("getYesterdayZTPool", date_text, "zs:desc"),
            )
            if zt or zb or dt:
                selected_date = candidate
                pools = {"zt": zt, "zb": zb, "dt": dt, "previous": previous}
                break
        if selected_date is None:
            raise ResearchProviderError("short_term_emotion_empty")

        zt_pool = pools["zt"]
        zb_pool = pools["zb"]
        previous_pool = pools["previous"]
        board_counts: list[int] = []
        leaders: list[EmotionStockRow] = []
        for row in zt_pool:
            board_count = max(1, _integer(row.get("lbc")))
            board_counts.append(board_count)
            if board_count >= 2:
                leaders.append(
                    EmotionStockRow(
                        security_code=str(row.get("c") or "").zfill(6),
                        security_name=str(row.get("n") or ""),
                        board_count=board_count,
                        turnover_yuan=_decimal(row.get("amount")),
                    )
                )
        leaders.sort(key=lambda item: (-item.board_count, -(item.turnover_yuan or Decimal("0"))))
        ladder_counts = {
            "2板": sum(1 for value in board_counts if value == 2),
            "3板": sum(1 for value in board_counts if value == 3),
            "4板": sum(1 for value in board_counts if value == 4),
            "5板+": sum(1 for value in board_counts if value >= 5),
        }
        from app.a_share_research_policy import calculate_short_term_emotion_rates

        rates = calculate_short_term_emotion_rates(
            limit_up_count=len(zt_pool),
            broken_board_count=len(zb_pool),
            today_lianban_count=sum(1 for value in board_counts if value >= 2),
            yesterday_limit_up_count=len(previous_pool),
        )
        return ShortTermEmotionSnapshot(
            limit_up_count=len(zt_pool),
            broken_board_count=len(zb_pool),
            limit_down_count=len(pools["dt"]),
            highest_board_count=max(board_counts, default=0),
            consecutive_board_count=sum(1 for value in board_counts if value >= 2),
            seal_rate_pct=rates.seal_rate,
            break_rate_pct=rates.break_rate,
            promotion_rate_pct=rates.promotion_rate,
            ladder=[
                EmotionLadderRow(board_count=label, stock_count=count)
                for label, count in ladder_counts.items()
            ],
            leaders=leaders,
            trade_date=selected_date,
        )

    async def _limit_pool(self, endpoint: str, trade_date: str, sort: str) -> list[dict[str, Any]]:
        params = {
            "ut": "7eea3edcaed734bea9cbfc24409ed989",
            "dpt": "wz.ztzt",
            "Pageindex": 0,
            "pagesize": 10000,
            "sort": sort,
            "date": trade_date,
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds, trust_env=False) as client:
                response = await client.get(
                    f"https://push2ex.eastmoney.com/{endpoint}",
                    params=params,
                    headers={"User-Agent": USER_AGENT, "Referer": "https://quote.eastmoney.com/"},
                )
                response.raise_for_status()
                return ((response.json().get("data") or {}).get("pool") or [])
        except (httpx.HTTPError, ValueError):
            return []

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
