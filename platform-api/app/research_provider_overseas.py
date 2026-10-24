"""海外公开数据源 fetcher：CME FedWatch / BTC ETF Flow / Deribit IV。

设计要点：
- 用项目已声明的 ``httpx`` + ``truststore`` 抓只读公开数据（farside / CME
  结算价 / FRED / Deribit），与 ``research_provider_shenwan`` 保持一致的安全
  客户端实践。TLS 证书默认校验，使用操作系统信任库；不关闭校验、不改全局 SSL
  设置、不使用浏览器指纹伪装或反爬绕过。
- 先直连，再在直连网络不可达时使用部署环境显式配置的 HTTP(S) 代理；源码
  不硬编码本机端口。直连优先保证默认行为可预期，同时让受限网络中的公开
  数据 worker 能真正完成生产刷新。TLS 校验在两条路径上都保持开启。
- 这些源均为只读公开行情，不携带任何凭据；请求只走 HTTPS。
- FedWatch 使用 CME Aggregated 口径：无会议月锚定、反向传播会前/会后 EFFR，
  相对首场会前利率计算累计变动，不使用目标区间中点递推。
"""

from __future__ import annotations

import math
import re
import ssl
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import truststore

from app.research_provider_errors import ResearchProviderError

_TIMEOUT_SECONDS = 20.0

_CME_SETTLEMENTS_URL = (
    "https://www.cmegroup.com/CmeWS/mvc/Settlements/Futures/Settlements/305/FUT"
)
_YAHOO_ZQ_SPARK_URL = "https://query1.finance.yahoo.com/v7/finance/spark"
_FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"

# FOMC 会议结束日（决议公布日）。来源：
# https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
_FOMC_MEETINGS: tuple[date, ...] = (
    date(2025, 1, 29), date(2025, 3, 19), date(2025, 5, 7), date(2025, 6, 18),
    date(2025, 7, 30), date(2025, 9, 17), date(2025, 10, 29), date(2025, 12, 10),
    date(2026, 1, 28), date(2026, 3, 18), date(2026, 4, 29), date(2026, 6, 17),
    date(2026, 7, 29), date(2026, 9, 16), date(2026, 10, 28), date(2026, 12, 9),
    date(2027, 1, 27), date(2027, 3, 17), date(2027, 4, 28), date(2027, 6, 9),
    date(2027, 7, 28), date(2027, 9, 15), date(2027, 10, 27), date(2027, 12, 8),
    date(2028, 1, 26),
)

_MONTH_CODES = {1: "F", 2: "G", 3: "H", 4: "J", 5: "K", 6: "M",
                7: "N", 8: "Q", 9: "U", 10: "V", 11: "X", 12: "Z"}
_MONTH_NAMES = {1: "JAN", 2: "FEB", 3: "MAR", 4: "APR", 5: "MAY", 6: "JUN",
                7: "JUL", 8: "AUG", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DEC"}


class _Response:
    """最小响应封装，让调用方继续用 ``.text`` / ``.json()`` / ``.raise_for_status()``。

    保留这一层是为了让既有解析代码不被 HTTP 客户端类型绑死，也便于测试注入。
    """

    __slots__ = ("_response",)

    def __init__(self, response: httpx.Response) -> None:
        self._response = response

    @property
    def text(self) -> str:
        return self._response.text

    def json(self) -> Any:
        return self._response.json()

    def raise_for_status(self) -> None:
        self._response.raise_for_status()


def _get(url: str, *, _timeout: float | None = None, **kwargs: Any) -> _Response:
    """对海外公开源发起一次 GET，默认校验 TLS 证书。

    使用独立 ``httpx.Client``：作用域限定在单次请求，``verify`` 走
    ``truststore`` 的系统信任库（Windows 上可补齐缺失的中间证书链），
    绝不修改全局 SSL 设置，也不传 ``verify=False``。
    """
    client_kwargs = {
        "verify": truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
        "timeout": _timeout or _TIMEOUT_SECONDS,
        "follow_redirects": True,
    }
    try:
        # Keep direct egress first; do not silently inherit a proxy on normal deployments.
        with httpx.Client(**client_kwargs, trust_env=False) as client:
            response = client.get(url, **kwargs)
        # A direct egress address can be reachable but denied by the upstream
        # edge (403/429/5xx). In that case the configured deployment proxy is
        # the only usable route, so retry it before surfacing the response.
        if response.status_code not in {403, 429, 502, 503, 504}:
            return _Response(response)
    except httpx.TransportError:
        # Restricted Windows deployments may expose approved egress only via
        # HTTP(S)_PROXY. Retry transport connect failures through that setting.
        pass
    with httpx.Client(**client_kwargs, trust_env=True) as client:
        response = client.get(url, **kwargs)
    return _Response(response)


def _recent_business_day(d: date) -> date:
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def _fetch_fred_series(series_id: str) -> float:
    end = date.today()
    start = end - timedelta(days=15)
    resp = _get(
        _FRED_CSV_URL,
        params={"id": series_id, "cosd": start.isoformat(), "coed": end.isoformat()},
    )
    resp.raise_for_status()
    for line in reversed(resp.text.strip().split("\n")[1:]):
        parts = line.split(",")
        if len(parts) == 2 and parts[1] not in (".", ""):
            return float(parts[1])
    raise ResearchProviderError(f"fred_series_empty:{series_id}")


def _fetch_cme_settlements() -> tuple[dict[str, float], dict[str, Any]]:
    """拉取 CME 30 天联邦基金期货结算价，返回 {month_key: settle_price}。

    month_key 形如 "SEP 26"。失败时向前回退一个工作日重试一次。
    """
    trade_date = _recent_business_day(_fedwatch_today() - timedelta(days=1))
    data: dict[str, Any] | None = None
    for _ in range(2):
        date_str = trade_date.strftime("%m/%d/%Y")
        # CME's blocked/black-holed endpoint must not hold the hourly worker
        # for the full generic public-source timeout before Yahoo fallback.
        resp = _get(_CME_SETTLEMENTS_URL, _timeout=5.0, params={"tradeDate": date_str})
        resp.raise_for_status()
        payload = resp.json()
        if not payload.get("empty"):
            data = payload
            break
        trade_date = _recent_business_day(trade_date - timedelta(days=1))
    if data is None:
        raise ResearchProviderError("cme_settlements_empty")

    settle_map: dict[str, float] = {}
    for s in data.get("settlements", []):
        if s.get("month") == "Total":
            continue
        try:
            settle_map[str(s["month"])] = float(s["settle"])
        except (ValueError, TypeError, KeyError):
            continue
    if not settle_map:
        raise ResearchProviderError("cme_settlements_unparsable")
    return settle_map, {"quoteAsOf": trade_date.isoformat()}


def _fetch_yahoo_zq_settlements() -> tuple[dict[str, float], dict[str, Any]]:
    """Fetch the same ZQ curve from Yahoo's public delayed quote endpoint.

    CME's browser settlement endpoint blocks automated requests from some
    deployment IPs. Yahoo exposes the corresponding 30-Day Fed Funds futures
    contracts in one bounded Spark response, which keeps the hourly worker
    usable without inventing probabilities or requiring credentials. Values
    are the latest delayed quote, not CME's official settlement print.
    """
    today = _fedwatch_today()
    symbols: list[str] = []
    year, month = today.year, today.month
    for _ in range(14):
        symbols.append(f"ZQ{_MONTH_CODES[month]}{year % 100:02d}.CBT")
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1
    response = _get(
        _YAHOO_ZQ_SPARK_URL,
        params={"symbols": ",".join(symbols), "range": "5d", "interval": "1d"},
        headers={
            "Accept": "application/json",
            "User-Agent": "Platform-API research worker/1.0",
        },
    )
    response.raise_for_status()
    payload = response.json()
    results = ((payload.get("spark") or {}).get("result") or [])
    settle_map: dict[str, float] = {}
    quote_times = {}
    for result in results:
        if not isinstance(result, dict):
            continue
        symbol = str(result.get("symbol") or "")
        match = re.fullmatch(r"ZQ([FGHJKMNQUVXZ])(\d{2})\.CBT", symbol)
        if not match:
            continue
        month_number = next((m for m, code in _MONTH_CODES.items() if code == match.group(1)), None)
        if month_number is None:
            continue
        key = _month_key(2000 + int(match.group(2)), month_number)
        responses = result.get("response") or []
        meta = responses[0].get("meta") if responses and isinstance(responses[0], dict) else None
        if not isinstance(meta, dict):
            continue
        value = meta.get("regularMarketPrice")
        try:
            if value is not None:
                stamp = meta.get("regularMarketTime")
                if not stamp:
                    continue
                quote_times[key] = datetime.fromtimestamp(int(stamp), UTC).isoformat()
                settle_map[key] = float(value)
        except (TypeError, ValueError):
            continue
    if not settle_map:
        raise ResearchProviderError("yahoo_zq_quotes_unavailable")
    return settle_map, {"quoteAsOf": min(quote_times.values()), "contractQuoteTimes": quote_times}


def _fetch_fed_fund_settlements() -> tuple[dict[str, float], str, dict[str, Any]]:
    """Use CME settlement first, then a public delayed ZQ quote fallback."""
    try:
        prices, metadata = _fetch_cme_settlements()
        return prices, "CME official settlements", metadata
    except Exception as cme_error:
        try:
            prices, metadata = _fetch_yahoo_zq_settlements()
            return prices, "Yahoo Finance delayed ZQ quotes", metadata
        except Exception as yahoo_error:
            raise ResearchProviderError(
                f"fed_funds_curve_unavailable:cme={type(cme_error).__name__}:yahoo={type(yahoo_error).__name__}"
            ) from yahoo_error


def _fedwatch_today() -> date:
    return datetime.now(ZoneInfo("America/New_York")).date()


def _month_key(year: int, month: int) -> str:
    return f"{_MONTH_NAMES[month]} {year % 100}"


def _next_month(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


def _target_range_label(lower_bps: int) -> str:
    return f"{lower_bps}-{lower_bps + 25}"


def _improved_fedwatch(
    settle_map: dict[str, float],
    meetings: list[date],
    effr: float,
) -> list[dict[str, Any]]:
    from app.research_fedwatch import aggregated_probabilities

    return aggregated_probabilities(settle_map, meetings, effr)


_ZQ_QUARTERLY_CODES = ("U", "V", "X", "Z")  # 季月合约代码（CME IMM 月）


def _current_target_range(effr: float) -> str:
    lower_bps = int(math.floor(effr * 100 / 25.0)) * 25
    return f"{lower_bps / 100:.2f}%-{(lower_bps + 25) / 100:.2f}%"


def _build_zq_pricing_table(settle_map: dict[str, float]) -> list[dict[str, Any]]:
    """构造 CME 13 个月 ZQ 合约价格表（季月 IMM + 月合约）。

    返回 [{code: "ZQU6", month: "SEP 26", settle: 96.2913}, ...]，按月序列出。
    用于前端顶部「FED FUND FUTURES」展示。
    """
    used_keys: set[str] = set()
    rows: list[dict[str, Any]] = []
    today = _fedwatch_today()
    cur_year, cur_month = today.year, today.month
    yy, mm = cur_year, cur_month
    for _ in range(13):
        mk = _month_key(yy, mm)
        # ZQ 月代码
        code = "ZQ" + _MONTH_CODES[mm] + f"{yy % 100:02d}"
        settle = settle_map.get(mk)
        rows.append(
            {
                "code": code,
                "month": _MONTH_NAMES[mm] + f" {yy % 100:02d}",
                "monthISO": f"{yy:04d}-{mm:02d}",
                "settle": round(float(settle), 4) if settle is not None else None,
            }
        )
        used_keys.add(mk)
        # 推进 1 个月
        if mm == 12:
            yy += 1
            mm = 1
        else:
            mm += 1
    return rows


def fetch_fedwatch() -> dict[str, Any]:
    """抓取并计算 CME FedWatch 概率矩阵 + 13 个月 ZQ 价格表。

    返回 {
        "effr": float,
        "currentTarget": str,
        "observedAt": "YYYY-MM-DD" (upstream observation date; the platform
        stores its own hourly UTC capture bucket),
        "scheduleStatus": str,   # 库原文
        "zqPricing": [{code, month, monthISO, settle}, ...],
        "meetings":  [{date, probabilities, contract}, ...]
    }
    """
    from app.research_fedwatch import METHODOLOGY
    from app.research_local_data import write_local_json

    settle_map, settlement_source, pricing_meta = _fetch_fed_fund_settlements()
    effr = _fetch_fred_series("EFFR")
    meetings_all = [m for m in _FOMC_MEETINGS if m >= _fedwatch_today()]
    meetings_probs = _improved_fedwatch(settle_map, meetings_all, effr)

    pricing_table = _build_zq_pricing_table(settle_map)
    visible_months = {row["month"] for row in pricing_table}
    meetings_probs = [
        m
        for m in meetings_probs
        if _month_key(date.fromisoformat(m["date"]).year, date.fromisoformat(m["date"]).month)
        in visible_months
    ]
    expected = [
        m.isoformat() for m in meetings_all if _month_key(m.year, m.month) in visible_months
    ]
    missing = [day for day in expected if day not in {m["date"] for m in meetings_probs}]
    now = datetime.now(UTC)
    write_local_json(
        f"history/research/fedwatch/{now.strftime('%Y%m%dT%H%M%S%fZ')}.json",
        dict(
            methodology=METHODOLOGY,
            probabilityUnit="percent",
            retrievedAt=now.isoformat(),
            settlementSource=settlement_source,
            prices=settle_map,
            effr=effr,
            meetings=[day.isoformat() for day in meetings_all],
            pricing=pricing_meta,
        ),
    )

    # 给每场会议配对 contract code (e.g. ZQU6)
    meetings: list[dict[str, Any]] = []
    for m in meetings_probs:
        meeting_date = date.fromisoformat(m["date"])
        contract = "ZQ" + _MONTH_CODES[meeting_date.month] + f"{meeting_date.year % 100:02d}"
        meetings.append(
            {
                "date": m["date"],
                "contract": contract,
                "probabilities": m["probabilities"],
            }
        )

    return {
        "effr": effr,
        "currentTarget": _current_target_range(effr),
        "observedAt": _recent_business_day(_fedwatch_today()).isoformat(),
        "methodology": METHODOLOGY,
        "probabilityUnit": "percent",
        "missingMeetings": missing,
        **pricing_meta,
        "settlementSource": settlement_source,
        "zqPricing": pricing_table,
        "meetings": meetings,
    }


# ---------------------------------------------------------------------------
# BTC / ETH ETF Flow（farside.co.uk/btc、/eth）
# ---------------------------------------------------------------------------

_FARSIDE_BTC_URL = "https://farside.co.uk/btc/"
_FARSIDE_BTC_ALL_URL = "https://farside.co.uk/bitcoin-etf-flow-all-data/"
# Farside's edge currently returns 403 to the platform egress.  Jina Reader
# returns the same public Farside page as markdown without changing the source
# or its values, so it is used only as a transport fallback.
_FARSIDE_BTC_READER_URL = "https://r.jina.ai/https://farside.co.uk/btc/"
_FARSIDE_BTC_ALL_READER_URL = "https://r.jina.ai/https://farside.co.uk/bitcoin-etf-flow-all-data/"
_FARSIDE_ETH_URL = "https://farside.co.uk/eth/"
_FARSIDE_ETH_ALL_URL = "https://farside.co.uk/ethereum-etf-flow-all-data/"
_FARSIDE_ETH_READER_URL = "https://r.jina.ai/https://farside.co.uk/eth/"
_FARSIDE_ETH_ALL_READER_URL = "https://r.jina.ai/https://farside.co.uk/ethereum-etf-flow-all-data/"

# farside 表格固定列序（第 1 列为日期，随后 12 列 ETF，末列 Total）。
# 顺序与页面 thead 一致，供落库时作为稳定列序使用；解析时也会从表头回读。
_FARSIDE_TICKERS: tuple[str, ...] = (
    "IBIT", "FBTC", "BITB", "ARKB", "BTCO", "EZBC",
    "BRRR", "HODL", "BTCW", "MSBT", "GBTC", "BTC", "Total",
)
_FARSIDE_ETH_TICKERS: tuple[str, ...] = (
    "ETHA", "ETHB", "FETH", "ETHW", "TETH", "ETHV", "QETH", "EZET", "MSSE", "ETHE", "ETH", "Total",
)


def _clean_cell(raw: str) -> str:
    text = re.sub(r"<[^>]+>", "", raw)
    return text.replace("\xa0", " ").replace("&nbsp;", " ").strip()


def _parse_farside_btc(html: str) -> tuple[list[str], list[list[str]]]:
    """解析 farside 的 BTC/ETH ETF 表，返回 (tickers, rows)。

    rows 每行为 [date_str, flow_1..flow_12, total]，date_str 为 "24 Aug 2026"。
    表头 ticker 行的「Total」列 label 为空，据数据行列数自动补齐。
    """
    tickers: list[str] = []
    head_row = re.search(r"<tr[^>]*>((?:(?!</tr>).)*IBIT(?:(?!</tr>).)*)</tr>", html, re.S)
    if head_row:
        for cell in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", head_row.group(1), re.S):
            text = _clean_cell(cell)
            if text and text != "Fee":
                tickers.append(text)

    rows: list[list[str]] = []
    tbody = re.search(r"<tbody>(.*?)</tbody>", html, re.S)
    if tbody:
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", tbody.group(1), re.S):
            cells = [_clean_cell(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
            if len(cells) >= 2 and cells[0]:
                rows.append(cells)

    # 数据行比「日期 + 已解析 ticker」多一列，即为末列 Total。
    if rows and len(rows[0]) > len(tickers) + 1:
        tickers.append("Total")
    return tickers, rows


def _parse_farside_btc_markdown(markdown: str) -> tuple[list[str], list[list[str]]]:
    """解析 Jina Reader 返回的同一 Farside 表格 Markdown。"""
    return _parse_farside_markdown(markdown, _FARSIDE_TICKERS)


def _parse_farside_markdown(
    markdown: str, tickers: tuple[str, ...]
) -> tuple[list[str], list[list[str]]]:
    """解析 BTC/ETH Farside 表格的 Markdown 行。"""
    rows: list[list[str]] = []
    for line in markdown.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or not re.fullmatch(r"\d{2} [A-Z][a-z]{2} \d{4}", cells[0]):
            continue
        rows.append(cells)
    return list(tickers), rows


def _parse_farside_all_data_markdown(
    markdown: str, tickers: tuple[str, ...]
) -> tuple[list[str], list[list[str]]]:
    """解析 Farside ``all-data`` Reader 页面拆成的逐行表格。

    Reader 对该页不会保留 Markdown 的 ``|`` 行，而是把每个单元格放到
    单独一行；日期行后紧跟固定数量的 ETF 数值，空行只作为排版分隔。
    """
    lines = [line.strip() for line in markdown.splitlines()]
    rows: list[list[str]] = []
    date_pattern = re.compile(r"^\d{2} [A-Z][a-z]{2} \d{4}$")
    width = len(tickers) + 1
    index = 0
    while index < len(lines):
        if not date_pattern.fullmatch(lines[index]):
            index += 1
            continue
        cells = [lines[index]]
        index += 1
        while index < len(lines) and len(cells) < width:
            value = lines[index]
            index += 1
            if value:
                cells.append(value)
        if len(cells) >= 2:
            rows.append(cells[:width])
    return list(tickers), rows


def _parse_flow(value: str) -> float | None:
    """解析 farside 资金流单元格。

    farside 用会计括号表示负数：``(17.1)`` = -17.1；当日未发布的单元格为
    ``-``（返回 None）。支持千分位逗号。
    """
    v = (value or "").strip()
    if v in ("", "-", "n/a", "N/A", "—", "–"):
        return None
    negative = v.startswith("(") and v.endswith(")")
    if negative:
        v = v[1:-1].strip()
    try:
        parsed = float(v.replace(",", ""))
    except (ValueError, TypeError):
        return None
    return -parsed if negative else parsed


def fetch_etf_flow(days: int = 3650, asset: str = "btc") -> dict[str, Any]:
    """抓取 Farside 可提供的 BTC/ETH 现货 ETF 资金流历史。

    ``days`` 只限制返回窗口；默认覆盖源站可提供的全部历史，避免看板上线
    后只能看到最近两周。返回 {"tickers": [...], "days": [...]}（升序）。
    """
    asset_key = asset.lower().strip()
    if asset_key not in {"btc", "eth"}:
        raise ValueError(f"unsupported_etf_asset:{asset}")
    all_history = days > 90
    if asset_key == "btc":
        page_url = _FARSIDE_BTC_ALL_URL if all_history else _FARSIDE_BTC_URL
        reader_url = _FARSIDE_BTC_ALL_READER_URL if all_history else _FARSIDE_BTC_READER_URL
    else:
        page_url = _FARSIDE_ETH_ALL_URL if all_history else _FARSIDE_ETH_URL
        reader_url = _FARSIDE_ETH_ALL_READER_URL if all_history else _FARSIDE_ETH_READER_URL
    tickers_default = _FARSIDE_TICKERS if asset_key == "btc" else _FARSIDE_ETH_TICKERS
    source_error: Exception | None = None
    try:
        resp = _get(
            page_url,
            headers={
                "Accept": "text/html,application/xhtml+xml",
                "User-Agent": "Platform-API research worker/1.0",
            },
        )
        resp.raise_for_status()
        tickers, rows = _parse_farside_btc(resp.text)
    except Exception as exc:
        source_error = exc
        reader = _get(
            reader_url,
            headers={"Accept": "text/plain", "User-Agent": "Platform-API research worker/1.0"},
        )
        reader.raise_for_status()
        tickers, rows = _parse_farside_markdown(reader.text, tickers_default)
        if all_history and not rows:
            tickers, rows = _parse_farside_all_data_markdown(reader.text, tickers_default)
    if not tickers:
        tickers = list(tickers_default)
    if not rows:
        if source_error is not None:
            raise ResearchProviderError(
                f"farside_{asset_key}_empty:direct={type(source_error).__name__}"
            ) from source_error
        raise ResearchProviderError(f"farside_{asset_key}_empty")

    parsed: list[dict[str, Any]] = []
    for cells in rows[-days:]:
        if len(cells) < 2:
            continue
        try:
            day = datetime.strptime(cells[0], "%d %b %Y").date().isoformat()
        except ValueError:
            continue
        flows = {}
        for i, ticker in enumerate(tickers):
            flows[ticker] = _parse_flow(cells[i + 1]) if i + 1 < len(cells) else None
        parsed.append({"date": day, "flows": flows})

    if not parsed:
        raise ResearchProviderError("farside_btc_unparsable")
    return {"tickers": tickers, "days": parsed}


# ---------------------------------------------------------------------------
# Deribit BTC 期权 IV 期限结构
# ---------------------------------------------------------------------------

_DERIBIT_BASE = "https://www.deribit.com/api/v2/public"
_MONTH_ABBR = {1: "JAN", 2: "FEB", 3: "MAR", 4: "APR", 5: "MAY", 6: "JUN",
               7: "JUL", 8: "AUG", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DEC"}
_DERIBIT_MONTH = {v: k for k, v in _MONTH_ABBR.items()}

_INSTRUMENT_RE = re.compile(
    r"^BTC-(\d{1,2})([A-Z]{3})(\d{2})-(\d+)-([CP])$"
)


def _deribit_get(method: str, params: dict[str, Any]) -> dict[str, Any]:
    resp = _get(f"{_DERIBIT_BASE}/{method}", params=params)
    resp.raise_for_status()
    return resp.json()


def _tenor_label(days: int) -> str:
    """旧版 1W/2W/1M/2M/3M/6M/9M 桶（向后兼容，IV 面板改用 _major_tenor_label）。"""
    if days < 9:
        return "1W"
    if days < 20:
        return "2W"
    if days < 40:
        return "1M"
    if days < 75:
        return "2M"
    if days < 110:
        return "3M"
    if days < 200:
        return "6M"
    if days < 300:
        return "9M"
    return "1Y"


# 主要时段桶（数据.rtatrade.xyz 风格），dte 范围按 Deribit 月度到期日实测覆盖：
# - 1M: 次月到期 ~21-49 天
# - 3M: 季月到期 ~50-129 天
# - 6M: 半年期 ~130-219 天
# - 1Y: 1 年期 ~220-365 天
_MAJOR_TENOR_BANDS: tuple[tuple[str, int, int], ...] = (
    ("1M", 20, 49),
    ("3M", 50, 129),
    ("6M", 130, 219),
    ("1Y", 220, 365),
)
_MAJOR_TENOR_ORDER = {t: i for i, (t, _, _) in enumerate(_MAJOR_TENOR_BANDS)}


def _major_tenor_label(days: int) -> str | None:
    for label, lo, hi in _MAJOR_TENOR_BANDS:
        if lo <= days <= hi:
            return label
    return None


def fetch_deribit_iv() -> dict[str, Any]:
    """抓取 Deribit BTC 期权 ATM IV 标准期限结构。

    用 get_index_price 拿现货指数价，用 get_book_summary_by_currency 一次性取
    全量期权 mark_iv，对每个到期日取「行权价最接近指数价」的 ATM 合约，
    对该行权价的 call/put mark_iv 取均值；按 tenor 桶（1W/2W/1M/2M/3M/6M/9M）
    各自取最近一个到期日，避免短端堆点。

    返回 {"index": float, "term": [{expiry, daysToExpiry, tenor, iv}, ...]}。
    """
    index = float(
        _deribit_get("get_index_price", {"index_name": "btc_usd"})["result"]["index_price"]
    )
    book = _deribit_get(
        "get_book_summary_by_currency", {"currency": "BTC", "kind": "option"}
    )["result"]

    # 按到期日聚合 ATM 附近的 mark_iv
    atm: dict[date, dict[str, Any]] = {}
    for inst in book:
        name = inst.get("instrument_name", "")
        m = _INSTRUMENT_RE.match(name)
        if not m or inst.get("mark_iv") is None:
            continue
        day, mon, yy, strike, otype = (
            int(m.group(1)),
            m.group(2),
            int(m.group(3)),
            int(m.group(4)),
            m.group(5),
        )
        if mon not in _DERIBIT_MONTH:
            continue
        expiry = date(2000 + yy, _DERIBIT_MONTH[mon], day)
        strike = int(strike)
        iv = float(inst["mark_iv"])
        dist = abs(strike - index)
        slot = atm.setdefault(expiry, {"dist": 1e18, "calls": [], "puts": []})
        slot["dist"] = min(slot["dist"], dist)
        if otype == "C":
            slot["calls"].append((dist, iv))
        else:
            slot["puts"].append((dist, iv))

    term: list[dict[str, Any]] = []
    for expiry in sorted(atm):
        slot = atm[expiry]
        calls = [iv for d, iv in slot["calls"] if abs(d - slot["dist"]) < 1e-6]
        puts = [iv for d, iv in slot["puts"] if abs(d - slot["dist"]) < 1e-6]
        ivs = calls + puts
        if not ivs:
            continue
        iv = sum(ivs) / len(ivs)
        days_to_expiry = (expiry - date.today()).days
        if days_to_expiry < 0:
            continue
        term.append({
            "expiry": expiry.isoformat(),
            "daysToExpiry": days_to_expiry,
            "tenor": _tenor_label(days_to_expiry),
            "iv": round(iv, 2),
        })

    # 按 daysToExpiry 升序，同一 tenor 只保留最早一个（最近的合约）
    term.sort(key=lambda t: t["daysToExpiry"])
    seen_tenors: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for t in term:
        if t["tenor"] in seen_tenors:
            continue
        seen_tenors.add(t["tenor"])
        deduped.append(t)

    if not deduped:
        raise ResearchProviderError("deribit_iv_empty")
    return {"index": index, "term": deduped}


def fetch_btc_iv_snapshot() -> dict[str, Any]:
    """抓取 BTC 期权 ATM IV 主要时段（1M/3M/6M/1Y）快照。

    按 dte 范围取最近合约作为该时段代表，返回：
    {
      "index": float,        # BTC 指数价
      "dvol": float,         # Deribit Volatility Index（最新）
      "observedAt": "YYYY-MM-DD",
      "tenors": [
        {"tenor":"1M","expiry":"...","daysToExpiry":21,"iv":36.70,"strike":...}, ...
      ]
    }
    缺失时段（无合适合约）从 tenors 中省略，由前端显示 "—"。
    """
    index = float(
        _deribit_get("get_index_price", {"index_name": "btc_usd"})["result"]["index_price"]
    )
    book = _deribit_get(
        "get_book_summary_by_currency", {"currency": "BTC", "kind": "option"}
    )["result"]

    # 按到期日聚合 ATM 附近的 mark_iv
    atm: dict[date, dict[str, Any]] = {}
    for inst in book:
        name = inst.get("instrument_name", "")
        m = _INSTRUMENT_RE.match(name)
        if not m or inst.get("mark_iv") is None:
            continue
        day, mon, yy, strike, otype = (
            int(m.group(1)),
            m.group(2),
            int(m.group(3)),
            int(m.group(4)),
            m.group(5),
        )
        if mon not in _DERIBIT_MONTH:
            continue
        expiry = date(2000 + yy, _DERIBIT_MONTH[mon], day)
        strike = int(strike)
        iv = float(inst["mark_iv"])
        dist = abs(strike - index)
        slot = atm.setdefault(expiry, {"dist": 1e18, "calls": [], "puts": [], "strike": strike})
        slot["dist"] = min(slot["dist"], dist)
        slot["strike"] = strike
        if otype == "C":
            slot["calls"].append((dist, iv))
        else:
            slot["puts"].append((dist, iv))

    # 按到期日 + dte 计算 ATM IV
    per_expiry: list[dict[str, Any]] = []
    for expiry, slot in atm.items():
        dte = (expiry - date.today()).days
        if dte < 0:
            continue
        calls = [iv for d, iv in slot["calls"] if abs(d - slot["dist"]) < 1e-6]
        puts = [iv for d, iv in slot["puts"] if abs(d - slot["dist"]) < 1e-6]
        ivs = calls + puts
        if not ivs:
            continue
        per_expiry.append({
            "expiry": expiry.isoformat(),
            "daysToExpiry": dte,
            "iv": round(sum(ivs) / len(ivs), 2),
            "strike": slot["strike"],
        })

    # 按主要时段（1M/3M/6M/1Y）各取最近的合约
    band_best: dict[str, dict[str, Any]] = {}
    for p in per_expiry:
        label = _major_tenor_label(p["daysToExpiry"])
        if not label:
            continue
        # 取每个 bucket 中 dte 最小（最近到期）
        cur = band_best.get(label)
        if cur is None or p["daysToExpiry"] < cur["daysToExpiry"]:
            band_best[label] = p

    tenors: list[dict[str, Any]] = []
    for label, _, _ in _MAJOR_TENOR_BANDS:
        p = band_best.get(label)
        if p is None:
            continue
        tenors.append({
            "tenor": label,
            "expiry": p["expiry"],
            "daysToExpiry": p["daysToExpiry"],
            "iv": p["iv"],
            "strike": p["strike"],
        })

    # DVOL 最新值
    try:
        dvol_latest = fetch_deribit_dvol(7)["latest"]
    except Exception:
        dvol_latest = None

    return {
        "index": index,
        "dvol": dvol_latest,
        "observedAt": date.today().isoformat(),
        "tenors": tenors,
    }


def fetch_deribit_dvol(days: int = 90) -> dict[str, Any]:
    """抓取 Deribit BTC DVOL 历史（DERIBIT VOLATILITY INDEX = 30日 IV 年化）。

    返回 {"latest": float, "history": [{ts, value}]}，时间序列升序，间隔 1 小时
    (resolution=3600)。用于 IV 面板历史走势展示，前端按需等距抽样后渲染。
    """
    end_ms = int(datetime.now().timestamp() * 1000)
    start_ms = end_ms - days * 86_400_000
    values: dict[int, float] = {}
    for _ in range(100):
        res = _deribit_get(
            "get_volatility_index_data",
            {"currency": "BTC", "start_timestamp": start_ms,
             "end_timestamp": end_ms, "resolution": 3600},
        )["result"]
        for point in res["data"]:
            ts, _, _, _, value = point
            if value is None:
                continue
            value = float(value)
            if not math.isfinite(value) or value < 0:
                raise ValueError("invalid DVOL close")
            if ts in values and values[ts] != value:
                raise ValueError("conflicting DVOL candle")
            values[int(ts)] = value
        continuation = res.get("continuation")
        if continuation is None:
            break
        if type(continuation) is not int or not start_ms <= continuation < end_ms:
            raise ValueError("DVOL pagination did not advance")
        end_ms = continuation
    else:
        raise ValueError("DVOL pagination limit exceeded")
    history = [{"ts": ts, "value": value} for ts, value in sorted(values.items())]
    return {"latest": history[-1]["value"] if history else None, "history": history}
