"""Public A-share monitors. GET reads local data; background collection is isolated.

No Choice calls, authenticated/premium endpoints, synthetic observations or zero fill.
"""

import asyncio
import hashlib
import json
import logging
import re
import ssl
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import httpx
import truststore
from bs4 import BeautifulSoup

from app.research_equity_metrics import number
from app.research_equity_sources import archive, publish_artifact, read_artifact

BASE = "https://legulegu.com"
METRICS = {
    "netProfitYoy": "净利润同比", "orYoy": "营业收入同比", "opYoy": "营业利润同比",
    "trYoy": "营业总收入同比", "ebtYoy": "利润总额同比", "roeYoy": "ROE同比增长率",
}
_LOCK = asyncio.Lock()


def series(rows, fields):
    result = []
    for row in rows:
        day = str(row.get("date", row.get("quarter", "")))
        datetime.strptime(day, "%Y-%m-%d")
        result.append({"date": day, **{target: number(row.get(source)) for target, source in fields.items()}})
    if len({r["date"] for r in result}) != len(result):
        raise ValueError("duplicate_dates")
    if not result or not any(any(r[k] is not None for k in fields) for r in result):
        raise ValueError("empty_series")
    return sorted(result, key=lambda r: r["date"])


def industry_growth(content):
    soup = BeautifulSoup(content, "html.parser")
    table = soup.select_one("table.middle-avg-indicator-table")
    if table is None:
        raise ValueError("industry_growth_table_missing")
    dates = re.findall(r"\d{4}-\d{2}-\d{2}", table.select_one("thead").get_text())[:2]
    if len(dates) != 2 or dates[0] <= dates[1]:
        raise ValueError("industry_growth_dates_invalid")
    rows = []
    for tr in table.select("tr.sw-industry-item"):
        link = tr.select_one('a[href*="sw-industry-2021?"]')
        toggle = tr.select_one(".sw-sub-toggle")
        if toggle is None:  # The final row is the all-A aggregate, not a 32nd industry.
            continue
        code = toggle["data-code"]
        values = [number(tr.select_one("." + key).get_text(strip=True).removesuffix("%"))
                  for key in ["current-value", "before-value", "dif-value"]]
        current, previous, reported_change = values
        change = current - previous if current is not None and previous is not None else None
        if change is not None and reported_change is not None and abs(change - reported_change) > Decimal("0.011"):
            raise ValueError("industry_growth_change_mismatch")
        rows.append({"code": code, "name": link.get_text(strip=True), "date": dates[0],
                     "previousDate": dates[1], "value": current, "previous": previous, "change": change})
    if len(rows) != 31 or len({r["code"] for r in rows}) != 31:
        raise ValueError("industry_growth_coverage_invalid")
    return rows


def parse(key, raw):
    if key == "dividend":
        return [{"code": code, "name": name, "history": series(raw[code], {"value": "addDvTtm", "close": "close"})}
                for code, name in [("shangzheng", "上证A股"), ("shenzheng", "深证A股"),
                                   ("chuangyeban", "创业板"), ("kechuangban", "科创板")]]
    if key.startswith("fund_"):
        result = series(raw, {"value": "position", "close": "close"})
        if any(r["value"] is not None and not 0 <= r["value"] <= 100 for r in result):
            raise ValueError("fund_position_invalid")
        return result
    if key == "growth":
        return series(raw["middleIndicatorItemMap"]["all"]["middleIndicators"], {k: k for k in METRICS})
    if key.startswith("growth_"):
        return industry_growth(raw)
    if key == "industry":
        dates = raw["dates"]
        result = []
        for item in raw["swCodeNames"]:
            values = raw["congestions"][item["indexCode"]]
            if len(dates) != len(values):
                raise ValueError("industry_dates_mismatch")
            history = series([{"date": d, **v} for d, v in zip(dates, values, strict=True)],
                             {"turnover": "turnoverRateFQuantile", "amount": "amountCongestionQuantile"})
            if any(v is not None and not 0 <= v <= 100 for r in history for k, v in r.items() if k != "date"):
                raise ValueError("industry_percentile_invalid")
            result.append({"code": item["indexCode"], "name": item["indexName"], "history": history})
        if len(result) != 31:
            raise ValueError("industry_coverage_invalid")
        return result
    if key == "congestion":
        for r in raw["items"]:
            value, top, total = (number(r.get(k)) for k in ["congestion", "top5Amount", "totalAmount"])
            if value is not None and top is not None and total is not None:
                if total <= 0 or abs(top / total - value) > Decimal("0.000051"):
                    raise ValueError("congestion_ratio_mismatch")
        rows = series(raw["items"], {"value": "congestion", "close": "close"})
        for r in rows:
            if r["value"] is not None:
                if not 0 <= r["value"] <= 1:
                    raise ValueError("congestion_ratio_invalid")
                r["value"] *= 100
        return rows
    raise ValueError("unknown_source")


def merge_history(old, new):
    # Preserve history outside the public rolling window and actual same-day revisions.
    return sorted({r["date"]: r for r in [*old, *new]}.values(), key=lambda r: r["date"])


def read_monitor():
    return read_artifact("cn-monitor") or {"sources": {}, "generatedAt": None}


async def collect(force=False):
    async with _LOCK:
        now = datetime.now(UTC)
        stamp = now.isoformat()
        document = read_monitor()
        sources = document.setdefault("sources", {})
        definitions = {
            "dividend": ("guxilv", "guxilv", {}),
            "congestion": ("ashares-congestion", "ashares-congestion", {}),
            "industry": ("sw-congestion", "sw-congestion", {"level": 1, "severalTradeDays": 30}),
            "growth": ("middle-avg-indicator?indicatorCode=roeYoy", "middle-indicators-all", {}),
            **{f"fund_{k}": (f"fund-position/pos-{k}", "fund-position", {"type": f"pos_{k}", "category": "总仓位", "marketId": 5})
               for k in ["stock", "pingheng", "linghuo"]},
            **{f"growth_{k}": (f"middle-avg-indicator?indicatorCode={k}", None, {}) for k in METRICS},
        }
        context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        async with httpx.AsyncClient(verify=context, timeout=httpx.Timeout(25, connect=10), follow_redirects=True,
                                    headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json,text/html"}) as client:
            for key, (page, api, params) in definitions.items():
                old = sources.get(key, {})
                last = old.get("attemptedAt")
                if not force and last:
                    hours = 1 if old.get("status") == "error" else 20
                    if now - datetime.fromisoformat(last) < timedelta(hours=hours):
                        continue
                try:
                    response = await client.get(f"{BASE}/stockdata/{page}")
                    response.raise_for_status()
                    page_content = response.content
                    if api:
                        csrf = BeautifulSoup(page_content, "html.parser").select_one('meta[name="_csrf"]')["content"]
                        token = hashlib.md5(now.astimezone(ZoneInfo("Asia/Shanghai")).date().isoformat().encode()).hexdigest()
                        response = await client.get(f"{BASE}/api/stockdata/{api}", params={"token": token, **params},
                                                    headers={"X-CSRF-Token": csrf})
                        response.raise_for_status()
                        raw = json.loads(response.content, parse_float=Decimal)
                    else:
                        raw = page_content
                    data = parse(key, raw)
                    previous = old.get("data", [])
                    if key == "industry" or key == "dividend":
                        lookup = {r["code"]: r for r in previous}
                        for r in data:
                            r["history"] = merge_history(lookup.get(r["code"], {}).get("history", []), r["history"])
                    elif not key.startswith("growth_"):
                        data = merge_history(previous, data)
                    digest = await asyncio.to_thread(archive, f"legu_{key}", response.content, stamp)
                    sources[key] = {"status": "ready", "fetchedAt": stamp, "attemptedAt": stamp,
                                    "sourceUrl": f"{BASE}/stockdata/{page}", "rawSha256": digest, "data": data}
                except Exception as exc:
                    logging.getLogger(__name__).warning("CN monitor %s: %s", key, type(exc).__name__)
                    sources[key] = {**old, "status": "error", "attemptedAt": stamp, "error": type(exc).__name__,
                                    "sourceUrl": f"{BASE}/stockdata/{page}"}
                document["generatedAt"] = stamp
                await asyncio.to_thread(publish_artifact, "cn-monitor", document)
        return document


async def run_periodic():
    while True:
        try:
            await collect()
        except Exception:
            logging.getLogger(__name__).exception("CN monitor refresh failed")
        await asyncio.sleep(300)
