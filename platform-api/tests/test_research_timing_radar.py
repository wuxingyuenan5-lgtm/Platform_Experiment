from datetime import date, timedelta
from statistics import fmean

from pytest import approx

from app.research_timing_radar import DAILY, FACTORS, MONTHLY, REPORT, rounded
from app.research_timing_radar_model import (
    calculate_factors,
    held_signal,
    month_key,
    monthly_daily,
)


def test_report_four_class_composite_matches_published_value():
    assert len(FACTORS) == len(REPORT["current"]) == len(REPORT["previous"]) == 21
    groups = [
        fmean(
            score
            for factor, score in zip(FACTORS, REPORT["current"], strict=True)
            if factor[3] == group
        )
        for group in range(4)
    ]
    assert rounded(groups) == [0.61, 0.0, -0.6, 0.16]
    assert round(fmean(groups), 2) == 0.04


def test_monthly_value_is_unavailable_before_release_and_missing_never_neutral():
    dates = ["2026-11-19", "2026-11-20", "2026-12-21"]
    months = [month_key("2026-10-01"), month_key("2026-11-01")]
    assert monthly_daily(dates, months, [1, None]) == [None, 1, None]
    assert held_signal([1, 0, None, -1, 0, 0], 2) == [1, 1, None, -1, -1, 0]


def test_21_factor_paths_keep_scores_bounded_and_inputs_unmixed():
    dates = [(date(2025, 1, 1) + timedelta(days=i)).isoformat() for i in range(390)]
    daily = {key: {} for key in DAILY}
    monthly = {key: {} for key in MONTHLY}
    monthly["cpiLevel"] = {}
    daily["price"] = dict(zip(dates, range(100, 490), strict=True))
    daily["turnover"] = dict(zip(dates, range(100, 490), strict=True))
    daily["optionVix"] = dict(zip(dates, range(10, 400), strict=True))
    daily["etf50"] = dict(zip(dates, range(100, 490), strict=True))
    result = calculate_factors(dates, daily, monthly)
    assert set(result) == {factor[0] for factor in FACTORS}
    assert result["optionVix"][1][250] is None
    assert result["optionVix"][1][-1] == -1
    assert result["marginChange"][1][-1] is None
    assert result["priceTrend"][1][-1] in (0, 0.5, 1)
    assert result["priceTrend"][0][-1] == approx(
        (fmean(range(370, 490)) / fmean(range(250, 490)) - 1) * 100
    )
    assert all(
        -1 <= score <= 1 for _, scores in result.values() for score in scores if score is not None
    )
