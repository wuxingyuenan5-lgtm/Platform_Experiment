"""Bounded, indexed instrument analysis of stored native closing prices.

Price returns exclude cash distributions. No network, whole-market scan or
inferred event causes. Drawdowns are relative to the observed sample peak.
"""

import json
from bisect import bisect_right
from collections import deque
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from math import fsum, sqrt
from zoneinfo import ZoneInfo

from app.database_connection import read_only_connection
from app.research_equity_metrics import number

INSTRUMENTS = {
    "spy": ("SPY", "标普500 ETF · SPY", "USD"),
    "ndx": ("^NDX", "纳斯达克100指数", "点"),
    "dow": ("^DJI", "道琼斯工业指数", "点"),
    "soxx": ("SOXX", "半导体 ETF · SOXX", "USD"),
    "xlk": ("XLK", "信息技术 ETF · XLK", "USD"),
}


def annualized(a, b, days):
    return ((float(b / a) ** (365.25 / days)) - 1) * 100 if a > 0 and b > 0 and days > 0 else None


def annual_volatility(window):
    mean = fsum(window) / len(window)
    return sqrt(fsum((value - mean) ** 2 for value in window) / (len(window) - 1)) * sqrt(252)


def analyze_prices(points, current_year):
    rows = sorted(points, key=lambda r: r["date"])
    if len({r["date"] for r in rows}) != len(rows):
        raise ValueError("duplicate_price_dates")
    out, episodes, years = [], [], {}
    windows = {20: deque(maxlen=20), 60: deque(maxlen=60)}
    peak = peak_day = previous = previous_day = episode = None
    valid_dates, valid_prices = [], []
    invalid = gaps = 0
    for r in rows:
        day = date.fromisoformat(r["date"])
        price = number(r.get("close"))
        if price is None or price <= 0:
            invalid += 1
            for window in windows.values():
                window.clear()
            previous = previous_day = None
            out.append({"date": day.isoformat(), "close": None, "drawdown": None,
                        "return1": None, "vol20": None, "vol60": None, "rolling5y": None})
            continue
        gap = previous_day is not None and (day - previous_day).days > 7
        if gap:
            gaps += 1
        ret = (price / previous - 1) * 100 if previous is not None and not gap else None
        if ret is None:
            for window in windows.values():
                window.clear()
        else:
            for window in windows.values():
                window.append(float(ret))
        if peak is None or price >= peak:
            if episode:
                episode.update(recoveryDate=day.isoformat(), daysUnderwater=(day - date.fromisoformat(episode["peakDate"])).days)
                episodes.append(episode)
                episode = None
            peak, peak_day = price, day.isoformat()
        drawdown = (price / peak - 1) * 100
        if drawdown < 0:
            if episode is None:
                episode = {"peakDate": peak_day, "troughDate": day.isoformat(), "depth": drawdown, "recoveryDate": None}
            elif drawdown < episode["depth"]:
                episode.update(troughDate=day.isoformat(), depth=drawdown)
        years.setdefault(day.year, []).append((day.isoformat(), price))
        valid_dates.append(day)
        valid_prices.append(price)
        target = day.replace(year=day.year - 5, day=28) if day.month == 2 and day.day == 29 else day.replace(year=day.year - 5)
        idx = bisect_right(valid_dates, target) - 1
        rolling = annualized(valid_prices[idx], price, (day - valid_dates[idx]).days) if idx >= 0 and (target - valid_dates[idx]).days <= 7 else None
        out.append({"date": day.isoformat(), "close": price, "drawdown": drawdown, "return1": ret,
                    **{f"vol{n}": annual_volatility(window) if len(window) == n else None for n, window in windows.items()},
                    "rolling5y": rolling})
        previous, previous_day = price, day
    if episode:
        episode["daysUnderwater"] = (valid_dates[-1] - date.fromisoformat(episode["peakDate"])).days
        episodes.append(episode)
    annual = []
    for year, values in sorted(years.items()):
        preceding = years.get(year - 1, [])
        base = preceding[-1][1] if preceding and preceding[-1][0][5:7] == "12" else None
        running_peak = base or values[0][1]
        deepest = Decimal(0)
        for _, p in values:
            running_peak = max(running_peak, p)
            deepest = min(deepest, (p / running_peak - 1) * 100)
        annual.append({"date": values[-1][0], "year": year, "return": (values[-1][1] / base - 1) * 100 if base else None,
                       "drawdown": deepest, "samples": len(values),
                       "partial": year == current_year or len(values) < 200 or values[0][0][5:7] != "01" or values[-1][0][5:7] != "12" or base is None})
    valid = [r for r in out if r.get("close") is not None]
    return {"history": out, "annual": annual, "episodes": sorted(episodes, key=lambda e: e["depth"]),
            "start": valid[0]["date"] if valid else None, "asOf": valid[-1]["date"] if valid else None,
            "samples": len(valid), "invalid": invalid, "gaps": gaps,
            "summary": {"price": valid[-1]["close"] if valid else None,
                        "drawdown": valid[-1]["drawdown"] if valid else None,
                        "maxDrawdown": min(r["drawdown"] for r in valid) if valid else None,
                        "cagr": annualized(valid[0]["close"], valid[-1]["close"], (valid_dates[-1]-valid_dates[0]).days) if valid else None}}


@lru_cache(maxsize=8)
def _analyzed(points, year):
    return analyze_prices([{"date": d, "close": p} for d, p in points], year)


def read_history_risk(instrument):
    symbol, name, unit = INSTRUMENTS[instrument]
    with read_only_connection() as db:
        raw = db.execute("SELECT observed_at,payload_json FROM research_a_share_history "
                         "WHERE dataset='market_price' AND entity_code=? ORDER BY observed_at LIMIT 40000",
                         ("Yahoo Finance:" + symbol,)).fetchall()
    if len(raw) == 40000:
        raise ValueError("history_analysis_limit_reached")
    points = []
    for row in raw:
        value = json.loads(row["payload_json"])
        if value.get("symbol") != symbol:
            raise ValueError("history_instrument_mismatch")
        points.append((row["observed_at"], str(value["close"]) if value.get("close") is not None else None))
    result = _analyzed(tuple(points), datetime.now(ZoneInfo("America/New_York")).year)
    return {**result, "status": "ready" if points else "no_data", "instrument": instrument,
            "name": name, "unit": unit, "source": "Yahoo Finance",
            "sourceUrl": f"https://finance.yahoo.com/quote/{symbol}/history/",
            "referenceUrl": "https://historyofmarket.com/",
            "instruments": [{"id": key, "name": v[1]} for key, v in INSTRUMENTS.items()]}
