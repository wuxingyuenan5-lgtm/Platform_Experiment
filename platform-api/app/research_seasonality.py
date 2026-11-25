"""Source-specific native closing histories for shared monthly statistics."""

import json

from app.data_audit_calendar import cached_sessions
from app.database_connection import read_only_connection
from app.research_local_data import read_local_json

LOCAL = {
    "gold": "public/v1/commodity/series/xauusd_daily_close.json",
    "btc": "public/v1/crypto/series/binance_btc_spot.json",
}
US = {
    "us-spy": ("SPY", "标普500 ETF · SPY", "USD"),
    "us-ndx": ("^NDX", "纳斯达克100指数", "点"),
    "us-dow": ("^DJI", "道琼斯工业指数", "点"),
    "us-gld": ("GLD", "黄金 ETF · GLD", "USD"),
}
CN = {
    "cn-hs300": ("sh000300", "沪深300"),
    "cn-csi1000": ("sh000852", "中证1000"),
    "cn-chinext": ("sz399006", "创业板指"),
    "cn-star50": ("sh000688", "科创50"),
}


def read_seasonality(asset):
    if asset in LOCAL:
        return read_local_json(LOCAL[asset])
    calendar = {}
    if asset in US:
        symbol, label, unit = US[asset]
        with read_only_connection() as db:
            rows = db.execute(
                "SELECT observed_at,payload_json FROM research_a_share_history "
                "WHERE dataset='market_price' AND entity_code=? ORDER BY observed_at LIMIT 40001",
                ("Yahoo Finance:"+symbol,),
            ).fetchall()
        if len(rows) > 40000:
            raise ValueError("seasonality_history_limit_reached")
        points = []
        for row in rows:
            value = json.loads(row["payload_json"])
            if value.get("symbol") != symbol:
                raise ValueError("seasonality_instrument_mismatch")
            points.append({"date": row["observed_at"], "value": value.get("close")})
        source, url, timezone = "Yahoo Finance", f"https://finance.yahoo.com/quote/{symbol}/history/", "America/New_York"
        status, retrieved = ("ready" if points else "no_data"), None
    elif asset in CN:
        from app.research_etf_native import read
        symbol, label = CN[asset]
        doc = read("market/"+symbol)
        points = [{"date": row["date"], "value": row.get("close")} for row in doc.get("rows", [])]
        source, url, timezone, unit = "东方财富指数日行情", doc.get("sourceUrl"), "Asia/Shanghai", "点"
        status, retrieved = doc.get("status", "no_data"), doc.get("retrievedAt")
        if points:
            first, last = points[0]["date"], points[-1]["date"]
            sessions = cached_sessions(last)
            if sessions and sessions[0] <= first:
                calendar["tradingDates"] = [day for day in sessions if first <= day <= last]
    else:
        raise KeyError(asset)
    return {
        "seriesId": "seasonality_"+asset, "label": label, "status": status,
        "unit": unit, "frequency": "daily", "timezone": timezone,
        "source": source, "sourceUrl": url, "sourceSeriesId": symbol,
        "observationDate": points[-1]["date"] if points else None,
        "asOf": points[-1]["date"] if points else None, "retrievedAt": retrieved,
        "latestValue": points[-1]["value"] if points else None,
        "isStale": status not in ("ready", "succeeded"),
        "methodologyVersion": "native-close-monthly-v1",
        "qualityFlags": ["price_return_excludes_cash_distributions"],
        "observations": points,
        **calendar,
    }
