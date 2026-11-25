"""Single-fund research for theme references outside the tracked holdings groups."""

from decimal import Decimal

from app.research_a_share_repository import read_stored_stock_histories
from app.research_equity_catalog import CN_REFERENCES
from app.research_equity_metrics import number
from app.research_etf_native import read


def panorama(*, include_series=True, theme=None, days=0):
    """Native-share observations of the existing reference sample, without network IO."""
    from app.data_audit_calendar import cached_sessions

    archive, recent = read("theme-shares"), read("shares")
    funds = []
    for code, meta in reference_funds().items():
        values = dict(archive.get("funds", {}).get(code, {}))
        for day, members in recent.get("days", {}).items():
            if code in members:
                value = number(members[code])
                values[day] = None if day in values and number(values[day]) != value else value
        series = []
        for day in sorted(values):
            value = number(values[day])
            series.append(
                {
                    "date": day,
                    "units": str(value / Decimal(100000000))
                    if value is not None and value > 0
                    else None,
                }
            )
        funds.append({**meta, "series": series})
    end = max(
        (p["date"] for f in funds for p in f["series"] if p["units"] is not None), default=None
    )
    sessions = sorted(set(cached_sessions(end))) if end else []
    sessions = [d for d in sessions if d <= end]
    start = sessions[-6] if len(sessions) >= 6 and sessions[-1] == end else None
    start20 = sessions[-21] if len(sessions) >= 21 and sessions[-1] == end else None
    by_code = {f["code"]: f for f in funds}
    themes = []
    for theme_name, refs in CN_REFERENCES.items():
        codes = list(dict.fromkeys(r[0] for r in refs))
        members = [by_code[c] for c in codes]
        dates = sorted({p["date"] for f in members for p in f["series"]})
        points = [{p["date"]: number(p["units"]) for p in f["series"]} for f in members]
        series = []
        for day in dates:
            values = [p.get(day) for p in points]
            total = sum(values, Decimal(0)) if all(v is not None for v in values) else None
            series.append({"date": day, "units": str(total) if total is not None else None})
        themes.append(
            {
                "code": theme_name,
                "name": theme_name,
                "theme": theme_name,
                "scope": "主题目录内ETF合计",
                "members": codes,
                "series": series,
            }
        )
    for fund in [*funds, *themes]:
        points = {p["date"]: number(p["units"]) for p in fund["series"]}
        for baseline, suffix in ((start, ""), (start20, "20")):
            first, last = points.get(baseline), points.get(end)
            delta = last - first if first is not None and last is not None else None
            fund[f"delta{suffix}"] = str(delta) if delta is not None else None
            fund[f"change{suffix}Pct" if suffix else "changePct"] = (
                str(delta / first * 100) if delta is not None and first > 0 else None
            )
    if theme is not None:
        themes = [t for t in themes if theme == "all" or t["code"] == theme]
        codes = {c for t in themes for c in t["members"]}
        funds = [f for f in funds if f["code"] in codes]
    from datetime import date, timedelta

    cutoff = (date.fromisoformat(end) - timedelta(days=days)).isoformat() if end and days else ""
    for item in [*funds, *themes]:
        # The chart projection needs theme histories only; fund histories have a separate detail API.
        item["series"] = (
            [p for p in item["series"] if p["date"] >= cutoff]
            if (include_series and (theme is None or "members" in item))
            else []
        )
    return {
        "funds": funds,
        "themes": themes,
        "date": end,
        "start": start,
        "start20": start20,
        "source": "沪深交易所公布份额 / Choice 历史"
        if archive.get("choiceHistoryPrefix") else "沪深交易所公布份额",
        "status": "partial" if end else "no_data",
    }


def reference_funds():
    return {
        code: {"code": code, "name": name, "theme": theme, "scope": scope, "url": url}
        for theme, refs in CN_REFERENCES.items()
        for code, name, _, scope, url in refs
    }


def reference_detail(code, meta):
    prices = read_stored_stock_histories([code], limit_per_code=1500).get(code, [])
    archive = read("theme-shares")
    recent = read("shares")
    units = dict(archive.get("funds", {}).get(code, {}))
    for day, members in recent.get("days", {}).items():
        if code in members:
            value = number(members[code])
            if day in units and number(units[day]) != value:
                units[day] = None
            else:
                units[day] = value
    closes = {str(p.observed_at): p.close for p in prices}
    series = []
    for day in sorted(set(closes) | set(units)):
        shares = number(units.get(day))
        series.append(
            {
                "date": day,
                "etf_qfq_close": str(closes[day]) if day in closes else None,
                "native_units_yi": str(shares / Decimal(100000000))
                if shares is not None and shares > 0
                else None,
                "share_basis": "exchange_native_units",
            }
        )
    return {
        "meta": meta,
        "groupLabel": meta.get("theme") or meta.get("display_group"),
        "series": series,
        "shareBasis": "native",
        "margin": [],
        "members": [],
        "group": [],
        "groupMargin": [],
        "disclosures": [],
        "sources": {
            "market": {
                "status": "partial" if series else "no_data",
                "priceSource": "平台留存的腾讯复权日线",
                "shareSource": "沪深交易所公布份额 / Choice 历史"
                if code in archive.get("choiceHistoryPrefix", {}) else "沪深交易所公布份额",
                "priceDate": max(closes, default=None),
                "shareDate": max(
                    (r["date"] for r in series if r["native_units_yi"] is not None), default=None
                ),
            }
        },
    }
