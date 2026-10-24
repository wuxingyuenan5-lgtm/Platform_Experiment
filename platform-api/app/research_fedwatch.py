"""CME Aggregated view: anchored EFFR endpoints relative to the first start rate.

See CME's 2023 methodology (anchor direction and meeting-day weights) and
2024 Aggregated enhancement (no compounding of individual meeting outcomes).
"""

from calendar import monthrange
from datetime import date
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal

from app.research_provider_errors import ResearchProviderError

METHODOLOGY = "cme_aggregated_v1"
_MONTHS = "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()


def previous_month(month):
    year, number = month
    return (year - 1, 12) if number == 1 else (year, number - 1)


def next_month(month):
    year, number = month
    return (year + 1, 1) if number == 12 else (year, number + 1)


def aggregated_probabilities(prices: dict[str, float], meetings: list[date], effr: float):
    if not meetings:
        raise ResearchProviderError("fedwatch_schedule_unavailable")
    meetings = sorted(meetings)
    by_month = {(day.year, day.month): day for day in meetings}
    if len(by_month) != len(meetings):
        raise ResearchProviderError("fedwatch_multiple_meetings_in_month")
    averages = {}
    for key, value in prices.items():
        name, year = key.split()
        rate = Decimal(100) - Decimal(str(value))
        if not rate.is_finite() or rate < 0:
            raise ResearchProviderError("fedwatch_invalid_futures_price")
        averages[(2000 + int(year), _MONTHS.index(name) + 1)] = rate
    first = (meetings[0].year, meetings[0].month)
    # Do not infer a quiet month beyond the known FOMC calendar.
    last_known = max(by_month)
    anchors = sorted(
        month for month in averages if first < month <= last_known and month not in by_month
    )
    starts, ends = {}, {}
    for month in anchors:
        ends[previous_month(month)] = averages[month]
        starts[next_month(month)] = averages[month]
    for anchor in anchors:
        month = previous_month(anchor)
        while month in by_month and month >= first:
            if month not in averages or month not in ends:
                break
            day = by_month[month].day
            days = monthrange(*month)[1]
            # A decision affects EFFR from the following day, not meeting day.
            if month not in starts:
                starts[month] = (averages[month] * days - ends[month] * (days - day)) / day
            prior = previous_month(month)
            if prior not in by_month:
                break
            ends[prior] = starts[month]
            month = prior
    if first not in starts or first not in ends:
        raise ResearchProviderError("fedwatch_first_meeting_anchor_missing")
    baseline = starts[first]
    actual = Decimal(str(effr))
    if not actual.is_finite() or actual < 0 or baseline < 0:
        raise ResearchProviderError("fedwatch_invalid_reference_rate")
    current_lower = int((actual * 100 / 25).to_integral_value(rounding=ROUND_FLOOR)) * 25
    result = []
    for day in meetings:
        month = (day.year, day.month)
        if month not in ends or month not in starts or month not in averages:
            continue
        moves = (ends[month] - baseline) / Decimal(".25")
        # Decimal division may leave an exact grid point one ulp below an integer.
        nearest = moves.to_integral_value(rounding=ROUND_HALF_UP)
        if abs(moves - nearest) < Decimal("1e-20"):
            moves = nearest
        whole = int(moves.to_integral_value(rounding=ROUND_FLOOR))
        upper_probability = ((moves - whole) * 100).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
        lower = current_lower + whole * 25
        if lower < 0 or ends[month] < 0:
            raise ResearchProviderError("fedwatch_negative_target")
        probabilities = {}
        for target, probability in (
            (lower, 100 - upper_probability),
            (lower + 25, upper_probability),
        ):
            if probability > 0:
                probabilities[f"{target}-{target + 25}"] = float(probability)
        result.append(dict(date=day.isoformat(), probabilities=probabilities))
    return result
