"""A-share timing factor calculations on an ascending exchange-session calendar."""

from calendar import monthrange
from datetime import date
from math import log, sqrt
from statistics import fmean


def sign(value):
    return (value > 0) - (value < 0)


def combine(*series, calculate):
    return [
        calculate(*values) if all(x is not None for x in values) else None
        for values in zip(*series, strict=True)
    ]


def rolling(series, size, calculate):
    result = [None] * len(series)
    run = 0
    for i, value in enumerate(series):
        run = run + 1 if value is not None else 0
        if run >= size:
            result[i] = calculate(series[i + 1 - size : i + 1])
    return result


def lag(series, size):
    return [None if i < size else series[i - size] for i in range(len(series))]


def ratio(numerator, denominator):
    return numerator / denominator if denominator > 0 else None


def ma_distance(series):
    return combine(
        rolling(series, 120, fmean),
        rolling(series, 240, fmean),
        calculate=lambda short, long: short / long - 1 if long else None,
    )


def zscore(series, size, minimum=None):
    # Two running moments avoid scanning multi-year windows on each API read.
    result = [None] * len(series)
    count = total = squares = 0
    for i, value in enumerate(series):
        if value is not None:
            count += 1
            total += value
            squares += value * value
        if i >= size and (old := series[i - size]) is not None:
            count -= 1
            total -= old
            squares -= old * old
        if i >= size - 1 and count >= (minimum or size) and value is not None:
            mean = total / count
            variance = squares / count - mean**2
            result[i] = (value - mean) / sqrt(variance) if variance > 1e-20 else 0
    return result


def bounded_zscore(series, size, direction=1):
    return [
        None if value is None else max(-1, min(1, direction * value / 1.5))
        for value in zscore(series, size, minimum=int(size * 0.95))
    ]


def held_signal(events, duration):
    result = []
    score = 0
    until = -1
    for i, event in enumerate(events):
        if event:
            score, until = event, i + duration
        result.append(None if event is None else score if i < until else 0)
    return result


def extreme(series, small_window):
    def score(window):
        recent = window[-small_window:]
        contains_high = max(recent) == max(window)
        contains_low = min(recent) == min(window)
        return int(contains_high) - int(contains_low)

    return rolling(series, 60, score)


def month_key(day):
    return int(day[:4]) * 12 + int(day[5:7]) - 1


def monthly_grid(maps):
    return {
        key: {month_key(day): value for day, value in sorted(points.items())}
        for key, points in maps.items()
    }


def next_month_release(month):
    year, month_index = divmod(month + 1, 12)
    return date(year, month_index + 1, 20).isoformat()


def monthly_daily(calendar, months, values, lagged_release=True):
    """Use explicit release dates when supplied, otherwise next-month day 20."""
    events = []
    for month, item in zip(months, values, strict=True):
        year, mi = divmod(month, 12)
        release = (
            next_month_release(month)
            if lagged_release
            else date(year, mi + 1, monthrange(year, mi + 1)[1]).isoformat()
        )
        if isinstance(item, tuple):
            release, item = max(release, item[0]), item[1]
        events.append((release, item))
    events.sort()
    result = []
    i = 0
    value = None
    for day in calendar:
        while i < len(events) and events[i][0] <= day:
            value = events[i][1]
            i += 1
        result.append(value)
    return result


def monthly_events(calendar, events):
    result = []
    rows = iter(sorted(events.items()))
    current = next(rows, None)
    known_until = 0
    for i, day in enumerate(calendar):
        signal = 0 if i < known_until else None
        while current and current[0] <= day:
            if current[1] is not None:
                signal, known_until = current[1], i + 35
            current = next(rows, None)
        result.append(signal)
    return result


def year_average_earnings(calendar, close, pe, inflation):
    # Inflation adjustment uses the cumulative price level relative to the same
    # calendar month six years earlier. Monthly trailing earnings avoid daily
    # repetition of the same earnings figure in the smoothing window.
    month_earnings = {}
    for day, price, multiple in zip(calendar, close, pe, strict=True):
        if price is not None and multiple and multiple > 0:
            month_earnings[month_key(day)] = price / multiple
    real = {}
    for month, earnings in month_earnings.items():
        if (cpi := inflation.get(month)) is not None and cpi > 0:
            real[month] = earnings / cpi
    result = []
    for day, price, _ in zip(calendar, close, pe, strict=True):
        month = month_key(day)
        # CPI levels are admitted only after the conservative release gate.
        latest = month - (1 if int(day[-2:]) >= 20 else 2)
        values = [real.get(m) for m in range(latest - 71, latest + 1)]
        if not price or any(x is None for x in values):
            result.append(None)
        else:
            result.append(fmean(values) * inflation[latest] / price)
    return result


def calculate_factors(calendar, daily, monthly):
    d = {key: [points.get(day) for day in calendar] for key, points in daily.items()}
    monthly = monthly_grid(monthly)
    months = list(range(min(map(month_key, calendar)) - 72, max(map(month_key, calendar)) + 1))
    m = {key: [values.get(month) for month in months] for key, values in monthly.items()}

    def negate_diff(a, b):
        return b - a

    def direction(values):
        return [sign(value) if value is not None else None for value in values]

    def percentage(values):
        return [value * 100 if value is not None else None for value in values]

    def month_direction(values, reverse=False):
        delta = combine(values, lag(values, 3), calculate=lambda a, b: b - a if reverse else a - b)
        return monthly_daily(calendar, months, values), monthly_daily(
            calendar, months, direction(delta)
        )

    def surprise(actual, median, sd):
        return combine(m[actual], m[median], m[sd], calculate=lambda a, b, c: ratio(a - b, c))

    def stretch(values, holding, bullish, monthly_input=False):
        events = [
            None if v is None else (bullish if v > 1.5 else -bullish if v < -1.5 else 0)
            for v in values
        ]
        if monthly_input:
            events = monthly_events(
                calendar, dict(zip(map(next_month_release, months), events, strict=True))
            )
            values = monthly_daily(calendar, months, values)
        return values, held_signal(events, holding)

    def mean_delta(values, size):
        return combine(values, lag(values, size), calculate=lambda a, b: (a - b) / size)

    def option_events(metric, rule):
        ranks = rolling(
            metric,
            252,
            lambda window: (
                (sum(x < window[-1] for x in window) + sum(x == window[-1] for x in window) / 2)
                / len(window)
            ),
        )
        changes = combine(
            d["etf50"], lag(d["etf50"], 5), calculate=lambda a, b: a / b - 1 if b > 0 else None
        )
        return metric, held_signal(combine(changes, ranks, calculate=rule), 20)

    rates = combine(d["omo"], d["dr007"], calculate=fmean_pair)
    money_direction = combine(rates, lag(rates, 90), calculate=negate_diff)
    money_spread = combine(
        d["dr007"], d["omo"], calculate=lambda a, b: a / b - 1 if b > 0 else None
    )
    money_strength = zscore(rolling(money_spread, 20, fmean), 252)
    credit_increment = combine(
        m["longLoans"], lag(m["longLoans"], 12), calculate=lambda a, b: a - b
    )
    credit_yoy = combine(
        credit_increment, lag(credit_increment, 12), calculate=lambda a, b: percent_growth(a, b)
    )
    pmi_growth = [
        combine(average, lag(average, 12), calculate=percent_growth)
        for key in ("nbsPmi", "nbsServices", "privatePmi")
        for average in [rolling(m[key], 12, fmean)]
    ]
    growth = combine(*pmi_growth, calculate=lambda *values: fmean(values))
    inflation = combine(rolling(m["cpiYoY"], 3, fmean), m["ppiYoY"], calculate=fmean_pair)
    inflation_surprise = combine(
        surprise("cpiYoY", "cpiMedian", "cpiSd"),
        surprise("ppiYoY", "ppiMedian", "ppiSd"),
        calculate=fmean_pair,
    )
    earnings_yield = year_average_earnings(calendar, d["price"], d["pe"], monthly["cpiLevel"])
    erp = combine(
        earnings_yield, d["bond10y"], calculate=lambda earnings, bond: earnings * 100 - bond
    )
    aiae = combine(
        d["floatCap"], d["debt"], calculate=lambda cap, debt: ratio(cap * 100, cap + debt)
    )
    balances = combine(d["marginLong"], d["marginShort"], calculate=lambda a, b: a - b)
    margin = combine(
        mean_delta(balances, 120), mean_delta(balances, 240), calculate=lambda a, b: a - b
    )
    turnover = ma_distance(
        [log(v * 1e8) if v is not None and v > 0 else None for v in d["turnover"]]
    )
    trend = ma_distance(d["price"])
    contrary = rolling(d["newLowsMinusHighs"], 20, fmean)
    deviation = combine(
        d["cbPrice"], d["cbModel"], calculate=lambda a, b: (a / b - 1) * 100 if b > 0 else None
    )

    def declining(series):
        smooth = rolling(series, 5, fmean)
        return series, direction(combine(smooth, lag(smooth, 20), calculate=negate_diff))

    def options_rule(low, high):
        return lambda return5, pct: (
            1 if return5 < 0 and low(pct) else -1 if return5 > 0 and high(pct) else 0
        )

    return {
        "moneyDirection": (money_direction, direction(money_direction)),
        "moneyStrength": stretch(money_strength, 120, -1),
        "creditDirection": month_direction(credit_yoy),
        "creditStrength": stretch(surprise("newLoans", "loanMedian", "loanSd"), 60, 1, True),
        "growthDirection": month_direction(growth),
        "growthStrength": stretch(surprise("nbsPmi", "pmiMedian", "pmiSd"), 60, 1, True),
        "inflationDirection": month_direction(inflation, True),
        "inflationStrength": stretch(inflation_surprise, 60, -1, True),
        "shillerErp": (erp, bounded_zscore(erp, 1440)),
        "pb": (d["pb"], bounded_zscore(d["pb"], 1440, -1)),
        "aiae": (aiae, bounded_zscore(aiae, 1440, -1)),
        "marginChange": (margin, direction(margin)),
        "turnoverTrend": (percentage(turnover), extreme(turnover, 10)),
        "chinaCds": declining(d["chinaCds"]),
        "citiRai": declining(d["citiRai"]),
        "priceTrend": (
            percentage(trend),
            combine(direction(trend), extreme(trend, 20), calculate=fmean_pair),
        ),
        "newHighLow": (contrary, direction(contrary)),
        "optionBasis": option_events(
            d["optionBasis"], options_rule(lambda p: p < 0.3, lambda p: p > 0.7)
        ),
        "optionVix": option_events(
            d["optionVix"], options_rule(lambda p: p > 0.7, lambda p: p > 0.7)
        ),
        "optionSkew": option_events(
            d["optionSkew"], options_rule(lambda p: p > 0.7, lambda p: p < 0.3)
        ),
        "convertibleDeviation": (deviation, bounded_zscore(deviation, 720, -1)),
    }


def fmean_pair(left, right):
    return (left + right) / 2


def percent_growth(value, base):
    return (value / base - 1) * 100 if base > 0 else None
