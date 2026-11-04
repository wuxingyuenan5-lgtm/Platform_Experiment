"""Paired native-close returns over common market sessions, never weekend zero-fill."""

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
    today = today or datetime.now(UTC).date().isoformat()
    # Benchmark session dates define the grid; BTC weekend moves accrue into
    # the next common-session return (Friday -> Monday, not Sunday -> Monday).
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
    btc = read_local_json("public/v1/crypto/series/binance_btc_spot.json")
    if benchmark == "xau":
        other = read_local_json("public/v1/commodity/series/xauusd_daily_close.json")
    else:
        import json

        from app.database_connection import read_only_connection

        first = (
            min(p["date"] for p in btc.get("observations", []))
            if btc.get("observations")
            else "9999-12-31"
        )
        with read_only_connection() as db:
            records = db.execute(
                "SELECT observed_at,payload_json FROM research_a_share_history "
                "WHERE dataset='market_price' AND entity_code='Yahoo Finance:^NDX' "
                "AND observed_at>=? ORDER BY observed_at LIMIT 15000",
                (first,),
            ).fetchall()
        other = {
            "source": "Yahoo Finance",
            "sourceUrl": "https://finance.yahoo.com/quote/%5ENDX/history/",
            "history": [
                {"date": r["observed_at"], "close": json.loads(r["payload_json"]).get("close")}
                for r in records
            ],
        }
    points = other.get("observations", other.get("history", []))
    rows = rolling(positive_points(btc.get("observations", [])), positive_points(points), n)
    return {
        "rows": rows,
        "window": n,
        "benchmark": benchmark,
        "alignment": "common-session-native-close",
        "btcSource": btc.get("source"),
        "benchmarkSource": other.get("source"),
        "asOf": rows[-1]["date"] if rows else None,
        "sources": [btc.get("sourceUrl"), other.get("sourceUrl")],
        "note": (
            "按对手市场交易日计算同区间简单收益率的Pearson相关性；周末BTC变动计入下个交易日，"
            "不补零、不前向填充。N指共同交易区间数。BTC为UTC日收盘，NDX为纽约收盘、"
            "XAU为MT5日收盘，存在日内收盘时差，并非同步时刻相关性。"
        ),
    }
