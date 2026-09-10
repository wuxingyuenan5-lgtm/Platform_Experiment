"""Read public historical USD candles for a local capital-valuation request file.

Input/output are JSON arrays. Only currency and time leave this process; account
identities and capital amounts are never sent to the public market-data source.
Run with the configured Runtime Python; no credentials or order APIs are used.
"""

import argparse
import json
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("requests")
    parser.add_argument("output")
    args = parser.parse_args()
    result = []
    with httpx.Client(timeout=15) as client:
        for request in json.loads(Path(args.requests).read_text(encoding="utf-8")):
            currency = request["currency"]
            if not re.fullmatch(r"[A-Z0-9]{1,20}", currency):
                raise ValueError("Invalid currency")
            target = datetime.fromisoformat(request["asOf"].replace("Z", "+00:00"))
            if target.tzinfo is None:
                raise ValueError("Timestamp must be timezone-aware")
            product = "USDT" if currency == "BYUSDT" else currency
            entry = dict(request)
            try:
                response = client.get(
                    f"https://api.exchange.coinbase.com/products/{product}-USD/candles",
                    params={
                        "granularity": 60,
                        "start": (target - timedelta(minutes=5)).isoformat(),
                        "end": target.isoformat(),
                    },
                )
                response.raise_for_status()
                rows = json.loads(response.text, parse_float=Decimal)
                rows = [r for r in rows if 0 <= target.timestamp() - (int(r[0]) + 60) <= 300]
                if not rows:
                    raise ValueError("No recent completed candle")
                candle = max(rows, key=lambda r: r[0])
                rate = Decimal(str(candle[4]))
                if not rate.is_finite() or rate <= 0:
                    raise ValueError("Invalid historical price")
                entry.update(
                    usdRate=str(rate),
                    quoteAsOf=datetime.fromtimestamp(int(candle[0]) + 60, UTC).isoformat(),
                    source=f"coinbase:{product}-USD:1m-close"
                    + (":byusdt-1to1-backing" if currency == "BYUSDT" else ""),
                )
            except (httpx.HTTPError, ValueError) as exc:
                entry["error"] = type(exc).__name__
            result.append(entry)
    Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Valuations: {sum('usdRate' in r for r in result)}/{len(result)}")


if __name__ == "__main__":
    main()
