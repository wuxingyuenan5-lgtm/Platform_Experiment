"""Synchronous US equity open/close returns, including overnight opening gaps."""

from collections import deque
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from app.research_cross_asset import correlation
from app.research_local_data import read_local_json


def positive_points(rows):
    result = {}
    for row in rows:
        day = str(row.get("date", ""))[:10]
        try:
            datetime.strptime(day, "%Y-%m-%d")
        except ValueError:
            continue
        if day in result:
            raise ValueError("duplicate_price_date")
        try:
            raw = row.get("value", row.get("close"))
            value = Decimal(str(raw))
        except (ValueError, InvalidOperation):
            result[day] = None
            continue
        result[day] = value if value.is_finite() and value > 0 else None
    return result


def rolling(btc, benchmark, n, today=None):
    today = today or datetime.now(UTC).isoformat()
    # The price artifact owns the common clock. Consecutive close -> next open
    # pairs retain all overnight/weekend movement as the opening gap.
    days = sorted(d for d in benchmark if d < today)
    pairs, out = deque(maxlen=n), []
    previous = None
    for day in days:
        b, a = btc.get(day), benchmark[day]
        valid = a is not None and b is not None
        value = None
        if (
            valid
            and previous
            and (datetime.fromisoformat(day) - datetime.fromisoformat(previous[0])).days <= 7
        ):
            pairs.append((b / previous[1] - 1, a / previous[2] - 1))
            if len(pairs) == n:
                value = correlation([p[0] for p in pairs], [p[1] for p in pairs])
        else:
            pairs.clear()
        out.append(
            {
                "date": day,
                "correlation": value,
                "samples": len(pairs),
                "btcClose": b,
                "benchmarkClose": a,
            }
        )
        previous = (day, b, a) if valid else None
    return out


def read_rolling(n, benchmark):
    document = read_local_json("public/v1/crypto/us-session-prices.json")
    if document.get("alignment") != "synchronous-us-equity-open-close":
        return {"rows": [], "window": n, "benchmark": benchmark, "sources": [], "note": ""}

    def valid(value):
        try:
            result = Decimal(str(value))
            return result if result.is_finite() and result > 0 else None
        except InvalidOperation:
            return None

    records = document.get("rows", [])
    btc = {r["date"]: valid(r.get("btc")) for r in records}
    other = {r["date"]: valid(r.get(benchmark)) for r in records}
    rows = rolling(btc, other, n)
    phases = {r["date"]: r["phase"] for r in records}
    for row in rows:
        row["phase"] = phases[row["date"]]
    sources = document.get("sources", [])
    return {
        "rows": rows,
        "window": n,
        "benchmark": benchmark,
        "alignment": document["alignment"],
        "asOf": rows[-1]["date"] if rows else None,
        "sources": [sources[0], sources[1 if benchmark == "ndx" else 2]]
        if len(sources) == 3
        else [],
        "status": document.get("status"),
        "retrievedAt": document.get("retrievedAt"),
        "coverage": document.get("coverage"),
        "note": "",
    }
