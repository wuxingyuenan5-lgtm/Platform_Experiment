"""A-share capital dashboard: independent public collectors and local-only reads."""

import asyncio
import json
import logging
import re
import ssl
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import httpx
import truststore
from bs4 import BeautifulSoup

from app.research_cn_financing import local
from app.research_equity_metrics import number
from app.research_equity_sources import EASTMONEY_URL, archive, publish_artifact, read_artifact

ARTIFACT = "cn-capital"
_LOCK = asyncio.Lock()
SOURCES = {
    "issuance": ("股票发行规模", "同花顺", "https://data.10jqka.com.cn/macro/finance/"),
    "buybacks": ("公司回购", "东方财富", "https://data.eastmoney.com/gphg/hglist.html"),
    "holders": ("股东增减持", "东方财富", "https://data.eastmoney.com/executive/gdzjc.html"),
    "unlocks": ("限售解禁", "东方财富", "https://data.eastmoney.com/dxf/detail.html"),
    "funds": ("新成立权益基金", "天天基金", "https://fund.eastmoney.com/data/xinfound.html"),
}
MACRO = [
    "cn_margin_financing_balance",
    "cn_margin_financing_change",
    "cn_dr007",
    "cn_omo_7d",
    "cn_m2_yoy",
    "cn_m1_yoy",
    "cn_tsf_stock_yoy",
]


def day(value):
    result = str(value or "")[:10]
    date.fromisoformat(result)
    return result


def scaled(value, divisor=1):
    value = number(value)
    return str(value / Decimal(divisor)) if value is not None else None


def parse_issuance(content):
    table = BeautifulSoup(content, "lxml").select_one("table")
    if table is None:
        raise ValueError("issuance_table_missing")
    headers = [cell.get_text(strip=True) for cell in table.select("th")]
    expected = [
        "月份",
        "募集资金(亿元)",
        "首发募集资金(亿元)",
        "增发募集资金(亿元)",
        "配股募集资金(亿元)",
    ]
    if headers != expected:
        raise ValueError("issuance_columns_changed")
    rows = []
    for tr in table.select("tr"):
        cells = [c.get_text(strip=True).replace(",", "") for c in tr.select("td")]
        if not cells:
            continue
        if len(cells) != 5:
            raise ValueError("issuance_row_changed")
        rows.append(
            {
                "date": day(cells[0] + "-01"),
                **dict(
                    zip(
                        ["total", "ipo", "seo", "rights"],
                        [scaled(v) for v in cells[1:]],
                        strict=True,
                    )
                ),
            }
        )
    if not rows or len({r["date"] for r in rows}) != len(rows):
        raise ValueError("issuance_dates_invalid")
    return sorted(rows, key=lambda r: r["date"])


def parse_records(key, raw):
    rows = []
    for r in raw:
        if key == "buybacks":
            rows.append(
                {
                    "id": str(r["REPURCODE"]),
                    "code": r["DIM_SCODE"],
                    "name": r["SECURITYSHORTNAME"],
                    "date": day(r["UPD"]),
                    "asOf": day(r["DIM_DATE3"]) if r.get("DIM_DATE3") else None,
                    "planDate": day(r["DIM_DATE"]),
                    "progress": r["REPURPROGRESS"],
                    "amount": scaled(r.get("REPURAMOUNT"), 100000000),
                    "lower": scaled(r.get("REPURAMOUNTLOWER"), 100000000),
                    "upper": scaled(r.get("REPURAMOUNTLIMIT"), 100000000),
                }
            )
        elif key == "holders":
            # Change quantities are 10,000 shares; direction comes from disclosure,
            # never the sign of price changes or an inferred daily cash flow.
            rows.append(
                {
                    "code": r["SECURITY_CODE"],
                    "name": r["SECURITY_NAME_ABBR"],
                    "holder": r["HOLDER_NAME"],
                    "date": day(r["NOTICE_DATE"]),
                    "start": day(r["START_DATE"]) if r.get("START_DATE") else None,
                    "end": day(r["END_DATE"]) if r.get("END_DATE") else None,
                    "direction": r["DIRECTION"],
                    "shares": scaled(r.get("CHANGE_NUM")),
                    "price": scaled(r.get("TRADE_AVERAGE_PRICE")),
                    "market": r.get("MARKET"),
                }
            )
        elif key == "unlocks":
            rows.append(
                {
                    "code": r["SECURITY_CODE"],
                    "name": r["SECURITY_NAME_ABBR"],
                    "date": day(r["FREE_DATE"]),
                    "kind": r["FREE_SHARES_TYPE"],
                    "shares": scaled(r.get("CURRENT_FREE_SHARES")),
                    "amount": scaled(r.get("LIFT_MARKET_CAP"), 10000),
                    "ratio": scaled(number(r.get("TOTAL_RATIO")) * 100)
                    if number(r.get("TOTAL_RATIO")) is not None
                    else None,
                }
            )
        else:
            raise ValueError("unknown_capital_source")
    if key == "buybacks" and len({r["id"] for r in rows}) != len(rows):
        raise ValueError("duplicate_repurchase_plan")
    return sorted(rows, key=lambda r: (r["date"], r["code"]))


def parse_funds(content):
    # Only decode the JSON array; never execute upstream JavaScript.
    match = re.search(r"\bdatas\s*:\s*(\[.*\])\s*,\s*record\s*:\s*(\d+)", content, re.S)
    if not match:
        raise ValueError("fund_response_changed")
    raw = json.loads(match[1])
    rows = []
    for r in raw:
        if len(r) != 19:
            raise ValueError("fund_columns_changed")
        if not any(kind in r[4] for kind in ("股票", "混合")) or "QDII" in r[4]:
            continue
        # Keep share classes explicit. Source may repeat product-level amounts
        # across A/C; no aggregate and no guessed share-class merger.
        rows.append(
            {
                "code": r[0],
                "name": r[1],
                "manager": r[2],
                "kind": r[4],
                "shares": scaled(r[5]),
                "date": day(r[6]),
            }
        )
    return sorted(rows, key=lambda r: (r["date"], r["code"])), int(match[2])


async def fetch_records(client, key, today):
    recent = (today - timedelta(days=365)).isoformat()
    start, end = (today - timedelta(days=90)).isoformat(), (today + timedelta(days=90)).isoformat()
    report, sort, condition = {
        "buybacks": (
            "RPTA_WEB_GETHGLIST_NEW",
            "UPD,REPURCODE",
            f"(UPD>='{recent}')(UPD<='{today}')",
        ),
        "holders": (
            "RPT_SHARE_HOLDER_INCREASE",
            "NOTICE_DATE,SECURITY_CODE,EITIME",
            f"(NOTICE_DATE>='{start}')(NOTICE_DATE<='{today}')",
        ),
        "unlocks": (
            "RPT_LIFT_STAGE",
            "FREE_DATE,SECURITY_CODE",
            f"(FREE_DATE>='{start}')(FREE_DATE<='{end}')",
        ),
    }[key]
    rows, hashes, count = [], [], None
    stamp = datetime.now(UTC).isoformat()
    for page in range(1, 31):
        response = await client.get(
            EASTMONEY_URL,
            params={
                "reportName": report,
                "columns": "ALL",
                "sortColumns": sort,
                "sortTypes": ",".join(["-1"] * len(sort.split(","))),
                "filter": condition,
                "pageSize": 500,
                "pageNumber": page,
                "source": "WEB",
                "client": "WEB",
            },
        )
        response.raise_for_status()
        payload = json.loads(response.content, parse_float=Decimal)
        result = payload.get("result") or {}
        if payload.get("success") is not True or not isinstance(result.get("data"), list):
            raise ValueError("capital_provider_invalid")
        if count is not None and count != result["count"]:
            raise ValueError("capital_page_count_changed")
        count = result["count"]
        rows.extend(result["data"])
        hashes.append(await asyncio.to_thread(archive, f"capital_{key}", response.content, stamp))
        if page >= result["pages"]:
            if len(rows) != count:
                raise ValueError("capital_incomplete_pages")
            return (
                parse_records(key, rows),
                hashes,
                start if key != "buybacks" else recent,
                end if key == "unlocks" else today.isoformat(),
            )
    raise ValueError("capital_page_limit")


async def collect(force=False):
    async with _LOCK:
        now = datetime.now(UTC)
        today = now.astimezone(ZoneInfo("Asia/Shanghai")).date()
        stamp = now.isoformat()
        doc = read_artifact(ARTIFACT)
        sources = doc.setdefault("sources", {})
        context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        async with httpx.AsyncClient(
            verify=context,
            timeout=httpx.Timeout(25, connect=10),
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"},
        ) as client:
            for key, (label, provider, url) in SOURCES.items():
                old = sources.get(key, {})
                if not force and old.get("attemptedAt"):
                    hours = 1 if old.get("status") == "error" else 20
                    if now - datetime.fromisoformat(old["attemptedAt"]) < timedelta(hours=hours):
                        continue
                meta = {
                    "label": label,
                    "provider": provider,
                    "sourceUrl": url,
                    "attemptedAt": stamp,
                }
                try:
                    if key in {"issuance", "funds"}:
                        request_url = (
                            url
                            if key == "issuance"
                            else "https://fund.eastmoney.com/data/FundNewIssue.aspx"
                        )
                        params = (
                            {}
                            if key == "issuance"
                            else {
                                "t": "xcln",
                                "sort": "jzrgq,desc",
                                "y": "",
                                "page": "1,300",
                                "isbuy": "1",
                            }
                        )
                        response = await client.get(request_url, params=params)
                        response.raise_for_status()
                        if key == "issuance":
                            rows = parse_issuance(response.content)
                            # Retain earlier monthly rows, applying same-month revisions.
                            rows = sorted(
                                {r["date"]: r for r in [*old.get("rows", []), *rows]}.values(),
                                key=lambda r: r["date"],
                            )
                        else:
                            rows, total = parse_funds(response.text)
                            meta.update(sampleLimit=300, sourceRecordCount=total)
                        hashes = [
                            await asyncio.to_thread(
                                archive, f"capital_{key}", response.content, stamp
                            )
                        ]
                        start, end = None, None
                    else:
                        rows, hashes, start, end = await fetch_records(client, key, today)
                    if not rows:
                        raise ValueError("capital_no_observations")
                    sources[key] = {
                        **meta,
                        "status": "ready",
                        "fetchedAt": stamp,
                        "rows": rows,
                        "rawSha256": hashes,
                        "windowStart": start,
                        "windowEnd": end,
                        "observationDate": today.isoformat()
                        if key == "unlocks"
                        else max(r["date"] for r in rows),
                    }
                except Exception as exc:
                    logging.getLogger(__name__).warning(
                        "Capital source %s: %s", key, type(exc).__name__
                    )
                    sources[key] = {**old, **meta, "status": "error", "error": type(exc).__name__}
                doc["generatedAt"] = stamp
                await asyncio.to_thread(publish_artifact, ARTIFACT, doc)
        return doc


def aligned_difference(series, left, right, monthly=False):
    """Join actual observation periods only; never fill missing dates."""

    def lookup(sid):
        return {
            (r["date"][:7] if monthly else r["date"]): r.get("value")
            for r in series.get(sid, {}).get("observations", [])
        }

    a, b = lookup(left), lookup(right)
    rows = []
    for d in sorted(a.keys() | b.keys()):
        x, y = number(a.get(d)), number(b.get(d))
        rows.append(
            {
                "date": d + "-01" if monthly else d,
                "value": str(x - y) if x is not None and y is not None else None,
            }
        )
    return rows


def read_capital():
    from app.research_cn_institutions import read_institutions

    doc = read_artifact(ARTIFACT)
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    sources = {}
    for key, (label, provider, url) in SOURCES.items():
        source = dict(doc.get("sources", {}).get(key, {}))
        fetched = source.get("fetchedAt")
        source.update(
            label=label,
            provider=provider,
            sourceUrl=url,
            isStale=not fetched
            or datetime.now(UTC) - datetime.fromisoformat(fetched) > timedelta(hours=48),
        )
        source.setdefault("status", "unavailable")
        source.setdefault("rows", [])
        sources[key] = source
    series = {sid: local(f"public/v1/macro/series/{sid}.json") for sid in MACRO}
    for snapshot in series.values():
        observed = snapshot.get("observationDate")
        if observed:
            # Monthly timestamps label the period, not the publication date.
            tolerance = 75 if snapshot.get("frequency") == "monthly" else 7
            snapshot["isStale"] = bool(snapshot.get("isStale")) or (
                today - date.fromisoformat(observed)
            ).days > tolerance
    # Future events are disclosed schedules, not future observations or outflows.
    future = [
        r
        for r in sources["unlocks"]["rows"]
        if today.isoformat() <= r["date"] < (today + timedelta(days=30)).isoformat()
    ]
    weekly = {}
    for row in future:
        d = date.fromisoformat(row["date"])
        week = (d - timedelta(days=d.weekday())).isoformat()
        weekly.setdefault(week, []).append(number(row["amount"]))
    unlock_weeks = [
        {
            "date": k,
            "value": str(sum(v)) if all(x is not None for x in v) else None,
            "events": len(v),
        }
        for k, v in sorted(weekly.items())
    ]
    etf = local("public/v1/etf-observation/reference.json")
    from app.research_etf_observation import overview_summary
    broad_etf = overview_summary(etf.get("data", {}), {})
    daily = etf.get("data", {}).get("dailyData", {})
    dates, values = daily.get("dates", []), daily.get("netflow", [])
    if len(dates) != len(values):
        etf_rows = []
        etf = {**etf, "status": "error", "error": "etf_array_length_mismatch"}
    else:
        etf_rows = [{"date": d, "value": scaled(v)} for d, v in zip(dates, values, strict=True)]
    from app.data_audit_calendar import cached_sessions

    dates_needed = [rows[-1]["date"] for rows in (etf_rows, series["cn_margin_financing_balance"].get("observations", [])) if rows]
    sessions = cached_sessions(max(dates_needed, default=None))
    def session_values(rows, count):
        if not rows or not sessions:
            return []
        end = rows[-1]["date"]
        days = [day for day in sessions if day <= end][-count:]
        values = {r["date"]: number(r.get("value")) for r in rows}
        if len(days) != count or days[-1] != end or any(values.get(day) is None for day in days):
            return []
        return [values[day] for day in days]

    credit = session_values(series["cn_margin_financing_balance"].get("observations", []), 6)
    flows = session_values(etf_rows, 5)
    dr = series["cn_dr007"]
    policy = next((r for r in series["cn_omo_7d"].get("observations", []) if r["date"] == dr.get("observationDate")), {})
    rate, benchmark = number(dr.get("latestValue")), number(policy.get("value"))
    return {
        "asOf": today.isoformat(),
        "comparisons": {
            "marginChange5d": str(credit[-1] - credit[0]) if credit else None,
            "etfFlow5d": str(sum(flows)) if flows else None,
            "rateSpreadBp": str((rate - benchmark) * 100) if rate is not None and benchmark is not None else None,
        },
        "sources": sources,
        "institutions": read_institutions(),
        "handbook": local("public/v1/equity/cn-capital-handbook.json"),
        "macro": series,
        "moneyCreditGap": aligned_difference(series, "cn_m2_yoy", "cn_tsf_stock_yoy", monthly=True),
        "unlockWeeks": unlock_weeks,
        "etf": {**{k: v for k, v in etf.items() if k != "data"}, "rows": etf_rows},
        "broadEtf": {**broad_etf, "status": etf.get("status", "no_data")},
    }


async def run_periodic():
    while True:
        try:
            await collect()
            from app.research_cn_institutions import collect as collect_institutions

            await collect_institutions()
        except Exception:
            logging.getLogger(__name__).exception("Capital dashboard collection failed")
        try:
            from app.research_capital_handbook import refresh

            await refresh()
        except Exception:
            logging.getLogger(__name__).exception("Capital handbook collection failed")
        await asyncio.sleep(300)
