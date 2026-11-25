from decimal import Decimal

import pytest

from app.research_cn_crowding import (
    parse_flow,
    parse_industry_weekly,
    parse_turnover,
    report_count,
    seasonal_reports,
)


def test_public_industry_weekly_share_units_and_missing_values():
    rows = [
        {
            "date": "2026-10-30",
            "amountCongestion": "0.12",
            "turnoverRateF": "2.5",
            "indexClose": "1234.5",
        },
        {"date": "2026-11-05", "indexClose": "1200"},
    ]
    result = parse_industry_weekly({"data": rows})
    assert result[0]["amount"] == Decimal(12)
    assert result[0]["turnover"] == Decimal("2.5")
    assert result[1]["amount"] is None
    with pytest.raises(ValueError, match="industry_share"):
        parse_industry_weekly({"data": [{**rows[0], "amountCongestion": "12"}]})


def test_turnover_preserves_gaps_and_rejects_duplicate_dates():
    rows = [
        {"tradeDate": "2026-01-05", "turnover1d": "0", "hs300Close": "4000"},
        {"tradeDate": "2026-01-06", "hs300Close": "4010"},
    ]
    result = parse_turnover({"data": rows})
    assert result[0]["value"] == Decimal(0)
    assert result[1]["value"] is None
    with pytest.raises(ValueError, match="duplicate"):
        parse_turnover({"data": rows + rows[:1]})


def test_fundflow_converts_yuan_without_losing_sign_or_decimals():
    line = ",".join(["2026-01-05", "-123456789.12"] + ["0"] * 13)
    assert parse_flow({"data": {"klines": [line]}})[0]["value"] == Decimal("-1.2345678912")
    with pytest.raises(ValueError, match="schema"):
        parse_flow({"data": {"klines": ["2026-01-05,1"]}})


def test_rating_count_uses_verified_total_not_returned_page_size():
    raw = {"hits": 719, "data": [{"emRatingCode": "007", "publishDate": "2026-10-30 00:00:00"}]}
    assert report_count(raw, "007", "2026-10-26", "2026-11-01") == 719
    with pytest.raises(ValueError, match="filter"):
        report_count(raw, "006", "2026-10-26", "2026-11-01")
    with pytest.raises(ValueError, match="empty"):
        report_count({"hits": 719, "data": []}, "007", "2026-10-26", "2026-11-01")
    assert report_count({"hits": 0, "data": []}, "007", "2026-10-26", "2026-11-01") == 0


def test_seasonality_requires_three_matching_iso_weeks_and_excludes_partial():
    rows = [
        {"date": day, "count": count, "partial": False}
        for day, count in [
            ("2021-01-10", 30),
            ("2022-01-09", 60),
            ("2023-01-08", 90),
            ("2024-01-07", 100),
        ]
    ]
    result = seasonal_reports(rows)
    assert result[2]["value"] is None
    assert Decimal(result[3]["baseline"]) == 60
    assert Decimal(result[3]["value"]) == 40
    rows[0]["partial"] = True
    assert seasonal_reports(rows)[3]["value"] is None
    assert seasonal_reports([{"date": "2027-01-03", "count": 10}])[0]["value"] is None
