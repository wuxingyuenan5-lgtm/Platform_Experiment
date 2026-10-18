"""Pure calculations for equity observations. No fetching, imputation or signals."""

from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from statistics import median
from zoneinfo import ZoneInfo

from app.research_equity_catalog import CATALOG_VERSION, CN_THEMES, US_THEMES


def number(value):
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def percentage(a, b):
    return Decimal(a) / Decimal(b) * 100 if b else None


def percentile(values, value, minimum=60):
    values = [v for x in values if (v := number(x)) is not None]
    value = number(value)
    if value is None or len(values) < minimum:
        return None
    # Midrank: a constant history is the 50th percentile, not a false extreme.
    return (
        (sum(v < value for v in values) + Decimal(sum(v == value for v in values)) / 2)
        / len(values)
        * 100
    )


def rolling_rank(points, field, minimum=252):
    if not points:
        return {"value": None, "count": 0, "start": None, "end": None}
    end = points[-1]["date"]
    day = date.fromisoformat(end)
    try:
        cutoff = day.replace(year=day.year - 5).isoformat()
    except ValueError:  # February 29 in a non-leap year
        cutoff = day.replace(year=day.year - 5, day=28).isoformat()
    valid = [p for p in points if cutoff <= p["date"] <= end and number(p.get(field)) is not None]
    return {
        "value": percentile([p[field] for p in valid], points[-1].get(field), minimum),
        "count": len(valid),
        "start": valid[0]["date"] if valid else None,
        "end": end,
    }


def trend(points):
    by_date = {p["date"]: v for p in points if (v := number(p.get("value"))) is not None and v > 0}
    days = sorted(by_date)
    values = [by_date[d] for d in days]
    if not values:
        return {"date": None, "count": 0}
    last = values[-1]
    result = {"date": days[-1], "count": len(values), "close": last}
    for n in (20, 60, 200):
        avg = sum(values[-n:]) / n if len(values) >= n else None
        result[f"above{n}"] = last > avg if avg else None
        result[f"deviation{n}"] = (last / avg - 1) * 100 if avg else None
    for n in (5, 20):
        result[f"return{n}"] = (last / values[-n - 1] - 1) * 100 if len(values) > n else None
    result["drawdown252"] = (last / max(values[-252:]) - 1) * 100 if len(values) >= 252 else None
    return result


def distribution(rows):
    pe = [v for r in rows if (v := number(r.get("peTtm"))) is not None and v > 0]
    pb = [v for r in rows if (v := number(r.get("pb"))) is not None and v > 0]
    changes = [v for r in rows if (v := number(r.get("returnPct"))) is not None]
    turnover = [v for r in rows if (v := number(r.get("turnoverPct"))) is not None and v >= 0]
    amounts = sorted(
        [v for r in rows if (v := number(r.get("turnoverYuan"))) is not None and v >= 0],
        reverse=True,
    )
    total = sum(amounts)
    broken = sum(v < 1 for v in pb)
    return {
        "count": len(rows),
        "peCount": len(pe),
        "pbCount": len(pb),
        "medianPe": median(pe) if pe else None,
        "medianPb": median(pb) if pb else None,
        "nonpositivePeCount": sum(
            number(r.get("peTtm")) is not None and number(r["peTtm"]) <= 0 for r in rows
        ),
        "nonpositivePbCount": sum(
            number(r.get("pb")) is not None and number(r["pb"]) <= 0 for r in rows
        ),
        "belowBookCount": broken,
        "belowBookPct": percentage(broken, len(pb)),
        "medianReturn": median(changes) if changes else None,
        "advancingPct": percentage(sum(v > 0 for v in changes), len(changes)),
        "medianTurnover": median(turnover) if turnover else None,
        "turnoverCount": len(turnover),
        "amount": total if amounts else None,
        "amountCount": len(amounts),
        "top20AmountPct": percentage(sum(amounts[:20]), total),
        "top50AmountPct": percentage(sum(amounts[:50]), total),
    }


def cn_structure(stocks, memberships):
    # Keep dates at source local exchange time. Never combine different sessions.
    dated = []
    for row in stocks:
        try:
            stamp = datetime.fromisoformat(row["observedAt"].replace("Z", "+00:00"))
            if stamp.tzinfo is None or row.get("currency", "CNY") != "CNY":
                continue
            dated.append((stamp.astimezone(ZoneInfo("Asia/Shanghai")), row))
        except (ValueError, KeyError):
            continue
    latest = max((d.date() for d, _ in dated), default=None)
    rows = list({r["securityCode"]: r for d, r in dated if d.date() == latest}.values())
    closed = bool(rows) and all(d.hour >= 15 for d, _ in dated if d.date() == latest)
    member = {r["securityCode"]: r for r in memberships if not r.get("effectiveTo")}
    sectors = defaultdict(list)
    for row in rows:
        m = member.get(row["securityCode"])
        if m and m.get("effectiveFrom", "") <= (latest.isoformat() if latest else ""):
            sectors[(m["swL1Code"], m["swL1Name"])].append(row)
    all_stats = distribution(rows)
    result = []
    for (code, name), members in sectors.items():
        stats = distribution(members)
        result.append(
            {
                "code": code,
                "name": name,
                **stats,
                "amountSharePct": percentage(stats["amount"], all_stats["amount"])
                if stats["amount"] is not None
                else None,
            }
        )
    return {
        "date": latest.isoformat() if latest else None,
        "closed": closed,
        "excludedDateCount": len(dated) - len(rows),
        "unclassifiedCount": len(rows) - sum(len(v) for v in sectors.values()),
        "market": all_stats,
        "industries": sorted(result, key=lambda r: r["amount"] or 0, reverse=True),
    }, rows


def theme_observations(market, observations, date_key):
    catalog = CN_THEMES if market == "cn" else US_THEMES
    all_counts = Counter(
        s for _, parts in catalog for s in set(" ".join(c for _, c in parts).split())
    )
    themes = []
    for name, segments in catalog:
        members = []
        for segment, codes in segments:
            for code in codes.split():
                raw = observations.get(code, {})
                valid = bool(raw) and raw.get("date") == date_key and raw.get("status") == "ready"
                members.append(
                    {
                        "code": code,
                        "segment": segment,
                        "name": raw.get("name") or code,
                        "returnPct": raw.get("returnPct") if valid else None,
                        "amount": raw.get("amount") if valid else None,
                        "date": raw.get("date"),
                        "status": "ready" if valid else "no_data",
                        "themeCount": all_counts[code],
                    }
                )
        unique = {r["code"]: r for r in members}
        values = [
            number(r["returnPct"]) for r in unique.values() if number(r["returnPct"]) is not None
        ]
        themes.append(
            {
                "name": name,
                "segments": [s for s, _ in segments],
                "members": members,
                "expected": len(unique),
                "covered": len(values),
                "medianReturn": median(values) if values else None,
                "advancingPct": percentage(sum(v > 0 for v in values), len(values)),
            }
        )
    return {"version": CATALOG_VERSION, "date": date_key, "items": themes}


def month_shift(month, count):
    y, m = map(int, month.split("-"))
    total = y * 12 + m - 1 + count
    return f"{total // 12:04d}-{total % 12 + 1:02d}"


def monthly_yoy(series):
    return {
        m: (v / series[month_shift(m, -12)] - 1) * 100
        for m, v in series.items()
        if month_shift(m, -12) in series and series[month_shift(m, -12)] > 0
    }


def credit_impulse(tsf, gdp_ytd):
    # GDP input is cumulative nominal GDP, not quarterly GDP or real growth.
    annual = {}
    for m, v in sorted(gdp_ytd.items()):
        year, month = map(int, m.split("-"))
        if month == 12:
            annual[m] = v
        elif f"{year - 1}-12" in gdp_ytd and f"{year - 1}-{month:02d}" in gdp_ytd:
            annual[m] = v + gdp_ytd[f"{year - 1}-12"] - gdp_ytd[f"{year - 1}-{month:02d}"]
    ratio = {}
    for m in sorted(tsf):
        months = [month_shift(m, -i) for i in range(12)]
        # Historical observations, not a point-in-time backtest. Avoid assigning
        # a quarter's GDP to months before that quarter ended.
        eligible = [d for d in annual if d <= m and month_shift(m, -5) <= d]
        if all(d in tsf for d in months) and eligible and annual[max(eligible)] > 0:
            ratio[m] = sum(tsf[d] for d in months) / annual[max(eligible)] * 100
    return {
        m: v - ratio[month_shift(m, -12)] for m, v in ratio.items() if month_shift(m, -12) in ratio
    }


def hk_composite(components, today):
    labels = {
        "m2": "香港M2总额同比",
        "ppi": "内地PPI同比",
        "retail": "内地社零同比",
        "credit": "信用脉冲",
    }
    common = sorted(set.intersection(*(set(components.get(k, {})) for k in labels)))
    history = []
    for m in common:
        contributions = {}
        for key in labels:
            series = components[key]
            values = [v for d, v in sorted(series.items()) if month_shift(m, -59) <= d <= m]
            if len(values) < 36:
                break
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            if not variance:
                break
            contributions[key] = (series[m] - mean) / variance.sqrt() / 4
        if len(contributions) == 4:
            history.append(
                {"date": m, "value": sum(contributions.values()), "contributions": contributions}
            )
    latest = history[-1] if history else None
    rows = []
    for key, label in labels.items():
        series = components.get(key, {})
        m = max(series, default=None)
        rows.append(
            {
                "id": key,
                "name": label,
                "weight": 25,
                "date": m,
                "value": series.get(m),
                "count": len(series),
                "contribution": latest["contributions"][key] if latest else None,
                "compositeDate": latest["date"] if latest else None,
            }
        )
    return {
        "status": "no_data"
        if not latest
        else "stale"
        if latest["date"] < month_shift(today[:7], -3)
        else "ready",
        "date": latest["date"] if latest else None,
        "value": latest["value"] if latest else None,
        "components": rows,
        "history": history[-120:],
    }
