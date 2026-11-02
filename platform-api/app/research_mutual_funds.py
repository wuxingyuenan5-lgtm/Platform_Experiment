"""Disclosure-date-aware local read model for active equity mutual funds."""

from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.research_mutual_fund_refresh import COLLECTION_PAUSED, read, write
from app.research_mutual_fund_sources import HK_INDUSTRIES

D = Decimal


def previous_quarter(stamp):
    year, month = int(stamp[:4]), int(stamp[5:7])
    return (
        f"{year - 1}-12-31"
        if month == 3
        else f"{year}-" + {6: "03-31", 9: "06-30", 12: "09-30"}[month]
    )


def expected_period():
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    month = ((today.month - 1) // 3) * 3
    return (
        f"{today.year - 1}-12-31"
        if month == 0
        else f"{today.year}-" + {3: "03-31", 6: "06-30", 9: "09-30"}[month]
    )


def period(doc, key, stamp):
    return next((r for r in doc.get("data", {}).get(key, []) if r["date"] == stamp), None)


def subtract(a, b):
    return str(D(a) - D(b)) if a is not None and b is not None else None


def pct(a, b):
    return str(D(a) / D(b) * 100) if a is not None and b is not None and D(b) else None


def top_ten(row):
    return (
        sorted(
            (r for r in row.get("rows", []) if r["valueYuan"] is not None),
            key=lambda r: D(r["valueYuan"]),
            reverse=True,
        )[:10]
        if row
        else []
    )


def portfolio_nav(doc, stamp):
    allocation = period(doc, "allocations", stamp)
    if not allocation or not allocation["navYuan"] or D(allocation["navYuan"]) <= 0:
        return None
    nav = D(allocation["navYuan"])
    # Some sources report a share-class NAV alongside a portfolio's combined
    # holdings. Never weight those together. Rounded disclosure permits 2%.
    for row in top_ten(period(doc, "holdings", stamp)):
        weight = D(row["weightPct"] or "0")
        if weight >= 1 and row["valueYuan"]:
            implied = D(row["valueYuan"]) / weight * 100
            if abs(implied / nav - 1) > D("0.02"):
                return None
    return nav


def summary(docs, stamp):
    rows = [(doc, period(doc, "allocations", stamp), portfolio_nav(doc, stamp)) for doc in docs]
    rows = [(doc, a, nav) for doc, a, nav in rows if a and nav and a["stockPct"] is not None]
    nav = sum((n for _, _, n in rows), D(0))
    output = {"date": stamp, "fundCount": len(rows), "navYuan": str(nav) if rows else None}
    for key in ("stockPct", "cashPct", "bondPct"):
        valid = [(a[key], n) for _, a, n in rows if a[key] is not None]
        denominator = sum((n for _, n in valid), D(0))
        output[key] = (
            str(sum((D(v) * n for v, n in valid), D(0)) / denominator) if denominator else None
        )
        output[key + "Count"] = len(valid)
    return output


def industry_rows(docs, stamp):
    result = defaultdict(lambda: {"numerator": D(0), "fundCount": 0})
    denominator = D(0)
    valid = 0
    for doc in docs:
        row, nav = period(doc, "industries", stamp), portfolio_nav(doc, stamp)
        allocation = period(doc, "allocations", stamp)
        if (
            not row
            or not row["rows"]
            or not nav
            or not allocation
            or allocation["stockPct"] is None
        ):
            continue
        if any(x["weightPct"] is None for x in row["rows"]):
            continue
        total = sum((D(x["weightPct"]) for x in row["rows"]), D(0))
        if abs(total - D(allocation["stockPct"])) > 1:
            continue
        denominator += nav
        valid += 1
        for item in row["rows"]:
            name = (
                HK_INDUSTRIES.get(item["code"], item["name"])
                if item["market"] == "HK"
                else item["name"]
            )
            key = (item["market"], item["code"], name)
            result[key]["numerator"] += D(item["weightPct"]) * nav
            result[key]["fundCount"] += 1
    return (
        [
            {
                "market": market,
                "code": code,
                "name": name,
                "weightPct": str(value["numerator"] / denominator),
                "fundCount": value["fundCount"],
                "sampleCount": valid,
            }
            for (market, code, name), value in result.items()
        ]
        if denominator
        else []
    )


def aggregate(docs, stamp):
    prior = previous_quarter(stamp)
    eligible = [d for d in docs if portfolio_nav(d, stamp) and period(d, "allocations", stamp)]
    common = [d for d in eligible if portfolio_nav(d, prior) and period(d, "allocations", prior)]
    current, previous = summary(common, stamp), summary(common, prior)
    result = summary(eligible, stamp)
    result.update(
        {
            "commonCount": len(common),
            "stockChangePp": subtract(current["stockPct"], previous["stockPct"]),
            "navChangePct": pct(
                subtract(current["navYuan"], previous["navYuan"]), previous["navYuan"]
            ),
        }
    )
    # Changes in industry weights use exactly the same legal portfolios.
    industry_common = [d for d in common if industry_rows([d], stamp) and industry_rows([d], prior)]
    current_industry = industry_rows(eligible, stamp)
    ci = {(r["market"], r["code"]): r for r in industry_rows(industry_common, stamp)}
    pi = {(r["market"], r["code"]): r for r in industry_rows(industry_common, prior)}
    for row in current_industry:
        key = row["market"], row["code"]
        # Absent industries are known zeros only when both complete industry
        # tables reconcile to the same sample's reported equity allocation.
        row["changePp"] = (
            subtract(ci.get(key, {}).get("weightPct", "0"), pi.get(key, {}).get("weightPct", "0"))
            if industry_common
            else None
        )
        row["commonCount"] = len(industry_common)
    current_industry.sort(key=lambda r: D(r["weightPct"]), reverse=True)
    stocks = {}
    held = 0
    for doc in eligible:
        positions = top_ten(period(doc, "holdings", stamp))
        if not positions:
            continue
        held += 1
        previous_positions = {
            (r["market"], r["code"]): r for r in top_ten(period(doc, "holdings", prior))
        }
        for row in positions:
            key = row["market"], row["code"]
            stock = stocks.setdefault(
                key,
                {
                    "market": row["market"],
                    "code": row["code"],
                    "name": row["name"],
                    "value": D(0),
                    "shares": D(0),
                    "fundCount": 0,
                    "comparableCount": 0,
                    "previousShares": D(0),
                    "currentShares": D(0),
                },
            )
            stock["value"] += D(row["valueYuan"])
            if row["shares"] is not None:
                stock["shares"] += D(row["shares"])
            stock["fundCount"] += 1
            before = previous_positions.get(key)
            if before and before["shares"] is not None and row["shares"] is not None:
                stock["comparableCount"] += 1
                stock["previousShares"] += D(before["shares"])
                stock["currentShares"] += D(row["shares"])
    leaders = []
    for stock in stocks.values():
        leaders.append(
            {
                k: v
                for k, v in stock.items()
                if k not in {"value", "shares", "previousShares", "currentShares"}
            }
            | {
                "valueYuan": str(stock["value"]),
                "shares": str(stock["shares"]),
                "shareChangePct": pct(
                    stock["currentShares"] - stock["previousShares"], stock["previousShares"]
                ),
            }
        )
    leaders.sort(key=lambda r: D(r["valueYuan"]), reverse=True)
    return {
        "summary": result,
        "industries": current_industry,
        "stocks": leaders,
        "holdingFundCount": held,
    }


def publish_overview():
    universe = read("universe")
    documents = []
    legal_names = set()
    funds = []
    for entry in universe.get("rows", []):
        doc = read("funds/" + entry["code"])
        data = doc.get("data", {})
        profile = data.get("profile", {})
        if not profile.get("legalName") or not data.get("allocations"):
            continue
        # Legal names sometimes carry a class suffix in source presentation.
        legal_name = profile["legalName"]
        if legal_name in legal_names:
            continue
        legal_names.add(legal_name)
        documents.append(doc)
        latest = max(data["allocations"], key=lambda r: r["date"])
        funds.append(
            {
                **entry,
                **profile,
                **latest,
                "status": doc["status"],
                "aggregateEligible": portfolio_nav(doc, latest["date"]) is not None,
            }
        )
    target = expected_period()
    dates = sorted(
        {r["date"] for d in documents for r in d["data"]["allocations"] if r["date"] <= target},
        reverse=True,
    )[:12]
    # Publish the latest expected report even during its disclosure window.
    # Older data must not masquerade as the current quarter.
    if target not in dates:
        dates.insert(0, target)
    periods = {stamp: aggregate(documents, stamp) for stamp in dates}
    progress = read("progress")
    write(
        "overview",
        {
            "generatedAt": datetime.now(UTC).isoformat(),
            "expectedPeriod": target,
            "source": "天天基金公开基金档案（第三方整理）",
            "universeStatus": universe.get("status", "no_data"),
            "expectedCount": len(universe.get("rows", [])),
            "collectedCount": len(documents),
            "attemptedCount": len(progress.get("funds", {})),
            "readyCount": sum(d["status"] == "ready" for d in documents),
            "funds": funds,
            "dates": dates,
            "periods": periods,
            "history": [summary(documents, stamp) for stamp in reversed(dates)],
        },
    )


def overview(stamp=None):
    doc = read("overview")
    if not doc:
        return {
            "status": "no_data",
            "collectionStatus": "paused" if COLLECTION_PAUSED else "active",
            "expectedPeriod": expected_period(),
            "funds": [],
            "dates": [],
            "history": [],
        }
    stamp = stamp or doc["expectedPeriod"]
    if stamp not in doc["periods"]:
        raise ValueError("report period not available")
    old = (datetime.now(UTC) - datetime.fromisoformat(doc["generatedAt"])).total_seconds() > 172800
    result = {k: v for k, v in doc.items() if k != "periods"}
    result["collectionStatus"] = "paused" if COLLECTION_PAUSED else "active"
    result.update(doc["periods"][stamp])
    result["date"] = stamp
    result["status"] = (
        "stale"
        if old or doc["universeStatus"] != "ready"
        else "partial"
        if doc["collectedCount"] < doc["expectedCount"]
        or doc["readyCount"] < doc["expectedCount"]
        or result["summary"]["fundCount"] < doc["collectedCount"]
        else "ready"
    )
    return result


def detail(code):
    import re

    if not re.fullmatch(r"\d{6}", code):
        raise ValueError("invalid fund code")
    doc = read("funds/" + code)
    if not doc:
        raise KeyError(code)
    data = doc.get("data", {})
    holdings = []
    for report in data.get("holdings", []):
        before = period(doc, "holdings", previous_quarter(report["date"]))
        prior = {(r["market"], r["code"]): r for r in before.get("rows", [])} if before else {}
        rows = []
        for row in report["rows"]:
            old = prior.get((row["market"], row["code"]))
            rows.append(
                {
                    **row,
                    "shareChangePct": pct(subtract(row["shares"], old["shares"]), old["shares"])
                    if old
                    else None,
                    "valueChangePct": pct(
                        subtract(row["valueYuan"], old["valueYuan"]), old["valueYuan"]
                    )
                    if old
                    else None,
                    "comparison": "comparable"
                    if old
                    else "newly_disclosed"
                    if before
                    else "no_previous",
                }
            )
        holdings.append({**report, "rows": rows})
    stale = (
        doc.get("attemptedAt")
        and (datetime.now(UTC) - datetime.fromisoformat(doc["attemptedAt"])).total_seconds()
        > 691200
    )
    return {
        **doc,
        "status": "stale" if stale else doc.get("status", "partial"),
        "data": {**data, "holdings": holdings},
    }
