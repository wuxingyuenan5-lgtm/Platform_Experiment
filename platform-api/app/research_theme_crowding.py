"""Same-catalogue stock baskets: matched daily amount shares and fixed-base prices."""

from decimal import Decimal

from app.research_equity_catalog import CATALOG_EFFECTIVE_FROM, CATALOG_VERSION, CN_THEMES
from app.research_equity_metrics import number
from app.research_equity_themes import price_map


def close_amount_points(stocks, date_key, *, closed):
    """Keep the full-market denominator and its member amounts in the same run."""
    if not closed or not date_key:
        return []
    unique = {r["securityCode"]: r for r in stocks}
    if len(unique) < 1000:
        return []
    amounts = {code: number(r.get("turnoverYuan")) for code, r in unique.items()}
    if any(v is None or v < 0 for v in amounts.values()):
        return []
    total = sum(amounts.values(), Decimal(0))
    if total <= 0:
        return []
    codes = {c for _, parts in CN_THEMES for _, cs in parts for c in cs.split()}
    return [(date_key, "__market__", {"amountYuan": total, "count": len(unique)})] + [
        (date_key, code, {"amountYuan": value}) for code, value in amounts.items() if code in codes
    ]


def build_theme_crowding(histories, amount_points, sessions, end):
    prices = {
        code: price_map([{"date": str(p.observed_at), "value": p.close} for p in points], end)
        for code, points in histories.items()
    }
    amounts = {}
    for day, code, payload in amount_points:
        if day <= (end or ""):
            value = number(payload.get("amountYuan"))
            if value is not None and value >= 0:
                amounts.setdefault(day, {})[code] = value
    first = min([d for points in prices.values() for d in points] + list(amounts), default="")
    days = sorted(set(d for d in sessions if first <= d <= (end or "")) | set(amounts))[-1500:]

    def basket(name, codes):
        codes = sorted(set(codes))
        expected = len(codes)
        base = next(
            (d for d in days if expected and all(d in prices.get(c, {}) for c in codes)), None
        )
        rows = []
        for day in days:
            daily = amounts.get(day, {})
            total = daily.get("__market__")
            covered = sum(c in daily for c in codes)
            amount = sum((daily[c] for c in codes), Decimal(0)) if covered == expected else None
            share = (
                amount / total * 100 if amount is not None and total and amount <= total else None
            )
            price_count = sum(day in prices.get(c, {}) for c in codes)
            price = (
                sum((prices[c][day] / prices[c][base] for c in codes), Decimal(0)) / expected * 100
                if base and day >= base and price_count == expected
                else None
            )
            rows.append(
                {
                    "date": day,
                    "amountYuan": amount,
                    "marketAmountYuan": total,
                    "sharePct": share,
                    "shareMa5": None,
                    "amountCount": covered,
                    "price": price,
                    "priceCount": price_count,
                }
            )
            window = rows[-5:]
            if len(window) == 5 and all(r["sharePct"] is not None for r in window):
                rows[-1]["shareMa5"] = sum(r["sharePct"] for r in window) / 5
        first_valid = next(
            (i for i, r in enumerate(rows) if r["sharePct"] is not None or r["price"] is not None),
            max(0, len(rows) - 1),
        )
        return {
            "name": name,
            "expected": expected,
            "priceBaseDate": base,
            "history": rows[first_valid:],
        }

    return {
        "version": CATALOG_VERSION,
        "effectiveFrom": CATALOG_EFFECTIVE_FROM,
        "date": end,
        "items": [
            {
                **basket(name, [c for _, cs in parts for c in cs.split()]),
                "segments": [basket(segment, cs.split()) for segment, cs in parts],
            }
            for name, parts in CN_THEMES
            if parts
        ],
    }
