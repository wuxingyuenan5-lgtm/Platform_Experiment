"""Read-only macro narrative proxies from existing research histories.

These are price/rate signals, not news sentiment, positions or causal attribution.
No collection, source substitution, forward filling or historical release simulation.
"""

from collections import deque
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from math import sqrt

from app.research_a_share_repository import read_dataset
from app.research_local_data import read_local_json
from app.research_provider_errors import ResearchProviderError

VERSION = "macro-narrative-proxies-v1"
# Each leg: canonical source ID, direction, transform (price ratio or level change).
DRIVERS = (
    (
        "us-duration",
        "美国久期",
        "利率",
        "美债10年收益率下降",
        (("us_treasury_10y", -1, "difference"),),
    ),
    (
        "us-policy",
        "美国前端政策",
        "利率",
        "美债2年收益率上升",
        (("us_treasury_2y", 1, "difference"),),
    ),
    (
        "us-curve",
        "美债曲线陡峭化",
        "利率",
        "10Y−2Y利差扩大",
        (("ust_10y_2y_spread", 1, "difference"),),
    ),
    (
        "real-yield",
        "实际利率上行",
        "利率",
        "美国10年实际利率上升",
        (("us_10y_real_yield", 1, "difference"),),
    ),
    (
        "inflation-pricing",
        "通胀定价",
        "通胀",
        "美国5年盈亏平衡通胀率上升",
        (("us_5y_breakeven", 1, "difference"),),
    ),
    ("broad-usd", "强美元", "汇率", "DXY上涨", (("dxy", 1, "ratio"),)),
    ("yen-stress", "日元贬值压力", "汇率", "USD/JPY上涨", (("usdjpy", 1, "ratio"),)),
    ("cyclical-fx", "周期货币", "汇率", "AUD/USD上涨", (("audusd", 1, "ratio"),)),
    ("rmb-stress", "人民币贬值压力", "汇率", "USD/CNY上涨；在岸口径", (("usdcny", 1, "ratio"),)),
    (
        "credit-easing",
        "信用条件改善",
        "信用",
        "美国高收益债OAS收窄",
        (("us_hy_oas", -1, "difference"),),
    ),
    (
        "vol-stress",
        "波动率压力",
        "风险",
        "VIX与MOVE标准化变化等权平均",
        (("vix", 1, "difference"), ("move", 1, "difference")),
    ),
    (
        "funding-stress",
        "美元融资压力",
        "信用",
        "SOFR−EFFR利差扩大",
        (("sofr_effr_spread", 1, "difference"),),
    ),
    (
        "cn-duration",
        "中国久期",
        "利率",
        "中国10年国债收益率下降",
        (("cn_treasury_10y", -1, "difference"),),
    ),
    (
        "precious-metals",
        "贵金属／黄金",
        "商品",
        "MT5 XAUUSD上涨",
        (("xauusd_daily_close", 1, "ratio"),),
    ),
    ("equity-beta", "美国股票风险偏好", "股票", "SPY价格上涨", (("SPY", 1, "ratio"),)),
    (
        "growth-cyclical",
        "美股成长／周期",
        "股票",
        "QQQ相对XLI的标准化价格变化",
        (("QQQ", 1, "ratio"), ("XLI", -1, "ratio")),
    ),
    ("energy-equity", "能源股", "股票", "XLE价格上涨；并非油气现货", (("XLE", 1, "ratio"),)),
    ("industrial-equity", "工业与自动化", "股票", "XLI价格上涨", (("XLI", 1, "ratio"),)),
    (
        "crypto-risk",
        "加密风险偏好",
        "加密",
        "BTC/USD上涨；并非流动性总量",
        (("BTC-USD", 1, "ratio"),),
    ),
)


def points(document, today):
    result = {}
    for row in document.get("observations", document.get("history", [])):
        try:
            day = date.fromisoformat(str(row["date"])[:10])
            value = Decimal(str(row["value"]))
        except (KeyError, ValueError, InvalidOperation, TypeError):
            continue
        if day < today and value.is_finite():
            result[day.isoformat()] = value
    return dict(sorted(result.items()))


def rolling_signal(values, transform):
    """20-observation change vs preceding <=252 changes, minimum126; no lookahead.

    A >14-calendar-day gap resets the observation window. Zero historical variance
    stays unavailable. Financial input arithmetic uses Decimal; z scores are floats.
    """
    history = deque(maxlen=252)
    window = deque(maxlen=21)
    result = {}
    previous = None
    for day, value in values.items():
        stamp = date.fromisoformat(day)
        if previous and (stamp - previous).days > 14:
            window.clear()
            history.clear()
        previous = stamp
        if transform == "ratio" and value <= 0:
            window.clear()
            history.clear()
            continue
        window.append(value)
        if len(window) < 21:
            continue
        change = float(value / window[0] - 1 if transform == "ratio" else value - window[0])
        if len(history) >= 126:
            mean = sum(history) / len(history)
            variance = sum((x - mean) ** 2 for x in history) / len(history)
            if variance > 1e-18:
                result[day] = {
                    "score": (change - mean) / sqrt(variance),
                    "change": change,
                    "baselineCount": len(history),
                    "value": str(value),
                }
        history.append(change)
    return result


def build_driver(definition, sources, today):
    key, label, group, meaning, legs = definition
    signals = [rolling_signal(points(sources.get(code, {}), today), mode) for code, _, mode in legs]
    common = sorted(set.intersection(*(set(signal) for signal in signals))) if signals else []
    rows = []
    for i, day in enumerate(common):
        score = sum(
            signal[day]["score"] * leg[1] for signal, leg in zip(signals, legs, strict=True)
        ) / len(legs)
        change = None
        if i >= 5 and (date.fromisoformat(day) - date.fromisoformat(common[i - 5])).days <= 14:
            change = score - rows[i - 5]["score"]
        rows.append({"date": day, "score": score, "momentum": change})
    cutoff = (today - timedelta(days=366 * 5)).isoformat()
    rows = [row for row in rows if row["date"] >= cutoff]
    latest = rows[-1] if rows else None
    missing = [leg[0] for leg, signal in zip(legs, signals, strict=True) if not signal]
    source_meta = []
    for code, direction, mode in legs:
        document = sources.get(code, {})
        source_meta.append(
            {
                "id": code,
                "label": document.get("label", code),
                "direction": direction,
                "transform": mode,
                "source": document.get("source", ""),
                "url": document.get("sourceUrl"),
                "status": document.get("status", "no_data"),
                "date": max(points(document, today), default=None),
            }
        )
    stale = bool(latest and (today - date.fromisoformat(latest["date"])).days > 14)
    return {
        "id": key,
        "label": label,
        "group": group,
        "meaning": meaning,
        "status": "no_data"
        if not latest
        else "stale"
        if stale
        else "partial"
        if any(s["status"] != "ready" for s in source_meta)
        else "ready",
        "sources": source_meta,
        "missing": missing,
        "history": rows,
        "date": latest["date"] if latest else None,
    }


STATE_SOURCES = {
    "us": (
        ("增长", "us_ism_manufacturing_pmi"),
        ("通胀", "us_core_cpi_yoy"),
        ("政策", "fed_target_upper"),
        ("流动性", "net_dollar_liquidity"),
        ("财政", None),
        ("风险溢价", "us_hy_oas"),
    ),
    "cn": (
        ("增长", "cn_manufacturing_pmi"),
        ("通胀", "cn_cpi_yoy"),
        ("政策", "cn_omo_7d"),
        ("流动性", "cn_m2_yoy"),
        ("财政", "cn_fiscal_expenditure_ytd_yoy"),
        ("风险溢价", None),
    ),
}


def state_evidence(sources, market, today):
    evidence = []
    for dimension, code in STATE_SOURCES[market]:
        doc = sources.get(code, {})
        values = points(doc, today)
        monthly = {}
        for day, value in values.items():
            monthly[day[:7]] = (day, value)
        samples = list(monthly.values())
        latest = samples[-1] if samples else None
        delta = None
        if len(samples) >= 6:
            recent = samples[-6:]
            months = [int(d[:4]) * 12 + int(d[5:7]) for d, _ in recent]
            if months[-1] - months[0] == 5:
                delta = (sum(v for _, v in recent[3:]) - sum(v for _, v in recent[:3])) / 3
        evidence.append(
            {
                "dimension": dimension,
                "id": code,
                "label": doc.get("label"),
                "value": str(latest[1]) if latest else None,
                "date": latest[0] if latest else None,
                "unit": doc.get("unit", ""),
                "delta": str(delta) if delta is not None else None,
                "status": doc.get("status", "no_data"),
                "source": doc.get("source", ""),
                "url": doc.get("sourceUrl"),
            }
        )
    return {"market": market, "evidence": evidence}


def build(sources, today):
    drivers = [build_driver(definition, sources, today) for definition in DRIVERS]
    dates = sorted(
        {
            row["date"]
            for driver in drivers
            for row in driver["history"]
            if row["momentum"] is not None
        }
    )
    return {
        "version": VERSION,
        "asOf": dates[-1] if dates else None,
        "status": "no_data"
        if not dates
        else "partial"
        if any(d["status"] != "ready" for d in drivers)
        else "ready",
        "dates": dates,
        "drivers": drivers,
        "states": [state_evidence(sources, market, today) for market in ("us", "cn")],
    }


def read_macro_narratives():
    sources = {}
    ids = {code for _, _, _, _, legs in DRIVERS for code, _, _ in legs}
    ids |= {code for dims in STATE_SOURCES.values() for _, code in dims if code}
    for code in ids:
        if code in {"SPY", "QQQ", "XLI", "XLE", "BTC-USD"}:
            continue
        area = "commodity" if code == "xauusd_daily_close" else "macro"
        try:
            sources[code] = read_local_json(f"public/v1/{area}/series/{code}.json")
        except ResearchProviderError:
            sources[code] = {"status": "no_data"}
    for market in ("us", "crypto"):
        for row in (read_dataset(f"market_detail_{market}") or {}).get("rows", []):
            if row.get("symbol") in ids:
                sources[row["symbol"]] = {**row, "label": row.get("name", row["symbol"])}
    return build(sources, datetime.now(UTC).date())
