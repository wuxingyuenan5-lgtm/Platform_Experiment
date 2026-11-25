"""Read-only projections of locally retained Chinese financing/derivative data."""

from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.research_etf_tracking import INDICES, detail, index_key, number, read
from app.research_local_data import read_local_json
from app.research_provider_errors import ResearchProviderError

ETF_GROUPS = {
    "finance": "金融/稳定权重",
    "technology": "成长/制造/科技",
    "consumer": "消费/医药",
    "resources": "周期/资源",
    "overseas": "跨境/海外",
    "cash": "货币/现金ETF",
    "observation": "观察/非汇金证金主持仓",
    "msci_a50": "宽基/MSCI中国A50",
}


def local(path):
    try:
        return read_local_json(path)
    except ResearchProviderError:
        return {}


def weekly_summary(members, index_rows, index_margin=()):
    return aggregate_weeks(daily_summary(members, index_rows, index_margin))


def daily_summary(members, index_rows, index_margin=()):
    """One row per actual index session; missing fund observations remain NULL."""
    prices = {r["date"]: r.get("close") for r in index_rows}
    by_fund = [{r["date"]: r for r in m["series"]} for m in members]
    margins = [{r["date"]: r for r in m.get("margin", [])} for m in members]
    index_margins = {r["date"]: r for r in index_margin}
    result = []
    previous = None
    previous_units = None

    def total(funds, field):
        values = [number(f[field]) for f in funds]
        return str(sum(values)) if values and all(v is not None for v in values) else None

    for day in sorted(prices):
        funds = []
        for member, lookup, margin in zip(members, by_fund, margins, strict=True):
            row = lookup.get(day, {})
            flow = number(row.get("flow_yi"))
            turnover = number(row.get("etf_qfq_turnover_est_yi"))
            if turnover is None:
                turnover = number(row.get("native_turnover_yi"))
            funds.append(
                {
                    "code": member["meta"]["code"],
                    "name": member["meta"]["name"],
                    "value": str(flow) if flow is not None else None,
                    "turnoverYi": str(turnover) if turnover is not None else None,
                }
            )
            for target, source in (
                ("unitsYi", "qfq_total_units_yi"),
                ("deltaUnitsYi", "qfq_delta_units_yi"),
            ):
                value = number(row.get(source))
                funds[-1][target] = str(value) if value is not None else None
            for target, source in (
                ("financingBalanceYi", "financing_balance_yi"),
                ("financingNetBuyYi", "financing_net_buy_yi"),
            ):
                value = number(margin.get(day, {}).get(source))
                funds[-1][target] = str(value) if value is not None else None

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
        result[-1].update(
            {
                field: total(funds, field)
                for field in ("unitsYi", "deltaUnitsYi", "financingBalanceYi", "financingNetBuyYi")
            }
        )
        result[-1]["previousUnitsYi"] = previous_units
        previous_units = result[-1]["unitsYi"]
        source = index_margins.get(day, {})
        for target, field in (
            ("indexFinancingBalanceYi", "index_financing_balance_yi"),
            ("indexFinancingNetBuyYi", "index_financing_net_buy_yi"),
            ("indexCoveragePct", "index_coverage_pct"),
        ):
            result[-1][target] = source.get(field)
        previous = close
    return result


def aggregate_weeks(daily):
    """Sum flows over every actual session, take stocks only on the last session."""
    weeks = defaultdict(list)
    for row in daily:
        day = date.fromisoformat(row["date"])
        weeks[(day - timedelta(days=day.weekday())).isoformat()].append(row)
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()

    def complete_sum(rows, field):
        values = [number(row.get(field)) for row in rows]
        return (
            str(sum(values, Decimal(0))) if values and all(v is not None for v in values) else None
        )

    result = []
    previous_close = None
    for week, days in sorted(weeks.items()):
        row = {**days[-1], "weekStart": week, "sessions": len(days)}
        row["previousUnitsYi"] = days[0]["previousUnitsYi"]
        for field in (
            "total",
            "turnoverYi",
            "deltaUnitsYi",
            "financingNetBuyYi",
            "indexFinancingNetBuyYi",
        ):
            row[field] = complete_sum(days, field)
        row["funds"] = []
        for i, fund in enumerate(days[-1]["funds"]):
            observations = [day["funds"][i] for day in days]
            value = {**fund, "coveredSessions": sum(r["value"] is not None for r in observations)}
            for field in ("value", "turnoverYi", "deltaUnitsYi", "financingNetBuyYi"):
                value[field] = complete_sum(observations, field)
            row["funds"].append(value)
        close = number(row["indexClose"])
        row["indexReturnPct"] = (
            str((close / previous_close - 1) * 100)
            if previous_close and previous_close > 0 and close is not None
            else None
        )
        row["complete"] = row["total"] is not None
        row["partialWeek"] = week == (today - timedelta(days=today.weekday())).isoformat()
        result.append(row)
        previous_close = close
    return result


def broad_etfs(key, *, days=0, include_history=True):
    universe = read("universe").get("data", [])
    label = ETF_GROUPS.get(key)
    catalog = [
        m for m in universe if (m.get("display_group") == label if label else index_key(m) == key)
    ]
    candidates = [m for m in catalog if m.get("dashboard_eligible")]
    options = [
        {"key": k, "label": name.removeprefix("宽基/"), "kind": "broad"}
        for name, k in INDICES.items()
    ]
    options.extend(
        {"key": k, "label": name, "kind": "sector"}
        for k, name in ETF_GROUPS.items()
        if any(m.get("display_group") == name for m in universe)
    )
    single_funds = [
        {
            "code": m["code"],
            "name": m["name"],
            "group": o["key"],
            "tracked": bool(m.get("dashboard_eligible")),
        }
        for o in options
        for m in universe
        if (
            m.get("display_group") == ETF_GROUPS[o["key"]]
            if o["key"] in ETF_GROUPS
            else index_key(m) == o["key"]
        )
    ]
    from app.research_theme_etfs import reference_funds

    listed = {fund["code"] for fund in single_funds}
    single_funds.extend(
        {**fund, "group": "theme-reference", "tracked": False}
        for fund in reference_funds().values()
        if fund["code"] not in listed
    )
    if not candidates or not include_history:
        return {
            "options": options,
            "singleFunds": single_funds,
            "key": key,
            "weekly": [],
            "daily": [],
            "members": catalog,
            "trackedMemberCount": len(candidates),
            "hasIndex": key in INDICES.values(),
            "status": "no_data",
            "marketCapRatio": {
                "status": "unavailable",
                "rows": [],
                "reason": "此指数暂无已跟踪ETF数据。",
            },
        }
    data = detail(candidates[0]["code"])
    has_index = key in INDICES.values()
    if has_index:
        members = data["members"]
        index = read("index-turnover/" + key).get("data", {}).get("rows", [])
        first_fund_day = min(
            (series[0]["date"] for member in members if (series := member["series"])),
            default=None,
        )
        if first_fund_day:
            index = [row for row in index if row["date"] >= first_fund_day]
    else:
        members = [detail(m["code"], include_group=False) for m in candidates]
        dates = {r["date"] for m in members for r in m["series"]}
        calendar = read("index-turnover/hs300").get("data", {}).get("rows", [])
        sessions = {r["date"] for r in calendar if dates and min(dates) <= r["date"] <= max(dates)}
        index = [{"date": day, "close": None} for day in sorted(dates | sessions)]
        data["groupMargin"] = []
        data["sources"]["groupMarket"] = {
            "status": "ready"
            if all(m["sources"]["market"]["status"] == "ready" for m in members)
            else "stale"
        }
    caps = local("public/v1/a-share/etf-market-cap-ratios.json").get("groups", {}).get(key, [])
    daily = daily_summary(members, index, data["groupMargin"])
    weekly = aggregate_weeks(daily)
    if days and daily:
        from datetime import date, timedelta

        cutoff = (date.fromisoformat(daily[-1]["date"]) - timedelta(days=days)).isoformat()
        daily = [r for r in daily if r["date"] >= cutoff]
        weekly = [r for r in weekly if r["date"] >= cutoff]
        caps = [r for r in caps if r["date"] >= cutoff]
    return {
        "options": options,
        "singleFunds": single_funds,
        "key": key,
        "members": catalog,
        "trackedMemberCount": len(candidates),
        "hasIndex": has_index,
        "weekly": weekly,
        "daily": daily,
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
            "cn_margin_buy_share",
        )
    ]
    futures = local("public/v1/a-share/cffex-contracts.json")
    index_data = {
        key: read("index-turnover/" + key)
        for key in ("hs300", "sse50", "csi500", "csi1000", "star50", "chinext", "sz100")
    }
    indices = {
        family: {
            r["date"]: r for r in index_data[key].get("data", {}).get("rows", [])
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
    index_iv = local("public/v1/a-share/cffex-option-iv.json")
    szse_iv = local("public/v1/a-share/szse-etf-option-iv.json")
    szse_rows = szse_iv.get("rows", []) if szse_iv.get("methodology") == (
        "nearest_delta_half_standard_calls_puts_vega_gamma_iv_252_sessions"
    ) else []
    iv = {**iv, "rows": sorted(
        [*iv.get("rows", []), *index_iv.get("rows", []), *szse_rows],
        key=lambda row: (row["date"], row["underlying"], row["month"]),
    )}
    iv_index_history = local("public/v1/a-share/option-index-history.json").get("indices", {})
    iv_indices = []
    for key, code, name, underlyings in (
        ("sse50", "000016", "上证50", ["510050", "HO"]),
        ("hs300", "000300", "沪深300", ["510300", "159919", "IO"]),
        ("csi500", "000905", "中证500", ["510500", "159922"]),
        ("csi1000", "000852", "中证1000", ["MO"]),
        ("star50", "000688", "科创50", ["588000", "588080"]),
        ("chinext", "399006", "创业板指", ["159915"]),
        ("sz100", "399330", "深证100", ["159901"]),
    ):
        days = {r["date"] for r in iv.get("rows", []) if r["underlying"] in underlyings}
        rows = []
        historical = iv_index_history.get(key, {})
        index_rows = {row['date']: row for row in historical.get('rows', [])}
        index_rows.update({row['date']: row for row in index_data[key].get("data", {}).get("rows", [])})
        for row in index_rows.values():
            if row["date"] not in days:
                continue
            close = number(row.get("close"))
            rows.append({"date": row["date"], "close": str(close) if close and close > 0 else None})
        iv_indices.append({
            "code": code,
            "name": name,
            "underlyings": underlyings,
            "rows": sorted(rows, key=lambda row: row["date"]),
            "sourceUrl": index_data[key].get("url"),
            "historySourceUrl": historical.get("sourceUrl"),
        })
    gold_manifest = local("canonical/commodity/shfe_gold_iv.json")
    gold = [
        local(f"public/v1/commodity/series/{sid}.json")
        for sid in gold_manifest.get("seriesIds", [])
    ]
    margin_days = {o["date"] for series in margin for o in series.get("observations", [])}
    margin_index_rows = []
    for row in index_data["hs300"].get("data", {}).get("rows", []):
        if row["date"] not in margin_days:
            continue
        close = number(row.get("close"))
        margin_index_rows.append({"date": row["date"], "close": str(close) if close and close > 0 else None})
    return {
        "margin": [s for s in margin if s],
        "marginIndex": {
            "code": "000300", "name": "沪深300",
            "rows": sorted(margin_index_rows, key=lambda row: row["date"]),
            "sourceUrl": index_data["hs300"].get("url"),
        },
        "basis": basis,
        "futuresSource": {k: v for k, v in futures.items() if k != "rows"},
        "iv": iv,
        "ivIndices": iv_indices,
        "goldIv": [s for s in gold if s],
        "refresh": local("public/v1/a-share/derivatives-refresh.json"),
    }
