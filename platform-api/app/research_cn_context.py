"""A-share breadth and macro valuation, from public/local inputs only."""

import asyncio
import hashlib
import json
import logging
import ssl
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import httpx
import truststore
from bs4 import BeautifulSoup

from app.research_cn_monitor import BASE, merge_history, series
from app.research_equity_metrics import number
from app.research_equity_sources import archive, publish_artifact, read_artifact
from app.research_local_data import read_local_json
from app.research_provider_errors import ResearchProviderError

MARKETS = {"all": ("全部A股", "1"), "hs300": ("沪深300", "000300.XSHG"),
           "sz50": ("上证50", "000016.SH"), "zz500": ("中证500", "000905.SH")}
PE_INDICES = {
    "000300": ("hs300", "000300.SH"), "000016": ("sz50", "000016.SH"),
    "000905": ("zz500", "000905.SH"), "000852": ("zz1000", "000852.SH"),
    "000906": ("zz800", "000906.SH"), "000010": ("sz180", "000010.SH"),
    "000009": ("sz380", "000009.SH"), "000903": ("zz100", "000903.SH"),
    "000015": ("sz000015", "000015.SH"), "399324": ("sz399324", "399324.SZ"),
}
PE_FIELDS = ("addLyrPe", "addTtmPe", "lyrPe", "ttmPe", "middleLyrPe", "middleTtmPe")
_LOCK = asyncio.Lock()


def context_series(raw, fields):
    grouped = {}
    for row in raw:
        grouped.setdefault(row["date"], []).append(row)
    normalized, conflicts = [], {}
    for day, records in grouped.items():
        row = {"date": day}
        bad = []
        for target, source in fields.items():
            values = {v for r in records if (v := number(r.get(source))) is not None}
            row[target] = next(iter(values)) if len(values) == 1 else None
            if len(values) > 1:
                bad.append(target)
        if bad:
            conflicts[day] = ",".join(bad)
        normalized.append(row)
    result = series(normalized, {k: k for k in fields})
    for row in result:
        if row["date"] in conflicts:
            row["conflictFields"] = conflicts[row["date"]]
    return result


def counts_valid(rows, fields):
    for row in rows:
        for field in fields:
            value = row[field]
            if value is not None and (value < 0 or value != value.to_integral_value()):
                raise ValueError("count_invalid")


def parse_context(key, raw):
    if key.startswith("pe_"):
        rows = context_series(raw["data"], {k: k for k in (*PE_FIELDS, "close")})
        if not any(any(row[k] is not None for k in PE_FIELDS) for row in rows):
            raise ValueError("public_pe_empty")
        for row in rows:
            # A nonpositive PE is not a usable valuation, never convert it to zero.
            for field in PE_FIELDS:
                if row[field] is not None and row[field] <= 0:
                    row[field] = None
            if row["close"] is not None and row["close"] <= 0:
                row["close"] = None
                row["invalidFields"] = "close"
        return rows
    if key.startswith("below_"):
        rows = context_series(raw, {"count": "belowNetAsset", "total": "totalCompany", "close": "close"})
        counts_valid(rows, ["count", "total"])
        for row in rows:
            count, total = row["count"], row["total"]
            if count is not None and total is not None and count > total:
                raise ValueError("below_total_mismatch")
            row["value"] = count / total * 100 if count is not None and total else None
        return rows
    if key == "ma":
        rows = context_series(raw["data"], {"ma5": "value5", "ma20": "value20", "ma60": "value60", "close": "close"})
        if any(row[k] is not None and not 0 <= row[k] <= 100 for row in rows for k in ["ma5", "ma20", "ma60"]):
            raise ValueError("ma_percent_invalid")
        return rows
    if key == "highlow":
        fields = {f"{side}{days}": f"{side}{days}" for side in ["high", "low"] for days in [20, 60, 120]}
        rows = context_series(raw["data"], {**fields, "close": "close"})
        counts_valid(rows, fields)
        for row in rows:
            for days in [20, 60, 120]:
                high, low = row[f"high{days}"], row[f"low{days}"]
                row[f"net{days}"] = high - low if high is not None and low is not None else None
        return rows
    if key == "buffett":
        rows = context_series(raw["data"], {"marketCap": "marketCap", "gdp": "gdp", "close": "close"})
        for row in rows:
            cap, gdp = row["marketCap"], row["gdp"]
            if cap is not None and cap < 0 or gdp is not None and gdp <= 0:
                raise ValueError("buffett_denominator_invalid")
            row["value"] = cap / gdp * 100 if cap is not None and gdp else None
        return rows
    raise ValueError("context_source_unknown")


def risk_history(valuations, bonds):
    bond_lookup = {r["date"]: number(r.get("value")) for r in bonds}
    result = []
    for row in valuations:
        day = row["date"]
        rate = bond_lookup.get(day)
        point = {"date": day, "bond": rate, "close": number(row.get("close"))}
        for field, suffix in [("peLyr", "Lyr"), ("pe", "Ttm")]:
            pe = number(row.get(field))
            earnings = Decimal(100) / pe if pe is not None and pe > 0 else None
            point["earnings" + suffix] = earnings
            point["erp" + suffix] = earnings - rate if earnings is not None and rate is not None else None
        result.append(point)
    return result


def read_risk():
    try:
        bond = read_local_json("public/v1/macro/series/cn_treasury_10y.json")
        if bond.get("unit") != "percent" or bond.get("seriesId") != "cn_treasury_10y":
            raise ValueError("risk_bond_unit_invalid")
    except (ResearchProviderError, ValueError):
        bond = {}
    sources = {}
    for code, name in [("000300", "沪深300"), ("000016", "上证50"), ("000905", "中证500")]:
        try:
            doc = read_artifact("sources/choice_index_" + code)
        except ResearchProviderError:
            doc = {"status": "error"}
        status = "error" if doc.get("status") == "error" or bond.get("status") == "error" else "ready" if doc.get("rows") and bond.get("observations") else "no_data"
        sources[code] = {"name": name, "status": status,
                         "sourceUrl": doc.get("url", ""),
                         "valuationSource": doc.get("name"), "valuationFetchedAt": doc.get("fetchedAt"),
                         "bondSourceUrl": bond.get("sourceUrl"), "bondFetchedAt": bond.get("retrievedAt"),
                         "data": risk_history(doc.get("rows", []), bond.get("observations", []))}
    return {"sources": sources, "generatedAt": None}


def read_context(section):
    if section == "risk":
        return read_risk()
    return read_artifact("cn-monitor-" + section) or {"sources": {}, "generatedAt": None}


async def collect_context(force=False, keys=None):
    async with _LOCK:
        now = datetime.now(UTC)
        stamp = now.isoformat()
        documents = {k: read_context(k) for k in ["breadth", "macroValue", "valuation"]}
        specs = [
            *[("valuation", "pe_" + code, page + "-ttm-lyr", "/api/stockdata/index-basic-pe", {"indexCode": symbol})
              for code, (page, symbol) in PE_INDICES.items()],
            ("breadth", "ma", "ma-statistics", "/api/stockdata/member-ship/get-ma-statistics", {"indexCode": "all"}),
            ("breadth", "highlow", "high-low-statistics", "/api/stockdata/member-ship/get-high-low-statistics/all", {}),
            ("macroValue", "buffett", "marketcap-gdp", "/api/stockdata/marketcap-gdp/get-marketcap-gdp", {}),
            *[("breadth", "below_" + key, "below-net-asset-statistics?marketId=" + market_id,
               "/stockdata/below-net-asset-statistics-data", {"marketId": market_id}) for key, (_, market_id) in MARKETS.items()],
        ]
        context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        async with httpx.AsyncClient(verify=context, timeout=httpx.Timeout(25, connect=10), follow_redirects=True,
                                    headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json,text/html"}) as client:
            for section, key, page, api, params in specs:
                if keys is not None and key not in keys:
                    continue
                document = documents[section]
                old = document["sources"].get(key, {})
                if not force and old.get("attemptedAt"):
                    interval = 1 if old.get("status") == "error" else 20
                    if now - datetime.fromisoformat(old["attemptedAt"]) < timedelta(hours=interval):
                        continue
                try:
                    response = await client.get(BASE + "/stockdata/" + page)
                    response.raise_for_status()
                    csrf = BeautifulSoup(response.content, "html.parser").select_one('meta[name="_csrf"]')["content"]
                    token = hashlib.md5(now.astimezone(ZoneInfo("Asia/Shanghai")).date().isoformat().encode()).hexdigest()
                    if key.startswith("pe_"):
                        await asyncio.sleep(1)  # Space public history reads; never retry a rejected source in a tight loop.
                    response = await client.get(BASE + api, params={"token": token, **params}, headers={"X-CSRF-Token": csrf})
                    response.raise_for_status()
                    data = parse_context(key, json.loads(response.content, parse_float=Decimal))
                    digest = await asyncio.to_thread(archive, "legu_context_" + key, response.content, stamp)
                    document["sources"][key] = {"status": "ready", "data": merge_history(old.get("data", []), data),
                                                "fetchedAt": stamp, "attemptedAt": stamp, "rawSha256": digest,
                                                "sourceUrl": BASE + "/stockdata/" + page}
                except Exception as exc:
                    document["sources"][key] = {**old, "status": "error", "attemptedAt": stamp,
                                                "sourceUrl": BASE + "/stockdata/" + page, "error": type(exc).__name__}
                    logging.getLogger(__name__).warning("CN context %s: %s", key, type(exc).__name__)
                document["generatedAt"] = stamp
                await asyncio.to_thread(publish_artifact, "cn-monitor-" + section, document)
        return documents


async def run_periodic():
    while True:
        try:
            await collect_context()
        except Exception:
            logging.getLogger(__name__).exception("CN market context refresh failed")
        await asyncio.sleep(300)
