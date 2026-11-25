"""Broad-universe daily turnover and ratios; the minute basket stays independent."""

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from statistics import median

from app.research_local_data import write_local_json

YI = Decimal(100000000)
INNOVATION = ("159915", "588000", "159949", "588080", "159952")


def complete_sum(values):
    if not values or any(v is None for v in values):
        return None
    try:
        parsed = [Decimal(str(v)) for v in values]
        return sum(parsed, Decimal(0)) if all(v.is_finite() for v in parsed) else None
    except (InvalidOperation, ValueError, TypeError):
        return None


def amount_value(value):
    """A published zero is valid; absent, negative and non-finite inputs are not."""
    result = complete_sum([value])
    return result if result is not None and result >= 0 else None


def available_sum(values):
    valid = [value for value in values if value is not None]
    return sum(valid, Decimal(0)) if valid else None


def cash_total(broad, i):
    groups = broad.get("coverage", {}).get(broad["dates"][i], {})
    if groups and not any(g.get("covered", 0) > 0 for g in groups.values()):
        return None
    return available_sum(
        [complete_sum([broad.get("series", {}).get(cat, [])[i]]) for cat in broad.get("cats", [])]
    )


def merge_rows(previous, dates, members, markets, funds, listing_dates=None):
    listing_dates = listing_dates or {}
    rows = {row["date"]: row for row in previous}
    for day in dates:
        codes = sorted(
            {c for c in members.get(day, []) if not listing_dates.get(c) or day >= listing_dates[c]}
        )
        amounts = {c: amount_value(markets.get(c, {}).get(day, {}).get("amount")) for c in codes}
        total = available_sum(amounts.values())
        selected_codes = [c for c in INNOVATION if c in amounts]
        selected = (
            available_sum([amounts[c] for c in selected_codes]) if selected_codes else Decimal(0)
        )
        cash_values = [
            complete_sum([funds.get(c, {}).get(day, {}).get("flowYi")]) for c in selected_codes
        ]
        selected_cash = available_sum(cash_values) if selected_codes else Decimal(0)
        missing = [c for c, value in amounts.items() if value is None]
        rows[day] = {
            "date": day,
            "amountYi": str(total / YI) if total is not None else None,
            "selectedAmountYuan": str(selected) if selected is not None else None,
            "selectedNetFlowYi": str(selected_cash) if selected_cash is not None else None,
            "expected": len(codes),
            "covered": len(codes) - len(missing),
            "missingCodes": missing,
            "selectedExpected": len(selected_codes),
            "selectedCovered": sum(amounts[c] is not None for c in selected_codes),
            "selectedCashCovered": sum(v is not None for v in cash_values),
            "status": "partial" if missing else "ready" if codes else "unavailable",
        }
    return [rows[day] for day in sorted(rows)]


def quality_snapshot(catalog, rows, market_docs, fund_docs, listing_dates, failures=()):
    """Compact producer-side evidence; the audit never scans full quote histories."""
    day = rows[-1]["date"] if rows else None
    missing = {m["code"]: [] for m in catalog}
    for row in rows:
        for code in row.get("missingCodes", []):
            if code in missing:
                missing[code].append(row["date"])
    failed = {f.get("source"): f.get("error") for f in failures}
    members = []
    for meta in catalog:
        code, symbol = meta["code"], meta["symbol"]
        market = market_docs.get(code, {})
        quotes = {r["date"]: r for r in market.get("rows", [])}
        fund = fund_docs.get(code, {})
        cash = {r["date"]: r for r in fund.get("rows", [])}
        members.append(
            {
                "code": code,
                "name": meta["name"],
                "listingDate": listing_dates.get(code),
                "sourceDate": max(quotes, default=None),
                "expectedDate": day,
                "turnoverReady": amount_value(quotes.get(day, {}).get("amount")) is not None,
                "flowReady": complete_sum([cash.get(day, {}).get("flowYi")]) is not None,
                "missingDates": missing[code],
                "sourceUrl": market.get("sourceUrl"),
                "sourceRetrievedAt": market.get("retrievedAt"),
                "sourceError": failed.get(symbol) or failed.get(code),
            }
        )
    return {
        "updatedAt": datetime.now(UTC).isoformat(),
        "sourceDate": day,
        "catalogCodes": [m["code"] for m in catalog],
        "members": members,
        "missingRegisteredCodes": sorted(set(listing_dates) - {m["code"] for m in catalog}),
        "historyDates": len(rows),
        "partialDates": sum(r.get("status") == "partial" for r in rows),
        "missingInputs": sum(len(dates) for dates in missing.values()),
    }


def refresh_projection(catalog, sessions, shares, failures=()):
    from app.research_etf_native import read

    selected = [m for m in catalog if m.get("category")]
    codes = [m["code"] for m in selected]
    market_docs = {m["code"]: read("market/" + m["symbol"]) for m in selected}
    fund_docs = {code: read("funds/" + code) for code in codes}
    markets = {
        code: {r["date"]: r for r in doc.get("rows", [])} for code, doc in market_docs.items()
    }
    funds = {code: {r["date"]: r for r in doc.get("rows", [])} for code, doc in fund_docs.items()}
    listing_dates = read("listing").get("dates", {})
    members = {
        day: [
            code
            for code in codes
            if Decimal(str(shares.get(day, {}).get(code, 0))) > 0
            or (
                code not in shares.get(day, {})
                and Decimal(str(shares.get(sessions[i - 1], {}).get(code, 0))) > 0
            )
        ]
        for i, day in enumerate(sessions[1:], 1)
    }
    old = read("broad-observation")
    rows = merge_rows(old.get("rows", []), sessions[1:], members, markets, funds, listing_dates)
    write_local_json(
        "public/v1/etf-native/broad-observation.json",
        {
            "rows": rows,
            "catalogCodes": codes,
            "scope": "tracked_broad_etfs",
            "method": "sum_native_daily_turnover_and_fixed_innovation_numerator",
        },
    )
    write_local_json(
        "public/v1/etf-native/broad-quality.json",
        quality_snapshot(selected, rows, market_docs, fund_docs, listing_dates, failures),
    )


def project(reference, observation):
    broad = reference.get("broadData", {})
    dates = broad.get("dates", [])
    amounts = {r["date"]: r for r in observation.get("rows", [])}
    prices = {
        r["date"]: r.get("close")
        for r in reference.get("indexPrices", {}).get("hs300", {}).get("rows", [])
    }
    points, ratios = [], []
    for i, day in enumerate(dates):
        total = cash_total(broad, i)
        source = amounts.get(day, {})
        amount = source.get("amountYi")
        quality_note = (
            (
                f"成交额覆盖 {source.get('covered', 0)}/{source.get('expected', 0)} 只，"
                "按已取得成员汇总；缺失："
                + "、".join(source.get("missingCodes", []))
            )
            if source.get("status") == "partial"
            else ""
        )
        cash_coverage = broad.get("coverage", {}).get(day, {})
        cash_missing = [
            c for group in cash_coverage.values() for c in group.get("missingCodes", [])
        ]
        cash_note = (
            ("净申购按已取得成员汇总；缺失：" + "、".join(cash_missing)) if cash_missing else ""
        )
        points.append(
            {
                "date": day,
                "amount": float(amount) if amount is not None else None,
                "netflow": float(total) if total is not None else None,
                "idx": prices.get(day),
                "qualityNote": quality_note,
            }
        )
        cash, turnover = source.get("selectedNetFlowYi"), source.get("selectedAmountYuan")
        ratios.append(
            {
                "date": day,
                "netSubscriptionPct": str(Decimal(cash) / total * 100)
                if cash is not None and total
                else None,
                "turnoverPct": str(Decimal(turnover) / (Decimal(amount) * YI) * 100)
                if turnover is not None and amount is not None and Decimal(amount) > 0
                else None,
                "selectedNetFlowYi": cash,
                "basketNetFlowYi": str(total) if total is not None else None,
                "selectedAmountYuan": turnover,
                "basketAmountYuan": str(Decimal(amount) * YI) if amount is not None else None,
                "expected": source.get("expected"),
                "covered": source.get("covered"),
                "missingCodes": source.get("missingCodes", []),
                "qualityNote": "；".join(note for note in (quality_note, cash_note) if note),
            }
        )
    valid = [r for r in points if r["netflow"] is not None]
    support = [
        r
        for r in valid
        if r["netflow"] > 100
        and not (
            "2024-09-24" <= r["date"] <= "2024-10-18"
            or "2026-01-14" <= r["date"] <= "2026-01-30"
            or r["date"] in {"2026-02-02", "2026-02-13", "2026-02-26"}
        )
    ]
    return {
        "broadDailyData": {
            "dates": dates,
            **{
                key: [r[key] for r in points] for key in ("amount", "netflow", "idx", "qualityNote")
            },
        },
        "broadInnovationRatio": {"rows": ratios, "innovationCodes": list(INNOVATION)},
        "broadCmpData": {
            "support": support,
            "recent": points[-20:],
            "today": points[-1] if points else {},
            "latest": valid[-1] if valid else {},
            "sample": {
                "n": len(support),
                "amtMed": median(r["amount"] for r in support)
                if support and all(r["amount"] is not None for r in support)
                else None,
            },
        },
    }
