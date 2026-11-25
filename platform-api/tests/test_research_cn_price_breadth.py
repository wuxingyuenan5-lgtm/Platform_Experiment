from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.research_cn_price_breadth import parse_prices, price_breadth, sina_adjusted


def test_sina_factor_applies_from_effective_date_without_filling_price_gaps():
    rows = [{"date": "2025-01-02", "close": 20}, {"date": "2025-01-06", "close": 10}]
    factors = [{"d": "1900-01-01", "f": "2"}, {"d": "2025-01-06", "f": "1"}]
    assert sina_adjusted(rows, factors) == {"2025-01-02": Decimal(10), "2025-01-06": Decimal(10)}
    with pytest.raises(ValueError, match="factor_missing"):
        sina_adjusted(rows, factors[1:])
    with pytest.raises(ValueError, match="factor_invalid"):
        sina_adjusted(rows, [{"d": "1900-01-01", "f": "0"}])


def sessions(n=100):
    start = date(2025, 1, 6)
    days = [start + timedelta(days=i) for i in range(n * 2)]
    return [d.isoformat() for d in days if d.weekday() < 5][:n]


def test_parses_explicit_qfq_response_and_rejects_duplicate_or_invalid_price():
    assert parse_prices(
        {"code": 0, "data": {"sh600000": {"qfqday": [["2025-01-06", "1", "2.1234"]]}}}, "sh600000"
    ) == {"2025-01-06": Decimal("2.1234")}
    for rows in [
        [],
        [["2025-01-06", "1", "NaN"]],
        [["2025-01-06", "1", "0"]],
        [["2025-01-06", "1", "1"]] * 2,
    ]:
        with pytest.raises(ValueError):
            parse_prices({"code": 0, "data": {"sh600000": {"qfqday": rows}}}, "sh600000")


def test_high_counts_distinct_stock_once_in_week_and_ma_is_strict():
    days = sessions()
    histories = {
        "up": {d: Decimal(i + 1) for i, d in enumerate(days)},
        "flat": {d: Decimal(10) for d in days},
    }
    result = price_breadth(histories, days, "2025-06-01", 3)
    for key in ("ma30", "high60"):
        last = result[key][-1]
        assert last["numerator"] == 1
        assert last["eligible"] == 2
        assert Decimal(last["value"]) == 50
        assert last["universe"] == 3


def test_gap_and_short_listing_are_excluded_and_partial_week_marked():
    days = sessions()
    up = {d: Decimal(i + 1) for i, d in enumerate(days)}
    gap = dict(up)
    gap.pop(days[-10])
    result = price_breadth({"up": up, "gap": gap, "ipo": {days[-1]: Decimal(1)}}, days, days[-1], 3)
    assert result["ma30"][-1]["eligible"] == 1
    assert result["high60"][-1]["eligible"] == 1
    assert result["high60"][-1]["partial"]


def test_early_week_high_survives_friday_pullback():
    days = sessions()
    prices = {d: Decimal(10) for d in days}
    prices[days[-5]] = Decimal(20)
    result = price_breadth({"stock": prices}, days, "2025-06-01", 1)
    assert result["high60"][-1]["numerator"] == 1
    assert result["ma30"][-1]["numerator"] == 0


def test_truncated_full_windows_do_not_create_a_thin_early_rank_history():
    days = sessions(700)
    histories = {
        "old": {d: Decimal(1) for d in days[:640]},
        "current": {d: Decimal(2) for d in days[60:]},
        "ipo": {days[-1]: Decimal(3)},
    }
    result = price_breadth(histories, days, days[-1], 3)
    assert result["ma30"][0]["date"] >= days[60]
    assert len(result["ma30"]) > 100, "IPO history must not truncate the market's window"
