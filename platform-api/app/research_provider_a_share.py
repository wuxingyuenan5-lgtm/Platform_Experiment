from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode
from urllib.request import ProxyHandler, Request, build_opener
from zoneinfo import ZoneInfo

import httpx

from app.a_share_research_policy import annualized_volatility_20
from app.research_data_schemas import (
    AShareBreadthSnapshot,
    AShareIndexHistoryPoint,
    AShareIndexSnapshot,
    AShareMarketTurnoverRow,
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

# Match HTTPX trust_env=False's trust store without loading it synchronously
# for every live request on the API event loop (costly on Windows).
_HTTP_SSL_CONTEXT = httpx.create_ssl_context(trust_env=False)

INDEX_DEFINITIONS: tuple[tuple[str, str, str], ...] = (
    # Market Overview: core benchmarks followed by the fixed theme basket.
    ("000300", "沪深300", "sh000300"),
    ("000852", "中证1000", "sh000852"),
    ("399006", "创业板指", "sz399006"),
    ("000688", "科创50", "sh000688"),
    ("931071", "AI", "931071"),
    ("931238", "金股", "931238"),
    ("932082", "医药", "932082"),
    ("H30590", "机器人", "H30590"),
    # Retained for non-dashboard consumers that still use the broad index feed.
    ("000001", "上证指数", "sh000001"),
)

_CSI_THEME_INDEX_CODES = frozenset({"931071", "931238", "932082", "H30590"})
_CSI_INDEX_PERFORMANCE_URL = "https://www.csindex.com.cn/csindex-home/perf/index-perf"

_EM_ALL_A_PATH = "/api/qt/clist/get"
_EM_STOCK_QUOTE_PATH = "/api/qt/stock/get"
_EM_DELAY_HOSTS = ("push2delay2.eastmoney.com", "push2delay.eastmoney.com")
_EM_DELAY_HOST_INDEX = 0
_EM_ALL_A_FIELDS = "f2,f3,f5,f6,f8,f9,f12,f14,f18,f20,f23,f109,f124"
_EM_ALL_A_FILTER = "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:81 s:2048"
# Official quote center industry_board_1 filter; t:2 mixes all three levels.
_EM_SECTOR_FLOW_FILTER = "m:90+s:2+f:!50"
_EM_SECTOR_FLOW_FIELDS = "f12,f14,f3,f62,f104,f105,f106"
_CROWDING_SECTORS = {
    "通信设备": ("801102", "BK0448"),
    "计算机设备": ("801101", "BK0735"),
    "元件": ("801083", "BK0459"),
    "半导体": ("801081", "BK1036"),
}


async def _eastmoney_json(
    client: httpx.AsyncClient,
    path: str,
    params: dict[str, str],
    headers: dict[str, str],
) -> dict[str, Any]:
    """Read an Eastmoney payload through its working delay-node pool.

    Eastmoney's default delay node currently completes TLS then resets requests;
    the sibling delay2 node serves the same API and fields. Keep a successful
    node first for the process and fail over without changing data semantics.
    """
    global _EM_DELAY_HOST_INDEX
    start = _EM_DELAY_HOST_INDEX
    errors: list[BaseException] = []
    for offset in range(len(_EM_DELAY_HOSTS)):
        index = (start + offset) % len(_EM_DELAY_HOSTS)
        host = _EM_DELAY_HOSTS[index]
        try:
            response = await client.get(f"https://{host}{path}", params=params, headers=headers)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
                raise ValueError("eastmoney_clist_payload_missing_data")
            _EM_DELAY_HOST_INDEX = index
            return payload
        except (httpx.HTTPError, ValueError) as exc:
            errors.append(exc)
    raise ResearchProviderError("eastmoney_quote_nodes_unavailable") from errors[-1]


async def _eastmoney_clist(
    client: httpx.AsyncClient, params: dict[str, str], headers: dict[str, str]
) -> dict[str, Any]:
    return await _eastmoney_json(client, _EM_ALL_A_PATH, params, headers)


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
        try:
            return await self._eastmoney_a_share_spot()
        except ResearchProviderError:
            # AKShare is an explicitly bounded compatibility fallback only.
            # It is never used by the browser and an empty fallback cannot
            # overwrite a persisted complete snapshot.
            return await self._akshare_a_share_spot()

    async def innovation_drug_snapshot(self) -> dict[str, Any]:
        """Collect the close snapshot used by the innovation-drug crowding series."""
        params = {
            "secid": "90.BK1106",
            "fields": "f43,f47,f48,f86,f168,f170",
            "mpi": "1000",
            "invt": "2",
            "fltt": "2",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        }
        headers = {
            "User-Agent": self._user_agent,
            "Referer": "https://quote.eastmoney.com/",
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds, trust_env=False, verify=_HTTP_SSL_CONTEXT
            ) as client:
                payload = await _eastmoney_json(client, _EM_STOCK_QUOTE_PATH, params, headers)
        except (httpx.HTTPError, ValueError) as exc:
            raise ResearchProviderError("innovation_drug_quote_unavailable") from exc
        row = payload.get("data") or {}
        amount = _decimal(row.get("f48"))
        price = _decimal(row.get("f43"))
        turnover_raw = _decimal(row.get("f168"))
        timestamp = _integer(row.get("f86"))
        return_raw = _decimal(row.get("f170"))
        if amount is None or turnover_raw is None or timestamp is None:
            raise ResearchProviderError("innovation_drug_quote_incomplete")
        return {
            "observed_at": datetime.fromtimestamp(timestamp, UTC),
            "amount_yuan": amount,
            "close": price if price is not None and price > 0 else None,
            # The dashboard contract stores percentage points (3.27 means 3.27%),
            # while the chart converts that value to a fraction for percent axes.
            "turnover_pct": turnover_raw,
            "return_pct": (return_raw / Decimal("100") if return_raw is not None else None),
            "source": "东方财富创新药BK1106",
        }

    async def sector_crowding_snapshot(self) -> list[dict[str, Any]]:
        """Read the four selected Eastmoney industry-board close snapshots."""
        headers = {
            "User-Agent": self._user_agent,
            "Referer": "https://quote.eastmoney.com/center/boardlist.html#boards-BK0448",
        }
        base_params = {
            "fields": "f43,f47,f48,f86,f168",
            "mpi": "1000",
            "invt": "2",
            "fltt": "2",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds, trust_env=False, verify=_HTTP_SSL_CONTEXT
            ) as client:
                payloads = await asyncio.gather(
                    *(
                        _eastmoney_json(
                            client,
                            _EM_STOCK_QUOTE_PATH,
                            {**base_params, "secid": f"90.{board_code}"},
                            headers,
                        )
                        for _, board_code in _CROWDING_SECTORS.values()
                    )
                )
        except (httpx.HTTPError, ValueError) as exc:
            raise ResearchProviderError("sector_crowding_quote_unavailable") from exc

        result: list[dict[str, Any]] = []
        for (name, (code, board_code)), payload in zip(
            _CROWDING_SECTORS.items(), payloads, strict=True
        ):
            row = payload.get("data") or {}
            amount = _decimal(row.get("f48"))
            price = _decimal(row.get("f43"))
            turnover = _decimal(row.get("f168"))
            timestamp = _integer(row.get("f86"))
            if (
                amount is None
                or turnover is None
                or timestamp is None
                or amount < 0
                or turnover < 0
            ):
                raise ResearchProviderError(f"sector_crowding_quote_incomplete_{code}")
            result.append(
                {
                    "name": name,
                    "code": code,
                    "board_code": board_code,
                    "amount_yuan": amount,
                    "close": price if price is not None and price > 0 else None,
                    "turnover_pct": turnover,
                    "observed_at": datetime.fromtimestamp(timestamp, UTC),
                    "source": f"东方财富行业板块{board_code}",
                }
            )
        dates = {
            item["observed_at"].astimezone(ZoneInfo("Asia/Shanghai")).date() for item in result
        }
        if len(dates) != 1:
            raise ResearchProviderError("sector_crowding_quote_date_mismatch")
        return result

    async def sector_fund_flow(self) -> list[dict[str, Any]]:
        """Read live industry flow directly from Eastmoney's public quote feed.

        This is deliberately a small, live-only request.  It is not part of the
        daily A-share snapshot because net-flow and rotation are intraday values.
        """
        params = {
            "pn": "1",
            "pz": "50",
            "np": "1",
            "fltt": "2",
            "invt": "2",
            "fid": "f62",
            "fs": _EM_SECTOR_FLOW_FILTER,
            "fields": _EM_SECTOR_FLOW_FIELDS,
        }
        headers = {
            "User-Agent": self._user_agent,
            "Referer": "https://quote.eastmoney.com/center/boardlist.html#boards-BK06561",
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds, trust_env=False, verify=_HTTP_SSL_CONTEXT
            ) as client:
                responses = await asyncio.gather(
                    _eastmoney_clist(client, {**params, "po": "1"}, headers),
                    _eastmoney_clist(client, {**params, "po": "0"}, headers),
                )
                raw_rows: list[dict[str, Any]] = []
                for response in responses:
                    payload = response.get("data") or {}
                    diff = payload.get("diff") or []
                    raw_rows.extend(list(diff.values()) if isinstance(diff, dict) else list(diff))
        except (httpx.HTTPError, ValueError) as exc:
            raise ResearchProviderError("sector_fund_flow_request_failed") from exc

        merged: dict[str, dict[str, Any]] = {}
        for row in raw_rows:
            code = str(row.get("f12") or "").strip()
            name = str(row.get("f14") or "").strip()
            net_inflow = _decimal(row.get("f62"))
            if not code or not name or net_inflow is None:
                continue
            existing = merged.get(code)
            if existing is None or abs(net_inflow) > abs(existing["net_inflow_yuan"]):
                merged[code] = {
                    "sector_code": code,
                    "name": name,
                    "return_pct": _decimal(row.get("f3")),
                    "net_inflow_yuan": net_inflow,
                    "firm_count": (
                        sum(_integer(row.get(key)) or 0 for key in ("f104", "f105", "f106"))
                        if all(
                            _decimal(row.get(key)) is not None for key in ("f104", "f105", "f106")
                        )
                        else None
                    ),
                }
        result = sorted(merged.values(), key=lambda item: item["net_inflow_yuan"], reverse=True)
        if not result:
            raise ResearchProviderError("sector_fund_flow_empty")
        for item in result:
            net = item["net_inflow_yuan"]
            item["inflow_yuan"] = max(net, Decimal("0"))
            item["outflow_yuan"] = max(-net, Decimal("0"))
        return result

    async def market_turnover_top(self, limit: int = 20) -> list[AShareMarketTurnoverRow]:
        """Small live leaderboard; it never waits for the daily classification refresh."""
        params = {
            "pn": "1",
            "pz": str(max(1, min(limit, 50))),
            "po": "1",
            "np": "1",
            "fltt": "2",
            "invt": "2",
            "fid": "f6",
            "fs": _EM_ALL_A_FILTER,
            "fields": "f12,f14,f2,f3,f6,f20,f100",
        }
        headers = {
            "User-Agent": self._user_agent,
            "Referer": "https://quote.eastmoney.com/center/gridlist.html#hs_a_board",
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds, trust_env=False, verify=_HTTP_SSL_CONTEXT
            ) as client:
                payload = await _eastmoney_clist(client, params, headers)
                diff = (payload.get("data") or {}).get("diff") or []
        except (httpx.HTTPError, ValueError) as exc:
            raise ResearchProviderError("market_turnover_top_request_failed") from exc
        raw_rows = list(diff.values()) if isinstance(diff, dict) else list(diff)
        rows: list[AShareMarketTurnoverRow] = []
        for row in raw_rows:
            code = str(row.get("f12") or "").zfill(6)
            name = str(row.get("f14") or "").strip()
            amount = _decimal(row.get("f6"))
            if len(code) != 6 or not name or amount is None:
                continue
            rows.append(
                AShareMarketTurnoverRow(
                    security_code=code,
                    security_name=name,
                    price=_decimal(row.get("f2")),
                    return_pct=_decimal(row.get("f3")),
                    turnover_yuan=max(amount, Decimal("0")),
                    market_cap_yuan=_decimal(row.get("f20")),
                    industry=str(row.get("f100") or "").strip() or None,
                )
            )
        if not rows:
            raise ResearchProviderError("market_turnover_top_empty")
        return rows

    async def _eastmoney_a_share_spot(self) -> list[AShareTurnoverStock]:
        base_params = {
            "pz": "100",
            "po": "1",
            "np": "2",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": "2",
            "invt": "2",
            "fid": "f6",
            "fs": _EM_ALL_A_FILTER,
            "fields": _EM_ALL_A_FIELDS,
        }
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://quote.eastmoney.com/center/gridlist.html#hs_a_board",
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds, trust_env=False, verify=_HTTP_SSL_CONTEXT
            ) as client:
                first_payload = await _eastmoney_clist(client, {**base_params, "pn": "1"}, headers)
                first_data = first_payload.get("data") or {}
                total = int(first_data.get("total") or 0)
                first_rows = (
                    list((first_data.get("diff") or {}).values())
                    if isinstance(first_data.get("diff"), dict)
                    else list(first_data.get("diff") or [])
                )
                if total <= 0 or not first_rows:
                    raise ResearchProviderError("a_share_spot_empty")
                page_count = (total + 99) // 100
                pages: list[list[dict[str, Any]]] = [first_rows]
                # Vibe limits pagination concurrency to avoid upstream bursts.
                for start in range(2, page_count + 1, 3):
                    requests = [
                        _eastmoney_clist(client, {**base_params, "pn": str(page)}, headers)
                        for page in range(start, min(start + 3, page_count + 1))
                    ]
                    for payload in await asyncio.gather(*requests):
                        diff = (payload.get("data") or {}).get("diff") or []
                        pages.append(list(diff.values()) if isinstance(diff, dict) else list(diff))
        except (httpx.HTTPError, ValueError, ResearchProviderError) as exc:
            if isinstance(exc, ResearchProviderError):
                raise
            raise ResearchProviderError("a_share_spot_request_failed") from exc

        raw_rows = [row for page in pages for row in page]
        if len(raw_rows) != total:
            raise ResearchProviderError(f"a_share_spot_incomplete:{len(raw_rows)}/{total}")
        result: list[AShareTurnoverStock] = []
        seen: set[str] = set()
        for row in raw_rows:
            code = str(row.get("f12") or "").zfill(6)
            name = str(row.get("f14") or "").strip()
            price = _decimal(row.get("f2"))
            previous = _decimal(row.get("f18"))
            turnover = _decimal(row.get("f6"))
            if (
                len(code) != 6
                or code in seen
                or not name
                or price is None
                or previous is None
                or turnover is None
                or price <= 0
                or previous <= 0
                or turnover <= 0
                or "ST" in name.upper()
                or name.startswith(("N", "C"))
            ):
                continue
            seen.add(code)
            result.append(
                AShareTurnoverStock(
                    security_code=code,
                    security_name=name,
                    turnover_yuan=turnover,
                    price=price,
                    return_pct=_decimal(row.get("f3")),
                    observed_at=datetime.fromtimestamp(int(row["f124"]), UTC)
                    if _decimal(row.get("f124"))
                    else None,
                    turnover_pct=_decimal(row.get("f8")),
                    market_cap_yuan=_decimal(row.get("f20")),
                    pe_ttm=_decimal(row.get("f9")),
                    pb=_decimal(row.get("f23")),
                )
            )
        if len(result) < 4500:
            raise ResearchProviderError(f"a_share_spot_too_small:{len(result)}")
        return result

    async def _akshare_a_share_spot(self) -> list[AShareTurnoverStock]:
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

    async def stock_daily_histories(
        self, codes: list[str]
    ) -> dict[str, list[AShareIndexHistoryPoint]]:
        """Return daily close histories for the tracked pool, with no browser fan-out."""
        unique = [code for code in dict.fromkeys(str(code).strip() for code in codes) if code]
        semaphore = asyncio.Semaphore(4)

        async def load(code: str) -> tuple[str, list[AShareIndexHistoryPoint]]:
            async with semaphore:
                return code, await asyncio.to_thread(self._direct_stock_history, code)

        results = await asyncio.gather(*(load(code) for code in unique), return_exceptions=True)
        return {
            code: points
            for item in results
            if not isinstance(item, BaseException)
            for code, points in [item]
            if len(points) >= 2
        }

    async def tracked_stock_spot(self, codes: list[str]) -> list[AShareTurnoverStock]:
        """Tencent batch quote fallback for tracked HK/A-share instruments."""
        symbols = [(code, self._tencent_symbol(code)) for code in dict.fromkeys(codes)]
        symbols = [(code, symbol) for code, symbol in symbols if symbol]
        if not symbols:
            return []

        def load() -> list[AShareTurnoverStock]:
            opener = build_opener(ProxyHandler({}))
            result: list[AShareTurnoverStock] = []
            for offset in range(0, len(symbols), 40):
                batch = symbols[offset : offset + 40]
                request = Request(
                    "https://qt.gtimg.cn/q=" + ",".join(symbol for _, symbol in batch),
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                try:
                    with opener.open(request, timeout=self._timeout_seconds) as response:
                        body = response.read().decode("gbk", errors="ignore")
                except Exception:
                    continue
                for line in body.split(";"):
                    if "=" not in line or '"' not in line:
                        continue
                    key = line.split("=")[0].split("_")[-1]
                    code = key[2:]
                    values = line.split('"')[1].split("~")
                    if len(values) < 47 or not code:
                        continue
                    try:
                        price = Decimal(values[3])
                        previous = Decimal(values[4])
                        is_hk = key.startswith("hk")
                        amount = Decimal(values[37] or "0")
                        market_cap = _decimal(values[45])
                        observed = datetime.strptime(
                            values[30], "%Y/%m/%d %H:%M:%S" if is_hk else "%Y%m%d%H%M%S"
                        ).replace(tzinfo=ZoneInfo("Asia/Shanghai"))
                        if price <= 0 or previous <= 0:
                            continue
                        result.append(
                            AShareTurnoverStock(
                                security_code=code.zfill(6) if len(code) == 6 else code,
                                security_name=values[1].strip(),
                                price=price,
                                turnover_yuan=max(amount * (1 if is_hk else 10000), Decimal("0")),
                                currency="HKD" if is_hk else "CNY",
                                return_pct=(price / previous - 1) * Decimal("100"),
                                observed_at=observed,
                                turnover_pct=_decimal(values[38]) if not is_hk else None,
                                market_cap_yuan=(market_cap * Decimal("100000000"))
                                if market_cap is not None
                                else None,
                                pe_ttm=_decimal(values[39]),
                                pb=_decimal(values[46]) if not is_hk else None,
                            )
                        )
                    except (ArithmeticError, ValueError, IndexError):
                        continue
            return result

        return await asyncio.to_thread(load)

    def _direct_stock_history(self, code: str) -> list[AShareIndexHistoryPoint]:
        symbol = self._tencent_symbol(code)
        if not symbol:
            return []
        opener = build_opener(ProxyHandler({}))
        try:
            payload = self._direct_json(
                opener,
                (
                    "https://web.ifzq.gtimg.cn/appstock/app/hkfqkline/get"
                    if len(code) == 5
                    else "https://proxy.finance.qq.com/ifzqgtimg/appstock/app/newfqkline/get"
                ),
                {"param": f"{symbol},day,,,300,qfq"},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            node = (payload.get("data") or {}).get(symbol) or {}
            # Tencent's qfq request returns `day` for unadjusted listings (as
            # handled by the upstream stock_zh_a_hist_tx adapter). Both branches
            # belong to this same explicit qfq request, not a second raw query.
            raw_rows = node.get("qfqday") or node.get("day")
            rows = self._normalize_tencent_history(raw_rows or [])
            return sorted(
                [
                    AShareIndexHistoryPoint(
                        observed_at=row["date"],
                        close=row["close"],
                        source_name="tencent-qfq-daily",
                    )
                    for row in rows
                ],
                key=lambda point: point.observed_at,
            )
        except ResearchProviderError:
            return []

    @staticmethod
    def _tencent_symbol(code: str) -> str | None:
        if len(code) == 5 and code.isdigit():
            return f"hk{code}"
        if len(code) != 6 or not code.isdigit():
            return None
        return f"sh{code}" if code.startswith(("5", "6", "9")) else f"sz{code}"

    async def market_activity(self) -> AShareBreadthSnapshot:
        try:
            return await self._market_activity_from_complete_snapshot()
        except ResearchProviderError:
            return await self._market_activity_legu()

    async def _market_activity_from_complete_snapshot(self) -> AShareBreadthSnapshot:
        rows = await self._eastmoney_a_share_spot()
        from app.a_share_research_policy import classify_market_breadth, classify_speculation

        up = sum(1 for row in rows if row.return_pct is not None and row.return_pct > 0)
        down = sum(1 for row in rows if row.return_pct is not None and row.return_pct < 0)
        flat = len(rows) - up - down
        # Limit-pool counts remain authoritative in short_term_emotion; this
        # market breadth snapshot must not fabricate them from rounded returns.
        return AShareBreadthSnapshot(
            up=up,
            down=down,
            flat=flat,
            limit_up=0,
            real_limit_up=0,
            limit_down=0,
            real_limit_down=0,
            activity_pct=None,
            breadth_state=classify_market_breadth(up, down),
            speculation_state=classify_speculation(0),
            trade_date=date.today(),
        )

    async def _market_activity_legu(self) -> AShareBreadthSnapshot:
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
            self._index_snapshot(code, name, symbol) for code, name, symbol in INDEX_DEFINITIONS
        ]
        # The public quote hosts throttle short concurrent bursts.  A bounded
        # sequential collection is eight requests and runs only in the refresh
        # worker, never in a page request.
        results: list[AShareIndexSnapshot | BaseException] = []
        for task in tasks:
            try:
                results.append(await task)
            except Exception as exc:
                results.append(exc)
        snapshots = [item for item in results if isinstance(item, AShareIndexSnapshot)]
        # A rate-limited theme-index host must not suppress the four benchmark
        # cards. Theme data is retained from the last valid snapshot until its
        # own collector succeeds again.
        if not snapshots:
            raise ResearchProviderError("a_share_index_history_unavailable")
        return snapshots

    async def _index_snapshot(self, code: str, name: str, symbol: str) -> AShareIndexSnapshot:
        def load() -> AShareIndexSnapshot:
            # Do not route chart history through the reference project or an
            # AKShare process inheriting the user's proxy.  Vibe's public
            # chart route uses Tencent for mainland benchmarks; theme indexes
            # are listed by Eastmoney under market 2.  Both are fetched here
            # directly and persisted by Platform's refresh job.
            history = self._direct_index_history(code, symbol)
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
            return AShareIndexSnapshot(
                code=code,
                name=name,
                source_symbol=symbol,
                close=current,
                turnover_yuan=latest["amount"],
                volatility_20_pct=annualized_volatility_20(closes),
                return_1d_pct=_pct_change(current, closes[-2]),
                return_1w_pct=_pct_change(current, closes[-6]) if len(closes) >= 6 else None,
                return_1m_pct=_pct_change(current, closes[-22]) if len(closes) >= 22 else None,
                return_1y_pct=_pct_change(
                    current,
                    closes[-253] if len(closes) >= 253 else None,
                ),
                return_ytd_pct=_pct_change(current, _closest_prior(history, year_start)),
                return_qtd_pct=_pct_change(current, _closest_prior(history, quarter_start)),
                distance_52w_high_pct=_pct_change(current, high_52),
                # Minute-level AKShare collection does not belong in this
                # daily worker; it was the principal source of refresh stalls.
                signal_1h=None,
                signal_daily=_trend(current, closes[-2]),
                signal_3d=_trend(current, closes[-4] if len(closes) >= 4 else closes[0]),
                signal_weekly=_trend(current, closes[-6] if len(closes) >= 6 else closes[0]),
                spark=closes[-30:],
                history=[
                    AShareIndexHistoryPoint(
                        observed_at=item["date"],
                        source_name=item.get("source"),
                        close=item["close"],
                        turnover_yuan=item["amount"],
                    )
                    for item in history
                ],
            )

        return await asyncio.to_thread(load)

    def _direct_index_history(self, code: str, symbol: str) -> list[dict[str, Any]]:
        if code in _CSI_THEME_INDEX_CODES:
            return self._csindex_theme_history(code)

        opener = build_opener(ProxyHandler({}))
        if code in {"000300", "000852", "399006", "000688"}:
            records = _records(self._akshare().stock_zh_index_daily(symbol=symbol))
            return [
                {
                    "date": _date(row.get("date")),
                    "close": _decimal(row.get("close")),
                    "amount": None,
                    "source": "sina-index-daily",
                }
                for row in records
                if _date(row.get("date")) is not None
                and (_decimal(row.get("close")) or Decimal("0")) > 0
            ][-800:]

        endpoint = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        response = self._direct_json(
            opener,
            endpoint,
            {
                "secid": f"2.{code}",
                "ut": "fa5fd1943c7b386f172d6893dbfba10b",
                "fields1": "f1,f2,f3,f4,f5",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
                "klt": "101",
                "fqt": "0",
                "beg": "0",
                "end": "20500101",
            },
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://quote.eastmoney.com/",
            },
        )
        return self._normalize_eastmoney_history((response.get("data") or {}).get("klines") or [])

    def _csindex_theme_history(self, code: str) -> list[dict[str, Any]]:
        """Read the official CSI daily index series for the fixed theme basket.

        CSI publishes these theme indexes directly.  They are not Eastmoney
        market-2 instruments, so using that route silently returned an empty
        series and produced the ``—`` cards in the terminal.
        """
        start_date = (date.today() - timedelta(days=1_150)).strftime("%Y%m%d")
        params = {
            "indexCode": code,
            "startDate": start_date,
            "endDate": date.today().strftime("%Y%m%d"),
        }
        try:
            response = httpx.get(
                _CSI_INDEX_PERFORMANCE_URL,
                params=params,
                headers={
                    "User-Agent": self._user_agent,
                    "Referer": "https://www.csindex.com.cn/",
                },
                timeout=self._timeout_seconds,
                trust_env=False,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # noqa: BLE001
            raise ResearchProviderError("csi_theme_index_history_request_failed") from exc
        if not isinstance(payload, dict) or str(payload.get("code")) != "200":
            raise ResearchProviderError("csi_theme_index_history_invalid_payload")
        return self._normalize_csindex_history(payload.get("data") or [])

    def _direct_json(
        self,
        opener: Any,
        endpoint: str,
        params: dict[str, str],
        *,
        headers: dict[str, str],
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for _attempt in range(3):
            try:
                request = Request(f"{endpoint}?{urlencode(params)}", headers=headers)
                with opener.open(request, timeout=self._timeout_seconds) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                break
            except Exception as exc:  # noqa: BLE001
                last_error = exc
        else:
            raise ResearchProviderError("a_share_index_history_request_failed") from last_error
        if not isinstance(payload, dict):
            raise ResearchProviderError("a_share_index_history_invalid_payload")
        return payload

    @staticmethod
    def _normalize_tencent_history(rows: list[list[Any]]) -> list[dict[str, Any]]:
        history: list[dict[str, Any]] = []
        for row in rows:
            if len(row) < 3:
                continue
            observed = _date(row[0])
            close = _decimal(row[2])
            if observed is not None and close is not None and close > 0:
                history.append({"date": observed, "close": close, "amount": None})
        return history

    @staticmethod
    def _normalize_eastmoney_history(rows: list[str]) -> list[dict[str, Any]]:
        history: list[dict[str, Any]] = []
        for raw in rows:
            row = raw.split(",")
            if len(row) < 7:
                continue
            observed = _date(row[0])
            close = _decimal(row[2])
            if observed is not None and close is not None and close > 0:
                history.append({"date": observed, "close": close, "amount": _decimal(row[6])})
        return history

    @staticmethod
    def _normalize_csindex_history(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        history: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            raw_date = str(row.get("tradeDate") or "")
            observed = _date(
                f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
                if len(raw_date) == 8
                else raw_date
            )
            close = _decimal(row.get("close"))
            turnover_yi = _decimal(row.get("tradingValue"))
            if observed is None or close is None or close <= 0:
                continue
            history.append(
                {
                    "date": observed,
                    "close": close,
                    # CSI reports trading value in CNY hundred-millions.
                    "amount": turnover_yi * Decimal("100000000")
                    if turnover_yi is not None
                    else None,
                }
            )
        return history

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
        from app.research_provider_shenwan import collect_shenwan_memberships

        return await collect_shenwan_memberships(timeout=self._timeout_seconds)

    async def short_term_emotion(self) -> ShortTermEmotionSnapshot:
        selected_date: date | None = None
        pools: dict[str, list[dict[str, Any]]] = {}
        for offset in range(0, 8):
            candidate = date.today() - timedelta(days=offset)
            date_text = candidate.strftime("%Y%m%d")
            pool_results = await asyncio.gather(
                self._limit_pool("getTopicZTPool", date_text, "fbt:asc"),
                self._limit_pool("getTopicZBPool", date_text, "zttj:desc"),
                self._limit_pool("getTopicDTPool", date_text, "fund:asc"),
                self._limit_pool("getYesterdayZTPool", date_text, "zs:desc"),
            )
            source_dates = {source_date for source_date, rows in pool_results if rows}
            if len(source_dates) != 1 or None in source_dates:
                continue
            zt, zb, dt, previous = (rows for _, rows in pool_results)
            if zt or zb or dt:
                selected_date = next(iter(source_dates))
                if selected_date is None or selected_date > candidate:
                    continue
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

    async def _limit_pool(
        self, endpoint: str, trade_date: str, sort: str
    ) -> tuple[date | None, list[dict[str, Any]]]:
        params = {
            "ut": "7eea3edcaed734bea9cbfc24409ed989",
            "dpt": "wz.ztzt",
            "Pageindex": 0,
            "pagesize": 10000,
            "sort": sort,
            "date": trade_date,
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds, trust_env=False, verify=_HTTP_SSL_CONTEXT
            ) as client:
                response = await client.get(
                    f"https://push2ex.eastmoney.com/{endpoint}",
                    params=params,
                    headers={
                        "User-Agent": self._user_agent,
                        "Referer": "https://quote.eastmoney.com/",
                    },
                )
                response.raise_for_status()
                data = response.json().get("data") or {}
                source_date = datetime.strptime(str(data.get("qdate")), "%Y%m%d").date()
                return source_date, data.get("pool") or []
        except (httpx.HTTPError, ValueError):
            return None, []
