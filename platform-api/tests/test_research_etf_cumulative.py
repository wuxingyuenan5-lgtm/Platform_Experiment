from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.research_etf_cumulative import MINUTES, SLOTS, build_cumulative, day_curve


def rows(day, slots=SLOTS, amount="100000000"):
    return [{"day": f"{day} {slot}:00", "amount": amount} for slot in slots]


def fixture():
    dates = [(date(2026, 10, 1) + timedelta(days=i)).isoformat() for i in range(21)]
    basket = ("sh000001", *(f"sh{510000+i}" for i in range(25)))
    docs = {"minutes-5m/"+symbol: {"days": {
        day: rows(day, amount=str((i+1)*100000000)) for i, day in enumerate(dates)
    }} for symbol in basket[1:]}
    return dates, basket, docs


def test_exact_windows_use_all_25_members_and_exclude_today():
    dates, basket, docs = fixture()
    result = build_cumulative(lambda key: docs.get(key, {}), basket, dates, dates[-1])
    assert result["status"] == "ready"
    assert result["requestedDays"] == dates[:20]
    assert result["avg5Days"] == 5 and result["avgDays"] == 20
    assert result["avg5"][-1] == 25*48*18
    assert result["avg20"][-1] == 25*48*10.5
    assert len(result["slots"]) == len(result["avg20"]) == 49
    assert result["slots"][24:27] == ["11:30", "13:05", "13:10"]


def test_missing_member_bar_never_shrinks_a_window_or_fills_zero():
    dates, basket, docs = fixture()
    docs["minutes-5m/"+basket[-1]]["days"][dates[0]].pop()
    result = build_cumulative(lambda key: docs.get(key, {}), basket, dates, dates[-1])
    assert result["avg20"] == [] and result["avgDays"] == 19
    assert result["avg5Days"] == 5
    assert result["missingDays"] == [dates[0]]
    docs["minutes-5m/"+basket[-1]]["days"][dates[19]].pop()
    result = build_cumulative(lambda key: docs.get(key, {}), basket, dates, dates[-1])
    assert result["avg5"] == [] and result["avg5Days"] == 0


@pytest.mark.parametrize("amount", ["-1", "NaN", "Infinity", None])
def test_invalid_amount_rejected(amount):
    data = rows("2026-11-04")
    data[0]["amount"] = amount
    assert day_curve(data, "2026-11-04", 5) is None


def test_explicit_zero_is_valid_but_duplicate_or_missing_bar_is_not():
    data = rows("2026-11-04", amount="0")
    assert day_curve(data, "2026-11-04", 5) == [Decimal(0)]*49
    assert day_curve(data+[deepcopy(data[0])], "2026-11-04", 5) is None
    assert day_curve(data[:-1], "2026-11-04", 5) is None


def test_existing_original_minutes_roll_forward_without_interpolation():
    dates, basket, docs = fixture()
    symbol = basket[-1]
    latest = dates[19]
    del docs["minutes-5m/"+symbol]["days"][latest]
    docs["minutes/"+symbol] = {"days": {latest: rows(latest, MINUTES, "400000000")}}
    result = build_cumulative(lambda key: docs.get(key, {}), basket, dates, dates[-1])
    assert result["status"] == "ready"
    assert result["inputMethods"][latest][symbol] == "aggregated_original_1min"
    assert result["prev"][-1] == 25*48*20
    docs["minutes/"+symbol]["days"][latest].pop(10)
    result = build_cumulative(lambda key: docs.get(key, {}), basket, dates, dates[-1])
    assert result["avg5"] == []
