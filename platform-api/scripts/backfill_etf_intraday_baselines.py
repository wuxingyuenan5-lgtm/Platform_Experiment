"""Backfill the current ETF basket's 20-day original five-minute turnover."""

import argparse
import hashlib
import json
import ssl
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
import truststore

from app import research_etf_native as native
from app import research_etf_observation as observation
from app.research_etf_cumulative import SLOTS, day_curve
from app.research_local_data import hedge_board_data_root, write_local_json

EASTMONEY = "https://push2his.eastmoney.com/api/qt/stock/kline/get"


def parse_five(payload, symbol, dates):
    data = payload.get("data") or {}
    if data.get("code") != symbol[2:] or data.get("market") != (1 if symbol[:2] == "sh" else 0):
        raise ValueError("five-minute instrument identity mismatch")
    days = {}
    for line in data.get("klines", []):
        fields = line.split(",")
        if len(fields) < 7 or fields[0][:10] not in dates:
            continue
        stamp = fields[0] + ":00"
        datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S")
        days.setdefault(stamp[:10], []).append({
            "day": stamp, "open": fields[1], "close": fields[2],
            "high": fields[3], "low": fields[4], "volume": fields[5], "amount": fields[6],
        })
    for day in dates:
        if day_curve(days.get(day, []), day, 5) is None:
            raise ValueError(f"incomplete original five-minute session: {symbol} {day}")
    return days


def archive(response, symbol, source, acquired):
    digest = hashlib.sha256(response.content).hexdigest()
    write_local_json(f"raw/research/etf-native/minutes-5m/{symbol}/{digest}.json", {
        "body": response.content.decode("utf-8"), "sourceUrl": str(response.url),
        "sha256": digest, "observedAt": acquired, "source": source,
    })
    return digest


def archived_response(symbol, source):
    folder = hedge_board_data_root() / "raw/research/etf-native/minutes-5m" / symbol
    records = [json.loads(path.read_text(encoding="utf-8")) for path in folder.glob("*.json")]
    doc = max((row for row in records if row.get("source") == source), key=lambda row: row["observedAt"])
    body = doc["body"].encode("utf-8")
    if hashlib.sha256(body).hexdigest() != doc["sha256"]:
        raise ValueError("archived response checksum mismatch")
    return httpx.Response(200, content=body, request=httpx.Request("GET", doc["sourceUrl"])), doc


def collect(symbol, dates, replay=False):
    acquired = datetime.now(UTC).isoformat()
    with httpx.Client(timeout=25, follow_redirects=True,
                      verify=truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)) as client:
        params = {
            "secid": ("1." if symbol.startswith("sh") else "0.") + symbol[2:],
            "klt": 5, "fqt": 0, "beg": dates[0].replace("-", ""),
            "end": dates[-1].replace("-", ""), "lmt": 1970,
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        }
        if replay:
            response, stored = archived_response(symbol, "eastmoney_original_5min")
            acquired = stored["observedAt"]
        else:
            response = client.get(EASTMONEY, params=params)
        response.raise_for_status()
        digest = archive(response, symbol, "eastmoney_original_5min", acquired)
        days = parse_five(response.json(), symbol, dates)
        secondary = (archived_response(symbol, "sina_original_5min")[0] if replay else
                     client.get(observation.MINUTE_SOURCE, params={
                         "symbol": symbol, "scale": 5, "ma": "no", "datalen": 1970,
                     }))
        secondary.raise_for_status()
        secondary_digest = archive(secondary, symbol, "sina_original_5min", acquired)
        source_rows = secondary.json()
        if not isinstance(source_rows, list):
            raise ValueError("Sina five-minute comparison unavailable")
        secondary_totals = {}
        for row in source_rows:
            if row["day"][:10] in dates:
                secondary_totals.setdefault(row["day"][:10], Decimal(0))
                secondary_totals[row["day"][:10]] += native.number(row["amount"])
        daily = {row["date"]: row for row in native.read("market/" + symbol).get("rows", [])}
        checks = {}
        for day in dates:
            total = sum((native.number(row["amount"]) for row in days[day]), Decimal(0))
            official = native.number(daily[day]["amount"])
            alternate = secondary_totals.get(day)
            # Independent feeds differ in intraday turnover; keep raw values and
            # enforce the financial-data 1% check against the canonical daily total.
            tolerance = max(Decimal(1), abs(official) * Decimal("0.01"))
            if abs(total - official) > tolerance:
                raise ValueError(f"five-minute turnover does not reconcile: {symbol} {day}: {total}/{official}/{alternate}")
            checks[day] = {
                "fiveMinute": str(total), "daily": str(official), "sina": str(alternate),
                "dailyRelativeError": str(abs(total - official) / max(abs(official), Decimal(1))),
                "secondaryRelativeError": str(abs(total - alternate) / max(abs(total), Decimal(1))) if alternate is not None else None,
                "secondaryStatus": "consistent" if alternate is not None and abs(total - alternate) <= tolerance else "difference",
            }
        old = native.read("minutes-5m/" + symbol)
        write_local_json(native.ROOT + "minutes-5m/" + symbol + ".json", {
            "symbol": symbol, "intervalMinutes": 5, "amountUnit": "CNY", "volumeUnit": "lot",
            "days": {**old.get("days", {}), **days},
            "sourceUrl": str(response.url), "sha256": digest,
            "secondarySourceUrl": str(secondary.url), "secondarySha256": secondary_digest,
            "retrievedAt": acquired, "status": "ready", "dailyChecks": {**old.get("dailyChecks", {}), **checks},
        })
        return {"symbol": symbol, "sessions": len(days), "bars": sum(map(len, days.values()))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-archive", action="store_true", help="Replay verified raw responses without network requests")
    args = parser.parse_args()
    today = datetime.now(UTC).astimezone(native.CHINA).date().isoformat()
    dates = [day for day in observation._read("reference")["data"]["dailyData"]["dates"] if day < today][-20:]
    if len(dates) != 20:
        raise ValueError("20 actual prior trading dates are required")
    print(json.dumps({"from": dates[0], "to": dates[-1], "members": len(observation.SYMBOLS) - 1}), flush=True)
    failures = []
    def run(symbol):
        try:
            result = collect(symbol, dates, args.from_archive)
        except Exception as exc:
            result = {"symbol": symbol, "error": str(exc)}
            failures.append(result)
        print(json.dumps(result, ensure_ascii=True), flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(run, observation.SYMBOLS[1:]))
    if failures:
        raise SystemExit(f"{len(failures)} instruments failed validation; previous baseline retained")


if __name__ == "__main__":
    main()
