from copy import deepcopy
from decimal import Decimal

from app.research_etf_broad import INNOVATION, merge_rows, project


def inputs():
    day = "2026-11-05"
    codes = [*INNOVATION, "510300"]
    markets = {c: {day: {"amount": str((i + 1) * 100000000)}} for i, c in enumerate(codes)}
    funds = {c: {day: {"flowYi": "1"}} for c in INNOVATION}
    reference = {
        "broadData": {"dates": [day], "cats": ["A", "B"], "series": {"A": [2], "B": [3]}},
        "indexPrices": {"hs300": {"rows": [{"date": day, "close": "4113.41"}]}},
    }
    return day, codes, markets, funds, reference


def test_broad_turnover_ratios_and_historical_signals_use_the_same_universe():
    day, codes, markets, funds, reference = inputs()
    rows = merge_rows([], [day], {day: codes}, markets, funds)
    assert rows[0]["amountYi"] == "21" and rows[0]["expected"] == rows[0]["covered"] == 6
    result = project(reference, {"rows": rows})
    assert result["broadDailyData"]["amount"] == [21]
    assert result["broadDailyData"]["netflow"] == [5]
    ratio = result["broadInnovationRatio"]["rows"][0]
    assert Decimal(ratio["turnoverPct"]) == Decimal(15) / 21 * 100
    assert Decimal(ratio["netSubscriptionPct"]) == 100
    assert ratio["basketAmountYuan"] == "2100000000"
    assert result["broadCmpData"]["latest"]["netflow"] == 5
    assert result["broadCmpData"]["support"] == []
    reference["broadData"]["series"]["A"] = [101]
    assert project(reference, {"rows": rows})["broadCmpData"]["support"][0]["netflow"] == 104


def test_missing_member_keeps_available_total_ratio_and_reports_exact_coverage():
    day, codes, markets, funds, reference = inputs()
    old = [{"date": "2026-11-04", "amountYi": "42"}]
    saved = deepcopy(old)
    del markets[codes[-1]][day]
    rows = merge_rows(old, [day], {day: codes}, markets, funds)
    assert old == saved and rows[0] == saved[0]
    assert rows[-1]["amountYi"] == "15" and rows[-1]["covered"] == 5
    assert rows[-1]["missingCodes"] == [codes[-1]] and rows[-1]["status"] == "partial"
    result = project(reference, {"rows": rows})
    assert result["broadDailyData"]["amount"] == [15]
    assert result["broadDailyData"]["netflow"] == [5]
    assert result["broadInnovationRatio"]["rows"][0]["turnoverPct"] == "100"
    assert "5/6" in result["broadInnovationRatio"]["rows"][0]["qualityNote"]
    assert result["broadInnovationRatio"]["rows"][0]["netSubscriptionPct"] == "100"


def test_explicit_zero_unknown_and_nonfinite_amounts_are_distinct():
    day, codes, markets, funds, reference = inputs()
    for c in codes:
        markets[c][day]["amount"] = "0"
    rows = merge_rows([], [day], {day: codes}, markets, funds)
    assert rows[0]["amountYi"] == "0"
    assert (
        project(reference, {"rows": rows})["broadInnovationRatio"]["rows"][0]["turnoverPct"] is None
    )
    markets[codes[-1]][day]["amount"] = "NaN"
    partial = merge_rows([], [day], {day: codes}, markets, funds)[0]
    assert partial["amountYi"] == "0" and partial["covered"] == 5
    assert partial["missingCodes"] == [codes[-1]]
    assert merge_rows([], [day], {}, markets, funds)[0]["amountYi"] is None


def test_listing_boundary_and_missing_innovation_use_the_observed_denominator():
    day, codes, markets, funds, reference = inputs()
    del markets[codes[0]][day]
    rows = merge_rows([], [day], {day: codes}, markets, funds, {codes[-1]: "2026-11-06"})
    assert rows[0]["expected"] == 5 and rows[0]["covered"] == 4
    assert rows[0]["amountYi"] == "14" and rows[0]["selectedAmountYuan"] == "1400000000"
    assert (
        project(reference, {"rows": rows})["broadInnovationRatio"]["rows"][0]["turnoverPct"]
        == "100"
    )
    unknown = merge_rows([], [day], {day: codes}, {}, {})[0]
    assert unknown["covered"] == 0 and unknown["amountYi"] is None
    assert len(unknown["missingCodes"]) == 6


def test_quality_snapshot_separates_historical_gaps_from_current_members():
    from app.research_etf_broad import quality_snapshot

    day, codes, markets, funds, _ = inputs()
    catalog = [{"code": c, "symbol": "sz" + c, "name": c} for c in codes]
    rows = merge_rows([], [day], {day: codes}, markets, funds)
    rows.insert(0, {"date": "2026-11-04", "missingCodes": [codes[0]], "status": "partial"})
    market_docs = {c: {"rows": [{"date": day, **value[day]}]} for c, value in markets.items()}
    fund_docs = {c: {"rows": [{"date": day, **value[day]}]} for c, value in funds.items()}
    doc = quality_snapshot(catalog, rows, market_docs, fund_docs, {})
    assert doc["partialDates"] == doc["missingInputs"] == 1
    assert doc["members"][0]["missingDates"] == ["2026-11-04"]
    assert doc["members"][0]["turnoverReady"] is True and doc["members"][0]["flowReady"] is True
