"""Read the A-share timing radar from local, source-attributed observations."""

from functools import lru_cache
from datetime import date, timedelta
from bisect import bisect_right
from math import isfinite

from app.research_local_data import local_json_revision, read_local_json
from app.research_provider_errors import ResearchProviderError
from app.research_timing_radar_model import calculate_factors, month_key


DIMENSIONS = ("流动性", "经济面", "估值面", "资金面", "技术面", "拥挤度")
CLASSES = ("估值性价比", "宏观基本面", "资金与趋势", "拥挤度与反转")
# key, label, dimension, score class, unit, report pages, formula, required inputs
FACTORS = (
    (
        "moneyDirection",
        "货币方向",
        0,
        1,
        "百分点",
        "2",
        "DR007 与 7 天逆回购利率均值相对 90 个交易日前的降幅。降息方向得 +1。",
        "DR007、7 天逆回购利率",
    ),
    (
        "moneyStrength",
        "货币强度",
        0,
        1,
        "Z 值",
        "2–3",
        "DR007／7 天逆回购利率 − 1，20 日平滑后做 252 日标准化。低于 −1.5 得 +1，高于 +1.5 得 −1，持续 120 个交易日。",
        "DR007、7 天逆回购利率",
    ),
    (
        "creditDirection",
        "信用方向",
        0,
        1,
        "%",
        "3",
        "中长期贷款余额的 12 个月增量同比，与三个月前比较。上升得 +1。",
        "全国人民币中长期贷款余额",
    ),
    (
        "creditStrength",
        "信用强度",
        0,
        1,
        "Z 值",
        "3",
        "新增人民币贷款与发布前预测中位数的差除以预测标准差。超过 ±1.5 后顺向计分 60 个交易日。",
        "新增人民币贷款、预测中位数与标准差",
    ),
    (
        "growthDirection",
        "增长方向",
        1,
        1,
        "%",
        "4",
        "三项 PMI 各自的 12 个月均值同比取平均，高于三个月前得 +1。",
        "官方制造业、非制造业及财新／RatingDog 制造业 PMI",
    ),
    (
        "growthStrength",
        "增长强度",
        1,
        1,
        "Z 值",
        "4",
        "制造业 PMI 与发布前预测中位数的差除以预测标准差。超过 ±1.5 后顺向计分 60 个交易日。",
        "制造业 PMI、预测中位数与标准差",
    ),
    (
        "inflationDirection",
        "通胀方向",
        1,
        1,
        "%",
        "4–5",
        "CPI 同比的三个月均值与 PPI 同比等权。低于三个月前得 +1。",
        "CPI、PPI 同比",
    ),
    (
        "inflationStrength",
        "通胀强度",
        1,
        1,
        "Z 值",
        "5",
        "CPI、PPI 各自的实际值与预测中位数之差除以预测标准差，再取均值。超过 ±1.5 后反向计分 60 个交易日。",
        "CPI、PPI 实际值及两组预测中位数与标准差",
    ),
    (
        "shillerErp",
        "席勒 ERP",
        2,
        0,
        "百分点",
        "5–6",
        "中证 800 过去 72 个月通胀调整后的平均盈利收益率减 10 年期国债收益率。近六年标准化后截断映射到 ±1。",
        "中证 800、市盈率、CPI 定基指数、10 年国债",
    ),
    (
        "pb",
        "PB",
        2,
        0,
        "倍",
        "6",
        "中证 800 市净率取负，近六年标准化，以 ±1.5 截断映射到 ±1。",
        "中证 800 PB MRQ",
    ),
    (
        "aiae",
        "AIAE",
        2,
        0,
        "%",
        "6",
        "中证全指流通市值／（流通市值＋实体部门总债务）。取负后以近六年标准化计分。",
        "中证全指流通市值、实体部门总债务",
    ),
    (
        "marginChange",
        "两融增量",
        3,
        2,
        "亿元／日",
        "7",
        "融资余额减融券余额，再比较 120 日与 240 日的日均增量。短期高于长期得 +1。",
        "沪深融资余额、融券余额",
    ),
    (
        "turnoverTrend",
        "成交额趋势",
        3,
        2,
        "%",
        "7",
        "对中证 800 成交额取对数，计算 MA120／MA240 − 1。10、30、60 日同为区间高点得 +1，低点得 −1。",
        "中证 800 成交额",
    ),
    (
        "chinaCds",
        "中国主权 CDS 利差",
        3,
        2,
        "基点",
        "7–8",
        "5 年期利差在下一个 A 股交易日入模，5 日平滑后与 20 个交易日前作差。收窄得 +1。",
        "中国主权 CDS 同期限日收盘利差",
    ),
    (
        "citiRai",
        "海外风险厌恶指数",
        3,
        2,
        "指数",
        "8",
        "Citi RAI 进行 5 日平滑后与 20 个交易日前作差。风险厌恶下降得 +1。",
        "Citi Risk Aversion Index",
    ),
    (
        "priceTrend",
        "价格趋势",
        4,
        2,
        "%",
        "8–9",
        "中证 800 价格 MA120／MA240 − 1 的符号，与 20／60 日区间高低点信号等权。",
        "中证 800 价格指数",
    ),
    (
        "newHighLow",
        "新高新低数",
        4,
        3,
        "只",
        "9",
        "按当日中证 800 成分统计过去一年新低数减新高数，并做 20 日均值。新低较多得 +1。",
        "中证 800 逐日历史成分与复权价格，或同口径统计",
    ),
    (
        "optionBasis",
        "期权隐含升贴水",
        5,
        3,
        "%",
        "9–10",
        "用上交所结算价和平价关系估计 30 日年化升贴水。以 50ETF 近 5 日涨跌配合 30%／70% 分位反向计分，持续 20 个交易日。",
        "50ETF 收盘价与期权平价隐含升贴水",
    ),
    (
        "optionVix",
        "期权 VIX",
        5,
        3,
        "%",
        "10",
        "用上交所结算价估计 30 日隐含波动率。高于过去一年 70% 分位时，对 50ETF 近 5 日涨跌反向计分，持续 20 个交易日。",
        "50ETF 收盘价与 30 日方差口径波动率",
    ),
    (
        "optionSkew",
        "期权 SKEW",
        5,
        3,
        "指数",
        "10",
        "用上交所结算价估计 30 日隐含偏度。50ETF 下跌且偏度高分位得 +1，上涨且偏度低分位得 −1，持续 20 个交易日。",
        "50ETF 收盘价与期权隐含偏度指数",
    ),
    (
        "convertibleDeviation",
        "可转债定价偏离度",
        5,
        3,
        "%",
        "11",
        "转债实际价格／模型定价 − 1，取负后按近三年标准化计分。",
        "同口径可转债市场价格与模型公允价值",
    ),
)
REPORT = {
    "date": "2026-11-20",
    "previousDate": "2026-11-13",
    "published": "2026-11-21",
    "current": (1, 0, -1, -1, 1, 1, -1, 0, 0.79, 0.26, 0.78, -1, -1, 1, -1, -1, 1, 1, 0, -1, -0.20),
    "previous": (1, 0, -1, -1, 1, 1, -1, 0, 0.73, 0.23, 0.50, -1, -1, 1, -1, -1, 1, 1, 0, 0, -0.88),
}


def series(key, domain="macro"):
    return (f"public/v1/{domain}/series/{key}.json", "observations", "value")


DAILY = {
    "benchmark": series("timing_csi800_total_return", "equity"),
    "price": series("timing_csi800_close", "equity"),
    "allShare": series("timing_all_share_close", "equity"),
    "turnover": series("timing_csi800_turnover", "equity"),
    "pe": series("timing_csi800_pe", "equity"),
    "pb": ("public/v1/equity/sources/choice_index_000906.json", "rows", "pb"),
    "pbChoice": series("timing_csi800_pb"),
    "etf50": ("public/v1/etf-native/market/sh510050.json", "rows", "close"),
    "omo": series("cn_omo_7d"),
    "dr007": series("cn_dr007"),
    "bond10y": series("cn_treasury_10y"),
    "marginLong": series("cn_margin_financing_balance"),
    "marginShort": series("cn_margin_short_balance"),
    "floatCap": series("timing_csi_all_share_float_cap"),
    "debt": series("timing_cn_nonfinancial_debt"),
    "chinaCds": series("timing_cn_cds"),
    "citiRai": series("timing_citi_rai"),
    "newLowsMinusHighs": series("timing_csi800_new_lows_minus_highs"),
    "optionBasis": series("timing_50etf_option_basis"),
    "optionVix": series("timing_50etf_vix"),
    "optionSkew": series("timing_50etf_skew"),
    "cbPrice": series("timing_cb_price"),
    "cbModel": series("timing_cb_model"),
}
MONTHLY = {
    "longLoans": series("timing_cn_long_loans"),
    "newLoans": series("cn_new_rmb_loans"),
    "nbsPmi": series("cn_manufacturing_pmi"),
    "nbsServices": series("cn_nonmanufacturing_pmi"),
    "privatePmi": series("timing_cn_private_manufacturing_pmi"),
    "cpiYoY": series("cn_cpi_yoy"),
    "ppiYoY": series("cn_ppi_yoy"),
    "cpiMom": series("cn_cpi_mom"),
    **{
        name: series("timing_consensus_" + key + "_" + stat)
        for key in ("loan", "pmi", "cpi", "ppi")
        for stat, name in [("median", key + "Median"), ("sd", key + "Sd")]
    },
}


def load(source):
    path, container, field = source
    try:
        doc = read_local_json(path)
    except ResearchProviderError:
        return {}
    result = {}
    for row in doc.get(container, []):
        day, value = row.get("date"), row.get(field)
        if not isinstance(day, str) or len(day) != 10:
            continue
        try:
            number = float(value)
        except (ValueError, TypeError):
            continue
        if isfinite(number):
            result[day] = number
    return result


def read_timing_radar():
    sources = {source[0] for source in (*DAILY.values(), *MONTHLY.values())}
    return _read(tuple(local_json_revision(path) for path in sorted(sources)))


def chain_price_level(changes):
    """A CPI level from the reported month-on-month national CPI, scaled to 100."""
    level = 100.0
    previous_month = None
    result = {}
    for day, change in sorted(changes.items()):
        month = month_key(day)
        if change <= -100:
            continue
        if previous_month != month - 1:
            # A missing month breaks the chain, and a 72-month window that
            # crosses the gap is ineligible.
            level = 100.0
        level *= 1 + change / 100
        result[day] = level
        previous_month = month
    return result


@lru_cache(maxsize=1)
def _read(revisions):
    daily = {key: load(source) for key, source in DAILY.items()}
    monthly = {key: load(source) for key, source in MONTHLY.items()}
    monthly["cpiLevel"] = chain_price_level(monthly.pop("cpiMom"))
    calendar = sorted(daily["benchmark"])
    daily["pb"].update(daily.pop("pbChoice"))
    cds = {}
    for day, value in sorted(daily["chinaCds"].items()):
        next_session = bisect_right(calendar, day)
        if next_session < len(calendar):
            cds[calendar[next_session]] = value
    daily["chinaCds"] = cds
    # Historical quarter publication vintages are absent. Keep a six-month
    # release lag before the BIS denominator enters a daily AIAE reading.
    debt_points = iter(
        sorted(
            (date.fromisoformat(day) + timedelta(days=183), value)
            for day, value in daily["debt"].items()
        )
    )
    next_debt = next(debt_points, None)
    debt = None
    daily["debt"] = {}
    for day in calendar:
        as_of = date.fromisoformat(day)
        while next_debt and next_debt[0] <= as_of:
            debt = next_debt
            next_debt = next(debt_points, None)
        if debt and (as_of - debt[0]).days <= 150:
            daily["debt"][day] = debt[1]
    factors = calculate_factors(calendar, daily, monthly) if calendar else {}
    # The raw value and score keep independent gaps and units on the same date axis.
    first = next((i for i, day in enumerate(calendar) if day >= "2011-01-01"), len(calendar))
    return {
        "dimensions": DIMENSIONS,
        "classes": CLASSES,
        "report": REPORT,
        "dates": calendar[first:],
        "benchmarks": {
            key: [daily[key].get(day) for day in calendar[first:]]
            for key in ("benchmark", "price", "allShare", "etf50")
        },
        "factors": [
            dict(
                key=key,
                name=label,
                dimension=dim,
                group=group,
                unit=unit,
                pages=pages,
                method=method,
                inputs=inputs,
                values=rounded(factors.get(key, ([], []))[0][first:]),
                scores=rounded(factors.get(key, ([], []))[1][first:]),
            )
            for key, label, dim, group, unit, pages, method, inputs in FACTORS
        ],
    }


def rounded(series):
    return [None if value is None else round(value, 8) for value in series]
