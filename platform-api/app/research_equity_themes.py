"""Closed-session, fixed-universe theme comparisons; no fetching or trading signals."""

from collections import defaultdict
from decimal import Decimal
from statistics import median

from app.research_equity_catalog import (
    CATALOG_EFFECTIVE_FROM,
    CATALOG_VERSION,
    CN_REFERENCES,
    CN_THEMES,
    RELATED_THEMES,
    SATELLITE_THEMES,
    US_REFERENCES,
    US_THEMES,
)
from app.research_equity_metrics import number, percentage


def price_map(points, end):
    return {
        str(p.get("date", ""))[:10]: value
        for p in points
        if p.get("date")
        and str(p["date"])[:10] <= (end or "")
        and (value := number(p.get("value"))) is not None
        and value > 0
    }


def window_metrics(points, sessions, end):
    prices = price_map(points, end)
    result = {"return1": None, "return5": None, "return20": None, "above20": None}
    if not end or not sessions or sessions[-1] != end or end not in prices:
        return result
    for n in (1, 5, 20):
        days = sessions[-n - 1 :]
        # A suspension, missing session or short history cannot become a shorter window.
        if len(days) == n + 1 and all(day in prices for day in days):
            result[f"return{n}"] = (prices[end] / prices[days[0]] - 1) * 100
    days = sessions[-20:]
    if len(days) == 20 and all(day in prices for day in days):
        result["above20"] = prices[end] > sum(prices[d] for d in days) / 20
    return result


def summarize(members):
    unique = list({m["code"]: m for m in members}.values())
    expected = len(unique)
    result = {"expected": expected}
    for field in ("returnPct", "return5", "return20", "relative20"):
        values = [v for row in unique if (v := number(row.get(field))) is not None]
        result[field] = median(values) if values else None
        result[field + "Count"] = len(values)
        result[field + "Rankable"] = bool(
            expected and len(values) >= 3 and Decimal(len(values)) / expected >= Decimal("0.8")
        )
    result["medianReturn"] = result["returnPct"]
    result["covered"] = result["returnPctCount"]
    result["advancingPct"] = percentage(
        sum(
            number(m.get("returnPct")) > 0 for m in unique if number(m.get("returnPct")) is not None
        ),
        result["covered"],
    )
    breadth = [m["above20"] for m in unique if m.get("above20") is not None]
    result["above20Count"] = len(breadth)
    result["above20Pct"] = percentage(sum(breadth), len(breadth))
    return result


def build_themes(market, observations, date_key, *, benchmark=None, references=None):
    catalog = CN_THEMES if market == "cn" else US_THEMES
    reference_catalog = CN_REFERENCES if market == "cn" else US_REFERENCES
    benchmark = benchmark or {}
    references = references or {}
    baseline = price_map(benchmark.get("history", []), date_key)
    sessions = sorted(baseline)
    baseline_metrics = window_metrics(benchmark.get("history", []), sessions, date_key)
    memberships = defaultdict(set)
    for name, parts in catalog:
        for _, codes in parts:
            for code in codes.split():
                memberships[code].add(name)
    items = []
    for name, parts in catalog:
        members = []
        for segment, codes in parts:
            for code in codes.split():
                raw = observations.get(code, {})
                valid = raw.get("date") == date_key and raw.get("status") == "ready"
                metrics = (
                    window_metrics(raw.get("history", []), sessions, date_key) if valid else {}
                )
                daily = number(raw.get("returnPct")) if valid else None
                # Histories are required for multi-day returns; same-session spot
                # change remains useful where a complete history is unavailable.
                change = metrics.get("return1") if metrics.get("return1") is not None else daily
                r20, b20 = metrics.get("return20"), baseline_metrics.get("return20")
                members.append(
                    {
                        "code": code,
                        "name": raw.get("name") or code,
                        "segment": segment,
                        "returnPct": change,
                        "return5": metrics.get("return5"),
                        "return20": r20,
                        "relative20": r20 - b20 if r20 is not None and b20 is not None else None,
                        "above20": metrics.get("above20"),
                        "date": raw.get("date"),
                        "industry": raw.get("industry"),
                        "region": raw.get("region"),
                        "source": raw.get("source"),
                        "sourceUrl": raw.get("sourceUrl"),
                        "themes": sorted(memberships[code]),
                        "themeCount": len(memberships[code]),
                        "status": "ready" if valid else "no_data",
                        "history": [
                            {"date": day, "value": value}
                            for day, value in sorted(
                                price_map(raw.get("history", []), date_key).items()
                            )[-65:]
                        ],
                    }
                )
        codes = {m["code"] for m in members}
        overlaps = [
            {"name": other, "count": len(codes & {s for _, cs in segs for s in cs.split()})}
            for other, segs in catalog
            if other != name
        ]
        refs = []
        for code, label, coverage, scope, url in reference_catalog.get(name, []):
            raw = references.get(code, observations.get(code, {}))
            values = window_metrics(raw.get("history", []), sessions, date_key)
            refs.append(
                {
                    "code": code,
                    "name": label,
                    "coverage": coverage,
                    "scope": scope,
                    "url": url,
                    "date": raw.get("date"),
                    **values,
                }
            )
        items.append(
            {
                "name": name,
                "kind": "style"
                if not parts
                else "satellite"
                if name in SATELLITE_THEMES.get(market, set())
                else "theme",
                "segments": [s for s, _ in parts],
                **summarize(members),
                "members": members,
                "segmentMetrics": [
                    {"name": segment, **summarize([m for m in members if m["segment"] == segment])}
                    for segment, _ in parts
                ],
                "overlaps": sorted([o for o in overlaps if o["count"]], key=lambda o: -o["count"]),
                "related": RELATED_THEMES.get(market, {}).get(name, []),
                "references": refs,
            }
        )
    from app.research_equity_styles import build_styles

    return {
        "version": CATALOG_VERSION,
        "effectiveFrom": CATALOG_EFFECTIVE_FROM,
        "date": date_key,
        "items": items,
        "benchmark": {
            "code": benchmark.get("code"),
            "name": benchmark.get("name"),
            "date": date_key if date_key in baseline else None,
            **baseline_metrics,
        },
        "uniqueStocks": len(memberships),
        "styles": build_styles(
            market, observations, references, benchmark.get("history", []), sessions, date_key
        ),
    }
