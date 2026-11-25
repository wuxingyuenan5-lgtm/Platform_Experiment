"""Public historical inputs: dates, decimal units and first-listing boundary."""

import importlib.util
from decimal import Decimal
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "etf_backfill", Path(__file__).parents[1] / "scripts/backfill_etf_observation_history.py"
)
backfill = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backfill)


def test_nav_script_identity_native_nav_and_shanghai_date():
    text = 'var fS_code = "510300"; var Data_netWorthTrend = [{"x":1698940800000,"y":3.1234}];'
    assert backfill.parse_nav_script(text, "510300") == {"2023-11-03": Decimal("3.1234")}
    with pytest.raises(ValueError):
        backfill.parse_nav_script(text, "510500")


def test_historical_cash_formula_empty_category_and_missing_nav_are_distinct():
    days = ["2026-01-02", "2026-01-05"]
    shares = {
        days[0]: {"510300": "100000000"},
        days[1]: {"510300": "110000000", "588000": "50000000"},
    }
    catalog = [{"code": "510300", "category": "沪深300"}, {"code": "588000", "category": "科创50"}]
    rows, coverage = backfill.category_rows(
        days, shares, {"510300": {days[1]: Decimal("4.1234")}}, catalog
    )
    assert rows[days[1]]["沪深300"] == Decimal(".41234")
    # A new listing is not treated as a daily creation from invented zero shares.
    assert rows[days[1]]["科创50"] == 0
    assert coverage[days[1]]["科创50"] == {"expected": 0, "covered": 0}
    rows, _ = backfill.category_rows(days, shares, {}, catalog)
    assert rows[days[1]]["沪深300"] is None


@pytest.mark.parametrize("flag,wording", [("106", "折算"), ("105", "分拆")])
def test_explicit_conversion_reconciles_return_and_does_not_create_false_cash(flag, wording):
    payload = {
        "Data": {
            "LSJZList": [
                {
                    "FSRQ": "2026-01-05",
                    "DWJZ": "1.01",
                    "JZZZL": "1.00",
                    "FHFCZ": "2",
                    "FHFCBZ": flag,
                    "FHSP": f"每份基金份额{wording}2份",
                }
            ]
        }
    }
    factor = backfill.parse_conversion(payload, "2026-01-05", Decimal("1.01"), Decimal("2"))
    assert factor == 2
    days = ["2026-01-02", "2026-01-05"]
    shares = {days[0]: {"510300": "100000000"}, days[1]: {"510300": "200000000"}}
    navs = {"510300": {days[0]: Decimal("2"), days[1]: Decimal("1.01")}}
    rows, _ = backfill.category_rows(
        days,
        shares,
        navs,
        [{"code": "510300", "category": "沪深300"}],
        {("510300", days[1]): factor},
    )
    assert rows[days[1]]["沪深300"] == 0
    payload["Data"]["LSJZList"][0]["FHFCZ"] = "3"
    with pytest.raises(ValueError):
        backfill.parse_conversion(payload, days[1], Decimal("1.01"), Decimal("2"))


def test_missing_conversion_metadata_is_a_verifiable_gap_not_decimal_crash():
    payload = {"Data": {"LSJZList": [{"FSRQ": "2022-09-02", "FHFCZ": "", "FHFCBZ": ""}]}}
    with pytest.raises(ValueError, match="not explicitly published"):
        backfill.parse_conversion(payload, "2022-09-02", Decimal("2.7109"), Decimal(".9823"))


def load_extension():
    spec = importlib.util.spec_from_file_location("etf_extend", Path(__file__).parents[1] / "scripts/extend_etf_tracking_history.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_margin_native_units_identity_and_net_buy_conservation():
    extension = load_extension()
    row = {"DATE": "2020-12-29 00:00:00", "SCODE": "510300", "RZYE": "123456789.1234", "RZMRE": "11000000", "RZCHE": "20000000", "RZJME": "-9000000", "RQYE": None, "RZRQYE": None}
    payload = {"success": True, "result": {"data": [row]}}
    result = extension.margin_rows(payload, "510300")[0]
    assert result["financing_balance_yi"] == "1.234567891234"
    assert Decimal(result["financing_net_buy_yi"]) == Decimal("-.09")
    assert result["securities_lending_balance_yi"] is None
    with pytest.raises(ValueError, match="identity"):
        extension.margin_rows(payload, "510500")
    row["RZJME"] = "0"
    with pytest.raises(ValueError, match="reconciliation"):
        extension.margin_rows(payload, "510300")


def test_overlap_rejects_changed_adjustment_basis_and_keeps_null():
    extension = load_extension()
    old = [{"date": "2023-12-29", "close": "2.716"}, {"date": "2024-01-02", "close": None}]
    with pytest.raises(ValueError, match="overlap mismatch"):
        extension.check_overlap(old, [{"date": "2023-12-29", "close": "2.687"}], "close")
    assert extension.check_overlap(old, [{"date": "2023-12-29", "close": "2.716"}, {"date": "2024-01-02", "close": "2.655"}], "close") == 1
    assert old[-1]["close"] is None


def test_historical_group_margin_requires_every_fund_and_never_backcasts_index(monkeypatch):
    extension = load_extension()
    old = {"data": {"rows": [{"date": "2023-12-29", "index_financing_balance_yi": "99"}]}}
    documents = {
        "margin/hs300": old,
        "index-turnover/hs300": {"data": {"rows": [{"date": "2020-12-29"}, {"date": "2020-12-30"}]}},
        "margin/etfs/510300": {"data": {"rows": [{"date": "2020-12-29", "financing_balance_yi": "1"}, {"date": "2020-12-30", "financing_balance_yi": "1"}]}},
        "margin/etfs/510310": {"data": {"rows": [{"date": "2020-12-30", "financing_balance_yi": "2"}]}},
    }
    monkeypatch.setattr(extension.tracking, "read", lambda path: documents.get(path, {}))
    monkeypatch.setattr(extension.tracking, "write", lambda path, doc: documents.update({path: doc}))
    members = [{"code": code, "display_group": "宽基/沪深300"} for code in ["510300", "510310"]]
    extension.extend_group_margin(members, "2020-12-29")
    rows = documents["margin/hs300"]["data"]["rows"]
    assert rows[0]["etf_group_financing_balance_yi"] is None
    assert rows[0]["etf_group_coverage"] == "1/2"
    assert rows[1]["etf_group_financing_balance_yi"] == "3"
    assert rows[1]["index_financing_balance_yi"] is None
    assert rows[-1] == old["data"]["rows"][-1]
