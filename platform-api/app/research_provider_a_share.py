from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import date, datetime, timedelta
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
    ShenwanMembership,
    ShortTermEmotionSnapshot,
)
from app.research_provider_errors import ResearchProviderError
from app.research_provider_normalization import as_date as _date
from app.research_provider_normalization import as_decimal as _decimal
from app.research_provider_normalization import as_non_negative_integer as _integer
from app.research_provider_normalization import closest_prior_close as _closest_prior
from app.research_provider_normalization import first_present as _pick
from app.research_provider_normalization import frame_records as _records
from app.research_provider_normalization import percentage_change as _pct_change
from app.research_provider_normalization import trend_marker as _trend

AkshareLoader = Callable[[], Any]

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


class AShareResearchProvider:
    def __init__(
        self,
        *,
        timeout_seconds: float,
        user_agent: str,
        akshare_loader: AkshareLoader,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._user_agent = user_agent
        self._akshare = akshare_loader

    async def a_share_spot(self) -> list[AShareTurnoverStock]:
        def load() -> list[AShareTurnoverStock]:
            frame = self._akshare().stock_zh_a_spot_em()
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
            frame = self._akshare().stock_market_activity_legu()
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
        tasks = [
            self._index_snapshot(code, name, symbol)
            for code, name, symbol in INDEX_DEFINITIONS
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        snapshots = [item for item in results if isinstance(item, AShareIndexSnapshot)]
        if not snapshots:
            raise ResearchProviderError("a_share_index_history_unavailable")
        return snapshots

    async def _index_snapshot(self, code: str, name: str, symbol: str) -> AShareIndexSnapshot:
        def load() -> AShareIndexSnapshot:
            frame = self._akshare().stock_zh_index_daily_em(symbol=symbol)
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
                return_1y_pct=_pct_change(
                    current,
                    closes[-253] if len(closes) >= 253 else closes[0],
                ),
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

    def _intraday_signal(self, code: str) -> str | None:
        try:
            end = datetime.now().strftime("%Y-%m-%d 15:00:00")
            start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d 09:30:00")
            frame = self._akshare().index_zh_a_hist_min_em(
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
            ak = self._akshare()
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
                    headers={
                        "User-Agent": self._user_agent,
                        "Referer": "https://quote.eastmoney.com/",
                    },
                )
                response.raise_for_status()
                return ((response.json().get("data") or {}).get("pool") or [])
        except (httpx.HTTPError, ValueError):
            return []
