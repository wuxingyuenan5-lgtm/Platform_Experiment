"""Transparent quantity/price/structure lens, not a replica of a proprietary score."""

from datetime import date, timedelta
from decimal import Decimal

from app.research_equity_metrics import number, percentile
from app.research_local_data import read_local_json
from app.research_provider_errors import ResearchProviderError

SPECS = [
    ("walcl", "Fed总资产", "量", "usd_million", "十亿美元", Decimal('0.001')),
    ("wdtgal", "TGA余额", "量", "usd_million", "十亿美元", Decimal('0.001')),
    ("fed_on_rrp_million", "ON RRP余额", "量", "usd_million", "十亿美元", Decimal('0.001')),
    ("reserve_balances", "银行准备金", "结构", "usd_million", "十亿美元", Decimal('0.001')),
    ("sofr_iorb_spread", "SOFR−IORB", "价", "basis_points", "bp", Decimal(1)),
    ("sofr_effr_spread", "SOFR−EFFR", "价", "basis_points", "bp", Decimal(1)),
    ("us_srf_usage", "SRF使用量", "结构", "usd_100million", "十亿美元", Decimal('0.1')),
    ("us_hy_oas", "高收益债OAS", "市场反馈", "percent", "bp", Decimal(100)),
    ("us_ig_oas", "投资级债OAS", "市场反馈", "percent", "bp", Decimal(100)),
    ("vix", "VIX", "市场反馈", "index", "点", Decimal(1)),
    ("us_10y_real_yield", "10年实际利率", "价", "percent", "%", Decimal(1)),
]


def values(doc, expected_unit, factor):
    if doc.get("unit") != expected_unit:
        raise ValueError("liquidity_unit_mismatch")
    result = {}
    for point in doc.get("observations", []):
        day = date.fromisoformat(point["date"]).isoformat()
        value = number(point.get("value"))
        if day in result:
            raise ValueError("liquidity_duplicate_dates")
        result[day] = value * factor if value is not None else None
    return result


def aligned_quantity(assets, tga, rrp):
    rows = []
    previous = None
    for day in sorted(assets.keys() & tga.keys() & rrp.keys()):
        a, t, r = assets[day], tga[day], rrp[day]
        if any(v is None for v in [a, t, r]):
            previous = None
            continue
        point = {"date": day, "assets": a, "tga": t, "rrp": r, "net": a - t - r,
                 "fedChange": None, "tgaEffect": None, "rrpEffect": None, "netChange": None, "previousDate": None}
        if previous:
            point.update(fedChange=a-previous["assets"], tgaEffect=previous["tga"]-t,
                         rrpEffect=previous["rrp"]-r, netChange=point["net"]-previous["net"], previousDate=previous["date"])
        rows.append(point)
        previous = point
    return rows


def build_lens(sources):
    cards, lookups, issues = [], {}, {}
    for key, label, category, unit, display_unit, factor in SPECS:
        doc = sources.get(key, {})
        issue = None
        try:
            lookup = values(doc, unit, factor)
        except ValueError as exc:
            lookup = {}
            issue = str(exc)
        lookups[key] = lookup
        issues[key] = issue
    aligned = aligned_quantity(lookups.get("walcl", {}), lookups.get("wdtgal", {}), lookups.get("fed_on_rrp_million", {}))
    latest = aligned[-1] if aligned else None
    for key, label, category, unit, display_unit, factor in SPECS:
        doc = sources.get(key, {})
        lookup, issue = lookups[key], issues[key]
        valid = sorted((day, v) for day, v in lookup.items() if v is not None)
        if category == "量" and latest:
            valid = [(day, v) for day, v in valid if day <= latest["date"]]
        current = valid[-1] if valid else None
        history = []
        if current:
            day = date.fromisoformat(current[0])
            cutoff = day.replace(year=day.year-5, day=28) if day.month == 2 and day.day == 29 else day.replace(year=day.year-5)
            history = [(d, v) for d, v in valid if d >= cutoff.isoformat()]
        cards.append({"id": key, "name": label, "category": category, "unit": display_unit,
                      "value": current[1] if current else None, "date": current[0] if current else None,
                      "change": current[1]-valid[-2][1] if len(valid)>1 else None,
                      "previousDate": valid[-2][0] if len(valid)>1 else None,
                      "rank": percentile([v for _, v in history], current[1], minimum=52) if current else None,
                      "count": len(history), "historyStart": history[0][0] if history else None,
                      "sourceUrl": doc.get("sourceUrl"), "status": "error" if issue and doc else doc.get("status", "no_data"),
                      "spark": [{"date": d, "value": v} for d,v in valid[-30:]]})
    previous = None
    if latest:
        target = (date.fromisoformat(latest["date"]) - timedelta(days=28)).isoformat()
        previous = next((r for r in reversed(aligned) if r["date"] == target), None)
    change = {"date": latest["date"] if latest else None, "previousDate": previous["date"] if previous else None,
              "fed": None, "tga": None, "rrp": None, "net": None}
    if latest and previous:
        change.update(fed=latest["assets"]-previous["assets"], tga=previous["tga"]-latest["tga"],
                      rrp=previous["rrp"]-latest["rrp"], net=latest["net"]-previous["net"])
    structure = []
    for point in aligned:
        reserve = lookups.get("reserve_balances", {}).get(point["date"])
        a = point["assets"]
        structure.append({"date": point["date"], "reserves": reserve / a * 100 if reserve is not None and a > 0 else None,
                          "tga": point["tga"] / a * 100 if a > 0 else None,
                          "rrp": point["rrp"] / a * 100 if a > 0 else None})
    return {"status": "ready" if aligned else "no_data", "asOf": latest["date"] if latest else None,
            "latest": latest, "change4w": change, "cards": cards, "history": aligned,
            "structure": structure,
            "referenceUrl": "https://dollarliquidity.com/zh/methodology"}


def read_liquidity_lens():
    sources = {}
    for key, *_ in SPECS:
        try:
            sources[key] = read_local_json(f"public/v1/macro/series/{key}.json")
        except ResearchProviderError:
            sources[key] = {}
    return build_lens(sources)
