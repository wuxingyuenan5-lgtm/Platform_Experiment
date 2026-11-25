"""Extend existing ETF daily views from archived exchange inputs and public quotes."""
from __future__ import annotations

import argparse
import json
import ssl
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
import truststore
from app import research_etf_native as native
from app import research_etf_tracking as tracking
from app.research_local_data import hedge_board_data_root, write_local_json

YI = Decimal(100000000)
MARGIN = "https://datacenter-web.eastmoney.com/api/data/v1/get"


def margin_rows(payload, code):
    if payload.get("success") is not True:
        raise ValueError("margin source rejected query")
    rows = []
    for item in payload["result"]["data"]:
        if item["SCODE"] != code:
            raise ValueError("margin identity mismatch")
        day = item["DATE"][:10]
        date.fromisoformat(day)
        row = {"date": day}
        for field, source in {
            "financing_balance_yi": "RZYE", "financing_buy_yi": "RZMRE",
            "financing_repayment_yi": "RZCHE", "financing_net_buy_yi": "RZJME",
            "securities_lending_balance_yi": "RQYE", "margin_balance_yi": "RZRQYE",
        }.items():
            row[field] = str(native.number(item[source]) / YI) if item.get(source) is not None else None
        if item.get("SPJ") is not None:
            row["close"] = str(native.number(item["SPJ"]))
        if all(row[k] is not None for k in ("financing_buy_yi", "financing_repayment_yi", "financing_net_buy_yi")):
            if abs(Decimal(row["financing_buy_yi"]) - Decimal(row["financing_repayment_yi"]) - Decimal(row["financing_net_buy_yi"])) > Decimal("0.000001"):
                raise ValueError("margin net-buy reconciliation failed")
        rows.append(row)
    return rows


def check_overlap(old, incoming, field):
    existing = {r["date"]: r.get(field) for r in old}
    checks = 0
    for row in incoming:
        left, right = existing.get(row["date"]), row.get(field)
        if left is None or right is None:
            continue
        a, b = Decimal(str(left)), Decimal(str(right))
        if abs(a-b) > max(abs(a) * Decimal("0.001"), Decimal("0.000001")):
            raise ValueError("overlap mismatch:" + row["date"] + ":" + field)
        checks += 1
    return checks


def extend_group_margin(universe, start):
    results = {}
    for key in sorted({tracking.index_key(m) for m in universe if tracking.index_key(m)}):
        old = tracking.read("margin/" + key)
        rows = old.get("data", {}).get("rows", [])
        if not rows:
            continue
        first = rows[0]["date"]
        members = [m for m in universe if tracking.index_key(m) == key]
        histories = [{r["date"]: r for r in tracking.read("margin/etfs/" + m["code"]).get("data", {}).get("rows", [])} for m in members]
        calendar = tracking.read("index-turnover/" + key).get("data", {}).get("rows", [])
        prefix = []
        for day in sorted({r["date"] for r in calendar if start <= r["date"] < first}):
            row = {"date": day, "etf_group_coverage": f"{sum(day in h for h in histories)}/{len(members)}", "index_financing_balance_yi": None, "index_financing_net_buy_yi": None, "index_coverage_pct": None}
            for field in ("financing_balance_yi", "financing_buy_yi", "financing_repayment_yi", "financing_net_buy_yi"):
                values = [h.get(day, {}).get(field) for h in histories]
                row["etf_group_"+field] = str(sum((Decimal(v) for v in values), Decimal(0))) if values and all(v is not None for v in values) else None
            prefix.append(row)
        if prefix:
            data = {**old["data"], "rows": prefix + rows}
            data["meta"] = {**data.get("meta", {}), "date_start": prefix[0]["date"], "row_count": len(data["rows"])}
            tracking.write("margin/" + key, {**old, "data": data, "historicalETFSource": MARGIN, "historicalIndexMargin": "No point-in-time constituent financing archive; NULL retained"})
        results[key] = len(prefix)
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="2020-12-29")
    p.add_argument("--workers", type=int, default=3, choices=range(1, 5))
    args = p.parse_args()
    start = date.fromisoformat(args.start)
    root = hedge_board_data_root()
    run = "backfill/tracking-prefix-" + args.start + "/"
    universe = [m for m in tracking.read("universe")["data"] if m.get("dashboard_eligible")]
    baseline = native.read(run + "baseline")
    if not baseline:
        baseline = {"first": {m["code"]: tracking.read("etfs/"+m["code"])["data"]["series"][0]["date"] for m in universe}, "marginFirst": {}}
        write_local_json(native.ROOT + run + "baseline.json", baseline)
    shares = {}
    # Every file is an already validated complete exchange-date snapshot.
    for folder in sorted((root / native.ROOT / "backfill").iterdir()):
        for path in (folder / "sse").glob("*.json"):
            doc = json.loads(path.read_text(encoding="utf-8"))
            shares.setdefault(path.stem, {}).update(doc["shares"])
        for path in (folder / "szse").glob("*.json"):
            doc = json.loads(path.read_text(encoding="utf-8"))
            for day, values in doc["days"].items():
                shares.setdefault(day, {}).update(values)
    days = sorted(shares)
    conversions = {}
    for folder in (root / native.ROOT / "backfill").iterdir():
        for path in (folder / "verified-actions").glob("*.json"):
            doc = json.loads(path.read_text(encoding="utf-8"))
            conversions[doc["code"], doc["date"]] = native.number(doc["factor"])
        result = folder / "result.json"
        # Ordinary action records were validated by the NAV backfill first.
        if result.exists():
            broad = json.loads((root / "public/v1/etf-observation/reference.json").read_text(encoding="utf-8"))["data"]["broadData"]
            for action in broad.get("shareConversions", []):
                conversions[action["code"], action["date"]] = native.number(action["factor"])

    def collect(meta):
        code, symbol = meta["code"], meta["exchange"].lower() + meta["code"]
        old = tracking.read("etfs/" + code)
        old_rows = old["data"]["series"]
        first = baseline["first"][code]
        first_day = date.fromisoformat(first)
        fund_start = max(start, first_day.replace(year=first_day.year-3))
        end = first_day + timedelta(days=4)
        begin = fund_start - timedelta(days=14)
        with httpx.Client(timeout=30, verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)) as client:
            prices = {}
            for adjustment in (0, 1):
                name = run + f"quotes/{code}-{adjustment}"
                doc = native.read(name)
                if "rows" not in doc:
                    response = native.get(client, native.DAILY_MARKET, params={
                        "secid": ("1." if meta["exchange"] == "SH" else "0.") + code,
                        "klt": 101, "fqt": adjustment, "beg": begin.strftime("%Y%m%d"),
                        "end": end.strftime("%Y%m%d"), "fields1": "f1,f2,f3,f4,f5,f6",
                        "fields2": "f51,f52,f53,f54,f55,f56,f57",
                    })
                    data = json.loads(response.text, parse_float=str)["data"]
                    if data["code"] != code:
                        raise ValueError("ETF price identity mismatch")
                    rows = []
                    for line in data.get("klines") or []:
                        v = line.split(",")
                        rows.append({"date": v[0], "close": v[2], "amount": v[6], "volume": str(native.number(v[5])*100), "average": str(sum(map(native.number, v[1:5]))/4)})
                    doc = {"rows": rows, "sourceUrl": str(response.url), "retrievedAt": datetime.now(UTC).isoformat()}
                    write_local_json(native.ROOT + name + ".json", doc)
                prices[adjustment] = {r["date"]: r for r in doc["rows"]}
            rebuilt = 0
            try:
                overlap = check_overlap(
                    [{"date": r["date"], "close": r.get("etf_qfq_close")} for r in old_rows], list(prices[1].values()), "close")
            except ValueError:
                # A dividend can change the provider's entire forward-adjusted
                # price basis. Re-fetch the complete retained range on one basis;
                # never splice an inferred offset into native observations.
                complete = {}
                for adjustment in (0, 1):
                    name = run + f"basis/{code}-{adjustment}"
                    doc = native.read(name)
                    if "rows" not in doc:
                        response = native.get(client, native.DAILY_MARKET, params={
                            "secid": ("1." if meta["exchange"] == "SH" else "0.") + code,
                            "klt": 101, "fqt": adjustment, "beg": begin.strftime("%Y%m%d"),
                            "end": old_rows[-1]["date"].replace("-", ""), "lmt": 2000,
                            "fields1": "f1,f2,f3,f4,f5,f6", "fields2": "f51,f52,f53,f54,f55,f56,f57"})
                        source = json.loads(response.text, parse_float=str)["data"]
                        if source["code"] != code:
                            raise ValueError("rebased price identity mismatch")
                        rows = []
                        for line in source["klines"]:
                            v = line.split(",")
                            rows.append({"date": v[0], "close": v[2], "amount": v[6], "volume": str(native.number(v[5])*100), "average": str(sum(map(native.number,v[1:5]))/4)})
                        doc = {"rows": rows, "sourceUrl": str(response.url), "retrievedAt": datetime.now(UTC).isoformat()}
                        write_local_json(native.ROOT + name + ".json", doc)
                    complete[adjustment] = {r["date"]: r for r in doc["rows"]}
                normalized = []
                for row in old_rows:
                    d = row["date"]
                    if row.get("etf_qfq_close") is not None and (d not in complete[1] or d not in complete[0]):
                        raise ValueError("complete price-basis history missing:" + d)
                    if d in complete[1] and d in complete[0]:
                        quote, raw = complete[1][d], complete[0][d]
                        row = {**row, "etf_qfq_close": quote["close"], "etf_qfq_avg_price_est": quote["average"], "etf_qfq_turnover_est_yi": str(native.number(quote["average"])*native.number(raw["volume"])/YI)}
                        rebuilt += 1
                    normalized.append(row)
                old_rows, prices, overlap = normalized, complete, 0
            new = []
            for previous, day in zip(days, days[1:]):
                if not fund_start.isoformat() <= day < first or day not in prices[0] or day not in prices[1]:
                    continue
                units, prior = shares[day].get(code), shares[previous].get(code)
                if units is None or prior is None:
                    continue
                quote, raw = prices[1][day], prices[0][day]
                factor = conversions.get((code, day), Decimal(1))
                new.append({"date": day, "etf_qfq_close": quote["close"], "etf_qfq_avg_price_est": quote["average"],
                    "etf_qfq_turnover_est_yi": str(native.number(quote["average"])*native.number(raw["volume"])/YI),
                    "qfq_total_units_yi": str(native.number(units)/YI),
                    "qfq_delta_units_yi": str((native.number(units)-native.number(prior)*factor)/YI),
                    "shareConversionFactor": str(factor), "share_basis": "exchange_native_units", "source": "native_history"})
            if new:
                merged = {r["date"]: r for r in new}
                merged.update({r["date"]: r for r in old_rows})
                data = {**old["data"], "series": [merged[d] for d in sorted(merged)]}
                data["meta"] = {**data["meta"], "date_start": new[0]["date"], "row_count": len(data["series"])}
                tracking.write("etfs/" + code, {**old, "data": data, "historicalBackfillAt": datetime.now(UTC).isoformat(), "historicalSource": [native.SSE, native.SZSE, native.DAILY_MARKET]})
            # Financed ETF observations are independent of price/units coverage.
            margin = tracking.read("margin/etfs/" + code)
            retained = margin.get("data", {}).get("rows", [])
            margin_first = baseline.get("marginFirst", {}).get(code, first)
            all_rows = []
            page, count, pages = 1, None, 1
            while page <= pages:
                name = run + f"margin/{code}-{page}"
                doc = native.read(name)
                if not doc:
                    response = native.get(client, MARGIN, params={"reportName": "RPTA_WEB_RZRQ_GGMX", "columns": "ALL", "filter": f'(SCODE="{code}")(DATE>=\'{args.start}\')(DATE<=\'{margin_first}\')', "pageNumber": page, "pageSize": 500, "sortColumns": "DATE", "sortTypes": "1", "source": "WEB", "client": "WEB"})
                    doc = {"payload": json.loads(response.text, parse_float=str), "sourceUrl": str(response.url)}
                    write_local_json(native.ROOT + name + ".json", doc)
                result = doc["payload"].get("result")
                if result is None and doc["payload"].get("success") is False and doc["payload"].get("code") == 9201:
                    break
                if not result:
                    raise ValueError("margin response unavailable:" + code)
                count, pages = result["count"], result["pages"]
                all_rows.extend(margin_rows(doc["payload"], code)); page += 1
            if count is not None and len(all_rows) != count:
                raise ValueError("margin pagination incomplete:" + code)
            margin_checks = check_overlap(retained, all_rows, "financing_balance_yi")
            added = [r for r in all_rows if r["date"] < margin_first]
            if added:
                merged = {r["date"]: r for r in added}
                merged.update({r["date"]: r for r in retained})
                data = {**margin.get("data", {}), "rows": [merged[d] for d in sorted(merged)]}
                data["meta"] = {**data.get("meta", {}), "date_start": added[0]["date"], "row_count": len(data["rows"])}
                tracking.write("margin/etfs/" + code, {**margin, "data": data, "historicalSource": MARGIN, "historicalBackfillAt": datetime.now(UTC).isoformat()})
            return {"code": code, "priceRowsAdded": len(new), "first": new[0]["date"] if new else first, "priceBasisRowsRebuilt": rebuilt, "marginRowsAdded": len(added), "priceOverlapChecks": overlap, "marginOverlapChecks": margin_checks}

    results, failures = [], []
    def safe(meta):
        try:
            result = collect(meta); results.append(result); print(json.dumps(result), flush=True)
        except Exception as exc:
            failure = {"code": meta["code"], "error": str(exc)};failures.append(failure);print(json.dumps(failure), flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(safe, universe))
    groups = extend_group_margin(universe, args.start)
    write_local_json(native.ROOT + run + "result.json", {"results": results, "failures": failures, "groupMarginPrefixRows": groups})
    print(json.dumps({"completed": len(results), "failures": failures}), flush=True)


if __name__ == "__main__":
    main()
