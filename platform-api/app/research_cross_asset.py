"""Date-aligned research from existing snapshots; never collects or fills gaps."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from app.research_a_share_repository import read_dataset
from app.research_local_data import read_local_json
from app.research_provider_errors import ResearchProviderError


def _points(items: list[dict], cutoff: date, today: date) -> dict[str, Decimal]:
    result = {}
    for item in items:
        try:
            day = date.fromisoformat(item["date"])
            value = Decimal(str(item["value"]))
        except (KeyError, ValueError, InvalidOperation):
            continue
        if cutoff <= day < today and value.is_finite():
            result[day.isoformat()] = value
    return result


def correlation(left: list[Decimal], right: list[Decimal]) -> Decimal | None:
    if len(left) < 10 or len(left) != len(right):
        return None
    a, b = sum(left, Decimal(0)) / len(left), sum(right, Decimal(0)) / len(right)
    xx = sum(((x - a) ** 2 for x in left), Decimal(0))
    yy = sum(((y - b) ** 2 for y in right), Decimal(0))
    if not xx or not yy:
        return None
    return (
        sum(((x - a) * (y - b) for x, y in zip(left, right, strict=True)), Decimal(0))
        / (xx * yy).sqrt()
    )


def compare(prices: list[dict], days: int, today: date | None = None) -> dict:
    today = today or datetime.now(UTC).date()
    cutoff = today - timedelta(days=days)
    available = []
    unavailable = []
    for item in prices:
        points = {d: v for d, v in _points(item.get("history", []), cutoff, today).items() if v > 0}
        if len(points) >= 2:
            available.append((item, points))
        else:
            unavailable.append(item["label"])
    common = (
        sorted(set.intersection(*(set(points) for _, points in available))) if available else []
    )
    if len(common) < 2:
        return {
            "status": "no_data",
            "days": days,
            "dates": [],
            "assets": [],
            "unavailable": unavailable,
        }
    returns = {
        item["id"]: [points[b] / points[a] - 1 for a, b in zip(common, common[1:], strict=False)]
        for item, points in available
    }
    reference = returns.get("spy", [])
    assets = []
    for item, points in available:
        values = [points[d] for d in common]
        peak, drawdown = values[0], Decimal(0)
        for value in values:
            peak = max(peak, value)
            drawdown = min(drawdown, value / peak - 1)
        changes = returns[item["id"]]
        downside = [value for i, value in enumerate(changes) if reference and reference[i] < 0]
        assets.append(
            {
                **{k: v for k, v in item.items() if k != "history"},
                "normalized": [value / values[0] * 100 for value in values],
                "returnPct": (values[-1] / values[0] - 1) * 100,
                "drawdownPct": drawdown * 100,
                "correlation20": correlation(changes[-20:], reference[-20:]),
                "downsideMeanPct": sum(downside) / len(downside) * 100
                if len(downside) >= 5
                else None,
                "downsideSamples": len(downside),
            }
        )
    return {
        "status": "partial"
        if unavailable or any(x.get("status") != "ready" for x in assets)
        else "ready",
        "days": days,
        "dates": common,
        "assets": assets,
        "unavailable": unavailable,
    }


def read_cross_asset(days: int) -> dict:
    prices = []
    for market, row_id, key, label in [
        ("us", "us-spy", "spy", "美股 SPY"),
        ("gold", "gold-gld-row", "gld", "黄金 ETF GLD"),
        ("crypto", "crypto-btc-row", "btc", "比特币 BTC/USD"),
    ]:
        snapshot = read_dataset(f"market_detail_{market}") or {}
        row = next((r for r in snapshot.get("rows", []) if r["id"] == row_id), {})
        status = row.get("status", "no_data")
        try:
            retrieved = datetime.fromisoformat(snapshot["retrievedAt"].replace("Z", "+00:00"))
            if retrieved.tzinfo is None or datetime.now(UTC) - retrieved > timedelta(hours=1):
                status = "stale"
        except (KeyError, ValueError):
            status = "stale" if row else "no_data"
        prices.append(
            {
                "id": key,
                "label": label,
                "source": row.get("source"),
                "asOf": row.get("observationDate"),
                "status": status,
                "history": row.get("history", []),
            }
        )
    result = compare(prices, days)
    result["yieldChangeBp"] = None
    result["yieldDates"] = []
    try:
        document = read_local_json("public/v1/macro/dashboard.json")
        series = next(
            (
                s
                for group in document["groups"].values()
                for s in group
                if s["seriesId"] == "us_treasury_10y"
            ),
            {},
        )
        points = _points(
            series.get("observations", []),
            datetime.now(UTC).date() - timedelta(days=days),
            datetime.now(UTC).date(),
        )
        dates = result["dates"]
        if dates and dates[0] in points and dates[-1] in points:
            result["yieldChangeBp"] = (points[dates[-1]] - points[dates[0]]) * 100
            result["yieldDates"] = [dates[0], dates[-1]]
    except (ResearchProviderError, KeyError):
        pass  # Only the independent yield comparison is unavailable.
    return result
