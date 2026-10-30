"""Read-only projections of locally retained Chinese financing/derivative data."""

from collections import defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.research_etf_tracking import INDICES, detail, index_key, number, read
from app.research_local_data import read_local_json
from app.research_provider_errors import ResearchProviderError


def local(path):
    try:
        return read_local_json(path)
    except ResearchProviderError:
        return {}


def weekly_summary(members, index_rows):
    """Calendar weeks, no filling, no silent partial sum; current week retained."""
    calendar = sorted({r["date"] for r in index_rows})
    weeks = defaultdict(list)
    for day in calendar:
        d = date.fromisoformat(day)
        weeks[(d - timedelta(days=d.weekday())).isoformat()].append(day)
    by_fund = [{r["date"]: r for r in m["series"]} for m in members]
    prices = {r["date"]: r.get("close") for r in index_rows}
    previous_close = {day: prices[calendar[i - 1]] if i else None for i, day in enumerate(calendar)}
    result = []
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    for week, days in sorted(weeks.items()):
        row = {
            "date": days[-1],
            "weekStart": week,
            "sessions": len(days),
            "indexClose": prices[days[-1]],
            "funds": [],
            "complete": True,
        }
        total = 0
        turnover_total = 0
        turnover_complete = bool(members)
        for member, lookup in zip(members, by_fund, strict=True):
            # No pre-inception zeros and no substitution of a partial week's sum.
            values = [number(lookup.get(d, {}).get("flow_yi")) for d in days]
            value = sum(values) if all(v is not None for v in values) else None
            turnovers = [number(lookup.get(d, {}).get("etf_qfq_turnover_est_yi")) for d in days]
            turnover = sum(turnovers) if all(v is not None for v in turnovers) else None
            turnover_complete &= turnover is not None
            if turnover is not None:
                turnover_total += turnover
            row["funds"].append(
                {
                    "code": member["meta"]["code"],
                    "name": member["meta"]["name"],
                    "value": str(value) if value is not None else None,
                    "coveredSessions": sum(v is not None for v in values),
                    "turnoverYi": str(turnover) if turnover is not None else None,
                }
            )
            row["complete"] &= value is not None
            if value is not None:
                total += value
        row["total"] = str(total) if row["complete"] and members else None
        row["turnoverYi"] = str(turnover_total) if turnover_complete else None
        first, last = number(previous_close[days[0]]), number(row["indexClose"])
        row["indexReturnPct"] = (
            str((last / first - 1) * 100) if first and first > 0 and last is not None else None
        )
        row["partialWeek"] = week == (today - timedelta(days=today.weekday())).isoformat()
        result.append(row)
    return result


def daily_summary(members, index_rows):
    """One row per actual index session; missing fund observations remain NULL."""
    prices = {r["date"]: r.get("close") for r in index_rows}
    by_fund = [{r["date"]: r for r in m["series"]} for m in members]
    result = []
    previous = None

    def total(funds, field):
        values = [number(f[field]) for f in funds]
        return str(sum(values)) if values and all(v is not None for v in values) else None

    for day in sorted(prices):
        funds = []
        for member, lookup in zip(members, by_fund, strict=True):
            row = lookup.get(day, {})
            flow = number(row.get("flow_yi"))
            turnover = number(row.get("etf_qfq_turnover_est_yi"))
            funds.append(
                {
                    "code": member["meta"]["code"],
                    "name": member["meta"]["name"],
                    "value": str(flow) if flow is not None else None,
                    "turnoverYi": str(turnover) if turnover is not None else None,
                }
            )

        close = number(prices[day])
        result.append(
            {
                "date": day,
                "indexClose": prices[day],
                "funds": funds,
                "total": total(funds, "value"),
                "turnoverYi": total(funds, "turnoverYi"),
                "indexReturnPct": str((close / previous - 1) * 100)
                if previous and previous > 0 and close is not None
                else None,
            }
        )
        previous = close
    return result


def broad_etfs(key):
    universe = read("universe").get("data", [])
    candidates = [m for m in universe if m.get("dashboard_eligible") and index_key(m) == key]
    options = [{"key": k, "label": label.removeprefix("宽基/")} for label, k in INDICES.items()]
    if not candidates:
        return {
            "options": options,
            "key": key,
            "weekly": [],
            "daily": [],
            "members": [],
            "status": "no_data",
            "marketCapRatio": {
                "status": "unavailable",
                "rows": [],
                "reason": "此指数暂无已跟踪ETF数据。",
            },
        }
    data = detail(candidates[0]["code"])
    index = read("index-turnover/" + key).get("data", {}).get("rows", [])
    caps = local("public/v1/a-share/etf-market-cap-ratios.json").get("groups", {}).get(key, [])
    return {
        "options": options,
        "key": key,
        "members": [m["meta"] for m in data["members"]],
        "weekly": weekly_summary(data["members"], index),
        "daily": daily_summary(data["members"], index),
        "sources": data["sources"],
        "status": data["sources"]["groupMarket"]["status"],
        "scope": "tracked_etfs_only",
        "flowMethod": "estimated_share_change_times_price",
        "marketCapRatio": {
            "status": "ready" if caps else "unavailable",
            "rows": caps,
            "reason": "同日闭市价格×份额 / 指数流通市值；已归档历史起点：" + caps[0]["date"]
            if caps
            else "同日闭市流通市值尚未采集成功。",
            "numerator": "本页已跟踪ETF：未复权收盘价×实际份额",
            "denominator": "当日指数成分股流通市值合计",
        },
    }


def domestic_financing():
    margin = [
        local(f"public/v1/macro/series/{sid}.json")
        for sid in (
            "cn_margin_total_balance",
            "cn_margin_financing_balance",
            "cn_margin_short_balance",
            "cn_margin_financing_buy",
            "cn_margin_financing_change",
        )
    ]
    futures = local("public/v1/a-share/cffex-contracts.json")
    indices = {
        family: {
            r["date"]: r for r in read("index-turnover/" + key).get("data", {}).get("rows", [])
        }
        for family, key in {"IF": "hs300", "IH": "sse50", "IC": "csi500", "IM": "csi1000"}.items()
    }
    basis = []
    for row in futures.get("rows", []):
        family = row["contract"][:2]
        spot = number(indices.get(family, {}).get(row["date"], {}).get("close"))
        close = number(row["close"])
        if spot is None or spot <= 0 or close is None:
            continue
        value = close - spot
        basis.append(
            {
                **row,
                "family": family,
                "spot": str(spot),
                "basis": str(value),
                "basisPct": str(value / spot * 100),
            }
        )
    iv = local("public/v1/a-share/etf-option-iv.json")
    gold_manifest = local("canonical/commodity/shfe_gold_iv.json")
    gold = [
        local(f"public/v1/commodity/series/{sid}.json")
        for sid in gold_manifest.get("seriesIds", [])
    ]
    return {
        "margin": [s for s in margin if s],
        "basis": basis,
        "futuresSource": {k: v for k, v in futures.items() if k != "rows"},
        "iv": iv,
        "goldIv": [s for s in gold if s],
        "refresh": local("public/v1/a-share/derivatives-refresh.json"),
    }
