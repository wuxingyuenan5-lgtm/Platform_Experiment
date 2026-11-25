"""Five-session stock and industry returns from aligned, locally archived closes."""

import json
from collections import defaultdict

from app.data_audit_calendar import calendar_snapshot
from app.research_equity_metrics import number


def add_industry_comparisons(db, stocks, end):
    if not end or not stocks:
        return
    calendar = calendar_snapshot(db, end)
    days = [d for d in calendar["days"] if d <= end][-6:] if calendar else []
    if len(days) != 6 or days[-1] != end:
        return
    codes = {row.get("code") for row in stocks if row.get("history_date") == end}
    membership = db.execute(
        "SELECT payload_json FROM research_a_share_dataset_snapshots WHERE dataset='memberships'"
    ).fetchone()
    if not codes or not membership:
        return
    assigned = defaultdict(list)
    for item in json.loads(membership[0]):
        if (
            item["securityCode"] in codes
            and item["effectiveFrom"] <= days[0]
            and (not item.get("effectiveTo") or end < item["effectiveTo"])
        ):
            assigned[item["securityCode"]].append(item)
    benchmarks = defaultdict(lambda: defaultdict(set))
    for row in db.execute(
        """SELECT instrument_code,trade_date,close,quality_status
           FROM research_a_share_price_history
           WHERE instrument_code LIKE '%.SWI' AND trade_date BETWEEN ? AND ?""",
        (days[0], end),
    ):
        benchmarks[row[0]][row[1]].add(number(row[2]) if row[3] == "ready" else None)
    if not benchmarks:
        return
    prices = defaultdict(dict)
    for code, day, payload in db.execute(
        """SELECT entity_code,observed_at,payload_json FROM research_a_share_history
           WHERE dataset='stock' AND observed_at BETWEEN ? AND ?""",
        (days[0], end),
    ):
        if code in assigned:
            prices[code][day] = number(json.loads(payload).get("close"))
    for stock in stocks:
        code = stock.get("code")
        if stock.get("history_date") != end or len(assigned[code]) != 1:
            continue
        member = assigned[code][0]
        for level in ("L2", "L1"):
            symbol = str(member.get("sw" + level + "Code") or "") + ".SWI"
            if symbol in benchmarks:
                break
        else:
            continue
        curve = []
        for day in days:
            closes = benchmarks[symbol][day]
            stock_close = prices[code].get(day)
            index_close = next(iter(closes)) if len(closes) == 1 else None
            if not stock_close or stock_close <= 0 or not index_close or index_close <= 0:
                break
            if not curve:
                stock_base, index_base = stock_close, index_close
            curve.append(
                {
                    "date": day,
                    "stock": stock_close / stock_base * 100,
                    "industry": index_close / index_base * 100,
                }
            )
        if len(curve) == len(days):
            stock["relative_5d_pp"] = float(curve[-1]["stock"] - curve[-1]["industry"])
            stock["industryComparison"] = {
                "code": symbol,
                "name": member["sw" + level + "Name"],
                "points": [
                    {**p, "stock": str(p["stock"]), "industry": str(p["industry"])} for p in curve
                ],
            }
