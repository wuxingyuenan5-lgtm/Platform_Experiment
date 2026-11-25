"""Five-minute cumulative ETF turnover, with fixed 5/20-session windows."""

from decimal import Decimal, InvalidOperation

SLOTS = tuple(
    f"{minute // 60:02d}:{minute % 60:02d}"
    for start, end in ((9 * 60 + 35, 11 * 60 + 30), (13 * 60 + 5, 15 * 60))
    for minute in range(start, end + 1, 5)
)
MINUTES = tuple(
    f"{minute // 60:02d}:{minute % 60:02d}"
    for start, end in ((9 * 60 + 31, 11 * 60 + 30), (13 * 60 + 1, 15 * 60))
    for minute in range(start, end + 1)
)
YI = Decimal(100000000)


def day_curve(rows, day, interval):
    """Return actual cumulative samples; never interpolate or fill missing bars."""
    lookup = {}
    try:
        for row in rows:
            stamp = row["day"]
            if stamp[:10] != day:
                return None
            slot = stamp[11:16]
            if slot in lookup:
                return None
            amount = Decimal(str(row["amount"]))
            if not amount.is_finite() or amount < 0:
                return None
            lookup[slot] = amount
    except (KeyError, InvalidOperation, TypeError, ValueError):
        return None
    required = SLOTS if interval == 5 else MINUTES
    permitted_absences = set() if interval == 5 else {"14:58", "14:59"}
    if set(required) - set(lookup) - permitted_absences:
        return None
    result = [Decimal(0)]
    running = Decimal(0)
    for slot in required:
        if slot in lookup:
            running += lookup[slot]
        if slot in SLOTS:
            result.append(running / YI)
    return result


def build_cumulative(read, basket, dates, today):
    """Combine the same members on exact recent sessions, excluding today."""
    days = sorted({day for day in dates if day < today})[-20:]
    members = list(basket[1:])
    archives = {
        symbol: (read("minutes-5m/" + symbol), read("minutes/" + symbol))
        for symbol in members
    }
    curves, sources = {}, {}
    for day in days:
        parts, methods = [], []
        for symbol in members:
            five, one = archives[symbol]
            curve = day_curve(five.get("days", {}).get(day, []), day, 5)
            method = "original_5min"
            if curve is None:
                curve = day_curve(one.get("days", {}).get(day, []), day, 1)
                method = "aggregated_original_1min"
            if curve is None:
                break
            parts.append(curve)
            methods.append(method)
        if members and len(parts) == len(members):
            curves[day] = [sum(values, Decimal(0)) for values in zip(*parts, strict=True)]
            sources[day] = dict(zip(members, methods, strict=True))

    def average(window):
        selected = days[-window:]
        if len(selected) != window or any(day not in curves for day in selected):
            return []
        return [float(sum(values, Decimal(0)) / window)
                for values in zip(*(curves[day] for day in selected), strict=True)]

    previous = days[-1] if days else None
    avg5, avg20 = average(5), average(20)
    return {
        "slots": ["09:30", *SLOTS],
        "intervalMinutes": 5,
        "basketCodes": [symbol[2:] for symbol in members],
        "prevDate": previous,
        "prev": [float(value) for value in curves.get(previous, [])],
        "avg5": avg5,
        "avg5Days": 5 if avg5 else 0,
        "avg5From": days[-5] if avg5 else None,
        "avg5To": previous if avg5 else None,
        "avg20": avg20,
        "avgDays": len(curves),
        "avgFrom": days[0] if days else None,
        "avgTo": previous,
        "requestedDays": days,
        "missingDays": [day for day in days if day not in curves],
        "inputMethods": sources,
        "source": "native_5min_cumulative",
        "status": "ready" if avg5 and avg20 else "partial" if curves else "no_data",
    }
