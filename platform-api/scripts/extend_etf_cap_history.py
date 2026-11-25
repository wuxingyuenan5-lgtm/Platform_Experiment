"""Extend index candles and cap ratios using dated public inputs, without API spend."""
import json
import ssl
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import httpx
import truststore
from app import research_etf_native as native
from app import research_etf_tracking as tracking
from app.research_local_data import hedge_board_data_root, write_local_json


def main():
    root = hedge_board_data_root()
    run = "backfill/cap-prefix-2020-12-29/"
    with httpx.Client(timeout=30, verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)) as client:
        for key, symbol in native.INDEX_SYMBOLS.items():
            old = tracking.read("index-turnover/" + key)
            prior = old.get("data", {}).get("rows", [])
            name = run + "index/" + key
            doc = native.read(name)
            if "rows" not in doc:
                response = native.get(client, native.DAILY_MARKET, params={
                    "secid": ("1." if symbol.startswith("sh") else "0.") + symbol[2:],
                    "klt": 101, "fqt": 0, "beg": "20201229", "end": "20231229",
                    "fields1": "f1,f2,f3,f4,f5,f6", "fields2": "f51,f52,f53,f54,f55,f56,f57"})
                source = json.loads(response.text, parse_float=str)["data"]
                if source["code"] != symbol[2:]:
                    raise ValueError("index identity mismatch")
                rows = [{"date": v[0], "close": v[2], "turnover_yi": str(native.number(v[6])/native.YI)} for v in (line.split(",") for line in source["klines"])]
                doc = {"rows": rows, "sourceUrl": str(response.url), "retrievedAt": datetime.now(UTC).isoformat()}
                write_local_json(native.ROOT + name + ".json", doc)
            merged = {r["date"]: r for r in doc["rows"]}
            merged.update({r["date"]: r for r in prior})
            tracking.write("index-turnover/" + key, {**old, "data": {**old["data"], "rows": [merged[d] for d in sorted(merged)]}, "historicalSource": doc["sourceUrl"]})

    shares = {}
    for folder in sorted((root / native.ROOT / "backfill").iterdir()):
        for p in (folder / "sse").glob("*.json"):
            shares.setdefault(p.stem, {}).update(json.loads(p.read_text(encoding="utf-8"))["shares"])
        for p in (folder / "szse").glob("*.json"):
            for day, values in json.loads(p.read_text(encoding="utf-8"))["days"].items():
                shares.setdefault(day, {}).update(values)
    cap_path = "public/v1/a-share/etf-market-cap-ratios.json"
    cap = json.loads((root/cap_path).read_text(encoding="utf-8"))
    public = json.loads((root/"research/etf-cap-history/public-hs300.json").read_text(encoding="utf-8"), parse_float=str)
    denominators = {r["tradeDate"]: native.number(r["floatMv"]) for r in public["data"] if r.get("floatMv") is not None}
    history = {r["date"]: r for r in cap["groups"]["hs300"]}
    first = min(history)
    members = history[first]["funds"]
    prices = {m["code"]: {r["date"]: r for r in native.read("market/" + ("sz" if m["code"].startswith("15") else "sh") + m["code"]).get("rows", [])} for m in members}
    gaps, added = [], []
    for day in sorted(r["date"] for r in tracking.read("index-turnover/hs300")["data"]["rows"] if "2020-12-29" <= r["date"] < first):
        value = denominators.get(day)
        funds = []
        for meta in members:
            code = meta["code"]
            close = prices[code].get(day, {}).get("close")
            units = shares.get(day, {}).get(code)
            if close is None or units is None:
                break
            amount = native.number(close)*native.number(units)/native.YI
            funds.append({"code": code, "name": meta["name"], "date": day, "close": close, "shares": units, "marketCapYi": str(amount), "priceSource": "Eastmoney public unadjusted daily close", "sharesSource": "SSE/SZSE dated exchange shares"})
        if value is None or value <= 0 or len(funds) != len(members):
            gaps.append(day);continue
        total = sum((Decimal(f["marketCapYi"]) for f in funds), Decimal(0))
        row = {"date": day, "ratioPct": str(total/value*100), "etfCapYi": str(total), "indexCapYi": str(value), "funds": funds, "denominatorSource": "Legu public floatMv (亿元)", "method": "unadjusted_close_times_native_units_over_index_float_cap"}
        history[day] = row;added.append(day)
    cap["groups"]["hs300"] = [history[d] for d in sorted(history)]
    receipt = {"source": "public exchange shares, unadjusted quotes and Legu floatMv", "hs300Added": len(added), "hs300First": min(history), "gaps": gaps, "choiceUnavailable": "10001029 data limit exceeded; no retry", "blockedGroups": [key for key in cap["groups"] if key != "hs300"], "observedAt": datetime.now(UTC).isoformat()}
    cap["historicalExtension20261105"] = receipt
    write_local_json(cap_path, cap)
    write_local_json(native.ROOT + run + "result.json", receipt)
    print(json.dumps(receipt), flush=True)


if __name__ == "__main__":
    main()
