"""Bounded public-source ETF history backfill; GET routes never run this collector."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import ssl
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
import truststore

from app import research_etf_native as native
from app.research_etf_observation import ROOT as OBS_ROOT
from app.research_etf_observation import SYMBOLS, _read
from app import research_etf_tracking as tracking
from app.research_local_data import write_local_json


def parse_nav_script(text: str, code: str) -> dict[str, Decimal]:
    identity = re.search(r'var\s+fS_code\s*=\s*["\x27](\d{6})["\x27]', text)
    match = re.search(r"var\s+Data_netWorthTrend\s*=\s*(\[.*?\]);", text, re.S)
    if not identity or identity[1] != code or not match:
        raise ValueError("fund NAV identity/series missing")
    result = {}
    for row in json.loads(match[1]):
        day = datetime.fromtimestamp(row["x"] / 1000, native.CHINA).date().isoformat()
        value = native.number(row["y"])
        if day in result or value <= 0:
            raise ValueError("invalid/duplicate unit NAV")
        result[day] = value
    return result


def parse_conversion(payload, day, nav, previous_nav):
    rows = (payload.get("Data") or {}).get("LSJZList") or []
    if len(rows) != 1 or rows[0]["FSRQ"] != day:
        raise ValueError("share conversion date mismatch")
    row = rows[0]
    if str(row.get("FHFCBZ")) not in {"105", "106"} or not row.get("FHFCZ"):
        raise ValueError("share conversion is not explicitly published")
    factor = native.number(row["FHFCZ"])
    wording = re.search(r"(?:折算|分拆)([0-9.]+)份", row.get("FHSP", ""))
    if str(row.get("FHFCBZ")) not in {"105", "106"} or factor <= 0 or not wording:
        raise ValueError("share conversion is not explicitly published")
    if native.number(wording[1]) != factor or native.number(row["DWJZ"]) != nav:
        raise ValueError("share conversion NAV/ratio mismatch")
    implied_return = (nav * factor / previous_nav - 1) * 100
    if abs(implied_return - native.number(row["JZZZL"])) > Decimal("0.03"):
        raise ValueError("share conversion fails native return reconciliation")
    return factor


def category_rows(sessions, shares, navs, catalog, conversions=None):
    """Secondary-market creation/redemption; first listing day is excluded."""
    result, coverage = {}, {}
    for previous, day in zip(sessions, sessions[1:], strict=False):
        values, counts = {}, {}
        for category in native.CATEGORIES:
            members = [
                m
                for m in catalog
                if m.get("category") == category
                and native.number(shares[day].get(m["code"], 0)) > 0
                and native.number(shares[previous].get(m["code"], 0)) > 0
            ]
            flows = []
            for meta in members:
                code = meta["code"]
                nav = navs.get(code, {}).get(day)
                prior_nav = navs.get(code, {}).get(previous)
                factor = (conversions or {}).get((code, day))
                if nav is None or (
                    factor is None
                    and (prior_nav and not Decimal("0.6") <= nav / prior_nav <= Decimal("1.6"))
                ):
                    flows.append(None)
                else:
                    flows.append(
                        (
                            native.number(shares[day][code])
                            - native.number(shares[previous][code]) * (factor or 1)
                        )
                        * nav
                        / native.YI
                    )
            values[category] = sum(flows, Decimal(0)) if all(v is not None for v in flows) else None
            counts[category] = {
                "expected": len(members),
                "covered": sum(v is not None for v in flows),
            }
        result[day], coverage[day] = values, counts
    return result, coverage


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--workers", type=int, default=4, choices=range(1, 5))
    args = parser.parse_args()
    start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
    if not timedelta(0) < end - start <= timedelta(days=1140):
        raise ValueError("backfill is limited to the requested three-year window")
    state = native.read("refresh")
    catalog = state["catalog"]
    tracked = [m for m in tracking.read("universe")["data"] if m.get("dashboard_eligible")]
    symbols = sorted(set(SYMBOLS[1:]) | {m["exchange"].lower() + m["code"] for m in tracked})
    run = f"backfill/{start.isoformat()}_{end.isoformat()}/"
    baseline = native.read(run + "baseline")
    if not baseline:
        baseline = {"funds": {s[2:]: min((r["date"] for r in native.read("funds/" + s[2:]).get("rows", [])), default="9999-12-31") for s in symbols}, "broadFirst": min(_read("reference")["data"]["broadData"]["dates"])}
        write_local_json(native.ROOT + run + "baseline.json", baseline)
    catalog_snapshot = native.read(run + "catalog")
    if catalog_snapshot.get("members"):
        catalog = catalog_snapshot["members"]
    else:
        write_local_json(
            native.ROOT + run + "catalog.json",
            {"members": catalog, "retrievedAt": state["retrievedAt"]},
        )
    failures = []

    with httpx.Client(
        timeout=30,
        follow_redirects=True,
        verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT),
        headers={"User-Agent": "Mozilla/5.0"},
    ) as client:

        def request(url, **kwargs):
            for attempt in range(3):
                try:
                    return native.get(client, url, **kwargs)
                except (httpx.HTTPError, ValueError):
                    if attempt == 2:
                        raise
                    time.sleep(attempt + 1)

        # These four unadjusted index histories also cover the retained turnover chart.
        for key in ("hs300", "csi1000", "star50", "chinext"):
            symbol = native.INDEX_SYMBOLS[key]
            checkpoint = run + "index/" + symbol
            doc = native.read(checkpoint)
            if not doc.get("rows"):
                response = request(
                    native.DAILY_MARKET,
                    params={
                        "secid": ("1." if symbol.startswith("sh") else "0.") + symbol[2:],
                        "klt": 101,
                        "fqt": 0,
                        "beg": (start - timedelta(days=14)).strftime("%Y%m%d"),
                        "end": end.strftime("%Y%m%d"),
                        "fields1": "f1,f2,f3,f4,f5,f6",
                        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                    },
                )
                payload = response.json()["data"]
                if payload["code"] != symbol[2:]:
                    raise ValueError("index identity mismatch")
                rows = native.parse_market(
                    [
                        {
                            "day": v[0],
                            "close": v[2],
                            "volume": str(native.number(v[5]) * 100),
                            "amount": v[6],
                        }
                        for v in (line.split(",") for line in payload["klines"])
                    ],
                    (end + timedelta(days=1)).isoformat(),
                )
                doc = {
                    "rows": rows,
                    "sourceUrl": str(response.url),
                    "retrievedAt": datetime.now(UTC).isoformat(),
                    "status": "ready",
                }
                write_local_json(native.ROOT + checkpoint + ".json", doc)
            retained = {r["date"]: r for r in native.read("market/" + symbol).get("rows", [])}
            retained.update({r["date"]: r for r in doc["rows"]})
            write_local_json(
                native.ROOT + "market/" + symbol + ".json",
                {**doc, "rows": [retained[d] for d in sorted(retained)]},
            )
            print(
                "index",
                key,
                len(doc["rows"]),
                doc["rows"][0]["date"],
                doc["rows"][-1]["date"],
                flush=True,
            )

        index = native.read("market/" + native.INDEX_SYMBOLS["hs300"])["rows"]
        sessions = [r["date"] for r in index if start.isoformat() <= r["date"] <= end.isoformat()]
        if len(sessions) < 700 or sessions[-1] != end.isoformat():
            raise ValueError("three-year trading calendar incomplete")
        shares = {}

        def sse(day):
            name = run + "sse/" + day
            doc = native.read(name)
            if doc.get("shares"):
                return day, doc["shares"]
            response = request(
                native.SSE,
                params={
                    "sqlId": "COMMON_SSE_ZQPZ_ETFZL_XXPL_ETFGM_SEARCH_L",
                    "STAT_DATE": day,
                    "isPagination": "true",
                    "pageHelp.pageSize": 10000,
                    "pageHelp.pageNo": 1,
                },
                headers={"Referer": "https://www.sse.com.cn/"},
            )
            payload = response.json()
            rows = native.parse_sse(payload, day)
            if len(rows) != int(payload["pageHelp"]["total"]):
                raise ValueError("SSE history pagination incomplete: " + day)
            write_local_json(
                native.ROOT + name + ".json", {"shares": rows, "sourceUrl": str(response.url)}
            )
            return day, rows

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(sse, day): day for day in sessions}
            for n, future in enumerate(as_completed(futures), 1):
                try:
                    day, values = future.result()
                    shares[day] = values
                except Exception as exc:
                    failures.append(
                        {"source": "sse", "date": futures[future], "error": str(exc)[:180]}
                    )
                if n % 75 == 0:
                    print("SSE", n, "/", len(sessions), "failures", len(failures), flush=True)

        cursor = start
        while cursor <= end:
            stop = min(cursor + timedelta(days=89), end)
            name = run + f"szse/{cursor}_{stop}"
            doc = native.read(name)
            if not doc.get("days"):
                response = request(
                    native.SZSE,
                    params={
                        "SHOWTYPE": "xlsx",
                        "CATALOGID": "scsj_fund_jjgm",
                        "TABKEY": "tab1",
                        "txtStart": cursor.isoformat(),
                        "txtEnd": stop.isoformat(),
                        "jjlb": "ETF",
                    },
                    headers={"Referer": "https://www.szse.cn/market/fund/volume/etf/index.html"},
                )
                doc = {"days": native.parse_szse(response.content), "sourceUrl": str(response.url)}
                write_local_json(native.ROOT + name + ".json", doc)
            for day in sessions:
                if cursor.isoformat() <= day <= stop.isoformat():
                    if day not in doc["days"]:
                        failures.append(
                            {"source": "szse", "date": day, "error": "missing exchange session"}
                        )
                    else:
                        shares.setdefault(day, {}).update(doc["days"][day])
            print("SZSE", cursor, stop, len(doc["days"]), flush=True)
            cursor = stop + timedelta(days=1)
        if failures:
            write_local_json(
                native.ROOT + run + "result.json", {"status": "partial", "failures": failures}
            )
            raise ValueError(f"Exchange inputs incomplete: {len(failures)}; checkpoints retained")

        def nav(meta):
            code = meta["code"]
            name = run + "nav/" + code
            doc = native.read(name)
            if not any(native.number(shares[d].get(code, 0)) > 0 for d in sessions):
                return code, {}
            if not doc.get("values"):
                response = request(f"https://fund.eastmoney.com/pingzhongdata/{code}.js")
                values = parse_nav_script(response.text, code)
                doc = {
                    "values": {
                        d: str(v)
                        for d, v in values.items()
                        if start.isoformat() <= d <= end.isoformat()
                    },
                    "sourceUrl": str(response.url),
                }
                if not doc["values"]:
                    raise ValueError("empty historical unit NAV: " + code)
                write_local_json(native.ROOT + name + ".json", doc)
            return code, {d: native.number(v) for d, v in doc["values"].items()}

        navs = {}
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(nav, m): m["code"] for m in catalog}
            for n, future in enumerate(as_completed(futures), 1):
                try:
                    code, values = future.result()
                    navs[code] = values
                except Exception as exc:
                    failures.append(
                        {"source": "nav", "code": futures[future], "error": str(exc)[:180]}
                    )
                if n % 30 == 0:
                    print("NAV", n, "/", len(catalog), "failures", len(failures), flush=True)

        conversions = {}
        for meta in catalog:
            code = meta["code"]
            values = navs.get(code, {})
            for previous, day in zip(sessions, sessions[1:], strict=False):
                nav_value, prior_nav = values.get(day), values.get(previous)
                if (
                    not nav_value
                    or not prior_nav
                    or Decimal("0.6") <= nav_value / prior_nav <= Decimal("1.6")
                ):
                    continue
                name = run + f"actions/{code}_{day}"
                doc = native.read(name)
                if not doc.get("payload"):
                    response = request(
                        native.NAV,
                        params={
                            "fundCode": code,
                            "pageIndex": 1,
                            "pageSize": 20,
                            "startDate": day,
                            "endDate": day,
                        },
                        headers={"Referer": "https://fundf10.eastmoney.com/"},
                    )
                    doc = {"payload": response.json(), "sourceUrl": str(response.url)}
                    write_local_json(native.ROOT + name + ".json", doc)
                try:
                    verified = native.read(run + f"verified-actions/{code}_{day}")
                    if verified.get("factor") and verified.get("sourceUrl"):
                        factor = native.number(verified["factor"])
                        implied = (nav_value * factor / prior_nav - 1) * 100
                        actual = native.number(doc["payload"]["Data"]["LSJZList"][0]["JZZZL"])
                        if factor <= 0 or abs(implied - actual) > Decimal("0.03"):
                            raise ValueError("published conversion fails NAV reconciliation")
                        conversions[code, day] = factor
                    else:
                        conversions[code, day] = parse_conversion(
                            doc["payload"], day, nav_value, prior_nav
                        )
                except (ValueError, KeyError) as exc:
                    failures.append(
                        {"source": "share_conversion", "code": code, "date": day, "error": str(exc)}
                    )
        print("verified conversions", len(conversions), flush=True)
        rows, coverage = category_rows(sessions, shares, navs, catalog, conversions)
        # Retain the exact constituent inputs used by the fixed-basket ratio;
        # the ordinary producer then merges recent dates into these histories.
        by_code = {m["code"]: m for m in catalog}
        for symbol in symbols:
            code = symbol[2:]
            old = native.read("funds/" + code)
            retained = {r["date"]: r for r in old.get("rows", [])}
            for previous, day in zip(sessions, sessions[1:], strict=False):
                if day in retained and day >= baseline["funds"].get(code, "9999-12-31"):
                    continue
                current = native.number(shares[day].get(code, 0))
                prior = native.number(shares[previous].get(code, 0))
                nav_value = navs.get(code, {}).get(day)
                factor = conversions.get((code, day), Decimal(1))
                if current <= 0 or prior <= 0:
                    cash = Decimal(0)  # no overlapping listed units; initial issuance excluded
                elif nav_value is None:
                    cash = None
                else:
                    prior_nav = navs[code].get(previous)
                    unresolved = (
                        prior_nav
                        and not Decimal("0.6") <= nav_value / prior_nav <= Decimal("1.6")
                        and (code, day) not in conversions
                    )
                    cash = (
                        None if unresolved else (current - prior * factor) * nav_value / native.YI
                    )
                retained[day] = {
                    "date": day,
                    "shares": str(current),
                    "previousShares": str(prior),
                    "unitNav": str(nav_value) if nav_value is not None else None,
                    "shareConversionFactor": str(factor),
                    "flowYi": str(cash) if cash is not None else None,
                    "listed": current > 0,
                }
            write_local_json(
                native.ROOT + "funds/" + code + ".json",
                {
                    **old,
                    "meta": by_code[code],
                    "rows": [retained[d] for d in sorted(retained)],
                    "historyFrom": sessions[1],
                },
            )

        def basket_market(symbol):
            if not any(native.number(shares[d].get(symbol[2:], 0)) > 0 for d in sessions):
                return
            name = run + "market/" + symbol
            doc = native.read(name)
            if not doc.get("rows"):
                response = request(
                    native.DAILY_MARKET,
                    params={
                        "secid": ("1." if symbol.startswith("sh") else "0.") + symbol[2:],
                        "klt": 101,
                        "fqt": 0,
                        "beg": (start - timedelta(days=14)).strftime("%Y%m%d"),
                        "end": end.strftime("%Y%m%d"),
                        "fields1": "f1,f2,f3,f4,f5,f6",
                        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                    },
                )
                payload = response.json()["data"]
                if payload["code"] != symbol[2:]:
                    raise ValueError("basket daily identity mismatch")
                quotes = native.parse_market(
                    [
                        {
                            "day": v[0],
                            "close": v[2],
                            "volume": str(native.number(v[5]) * 100),
                            "amount": v[6],
                        }
                        for v in (line.split(",") for line in payload["klines"])
                    ],
                    (end + timedelta(days=1)).isoformat(),
                )
                doc = {
                    "rows": quotes,
                    "sourceUrl": str(response.url),
                    "retrievedAt": datetime.now(UTC).isoformat(),
                    "status": "ready",
                }
                write_local_json(native.ROOT + name + ".json", doc)
            retained = {r["date"]: r for r in native.read("market/" + symbol).get("rows", [])}
            retained.update({r["date"]: r for r in doc["rows"]})
            write_local_json(
                native.ROOT + "market/" + symbol + ".json",
                {**doc, "rows": [retained[d] for d in sorted(retained)]},
            )

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            list(pool.map(basket_market, symbols))
        print("basket/tracked turnover histories", len(symbols), flush=True)
        reference = _read("reference")
        write_local_json(
            OBS_ROOT + f"history-before-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}.json",
            reference,
        )
        data = reference["data"]
        data["innovationRatio"] = native.build_innovation_ratio(
            {
                s[2:]: {r["date"]: r for r in native.read("funds/" + s[2:]).get("rows", [])}
                for s in SYMBOLS[1:]
            },
            {
                s: {r["date"]: r for r in native.read("market/" + s).get("rows", [])}
                for s in SYMBOLS[1:]
            },
            SYMBOLS,
        )
        broad = data["broadData"]
        old = {
            d: {c: broad["series"][c][i] for c in broad["cats"]}
            for i, d in enumerate(broad["dates"])
        }
        for day, values in rows.items():
            if day < baseline.get("broadFirst", end.isoformat()):
                old[day] = values
        dates = sorted(old)
        categories = list(native.CATEGORIES)
        totals = [
            sum((native.number(old[d][c]) for c in categories), Decimal(0))
            if all(old[d].get(c) is not None for c in categories)
            else None
            for d in dates
        ]
        running, cumulative = Decimal(0), []
        for value in totals:
            running = running + value if running is not None and value is not None else None
            cumulative.append(str(running) if running is not None else None)
        broad.update(
            {
                "dates": dates,
                "cats": categories,
                "series": {
                    c: [str(old[d][c]) if old[d].get(c) is not None else None for d in dates]
                    for c in categories
                },
                "total": [str(v) if v is not None else None for v in totals],
                "totalCum": cumulative,
                "historyCoverage": coverage,
                "shareConversions": [
                    {"code": code, "date": day, "factor": str(factor)}
                    for (code, day), factor in sorted(conversions.items())
                ],
                "historyScope": (
                    f"截至{args.end}的补采历史按{sum(bool(m.get('category')) for m in catalog)}只现有宽基ETF目录回溯；"
                    "仅统计相邻交易日均有交易所份额的上市ETF；"
                    "不计募集和首次上市份额，已退出当前目录基金不在样本内"
                ),
                "historyFundCount": sum(bool(m.get("category")) for m in catalog),
                "historyCatalog": [m for m in catalog if m.get("category")],
                "historyFrom": sessions[1],
                "historyTo": sessions[-1],
            }
        )
        data["indexPrices"] = {
            key: {
                "name": label,
                "symbol": native.INDEX_SYMBOLS[key],
                "sourceUrl": native.read("market/" + native.INDEX_SYMBOLS[key]).get("sourceUrl"),
                "rows": [
                    {"date": r["date"], "close": r["close"]}
                    for r in native.read("market/" + native.INDEX_SYMBOLS[key]).get("rows", [])
                ],
            }
            for key, label in (
                ("hs300", "沪深300"),
                ("csi1000", "中证1000"),
                ("star50", "科创50"),
                ("chinext", "创业板指"),
            )
        }
        missing = sum(v is None for v in totals)
        reference.update(
            {
                "data": data,
                "historicalBackfillAt": datetime.now(UTC).isoformat(),
                "historicalBackfillStatus": "partial" if failures or missing else "ready",
            }
        )
        # Publish all basket-dependent histories together from the same inputs.
        reference["data"] = native.build_reference(data, SYMBOLS)
        reference["nativeFrom"] = reference["data"]["nativeFrom"]
        basket_daily = reference["data"]["dailyData"]
        missing_basket_flow = sum(v is None for v in basket_daily["netflow"])
        missing_basket_turnover = sum(v is None for v in basket_daily["amount"])
        reference["sha256"] = hashlib.sha256(
            json.dumps(reference["data"], sort_keys=True).encode()
        ).hexdigest()
        if missing_basket_flow or missing_basket_turnover:
            reference["historicalBackfillStatus"] = "partial"
        if failures or missing:
            reference["status"] = "partial"
        write_local_json(OBS_ROOT + "reference.json", reference)
        receipt = {
            "status": reference["historicalBackfillStatus"],
            "start": dates[0],
            "end": dates[-1],
            "sessions": len(dates),
            "funds": len(catalog),
            "missingTotalDays": missing,
            "basketCount": len(SYMBOLS) - 1,
            "missingBasketFlowDays": missing_basket_flow,
            "missingBasketTurnoverDays": missing_basket_turnover,
            "failures": failures,
            "sha256": hashlib.sha256(json.dumps(broad, sort_keys=True).encode()).hexdigest(),
        }
        write_local_json(native.ROOT + run + "result.json", receipt)
        print(json.dumps(receipt, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
