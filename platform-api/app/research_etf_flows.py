"""Read-only, dated ETF flow attribution from the native fund archive."""

from datetime import date
from decimal import Decimal

from app.research_etf_native import read
from app.research_etf_tracking import number, read as read_tracking

YI = Decimal(100000000)


def text(value):
    return str(value) if value is not None else None


def window(rows, sessions, start, end, listing):
    days = [d for d in sessions if start <= d <= end and (not listing or d >= listing)]
    values = [number(rows.get(d, {}).get("flowYi")) for d in days]
    available = [v for v in values if v is not None]
    prior = max((d for d in sessions if d < start), default=None)
    base = rows.get(prior, {})
    shares, nav = number(base.get("shares")), number(base.get("unitNav"))
    scale = shares * nav / YI if shares is not None and nav is not None else None
    if listing and listing >= start:
        scale = Decimal(0)
    complete = bool(days) and len(available) == len(days)
    # A fund not yet listed contributes no flow, not a missing observation.
    if listing and listing > end:
        complete = True
    return {
        "flow": text(sum(available, Decimal(0))) if available else ("0" if complete else None),
        "expected": len(days), "covered": len(available), "complete": complete,
        "scale": text(scale), "baselineDate": prior,
    }


def aggregate(items):
    result = {}
    for key in ("current", "previous"):
        periods = [f[key] for f in items]
        values = [number(p["flow"]) for p in periods]
        scales = [number(p["scale"]) for p in periods]
        complete = bool(periods) and all(p["complete"] for p in periods)
        flow = sum((v for v in values if v is not None), Decimal(0)) if any(v is not None for v in values) else None
        scale = sum(scales, Decimal(0)) if scales and all(v is not None for v in scales) else None
        result[key] = {
            "flow": text(flow), "scale": text(scale), "complete": complete,
            "covered": sum(p["covered"] for p in periods),
            "expected": sum(p["expected"] for p in periods),
            "ratio": text(flow / scale * 100) if complete and flow is not None and scale is not None and scale > 0 else None,
        }
    before, after = result["previous"], result["current"]
    b, a = number(before["flow"]), number(after["flow"])
    result["recovery"] = text(a / abs(b) * 100) if before["complete"] and after["complete"] and b is not None and b < 0 and a is not None and a > 0 else None
    result["count"] = len(items)
    return result


def flow_analysis(start=None, end=None, previous_start=None, previous_end=None, days=20):
    state = read("refresh")
    catalog = state.get("catalog", [])
    documents = {m["code"]: read("funds/" + m["code"]) for m in catalog}
    histories = {code: {r["date"]: r for r in doc.get("rows", [])} for code, doc in documents.items()}
    sessions = sorted(set(state.get("sessions", [])) | {d for rows in histories.values() for d in rows})
    if not sessions:
        return {"status": "no_data", "funds": [], "groups": [], "assets": [], "sessions": []}
    end = end or sessions[-1]
    eligible = [d for d in sessions if d <= end]
    if not eligible:
        raise ValueError("所选结束日期早于已存历史")
    start = start or eligible[max(0, len(eligible) - days)]
    for value in (start, end, previous_start, previous_end):
        if value is not None:
            date.fromisoformat(value)
    if start > end or end > sessions[-1] or start < sessions[0]:
        raise ValueError("观察期起止日期须在已存历史范围内")
    previous = [d for d in sessions if d < start]
    length = len([d for d in eligible if d >= start])
    if not length or not previous:
        raise ValueError("所选区间缺少观察日或比较期")
    previous_end = previous_end or (previous[-1] if previous else start)
    previous_start = previous_start or (previous[max(0, len(previous) - length)] if previous else start)
    for value in (start, end, previous_start, previous_end):
        date.fromisoformat(value)
    if start > end or previous_start > previous_end or previous_end >= start:
        raise ValueError("比较期须在观察期之前，且起止日期有效")
    listing = read("listing").get("dates", {})
    old = {m["code"]: m for m in read_tracking("universe").get("data", [])}
    funds = []
    for meta in catalog:
        code = meta["code"]
        tracked = old.get(code, {})
        group = meta.get("category") or tracked.get("display_group") or "未分类"
        asset = "股票宽基" if meta.get("category") else "跨境" if group == "跨境/海外" else "行业与策略"
        rows = histories[code]
        periods = {
            "current": window(rows, sessions, start, end, listing.get(code)),
            "previous": window(rows, sessions, previous_start, previous_end, listing.get(code)),
        }
        funds.append({
            "code": code, "name": meta["name"], "group": group, "asset": asset,
            **aggregate([periods]),
            "sourceDate": max((d for d, r in rows.items() if number(r.get("flowYi")) is not None), default=None),
            "sourceStatus": documents[code].get("status", "unavailable"),
            "sourceUrls": documents[code].get("sourceUrls", []),
            "reportDate": tracked.get("latest_report_date"),
            "holdingRatio": tracked.get("latest_combined_ratio_pct"),
            "holdingValue": tracked.get("latest_combined_value_yi"),
        })
    def grouped(field):
        return [{"name": name, **aggregate([f for f in funds if f[field] == name])}
                for name in sorted({f[field] for f in funds})]
    return {
        "status": "ready" if all(f["current"]["complete"] for f in funds) else "partial",
        "date": sessions[-1], "retrievedAt": state.get("retrievedAt"),
        "start": start, "end": end, "previousStart": previous_start, "previousEnd": previous_end,
        "sessions": sessions, "funds": funds, "groups": grouped("group"), "assets": grouped("asset"),
        "summary": aggregate(funds),
        "source": "沪深交易所份额 × 基金公开单位净值；平台原始日度归档",
        "scope": "平台已跟踪ETF样本，非全市场；无债券、货币、商品ETF完整资金流与全量前十大持有人数据。",
    }
