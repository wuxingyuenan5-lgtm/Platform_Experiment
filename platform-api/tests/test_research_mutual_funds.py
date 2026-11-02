import copy
import json
from decimal import Decimal

import pytest

from app import research_mutual_fund_refresh as refresh
from app import research_mutual_fund_sources as source
from app import research_mutual_funds as funds


def doc(code, now_nav="1000000", now_weight="80", before_nav="1000000", before_weight="50"):
    return {
        "fund": {"code": code},
        "data": {
            "allocations": [
                {
                    "date": "2026-09-30",
                    "navYuan": now_nav,
                    "stockPct": now_weight,
                    "cashPct": "10",
                    "bondPct": None,
                },
                {
                    "date": "2026-06-30",
                    "navYuan": before_nav,
                    "stockPct": before_weight,
                    "cashPct": None,
                    "bondPct": None,
                },
            ],
            "industries": [
                {
                    "date": "2026-09-30",
                    "rows": [
                        {"market": "CN", "code": "C", "name": "制造业", "weightPct": now_weight}
                    ],
                },
                {
                    "date": "2026-06-30",
                    "rows": [
                        {"market": "CN", "code": "C", "name": "制造业", "weightPct": before_weight}
                    ],
                },
            ],
        },
    }


def position(code="600000", shares="100", value="1000", weight="0.1"):
    return {
        "code": code,
        "market": "CN",
        "name": code,
        "shares": shares,
        "valueYuan": value,
        "weightPct": weight,
    }


def test_directory_merges_classes_but_excludes_passive_qdii_and_backends():
    rows = [
        ["000001", "X", "基金A", "混合型-偏股", "X"],
        ["000002", "X", "基金C", "混合型-偏股", "X"],
        ["000003", "X", "基金A(后端)", "混合型-偏股", "X"],
        ["000004", "X", "指数A", "指数型-股票", "X"],
        ["000005", "X", "海外A", "QDII-普通股票", "X"],
    ]
    actual = source.catalog("var r = " + json.dumps(rows) + ";")
    assert len(actual) == 1 and len(actual[0]["classes"]) == 2
    assert actual[0]["code"] == "000001"
    with pytest.raises(ValueError):
        source.catalog("var r = []; fetch('evil')")


def test_archive_is_never_executed_and_quantities_keep_units():
    html = """<div class='boxitem'><h4><a href='https://fund.eastmoney.com/000001.html'>基金</a><font>2026-06-30</font></h4>
    <table><thead><tr><th>股票代码</th><th>股票名称</th><th>占净值比例</th><th>持股数（万股）</th><th>持仓市值（万元）</th></tr></thead>
    <tbody><tr><td><a href='//quote.eastmoney.com/unify/r/116.00700'>00700</a></td>
    <td>腾讯</td><td>0.00%</td><td>1.1234</td><td>3,000.01</td></tr></tbody></table>
    <div class='tfoot'>收起持仓明细</div></div>"""
    body = "var apidata={content:" + json.dumps(html, ensure_ascii=False) + "};"
    result = source.holdings(body, "000001")[0]
    assert result["coverage"] == "full"
    assert result["rows"][0] == {
        "code": "00700",
        "market": "HK",
        "name": "腾讯",
        "weightPct": "0.00",
        "shares": "11234.0000",
        "valueYuan": "30000100.00",
    }
    with pytest.raises(ValueError):
        source.holdings(body.replace("万股", "股"), "000001")
    with pytest.raises(ValueError):
        source.holdings(body, "000002")
    with pytest.raises(ValueError):
        source.archive_html('var apidata={content: (function(){return "bad"})()};')


def test_missing_is_not_zero_and_nonfinite_is_rejected():
    assert source.number("---") is None
    assert source.number("0.00%") == "0.00"
    for value in ("NaN", "Infinity", "-1", "invalid"):
        with pytest.raises(ValueError):
            source.number(value)


def test_qoq_uses_common_funds_not_growing_sample():
    first = doc("000001")
    newcomer = doc("000002", now_nav="9000000", now_weight="20")
    newcomer["data"]["allocations"] = newcomer["data"]["allocations"][:1]
    newcomer["data"]["industries"] = newcomer["data"]["industries"][:1]
    result = funds.aggregate([first, newcomer], "2026-09-30")
    assert Decimal(result["summary"]["stockPct"]) == 26
    assert Decimal(result["summary"]["stockChangePp"]) == 30
    assert result["summary"]["commonCount"] == 1
    assert Decimal(result["industries"][0]["changePp"]) == 30


def test_industry_missing_tables_do_not_dilute_denominator():
    a, b = doc("000001"), doc("000002", now_nav="9000000", now_weight="20")
    b["data"]["industries"] = []
    result = funds.industry_rows([a, b], "2026-09-30")[0]
    assert Decimal(result["weightPct"]) == 80
    assert result["sampleCount"] == 1
    a["data"]["industries"][0]["rows"][0]["weightPct"] = "10"
    assert funds.industry_rows([a], "2026-09-30") == []


def test_stock_comparison_excludes_entering_holder_and_keeps_price_separate():
    a, b = doc("000001"), doc("000002")
    a["data"]["holdings"] = [
        {"date": "2026-09-30", "rows": [position(shares="100", value="500")]},
        {"date": "2026-06-30", "rows": [position(shares="100", value="1000")]},
    ]
    b["data"]["holdings"] = [{"date": "2026-09-30", "rows": [position(shares="900", value="4500")]}]
    row = funds.aggregate([a, b], "2026-09-30")["stocks"][0]
    assert row["fundCount"] == 2 and row["comparableCount"] == 1
    assert Decimal(row["shareChangePct"]) == 0
    assert Decimal(row["valueYuan"]) == 5000


def test_halfyear_full_list_does_not_expand_top_ten_aggregate():
    a = doc("000001")
    a["data"]["holdings"] = [
        {
            "date": "2026-06-30",
            "coverage": "full",
            "rows": [position(code=str(600000 + i)) for i in range(15)],
        }
    ]
    assert len(funds.aggregate([a], "2026-06-30")["stocks"]) == 10


def test_inconsistent_class_nav_cannot_weight_combined_portfolio():
    a = doc("000001")
    a["data"]["holdings"] = [{"date": "2026-09-30", "rows": [position(value="100000", weight="5")]}]
    assert funds.portfolio_nav(a, "2026-09-30") is None
    assert funds.aggregate([a], "2026-09-30")["summary"]["stockPct"] is None


def test_report_dates_are_independent_of_acquisition_and_handle_chinese_year():
    result = source.reports(
        json.dumps(
            {
                "Data": [
                    {
                        "FUNDCODE": "000001",
                        "TITLE": "基金二0二六年第3季度报告",
                        "PUBLISHDATE": "2026-10-27T00:00:00",
                        "ID": "AN202610270001",
                    }
                ]
            }
        ),
        "000001",
    )[0]
    assert result["date"] == "2026-09-30" and result["publishedAt"] == "2026-10-27"
    assert result["url"].startswith("https://pdf.dfcfw.com/")


def test_date_regression_fails_and_full_history_is_preserved():
    before = [{"date": "2026-06-30", "coverage": "full", "rows": [position()]}]
    new = [
        {"date": "2026-09-30", "coverage": "top10", "rows": []},
        {"date": "2026-06-30", "coverage": "top10", "rows": []},
    ]
    assert refresh.merge_periods(before, new)[1]["rows"]
    with pytest.raises(ValueError):
        refresh.merge_periods(new, before)


def test_failed_transport_keeps_last_good_values_and_dates(monkeypatch):
    original = doc("000001") | {
        "sources": {"allocations": {"status": "ready", "retrievedAt": "2026-10-01T00:00:00+00:00"}}
    }
    published = {}
    monkeypatch.setattr(refresh, "read", lambda _: copy.deepcopy(original))
    monkeypatch.setattr(refresh, "write", lambda key, value: published.update({key: value}))
    monkeypatch.setattr(refresh, "fetch", lambda *a, **k: (_ for _ in ()).throw(TimeoutError()))
    refresh.collect(None, {"code": "000001"}, 2026)
    result = published["funds/000001"]
    assert result["data"]["allocations"] == original["data"]["allocations"]
    assert result["sources"]["allocations"]["retrievedAt"] == "2026-10-01T00:00:00+00:00"
    assert result["sources"]["allocations"]["status"] == "stale"


def test_invalid_fund_identity_cannot_read_arbitrary_artifact():
    with pytest.raises(ValueError):
        funds.detail("../../universe")


def test_same_hk_industry_code_with_different_chinese_labels_is_one_industry():
    a, b = doc("000001"), doc("000002")
    for item, label in ((a, "非日常生活消费品"), (b, "非必需消费品")):
        for row in item["data"]["industries"]:
            row["rows"][0].update(market="HK", code="25", name=label)
    result = funds.aggregate([a, b], "2026-09-30")["industries"]
    assert len(result) == 1 and result[0]["name"] == "非必需消费品"
    assert result[0]["fundCount"] == 2
    assert Decimal(result[0]["changePp"]) == 30


def test_allocation_ignores_inception_date_and_preserves_missing_bond():
    body = """<title>基金(000001)</title><table><tr><th>报告期</th><th>股票占净比</th>
    <th>债券占净比</th><th>现金占净比</th><th>净资产（亿元）</th></tr>
    <tr><td>2026-09-30</td><td>80%</td><td>---</td><td>10%</td><td>1.23</td></tr>
    <tr><td>2001-12-18</td><td>0%</td><td>---</td><td>100%</td><td>0.00</td></tr></table>"""
    rows = source.allocations(body, "000001")
    assert len(rows) == 1 and rows[0]["bondPct"] is None
    assert Decimal(rows[0]["navYuan"]) == Decimal("123000000")


def test_ready_components_are_not_refetched_when_only_one_source_failed(monkeypatch):
    from datetime import UTC, datetime

    original = doc("000001")
    original["sources"] = {
        key: {"status": "ready", "retrievedAt": datetime.now(UTC).isoformat()}
        for key in ("profile", "allocations", "sizes", "industries", "reports", "holdings")
    }
    original["sources"]["reports"]["status"] = "no_data"
    calls = []
    monkeypatch.setattr(refresh, "read", lambda _: copy.deepcopy(original))
    monkeypatch.setattr(refresh, "write", lambda *a: None)

    def failed(*args, **kwargs):
        calls.append(args[1])
        raise TimeoutError()

    monkeypatch.setattr(refresh, "fetch", failed)
    refresh.collect(None, {"code": "000001"}, 2026)
    assert calls == ["https://api.fund.eastmoney.com/f10/JJGG"]


def test_detail_never_calls_upstream_and_unreported_is_not_a_purchase(monkeypatch):
    document = doc("000001")
    document["data"]["holdings"] = [
        {"date": "2026-09-30", "rows": [position()]},
        {"date": "2026-06-30", "rows": [position(code="600001")]},
    ]
    monkeypatch.setattr(funds, "read", lambda _: document)
    result = funds.detail("000001")["data"]["holdings"][0]["rows"][0]
    assert result["shareChangePct"] is None and result["comparison"] == "newly_disclosed"
