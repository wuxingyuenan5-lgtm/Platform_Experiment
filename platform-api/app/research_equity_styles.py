"""Comparable closed-session ETF style proxies, not portfolio factor attribution."""

from app.research_equity_catalog import CN_STYLES, STYLE_PAIRS, US_STYLES


def build_styles(market, observations, references, baseline, sessions, end):
    from app.research_equity_themes import price_map, window_metrics

    catalog = CN_STYLES if market == "cn" else US_STYLES
    benchmark = window_metrics(baseline, sessions, end)
    rows, prices = [], {}
    for code, name, scope, url in catalog:
        raw = references.get(code, observations.get(code, {}))
        valid = raw.get("date") == end and raw.get("status", "ready") == "ready"
        points = raw.get("history", []) if valid else []
        metrics = window_metrics(points, sessions, end)
        prices[code] = price_map(points, end)
        r20, b20 = metrics["return20"], benchmark["return20"]
        rows.append(
            {
                "code": code,
                "name": name,
                "scope": scope,
                "url": url,
                "date": raw.get("date"),
                "status": "ready" if valid else "no_data",
                **metrics,
                "relative20": r20 - b20 if r20 is not None and b20 is not None else None,
                "history": [
                    {"date": d, "value": prices[code].get(d)} for d in sessions[-125:]
                ],
            }
        )
    by_code = {r["code"]: r for r in rows}
    pairs = []
    for name, a, b in STYLE_PAIRS[market]:
        left, right = by_code[a], by_code[b]
        ratios = [
            {"date": d, "value": prices[a][d] / prices[b][d]}
            for d in sessions
            if d in prices[a] and d in prices[b]
        ]
        pair = {
            "name": name,
            "numerator": a,
            "denominator": b,
            "date": end if ratios and ratios[-1]["date"] == end else None,
        }
        for n in (1, 5, 20):
            av, bv = left[f"return{n}"], right[f"return{n}"]
            pair[f"spread{n}"] = av - bv if av is not None and bv is not None else None
        # Fixed benchmark sessions; a missing day stays a gap in the chart.
        days = sessions[-125:]
        values = {p["date"]: p["value"] for p in ratios}
        first = values.get(days[0]) if days else None
        pair["history"] = [
            {"date": d, "value": values[d] / first * 100 if first and d in values else None}
            for d in days
        ]
        pairs.append(pair)
    return {"items": rows, "pairs": pairs}
