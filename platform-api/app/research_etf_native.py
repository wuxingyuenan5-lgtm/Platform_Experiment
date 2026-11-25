"""Platform-owned ETF daily inputs from exchange shares, fund NAV and market APIs."""

from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import ssl
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from statistics import median
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

import httpx
import truststore

from app.research_local_data import read_local_json, write_local_json
from app.research_provider_errors import ResearchProviderError

ROOT = "public/v1/etf-native/"
SSE = "https://query.sse.com.cn/commonQuery.do"
SZSE = "https://www.szse.cn/api/report/ShowReport"
NAV = "https://api.fund.eastmoney.com/f10/lsjz"
CATALOG = "https://fund.eastmoney.com/js/fundcode_search.js"
MARKET = "https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketDataService.getKLineData"
DAILY_MARKET = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
CHINA = ZoneInfo("Asia/Shanghai")
YI = Decimal("100000000")
CATEGORIES = (
    "沪深300",
    "中证1000",
    "中证500",
    "科创50",
    "中证A500",
    "创业板指",
    "上证50",
    "其他宽基",
    "创业板50",
    "双创50",
    "中证2000",
    "国证2000",
)
INNOVATION_CODES = ("159915", "588000", "159949", "588080", "159952")
INDEX_SYMBOLS = dict(
    zip(
        ("hs300", "sse50", "sse180", "csi500", "csi800", "csi1000", "chinext", "star50", "sz100"),
        (
            "sh000300",
            "sh000016",
            "sh000010",
            "sh000905",
            "sh000906",
            "sh000852",
            "sz399006",
            "sh000688",
            "sz399330",
        ),
        strict=True,
    )
)


def read(name):
    try:
        return read_local_json(ROOT + name + ".json")
    except ResearchProviderError:
        return {}


def number(value):
    result = Decimal(str(value).replace(",", ""))
    if not result.is_finite():
        raise ValueError("invalid native ETF number")
    return result


def get(client, url, **kwargs):
    response = client.get(url, **kwargs)
    response.raise_for_status()
    digest = hashlib.sha256(response.content).hexdigest()
    write_local_json(
        "raw/research/etf-native/" + digest + ".json",
        {
            "sourceUrl": str(response.url),
            "retrievedAt": datetime.now(UTC).isoformat(),
            "sha256": digest,
            "bodyHex": response.content.hex(),
            "responseHeaders": {
                key: response.headers[key]
                for key in ("date", "age", "cache-control", "via", "x-cache", "last-modified", "etag")
                if key in response.headers
            },
        },
    )
    return response


def category(name):
    if "联接" in name or "增强" in name:
        return None
    for text, label in (
        ("创业板50", "创业板50"),
        ("科创创业50", "双创50"),
        ("双创50", "双创50"),
        ("科创50", "科创50"),
        ("A500", "中证A500"),
        ("沪深300", "沪深300"),
        ("中证1000", "中证1000"),
        ("中证500", "中证500"),
        ("上证50", "上证50"),
        ("中证2000", "中证2000"),
        ("国证2000", "国证2000"),
    ):
        if re.search(re.escape(text) + r"(?:指数)?ETF", name):
            return label
    # Exclude other ChiNext sector, value, growth, composite and 200 indices.
    if re.search(r"创业板(?:指)?ETF", name):
        return "创业板指"
    if re.search(
        r"(?:科创100|科创综指|上证180|中证800|深证100|深证50|深证成指|中证A50|中证A100|上证综指|上证指数|中证100)ETF",
        name,
    ):
        return "其他宽基"
    return None


def parse_sse(payload, day):
    rows = payload["result"]
    if not rows:
        raise ValueError("SSE share date unpublished: " + day)
    result = {}
    for row in rows:
        if row["STAT_DATE"] != day:
            raise ValueError("SSE share date mismatch")
        code = row["SEC_CODE"]
        if not re.fullmatch(r"\d{6}", code):
            raise ValueError("invalid SSE fund code")
        if code in result:
            raise ValueError("duplicate SSE share code")
        shares = number(row["TOT_VOL"]) * 10000
        if shares < 0:
            raise ValueError("negative SSE shares")
        result[code] = str(shares)
    return result


def xlsx_rows(content):
    """Read the exchange's XLSX download as data, without evaluating formulas."""
    ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = [
                "".join(node.itertext())
                for node in ET.fromstring(archive.read("xl/sharedStrings.xml"))
            ]
        sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        for row in sheet.findall(".//s:sheetData/s:row", ns):
            values = []
            for cell in row.findall("s:c", ns):
                if cell.find("s:f", ns) is not None:
                    raise ValueError("unexpected formula in exchange data")
                value = cell.findtext("s:v", "", ns)
                if cell.get("t") == "s":
                    value = strings[int(value)]
                if cell.get("t") == "inlineStr":
                    value = "".join(cell.find("s:is", ns).itertext())
                values.append(value)
            yield values


def parse_szse(content):
    result = {}
    header = None
    for values in xlsx_rows(content):
        if "基金代码" in values and "日期" in values:
            header = values
            continue
        if header is None or len(values) != len(header):
            continue
        row = dict(zip(header, values, strict=True))
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row.get("日期", "")):
            continue
        code = row["基金代码"].strip().zfill(6)
        if not re.fullmatch(r"\d{6}", code):
            raise ValueError("invalid SZSE fund code")
        datetime.strptime(row["日期"], "%Y-%m-%d")
        key = "基金规模(份)" if "基金规模(份)" in row else "基金规模(万份)"
        if key not in row:
            raise ValueError("SZSE share unit changed")
        shares = number(row[key]) * (10000 if "万份" in key else 1)
        if shares < 0:
            raise ValueError("negative SZSE shares")
        group = result.setdefault(row["日期"], {})
        if code in group:
            raise ValueError("duplicate SZSE share code/date")
        group[code] = str(shares)
    if not result:
        raise ValueError("empty SZSE share history")
    return result


def parse_market(rows, closed_before):
    result = []
    for row in rows:
        day = row["day"][:10]
        datetime.strptime(day, "%Y-%m-%d")
        if day >= closed_before:
            continue
        close = number(row["close"])
        amount = number(row["amount"]) if row.get("amount") is not None else None
        if close <= 0 or (amount is not None and amount < 0):
            raise ValueError("invalid native daily quote")
        result.append(
            {
                "date": day,
                "close": str(close),
                "amount": str(amount) if amount is not None else None,
                "volume": str(number(row["volume"])),
            }
        )
    if not result or [r["date"] for r in result] != sorted({r["date"] for r in result}):
        raise ValueError("invalid native daily sessions")
    return result


def closed_market_cutoff(now):
    local = now.astimezone(CHINA)
    return (local.date() + timedelta(days=1 if local.time() >= time(15, 10) else 0)).isoformat()


def closed_session_target(now):
    """Scheduling target only; publication still requires dated source inputs."""
    local = now.astimezone(CHINA)
    day = local.date() if local.time() >= time(15, 10) else local.date() - timedelta(days=1)
    from app.data_audit_calendar import calendar_snapshot
    from app.database_connection import read_only_connection

    with read_only_connection() as db:
        calendar = calendar_snapshot(db, local.date().isoformat())
    if calendar:
        return max(d for d in calendar["days"] if d <= day.isoformat())
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day.isoformat()


def repair_cumulative_history(client, symbol, now):
    """Fetch original 5-minute bars only for gaps in the recent baseline window."""
    from app.research_etf_cumulative import day_curve

    today = now.astimezone(CHINA).date().isoformat()
    market = {r["date"]: r for r in read("market/" + symbol).get("rows", [])}
    dates = sorted(day for day in market if day < today)[-20:]
    old = read("minutes-5m/" + symbol)
    one = read("minutes/" + symbol).get("days", {})
    five = old.get("days", {})
    missing = [day for day in dates
               if day_curve(five.get(day, []), day, 5) is None
               and day_curve(one.get(day, []), day, 1) is None]
    if not missing:
        return []
    response = get(client, DAILY_MARKET, params={
        "secid": ("1." if symbol.startswith("sh") else "0.") + symbol[2:],
        "klt": 5, "fqt": 0, "beg": missing[0].replace("-", ""),
        "end": missing[-1].replace("-", ""), "lmt": 1970,
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
    })
    payload = response.json().get("data") or {}
    if payload.get("code") != symbol[2:] or payload.get("market") != (1 if symbol.startswith("sh") else 0):
        raise ValueError("cumulative five-minute instrument identity mismatch")
    candidates = {}
    for line in payload.get("klines") or []:
        fields = line.split(",")
        if len(fields) < 7 or fields[0][:10] not in missing:
            continue
        stamp = fields[0] + ":00"
        datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S")
        candidates.setdefault(stamp[:10], []).append({
            "day": stamp, "open": fields[1], "close": fields[2],
            "high": fields[3], "low": fields[4], "volume": fields[5], "amount": fields[6],
        })
    checks = {}
    for day in missing:
        curve = day_curve(candidates.get(day, []), day, 5)
        if curve is None:
            raise ValueError("incomplete cumulative five-minute session: " + symbol + " " + day)
        total = curve[-1] * YI
        official = number(market[day]["amount"])
        if official < 0 or abs(total - official) > max(Decimal(1), official * Decimal("0.01")):
            raise ValueError("cumulative five-minute turnover does not reconcile: " + symbol + " " + day)
        checks[day] = {"fiveMinute": str(total), "daily": str(official),
                       "dailyRelativeError": str(abs(total - official) / max(official, Decimal(1)))}
    digest = hashlib.sha256(response.content).hexdigest()
    write_local_json(ROOT + "minutes-5m/" + symbol + ".json", {
        **old, "symbol": symbol, "intervalMinutes": 5, "amountUnit": "CNY", "volumeUnit": "lot",
        "days": {**five, **candidates}, "sourceUrl": str(response.url), "sha256": digest,
        "retrievedAt": now.isoformat(), "status": "ready",
        "dailyChecks": {**old.get("dailyChecks", {}), **checks},
        "sourcesByDate": {**old.get("sourcesByDate", {}), **{
            day: {"sourceUrl": str(response.url), "sha256": digest, "retrievedAt": now.isoformat()}
            for day in missing}},
    })
    return missing


def refresh(universe, basket, *, pending_only=False):
    """Refresh recent source inputs; each fund keeps its own last valid cache."""
    now = datetime.now(UTC)
    local = now.astimezone(CHINA)
    # Daily production starts at 15:10. Shares and NAV must separately
    # publish that exact date; unavailable inputs never become today's values.
    cutoff = closed_market_cutoff(now)
    failures = []
    with httpx.Client(
        timeout=25,
        follow_redirects=True,
        verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
        headers={"User-Agent": "Mozilla/5.0"},
    ) as client:
        response = get(client, CATALOG)
        body = response.content.decode("utf-8-sig").strip().removesuffix(";")
        listing = json.loads(body[body.index("[") :])
        if len(listing) < 100:
            raise ValueError("native fund catalog incomplete")
        catalog = []
        required = {m["code"] for m in universe if m.get("dashboard_eligible")} | {
            s[2:] for s in basket[1:]
        }
        for code, _, name, kind, _ in listing:
            group = category(name) if kind == "指数型-股票" and "ETF" in name else None
            if (group or code in required) and code.startswith(("15", "51", "56", "58")):
                if not re.fullmatch(r"\d{6}", code) or re.search(r"[<>&\"']", name):
                    raise ValueError("invalid native ETF identity or label")
                catalog.append(
                    {
                        "code": code,
                        "name": name,
                        "category": group,
                        "symbol": ("sz" if code.startswith("15") else "sh") + code,
                    }
                )
        if not required <= {m["code"] for m in catalog}:
            raise ValueError("native ETF catalog missing required members")
        index_response = get(
            client, MARKET, params={"symbol": "sh000001", "scale": 240, "ma": "no", "datalen": 12}
        )
        index = parse_market(index_response.json(), cutoff)
        sessions = [r["date"] for r in index][-5:]
        shares = read("shares").get("days", {})
        prior_state = read("refresh") if pending_only else {}
        known_catalog = prior_state.get("catalog") or catalog
        exchange_codes = {
            exchange: {m["code"] for m in known_catalog if m["symbol"].startswith(exchange)}
            for exchange in ("sh", "sz")
        }

        def missing_days(exchange):
            return [
                day for day in sessions
                if not pending_only or not exchange_codes[exchange] <= shares.get(day, {}).keys()
            ]

        # Both exchanges expose dated histories; re-read recent dates for revisions.
        for day in missing_days("sh"):
            try:
                response = get(
                    client,
                    SSE,
                    params={
                        "sqlId": "COMMON_SSE_ZQPZ_ETFZL_XXPL_ETFGM_SEARCH_L",
                        "STAT_DATE": day,
                        "isPagination": "true",
                        "pageHelp.pageSize": 10000,
                        "pageHelp.pageNo": 1,
                    },
                    headers={"Referer": "https://www.sse.com.cn/"},
                )
                shares.setdefault(day, {}).update(parse_sse(response.json(), day))
            except Exception as exc:
                failures.append({"source": "sse", "date": day, "error": str(exc)[:160]})
        try:
            szse_days = missing_days("sz")
            if szse_days:
                response = get(
                    client,
                    SZSE,
                    params={
                        "SHOWTYPE": "xlsx",
                        "CATALOGID": "scsj_fund_jjgm",
                        "TABKEY": "tab1",
                        "txtStart": szse_days[0],
                        "txtEnd": szse_days[-1],
                        "jjlb": "ETF",
                    },
                    headers={
                        "Referer": "https://www.szse.cn/market/fund/volume/etf/index.html",
                        "Cache-Control": "no-cache",
                    },
                )
                dated = parse_szse(response.content)
                if any(
                    day not in sessions or not szse_days[0] <= day <= szse_days[-1]
                    for day in dated
                ):
                    raise ValueError("SZSE share date outside requested sessions")
                if szse_days[-1] not in dated:
                    logging.getLogger(__name__).warning(
                        "ETF SZSE shares response behind request: requested=%s returned=%s age=%s cache=%s",
                        szse_days[-1], max(dated, default="none"),
                        response.headers.get("age"), response.headers.get("x-cache"),
                    )
                for day, values in dated.items():
                    shares.setdefault(day, {}).update(values)
        except Exception as exc:
            failures.append({"source": "szse", "error": str(exc)[:160]})
        write_local_json(
            ROOT + "shares.json",
            {"days": shares, "retrievedAt": now.isoformat(), "sources": [SSE, SZSE]},
        )
        catalog = [
            m
            for m in catalog
            if m["code"] in required
            or any(number(shares.get(day, {}).get(m["code"], 0)) > 0 for day in sessions)
        ]

        def collect(meta):
            code = meta["code"]
            old = read("funds/" + code)
            rows = {r["date"]: r for r in old.get("rows", [])}
            if pending_only and old.get("status") == "ready" and rows.get(sessions[-1], {}).get("flowYi") is not None:
                return old
            try:
                if pending_only and any(code not in shares.get(day, {}) for day in sessions[-2:]):
                    raise ValueError("exchange shares pending for " + sessions[-1])
                response = get(
                    client,
                    NAV,
                    params={"fundCode": code, "pageIndex": 1, "pageSize": 12},
                    headers={"Referer": "https://fundf10.eastmoney.com/"},
                )
                navs = response.json()["Data"]["LSJZList"]
                nav = {
                    r["FSRQ"]: number(r["DWJZ"])
                    for r in navs
                    if r.get("DWJZ") not in (None, "", "--")
                }
                if not nav or any(v <= 0 for v in nav.values()):
                    raise ValueError("invalid fund unit NAV")
                fresh_dates = set()
                for i, day in enumerate(sessions[1:], 1):
                    current, previous = (
                        shares.get(day, {}).get(code),
                        shares.get(sessions[i - 1], {}).get(code),
                    )
                    if current is None or previous is None or day not in nav:
                        continue
                    delta = number(current) - number(previous)
                    if sessions[i - 1] in nav and (
                        nav[day] / nav[sessions[i - 1]] < Decimal("0.6")
                        or nav[day] / nav[sessions[i - 1]] > Decimal("1.6")
                    ):
                        raise ValueError("NAV/share corporate action requires verification")
                    rows[day] = {
                        "date": day,
                        "shares": current,
                        "previousShares": previous,
                        "unitNav": str(nav[day]),
                        "flowYi": str(delta * nav[day] / YI),
                    }
                    fresh_dates.add(day)
                if sessions[-1] not in fresh_dates:
                    missing = [
                        name for name, available in (
                            ("current_shares", code in shares.get(sessions[-1], {})),
                            ("previous_shares", code in shares.get(sessions[-2], {})),
                            ("unit_nav", sessions[-1] in nav),
                        ) if not available
                    ]
                    raise ValueError(
                        "fund shares/NAV not complete for " + sessions[-1] + ": " + ",".join(missing)
                    )
                doc = {
                    "meta": meta,
                    "rows": [rows[d] for d in sorted(rows)],
                    "status": "ready",
                    "retrievedAt": now.isoformat(),
                    "sourceUrls": [SSE if meta["symbol"].startswith("sh") else SZSE, NAV],
                }
            except Exception as exc:
                doc = {
                    **old,
                    "meta": meta,
                    "rows": [rows[d] for d in sorted(rows)],
                    "status": "stale" if old.get("rows") else "no_data",
                    "attemptedAt": now.isoformat(),
                    "error": str(exc)[:160],
                }
            write_local_json(ROOT + "funds/" + code + ".json", doc)
            return doc

        with ThreadPoolExecutor(max_workers=4) as pool:
            docs = list(pool.map(collect, catalog))

        symbols = (
            {m["symbol"] for m in catalog if m["code"] in required or m.get("category")}
            | set(INDEX_SYMBOLS.values())
            | {"sh000001"}
        )

        def collect_market(symbol):
            old = read("market/" + symbol)
            if (
                pending_only and old.get("status") == "ready"
                and (old.get("rows") or [{}])[-1].get("date") == sessions[-1]
                and old["rows"][-1].get("amount") is not None
                and not any(f.get("source") == symbol for f in prior_state.get("failures", []))
            ):
                return
            try:
                response = get(
                    client,
                    DAILY_MARKET,
                    params={
                        "secid": ("1." if symbol.startswith("sh") else "0.") + symbol[2:],
                        "klt": 101,
                        "fqt": 0,
                        "beg": sessions[0].replace("-", ""),
                        "end": sessions[-1].replace("-", ""),
                        "fields1": "f1,f2,f3,f4,f5,f6",
                        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                    },
                )
                payload = response.json()["data"]
                if payload["code"] != symbol[2:]:
                    raise ValueError("daily market identity mismatch")
                rows = parse_market(
                    [
                        {
                            "day": values[0],
                            "close": values[2],
                            "volume": str(number(values[5]) * 100),
                            "amount": values[6],
                        }
                        for values in (line.split(",") for line in payload["klines"])
                    ],
                    cutoff,
                )
                daily_url = str(response.url)
                if rows[-1]["date"] != sessions[-1]:
                    raise ValueError("daily market session delayed")
                retained = {r["date"]: r for r in read("market/" + symbol).get("rows", [])}
                retained.update({r["date"]: r for r in rows})
                write_local_json(
                    ROOT + "market/" + symbol + ".json",
                    {
                        "rows": [retained[day] for day in sorted(retained)],
                        "sourceUrl": daily_url,
                        "retrievedAt": now.isoformat(),
                        "status": "ready",
                    },
                )
                if symbol in basket or symbol in INDEX_SYMBOLS.values():
                    from app.research_etf_observation import (
                        minute_request, minute_response, parse_minutes,
                    )

                    url, params = minute_request(symbol, 1023)
                    response = get(client, url, params=params)
                    minutes = minute_response(symbol, response.json())

                    parse_minutes(minutes)
                    previous_days = read("minutes/" + symbol).get("days", {})
                    amounts = {
                        day: {m["day"]: m for m in group} for day, group in previous_days.items()
                    }
                    for minute in minutes:
                        amounts.setdefault(minute["day"][:10], {})[minute["day"]] = minute
                    write_local_json(
                        ROOT + "minutes/" + symbol + ".json",
                        {
                            "days": {
                                day: [group[t] for t in sorted(group)]
                                for day, group in amounts.items()
                            },
                            "sourceUrl": str(response.url),
                            "retrievedAt": now.isoformat(),
                        },
                    )
            except Exception as exc:
                failures.append({"source": symbol, "error": str(exc)[:160]})

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(collect_market, sorted(symbols)))

        # Baselines have their own completeness. A daily quote can be ready while
        # one-minute feeds omit a bar, so pending daily-input retries must not skip this.
        def repair_baseline(symbol):
            try:
                repair_cumulative_history(client, symbol, now)
            except Exception as exc:
                failures.append({"source": "cumulative:" + symbol, "error": str(exc)[:160]})

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(repair_baseline, basket[1:]))
    from app.research_etf_broad import refresh_projection

    failures.extend(
        {"source": d["meta"]["code"], "error": d.get("error")}
        for d in docs
        if d["status"] != "ready"
    )
    refresh_projection(catalog, sessions, shares, failures)
    result = {
        "catalog": catalog,
        "sessions": sessions,
        "index": index,
        "retrievedAt": now.isoformat(),
        "status": "partial" if failures else "ready",
        "failures": failures,
        "sourceUrls": [SSE, SZSE, NAV, DAILY_MARKET, MARKET, CATALOG],
    }
    write_local_json(ROOT + "refresh.json", result)
    return result


def build_innovation_ratio(funds, markets, basket):
    """Signed net-subscription and actual-turnover shares of the specified basket."""
    codes = [symbol[2:] for symbol in basket[1:]]
    result = {
        "basketCodes": codes,
        "innovationCodes": list(INNOVATION_CODES),
        "subscriptionMethod": "signed_net_subscription",
        "rows": [],
    }
    if len(codes) != len(set(codes)) or not set(INNOVATION_CODES).issubset(codes):
        return result
    fund_days = set().union(*(set(funds.get(code, {})) for code in codes))
    first_fund_day = min(fund_days) if fund_days else None
    days = sorted(
        set().union(
            *(set(funds.get(code, {})) for code in codes),
            *(set(markets.get(symbol, {})) for symbol in basket[1:]),
        )
    )
    for day in days:
        cash, amounts = {}, {}
        for symbol, code in zip(basket[1:], codes, strict=True):
            fund = funds.get(code, {}).get(day, {})
            value = fund.get("flowYi")
            cash[code] = number(value) if value is not None else None
            amount = markets.get(symbol, {}).get(day, {}).get("amount")
            # Complete exchange snapshots prove a not-yet-listed fund did not trade.
            amounts[code] = (
                number(amount)
                if amount is not None
                else (Decimal(0) if fund.get("listed") is False else None)
            )

        def ratio(values):
            if any(v is None for v in values.values()):
                return None, None, None
            denominator = sum(values.values(), Decimal(0))
            numerator = sum((values[code] for code in INNOVATION_CODES), Decimal(0))
            return (
                str(numerator / denominator * 100) if denominator else None,
                str(numerator),
                str(denominator),
            )

        net, selected_cash, total_cash = ratio(cash)
        turnover, selected_amount, total_amount = ratio(amounts)
        if (
            selected_cash is None
            and selected_amount is None
            and (first_fund_day is None or day < first_fund_day)
        ):
            continue
        result["rows"].append(
            {
                "date": day,
                "netSubscriptionPct": net,
                "turnoverPct": turnover,
                "selectedNetFlowYi": selected_cash,
                "basketNetFlowYi": total_cash,
                "selectedAmountYuan": selected_amount,
                "basketAmountYuan": total_amount,
            }
        )
    return result


def build_reference(previous, basket):
    """Build the chart projection; incomplete baskets/categories stay null."""
    state = read("refresh")
    if not state.get("sessions"):
        raise ValueError("native ETF daily inputs not yet collected")
    empty = {
        "dailyData": {"dates": [], "amount": [], "netflow": [], "idx": []},
        "broadData": {
            "dates": [],
            "cats": list(CATEGORIES),
            "colors": ["#5470c6", "#91cc75", "#fac858", "#ee6666"],
            "series": {c: [] for c in CATEGORIES},
            "total": [],
            "totalCum": [],
        },
        "initData": {
            "date": state["sessions"][-1],
            "times": [],
            "bars": [],
            "closes": [],
            "table": [
                {
                    "code": s[2:],
                    "name": next(
                        (m["name"] for m in state["catalog"] if m["code"] == s[2:]), s[2:]
                    ),
                }
                for s in basket[1:]
            ],
        },
        "cmpData": {"support": [], "recent": [], "today": {}, "latest": {}},
        "typData": {"slots": [], "supAmt": [], "supIdx": [], "norAmt": [], "norIdx": []},
        "cumData": {},
    }
    data = json.loads(json.dumps(previous or empty))
    codes = [s[2:] for s in basket[1:]]
    old_codes = [r["code"] for r in data["initData"].get("table", [])]
    changed_basket = set(old_codes) != set(codes)
    if changed_basket:
        data["initData"].update({"times": [], "bars": [], "closes": []})
        data["cumData"] = {}
    data["basketCodes"] = codes
    data["initData"]["table"] = empty["initData"]["table"]
    # Imported case studies retain their original, explicitly identified sample.
    data["typData"].setdefault("basketCount", len(old_codes) or len(codes))
    data["indexPrices"] = {
        key: {
            "name": name,
            "symbol": INDEX_SYMBOLS[key],
            "sourceUrl": read("market/" + INDEX_SYMBOLS[key]).get("sourceUrl"),
            "rows": [
                {"date": row["date"], "close": row["close"]}
                for row in read("market/" + INDEX_SYMBOLS[key]).get("rows", [])
            ],
        }
        for key, name in (
            ("hs300", "沪深300"),
            ("csi1000", "中证1000"),
            ("star50", "科创50"),
            ("chinext", "创业板指"),
        )
    }
    sessions = state["sessions"]
    shares = read("shares").get("days", {})
    funds = {
        m["code"]: {r["date"]: r for r in read("funds/" + m["code"]).get("rows", [])}
        for m in state["catalog"]
    }
    markets = {s: {r["date"]: r for r in read("market/" + s).get("rows", [])} for s in basket}
    data["innovationRatio"] = build_innovation_ratio(funds, markets, basket)
    daily = data["dailyData"]
    old_index = dict(zip(daily["dates"], daily["idx"], strict=True))
    # Rebuild every archived date from constituents so changing the basket never
    # splices an old basket's totals into the new history.
    fund_days = set().union(*(set(funds.get(code, {})) for code in codes))
    first_fund_day = min(fund_days) if fund_days else sessions[1]
    days = sorted(day for day in set(daily["dates"]) | set(sessions[1:]) | fund_days
                  if day >= first_fund_day)
    rows = {}
    coverage = {}
    history_until = data["broadData"].get("choiceHistoryUntil", "")
    history_listings = data["broadData"].get("choiceListingDates", {})
    for day in days:
        session_members = basket[1:]
        if day <= history_until:
            session_members = [
                symbol for symbol in session_members
                if day > history_listings.get(symbol[2:], day)
            ]
        flows = [funds.get(s[2:], {}).get(day, {}).get("flowYi") for s in session_members]
        amounts = [
            markets[s].get(day, {}).get("amount")
            if markets[s].get(day, {}).get("amount") is not None
            else (0 if funds.get(s[2:], {}).get(day, {}).get("listed") is False else None)
            for s in session_members
        ]
        rows[day] = {
            "netflow": float(sum((number(v) for v in flows), Decimal(0)))
            if flows and all(v is not None for v in flows)
            else None,
            "amount": float(sum((number(v) for v in amounts), Decimal(0)) / YI)
            if amounts and all(v is not None for v in amounts)
            else None,
            "idx": float(markets[basket[0]][day]["close"])
            if day in markets[basket[0]] else old_index.get(day),
        }
        coverage[day] = {
            "expected": len(session_members),
            "flow": sum(v is not None for v in flows),
            "turnover": sum(v is not None for v in amounts),
        }
    dates = sorted(rows)
    data["dailyData"] = {
        "dates": dates,
        **{k: [rows[d][k] for d in dates] for k in ("amount", "netflow", "idx")},
    }
    broad = data["broadData"]
    # Existing imported history retains its dates and source; new observations are native.
    all_dates = sorted(set(broad["dates"]) | set(sessions[1:]))
    old_rows = {
        d: {c: broad["series"][c][i] for c in broad["cats"]} for i, d in enumerate(broad["dates"])
    }
    cats = list(broad["cats"])
    for cat in CATEGORIES:
        if cat not in cats:
            cats.append(cat)
    broad_coverage = {}
    for i, day in enumerate(sessions[1:], 1):
        values = {}
        for cat in cats:
            members = [
                m
                for m in state["catalog"]
                if m["category"] == cat and (
                    number(shares.get(day, {}).get(m["code"], 0)) > 0
                    or (m["code"] not in shares.get(day, {})
                        and number(shares.get(sessions[i - 1], {}).get(m["code"], 0)) > 0)
                )
            ]
            flows = [funds[m["code"]].get(day, {}).get("flowYi") for m in members]
            # One unavailable fund must not hide the other funds' observations.
            valid = [number(v) for v in flows if v is not None]
            values[cat] = float(sum(valid, Decimal(0))) if valid or not members else None
            broad_coverage.setdefault(day, {})[cat] = {
                "expected": len(members),
                "covered": len(valid),
                "missingCodes": [m["code"] for m, value in zip(members, flows) if value is None],
            }
        old_rows[day] = values
    totals = [
        sum((number(old_rows[d][c]) for c in cats if old_rows.get(d, {}).get(c) is not None), Decimal(0))
        if any(old_rows.get(d, {}).get(c) is not None
               and broad_coverage.get(d, {}).get(c, {}).get("expected", 1) > 0 for c in cats)
        else None
        for d in all_dates
    ]
    cumulative, running = [], 0
    for value in totals:
        running = running + value if running is not None and value is not None else None
        cumulative.append(running)
    broad.update(
        {
            "dates": all_dates,
            "cats": cats,
            "series": {c: [old_rows.get(d, {}).get(c) for d in all_dates] for c in cats},
            "total": [str(value) if value is not None else None for value in totals],
            "totalCum": [str(value) if value is not None else None for value in cumulative],
            "coverage": broad_coverage,
        }
    )
    points = [{"date": d, **rows[d]} for d in dates]
    valid = [r for r in points if r["netflow"] is not None]
    support = {
        r["date"]: r for r in valid
        if r["netflow"] > 100
        and not (
            "2024-09-24" <= r["date"] <= "2024-10-18"
            or "2026-01-14" <= r["date"] <= "2026-01-30"
            or r["date"] in {"2026-02-02", "2026-02-13", "2026-02-26"}
        )
    }
    data["cmpData"].update(
        {
            "support": [support[d] for d in sorted(support)],
            "recent": points[-20:],
            "today": points[-1],
            "latest": valid[-1] if valid else {},
            "sample": {
                "n": len(support),
                "amtMed": float(median(number(r["amount"]) for r in support.values()))
                if support and all(r["amount"] is not None for r in support.values()) else None,
            },
            "excluded": "2024-09-24~10-18、2026-01-14~01-30、2026-02-02/13/26",
        }
    )
    data["nativeCoverage"] = {"basket": coverage, "broad": broad_coverage}
    data["nativeFrom"] = min(data.get("nativeFrom", first_fund_day), first_fund_day)
    data["flowMethod"] = "同日基金单位净值 × 相邻交易日份额变动；缺少输入留空"
    relevant = {s[2:] for s in basket[1:]} | {
        m["code"] for m in state["catalog"] if m.get("category")
    }
    data["nativeStatus"] = (
        "partial"
        if any(read("funds/" + code).get("status") != "ready" for code in relevant)
        or state.get("status") == "stale"
        or any(f.get("source") in {"sse", "szse", *basket} for f in state.get("failures", []))
        else "ready"
    )
    from app.research_etf_cumulative import build_cumulative

    data["cumData"] = build_cumulative(
        read, basket, data["dailyData"]["dates"],
        datetime.now(UTC).astimezone(CHINA).date().isoformat(),
    )
    from app.research_etf_broad import project

    data.update(project(data, read("broad-observation")))

    return data


def restore_tracking_shares(data, native_fund):
    """Rejoin archived exchange shares into retained price rows, without replacing observations."""
    from app.research_etf_tracking import number as maybe_number

    native_rows = {r["date"]: r for r in native_fund.get("rows", [])}
    # Imported tracking shares are rounded to four decimals in yi units. Reject a
    # different share basis instead of splicing raw units into adjusted history.
    anchors = 0
    for row in data.get("series", []):
        known = maybe_number(row.get("qfq_total_units_yi"))
        raw = maybe_number(native_rows.get(row["date"], {}).get("shares"))
        if known is not None and raw is not None:
            if abs(known - raw / YI) > Decimal("0.00005"):
                return data
            anchors += 1
    if not anchors:
        return data
    rows = []
    for original in data.get("series", []):
        row = dict(original)
        source = native_rows.get(row["date"], {})
        current, previous = maybe_number(source.get("shares")), maybe_number(source.get("previousShares"))
        if current is not None and maybe_number(source.get("shareConversionFactor", "1")) == 1:
            restored = False
            for field, value in (
                ("qfq_total_units_yi", current / YI),
                ("qfq_delta_units_yi", (current - previous) / YI if previous is not None else None),
            ):
                if row.get(field) is None and value is not None:
                    row[field] = str(value)
                    restored = True
            if restored:
                row["share_recovery_source"] = "exchange_native_archive"
                row["share_source_urls"] = native_fund.get("sourceUrls", [])
        rows.append(row)
    return {**data, "series": rows}


def publish_tracking(state, universe, *, pending_only=False):
    """Update existing tracking artifacts from native dated inputs, retaining history."""
    from app import research_etf_tracking as tracking

    now = datetime.now(UTC).isoformat()
    shares = read("shares").get("days", {})
    failures = []
    with httpx.Client(timeout=25, verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)) as client:

        def collect(meta):
            code = meta["code"]
            old = tracking.read("etfs/" + code)
            if old.get("data", {}).get("series"):
                restored = restore_tracking_shares(old["data"], read("funds/" + code))
                if restored != old["data"]:
                    old = {**old, "data": restored}
                    tracking.write("etfs/" + code, old)
            if (
                pending_only and old.get("status") == "ready"
                and (old.get("data", {}).get("series") or [{}])[-1].get("date") == state["sessions"][-1]
            ):
                return
            try:
                if pending_only and any(code not in shares.get(day, {}) for day in state["sessions"][-2:]):
                    raise ValueError("exchange shares pending for " + state["sessions"][-1])
                symbol = meta["exchange"].lower() + code
                market_doc = read("market/" + symbol)
                if market_doc.get("status") != "ready":
                    raise ValueError("native daily market source unavailable")
                market = {r["date"]: r for r in market_doc.get("rows", [])}
                response = get(
                    client,
                    DAILY_MARKET,
                    params={
                        "secid": ("1." if symbol.startswith("sh") else "0.") + code,
                        "klt": 101,
                        "fqt": 1,
                        "beg": state["sessions"][0].replace("-", ""),
                        "end": state["sessions"][-1].replace("-", ""),
                        "fields1": "f1,f2,f3,f4,f5,f6",
                        "fields2": "f51,f52,f53,f54,f55,f56,f57",
                    },
                )
                quoted = response.json()["data"]
                if quoted["code"] != code:
                    raise ValueError("qfq ETF identity mismatch")
                price_rows = {
                    values[0]: values for values in (line.split(",") for line in quoted["klines"])
                }
                prices = {d: number(r[2]) for d, r in price_rows.items()}
                if state["sessions"][-1] not in prices or state["sessions"][-1] not in market:
                    raise ValueError("native latest closed session incomplete")
                history = {r["date"]: r for r in old.get("data", {}).get("series", [])}
                for i, day in enumerate(state["sessions"][1:], 1):
                    prev = state["sessions"][i - 1]
                    current, prior = shares.get(day, {}).get(code), shares.get(prev, {}).get(code)
                    if day not in market or day not in prices or current is None or prior is None:
                        continue
                    price = prices[day]
                    # Only a stable recent share-unit basis can extend an imported qfq series.
                    native_price = number(market[day]["close"])
                    factor = price / native_price
                    previous_factor = prices.get(prev, price) / number(
                        market.get(prev, market[day])["close"]
                    )
                    if abs(factor / previous_factor - 1) > Decimal("0.001"):
                        raise ValueError(
                            "share/price adjustment requires corporate-action verification"
                        )
                    volume = number(market[day]["volume"])
                    # Native daily volume is shares. Keep the existing price×volume estimate.
                    average = sum((number(v) for v in price_rows[day][1:5]), Decimal(0)) / 4
                    turnover = average * volume / YI
                    history[day] = {
                        "date": day,
                        "etf_qfq_close": str(price),
                        "etf_qfq_avg_price_est": str(average),
                        "etf_qfq_turnover_est_yi": str(turnover),
                        "qfq_total_units_yi": str(number(current) / YI),
                        "qfq_delta_units_yi": str((number(current) - number(prior)) / YI),
                        "source": "native",
                        "share_basis": "exchange_native_units",
                    }
                if not history or max(history) < state["sessions"][-1]:
                    raise ValueError("native tracking inputs incomplete")
                data = {
                    **old.get("data", {}),
                    "meta": {
                        **old.get("data", {}).get("meta", meta),
                        "data_refreshed_at": now,
                        "shares_basis": "SSE/SZSE native daily shares",
                        "turnover_basis": (
                            "qfq OHLC typical price times native share volume; estimated turnover"
                        ),
                    },
                    "series": [history[d] for d in sorted(history)],
                }
                tracking.write(
                    "etfs/" + code,
                    {
                        "data": data,
                        "status": "ready",
                        "url": DAILY_MARKET,
                        "sourceUrls": [
                            SSE,
                            SZSE,
                            MARKET,
                            DAILY_MARKET,
                        ],
                        "fetchedAt": now,
                        "attemptedAt": now,
                    },
                )
            except Exception as exc:
                tracking.write(
                    "etfs/" + code,
                    {
                        **old,
                        "status": "stale" if old.get("data") else "no_data",
                        "attemptedAt": now,
                        "error": str(exc)[:160],
                    },
                )
                failures.append({"source": code, "error": str(exc)[:160]})

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(collect, [m for m in universe if m.get("dashboard_eligible")]))
    for key, symbol in INDEX_SYMBOLS.items():
        old = tracking.read("index-turnover/" + key)
        history = {r["date"]: r for r in old.get("data", {}).get("rows", [])}
        for row in read("market/" + symbol).get("rows", []):
            history[row["date"]] = {
                **history.get(row["date"], {}),
                "date": row["date"],
                "close": row["close"],
                "turnover_yi": str(number(row["amount"]) / YI)
                if row.get("amount") is not None
                else history.get(row["date"], {}).get("turnover_yi"),
            }
        tracking.write(
            "index-turnover/" + key,
            {
                "data": {
                    "meta": old.get("data", {}).get("meta", {}),
                    "rows": [history[d] for d in sorted(history)],
                },
                "status": "ready",
                "url": DAILY_MARKET,
                "fetchedAt": now,
                "attemptedAt": now,
            },
        )
    # Optional financing failures do not prevent price/share publication.
    from app.research_etf_native_margin import refresh as refresh_margin

    try:
        with httpx.Client(
            timeout=25,
            verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
            headers={"User-Agent": "Mozilla/5.0"},
        ) as client:
            failures.extend(refresh_margin(client, state, universe, pending_only=pending_only))
    except Exception as exc:
        failures.append({"source": "margin", "error": str(exc)[:160]})
    return failures
