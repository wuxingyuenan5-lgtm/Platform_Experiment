import json

import pytest

from app.research_capital_handbook import capital_event_months, normalize, resident_market_rows


def test_resident_market_joins_months_without_bridging_missing_index_months():
    from decimal import Decimal

    residents = [{"date": f"2026-0{month}-01", "personal": "10"} for month in range(1, 6)]
    closes = {
        "2026-01": ("2026-01-30", Decimal("100")),
        "2026-02": ("2026-02-27", Decimal("110")),
        "2026-04": ("2026-04-30", Decimal("100")),
        "2026-05": ("2026-05-29", Decimal("90")),
    }
    rows = resident_market_rows(residents, closes, "2026-02")
    assert [(row["date"], Decimal(row["marketReturnPct"])) for row in rows] == [
        ("2026-02-01", Decimal("10")),
        ("2026-05-01", Decimal("-10")),
    ]


def cache(tmp_path, jobs):
    for job, data in jobs:
        (tmp_path / (job["key"] + ".json")).write_text(
            json.dumps(
                {
                    "request": job,
                    "fetchedAt": "2026-11-08T08:00:00+00:00",
                    "data": data,
                }
            ),
            encoding="utf-8",
        )
    (tmp_path / "plan.json").write_text(
        json.dumps(
            {
                "jobs": [j for j, _ in jobs],
                "asOf": "2026-11-08",
                "industryNames": {"B_X": "电子"},
            }
        ),
        encoding="utf-8",
    )


def job(key, date, options=""):
    return {"key": key, "observationDate": date, "options": options, "requestHash": "fixture"}


def test_institution_previous_quarter_fills_only_missing_report(tmp_path):
    def report(day, current, previous):
        return (
            job(f"institutions-{day}", day),
            [{"REPORTDATE": day, "ORGTDYFPE": "券商",
              "DEC_BENQISHIZHI": current, "DEC_SHANGQISHIZHI": previous}],
        )

    year_end = report("2023-12-31", 40_000, 30_000)
    spring = report("2024-03-31", 50_000, 41_000)
    cache(tmp_path, [year_end, spring])
    assert normalize(tmp_path)["institutions"] == [
        {"date": "2023-09-30", "sourceReportDate": "2023-12-31", "broker": "3"},
        {"date": "2023-12-31", "broker": "4"},
        {"date": "2024-03-31", "broker": "5"},
    ]


def test_foreign_stock_ratio_joins_only_same_month_capitalization(tmp_path):
    cap = job("foreign-market-cap-2026-01-30", "2026-01-30", "IsHistory=1,TradeDate=2026-01-30")
    cache(tmp_path, [(cap, [{"CODES": "B_001071", "SUMMV": 100_000_000_000}])])
    (tmp_path / "public-supplement.json").write_text(json.dumps({"foreign": [
        {"date": "2026-01-31", "equities": "30"}, {"date": "2026-02-28", "equities": "31"},
    ]}), encoding="utf-8")
    assert normalize(tmp_path)["foreignValueShare"] == [
        {"date": "2026-01-31", "equities": "30", "marketDate": "2026-01-30", "sharePct": "3.00"},
    ]


def test_fund_report_uses_css_only_when_ctr_is_missing(tmp_path):
    day = "2026-09-30"
    css = {"date": day, "method": "css", "rows": []}
    (tmp_path / f"fund-stocks-css-{day}.json").write_text(json.dumps(css), encoding="utf-8")
    cache(tmp_path, [])
    assert normalize(tmp_path)["fundStockReports"] == [css]
    stock = {"MSECUCODE": "300308.SZ", "SECURITYSHORTNAME": "Sample", "REPORTDATE": day,
             "ORGTDYFPE": "基金", "DEC_BENQISHIZHI": 10000, "DEC_BENQICHIGU": 40,
             "DEC_SHANGQICHIGU": 30, "INT_CGJGJS": 5}
    cache(tmp_path, [(job(f"public-fund-stocks-{day}", day), [stock])])
    assert normalize(tmp_path)["fundStockReports"][0]["rows"][0]["shareChangeWan"] == "10"


def test_northbound_values_positions_and_rejects_wrong_dates():
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("sectors", Path(__file__).parents[1] / "scripts/collect_capital_sectors.py")
    sectors = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sectors)
    day = "2026-09-30"
    data = [{"DATES": day, "CODES": str(i), "SHAREHDNUM": 100_000_000, "CLOSE": i, "HISSW2021": str(i)}
            for i in range(1, 32)]
    report = sectors.aggregate_north(data, day, day, {str(i) for i in range(1, 32)})
    assert report["coveredCount"] == 31
    assert report["rows"][0]["name"] == "31" and report["rows"][0]["valueYi"] == "31"
    with pytest.raises(ValueError, match="wrong_trading_date"):
        sectors.aggregate_north(data, day, "2026-09-29", set())


def test_premium_subtracts_adjacent_same_year_and_preserves_missing_months():
    from app.research_cn_institutions import monthly_premiums

    rows = [{"date": day, "premiumYtd": total} for day, total in (
        ("2025-12-31", "100"), ("2026-01-31", "12"), ("2026-02-28", "19"), ("2026-04-30", "38"),
    )]
    assert [r["premiumMonth"] for r in monthly_premiums(rows)] == [None, "12", "7", None]


def test_implementation_aggregates_distinct_tranches_and_paid_a_share_dividends():
    issue = {"MSECUCODE": "000973.SZ", "DAT_SHANGSHIRIQI": "02/12/2026", "SUMFINA": 46.8,
             "ATTACHNAME": "notice"}
    issues = [issue, issue, {**issue, "SUMFINA": 9.828347}]
    assert capital_event_months(job("capital-events-seasoned-issues-2026-02-28", "2026-02-28"), issues) == [
        {"date": "2026-02-01", "seasonedIssuance": "56.628347"},
    ]
    dividend = {"SECURITYTYPE": "A股", "DIVCASHPSBFTAX": 0.25, "DIVRTISSBASESHARES": 20_000,
                "DIVPAYDATE": "2026-02-13", "SECUCODE": "000973.SZ", "REPORTDATE": "2025-12-31",
                "DIVIMPLANNCDATE": "2026-02-12"}
    dividends = [dividend, dividend, {**dividend, "SECURITYTYPE": "B股"},
                 {**dividend, "DIVPAYDATE": "2026-03-01"}]
    assert capital_event_months(job("capital-events-cash-dividends-2026-02-28", "2026-02-28"), dividends) == [
        {"date": "2026-02-01", "dividends": "0.50"},
    ]


def test_processing_date_is_not_observation_date_and_null_is_not_zero(tmp_path):
    cache(
        tmp_path,
        [
            (
                job("industry-margin-a", "2024-01-31", "TradeDate=2024-01-31,Ispandas=1"),
                [
                    {
                        "CODES": "B_X",
                        "DATES": "2026-11-08",
                        "RZYE": 200000000,
                        "ALLFREEFLOATMV": 10000000000,
                        "SUMPURMONEY": None,
                        "AMOUNTSUM": 100,
                    },
                ],
            )
        ],
    )
    row = normalize(tmp_path)["margins"][0]
    assert row["date"] == "2024-01-31"
    assert row["balance"] == "2"
    assert float(row["leverage"]) == 2
    assert row["buyShare"] is None


def test_institution_market_value_units_and_report_date(tmp_path):
    j = job("institutions-a", "2026-06-30")
    cache(
        tmp_path,
        [(j, [{"ORGTDYFPE": "基金", "REPORTDATE": "2026-06-30", "DEC_BENQISHIZHI": 123456}])],
    )
    assert normalize(tmp_path)["institutions"][0]["fund"] == "12.3456"
    cache(tmp_path, [(j, [{"ORGTDYFPE": "基金", "REPORTDATE": "2026-09-30"}])])
    with pytest.raises(ValueError, match="report_date"):
        normalize(tmp_path)


def test_partial_issue_months_excluded_and_share_unit_preserved(tmp_path):
    cache(
        tmp_path,
        [
            (
                job("fund-issues-a", "2026-11-08", "StartDate=2023-11-08,EndDate=2026-11-08"),
                [
                    {"ENDDATE": "2023年11月", "FIRSTRAISES": 5},
                    {"ENDDATE": "2023年12月", "FIRSTRAISES": 8, "FIRSTRAISEM": None},
                    {"ENDDATE": "2026年11月", "FIRSTRAISES": 9},
                ],
            )
        ],
    )
    assert normalize(tmp_path)["issues"] == [
        {"date": "2023-12-01", "stock": "8", "mixed": None, "stockCount": None, "mixedCount": None}
    ]


def test_cache_request_identity_required(tmp_path):
    j = job("institutions-a", "2026-06-30")
    cache(tmp_path, [(j, [])])
    p = tmp_path / "plan.json"
    plan = json.loads(p.read_text())
    plan["jobs"][0]["requestHash"] = "changed"
    p.write_text(json.dumps(plan))
    with pytest.raises(ValueError, match="request_hash"):
        normalize(tmp_path)
