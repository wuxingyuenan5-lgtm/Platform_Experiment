"""SEC company-facts accounting, with explicit periods and no YTD-as-quarter error."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from app.research_ai_catalog import INSTANT_METRICS, METRICS


def number(value):
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def span(start, end):
    return (date.fromisoformat(end) - date.fromisoformat(start)).days + 1


def source(row, tag, basis="reported", previous=None):
    return {
        "tag": tag,
        "filed": row.get("filed"),
        "accn": row.get("accn"),
        "basis": basis,
        **({"baseAccn": previous.get("accn"), "baseEnd": previous["end"]} if previous else {}),
    }


def native_rows(facts, tag, today):
    """Only USD, issuer-wide SEC facts and already filed observations."""
    rows = facts.get("us-gaap", {}).get(tag, {}).get("units", {}).get("USD", [])
    picked = {}
    for row in rows:
        if row.get("form") not in ("10-K", "10-Q", "10-K/A", "10-Q/A"):
            continue
        if row.get("filed", "9999") > today or row.get("end", "9999") > today:
            continue
        value = number(row.get("val"))
        if value is None:
            continue
        key = (row.get("start"), row["end"])
        old = picked.get(key)
        if old is None or (row.get("filed", ""), row.get("accn", "")) > (
            old.get("filed", ""),
            old.get("accn", ""),
        ):
            picked[key] = {**row, "val": value}
    return list(picked.values())


def duration_values(facts, tags, today):
    quarters, annuals = {}, {}
    for tag in reversed(tags):
        rows = [row for row in native_rows(facts, tag, today) if row.get("start")]
        direct, derived = {}, {}
        for row in rows:
            days = span(row["start"], row["end"])
            point = {
                "start": row["start"],
                "end": row["end"],
                "value": row["val"],
                "source": source(row, tag),
            }
            if 60 <= days <= 115:
                direct[row["end"]] = point
            if 330 <= days <= 385:
                annuals[(row["start"], row["end"])] = point
            if days <= 115 or days > 385:
                continue
            bases = [
                base
                for base in rows
                if base["start"] == row["start"]
                and base["end"] < row["end"]
                and 60
                <= (date.fromisoformat(row["end"]) - date.fromisoformat(base["end"])).days
                <= 115
            ]
            if bases:
                previous = max(bases, key=lambda item: item["end"])
                derived[row["end"]] = {
                    "start": (date.fromisoformat(previous["end"]) + timedelta(days=1)).isoformat(),
                    "end": row["end"],
                    "value": row["val"] - previous["val"],
                    "source": source(row, tag, "cumulative_difference", previous),
                }
        # Prefer a directly reported quarter to a difference in the same taxonomy.
        quarters.update({**derived, **direct})
    return quarters, annuals


def instant_values(facts, tags, today):
    result = {}
    for tag in reversed(tags):
        for row in native_rows(facts, tag, today):
            if not row.get("start"):
                result[row["end"]] = {"value": row["val"], "source": source(row, tag)}
    return result


def ratio(numerator, denominator, multiplier=100):
    return (
        numerator / denominator * multiplier
        if numerator is not None and denominator is not None and denominator > 0
        else None
    )


def derived_fields(row):
    values = row["values"]

    def both(a, b, fn):
        return (
            fn(values[a], values[b])
            if values.get(a) is not None and values.get(b) is not None
            else None
        )

    values["fcf"] = both("cfo", "capex", lambda a, b: a - b)
    values["grossMargin"] = ratio(values.get("grossProfit"), values.get("revenue"))
    values["operatingMargin"] = ratio(values.get("operatingIncome"), values.get("revenue"))
    values["fcfMargin"] = ratio(values.get("fcf"), values.get("revenue"))
    values["capexRevenue"] = ratio(values.get("capex"), values.get("revenue"))
    values["capexCfo"] = ratio(values.get("capex"), values.get("cfo"))
    values["sbcRevenue"] = ratio(values.get("sbc"), values.get("revenue"))
    values["rdRevenue"] = ratio(values.get("rd"), values.get("revenue"))
    values["interestCoverage"] = ratio(values.get("operatingIncome"), values.get("interest"), 1)
    # Lease additions are shown separately, never silently added to cash capex.
    values["daRevenue"] = ratio(values.get("da"), values.get("revenue"))
    return row


def trailing(rows, end_index):
    block = rows[max(0, end_index - 3) : end_index + 1]
    if len(block) != 4 or not 330 <= span(block[0]["start"], block[-1]["end"]) <= 385:
        return None
    if any(
        date.fromisoformat(b["start"]) != date.fromisoformat(a["end"]) + timedelta(days=1)
        for a, b in zip(block, block[1:], strict=False)
    ):
        return None
    values = {}
    for metric in METRICS:
        points = [row["values"].get(metric) for row in block]
        values[metric] = (
            sum(points, Decimal(0)) if all(value is not None for value in points) else None
        )
    result = derived_fields({"start": block[0]["start"], "end": block[-1]["end"], "values": values})
    return result


def build_company(document, company, today=None):
    today = today or date.today().isoformat()
    ticker, cik, name, sector, token = company
    if int(document.get("cik", -1)) != cik or token not in document.get("entityName", "").upper():
        raise ValueError("SEC issuer identity mismatch: " + ticker)
    facts = document["facts"]
    durations = {key: duration_values(facts, spec[1], today) for key, spec in METRICS.items()}
    # Constellation reports non-contract (including derivative) revenue too.
    # Its contract-only taxonomy is a component, not consolidated revenue.
    if ticker == "CEG":
        durations["revenue"] = duration_values(
            facts, ["Revenues", "RevenueFromContractWithCustomerIncludingAssessedTax"], today
        )
    balances = {key: instant_values(facts, spec[1], today) for key, spec in INSTANT_METRICS.items()}
    anchors = durations["revenue"][0]
    rows = []
    for end, anchor in sorted(anchors.items()):
        if end < "2012-01-01":
            continue
        row = {"start": anchor["start"], "end": end, "date": end, "values": {}, "provenance": {}}
        for metric, (quarter, _) in durations.items():
            point = quarter.get(end)
            if point and point["start"] == anchor["start"]:
                row["values"][metric] = point["value"]
                row["provenance"][metric] = point["source"]
            else:
                row["values"][metric] = None
        row["balance"] = {key: points.get(end, {}).get("value") for key, points in balances.items()}
        row["balanceProvenance"] = {
            key: points[end]["source"] for key, points in balances.items() if end in points
        }
        row["filed"] = max((p["filed"] or "" for p in row["provenance"].values()), default=None)
        rows.append(derived_fields(row))
    for i, row in enumerate(rows):
        row["ttm"] = trailing(rows, i)
        row["yoy"] = {}
        previous = rows[i - 4] if i >= 4 else None
        for metric in ("revenue", "capex", "cfo", "rpo"):
            if metric == "rpo":
                current = row["balance"].get(metric)
                base = previous["balance"].get(metric) if previous else None
            else:
                current = row["values"].get(metric)
                base = previous["values"].get(metric) if previous else None
            comparable = (
                previous
                and 350
                <= (date.fromisoformat(row["end"]) - date.fromisoformat(previous["end"])).days
                <= 380
            )
            row["yoy"][metric] = (
                ratio(current - base, base)
                if comparable and current is not None and base is not None
                else None
            )
    annual = []
    for key in sorted(durations["revenue"][1]):
        if key[1] < "2012-01-01":
            continue
        item = {"start": key[0], "end": key[1], "values": {}, "provenance": {}}
        for metric, (_, points) in durations.items():
            point = points.get(key)
            item["values"][metric] = point["value"] if point else None
            if point:
                item["provenance"][metric] = point["source"]
        annual.append(derived_fields(item))
    if not rows:
        raise ValueError("No valid USD quarterly revenue: " + ticker)
    latest = rows[-1]
    return {
        "ticker": ticker,
        "cik": cik,
        "name": name,
        "sector": sector,
        "sourceUrl": f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json",
        "filingsUrl": f"https://www.sec.gov/edgar/browse/?CIK={cik}&owner=exclude",
        "status": "stale"
        if (date.fromisoformat(today) - date.fromisoformat(latest["end"])).days > 180
        else "ready",
        "periodEnd": latest["end"],
        "latest": latest,
        "quarters": rows,
        "annual": annual,
        "crossChecks": [],
        "methodology": "sec-us-gaap-usd-latest-vintage-v2",
    }


def summary(company):
    return {key: value for key, value in company.items() if key not in ("quarters", "annual")}
