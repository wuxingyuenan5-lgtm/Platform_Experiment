from decimal import Decimal

import pytest

from app.research_cn_monitor import industry_growth, merge_history, parse, series


def test_zero_and_missing_preserved_and_dates_sorted():
    assert series([{"date": "2026-10-30", "x": None}, {"date": "2026-10-29", "x": 0}], {"value": "x"}) == [
        {"date": "2026-10-29", "value": Decimal(0)}, {"date": "2026-10-30", "value": None}]
    with pytest.raises(ValueError, match="duplicate"):
        series([{"date": "2026-10-30", "x": 1}] * 2, {"value": "x"})


def test_congestion_ratio_and_masked_dates():
    result = parse("congestion", {"items": [
        {"date": "2026-08-13", "congestion": "0.4946", "top5Amount": 4946, "totalAmount": 10000},
        {"date": "2026-10-30"}]})
    assert result[0]["value"] == Decimal("49.4600")
    assert result[1]["value"] is None
    with pytest.raises(ValueError, match="ratio_mismatch"):
        parse("congestion", {"items": [{"date": "2026-10-30", "congestion": .4, "top5Amount": 1, "totalAmount": 10}]})


def test_invalid_fund_percent_rejected():
    with pytest.raises(ValueError, match="fund_position_invalid"):
        parse("fund_stock", [{"date": "2026-10-30", "position": "101"}])


def test_congestion_index_closes_match_only_same_trading_day(monkeypatch):
    from app import research_etf_tracking
    from app.research_cn_monitor import _congestion_with_indices

    histories = {"hs300": [{"date": "2026-11-17", "close": "3979.8"}],
                 "chinext": [{"date": "2026-11-18", "close": "2311.62"}]}
    monkeypatch.setattr(research_etf_tracking, "read", lambda path: {
        "data": {"rows": histories.get(path.rsplit("/", 1)[-1], [])}})
    source = {"data": [{"date": "2026-11-17", "value": "31.00"}]}
    assert _congestion_with_indices(source)["data"] == [
        {**source["data"][0], "hs300": Decimal("3979.8"), "chinext": None, "star50": None}]


def test_public_industry_window_alignment():
    with pytest.raises(ValueError, match="dates_mismatch"):
        parse("industry", {"dates": ["2026-10-30"], "swCodeNames": [{"indexCode": "a", "indexName": "A"}], "congestions": {"a": []}})


def test_congestion_joins_history_and_platform_without_filling_missing_sessions(monkeypatch, tmp_path):
    from app import data_audit_calendar, research_etf_tracking
    from app.research_cn_monitor import read_monitor
    from app.research_equity_sources import publish_artifact

    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    monkeypatch.setattr(research_etf_tracking, "read", lambda _: {})
    monkeypatch.setattr(data_audit_calendar, "cached_sessions", lambda _: ["2026-11-18", "2026-11-19"])
    publish_artifact("cn-monitor", {"sources": {"congestion": {
        "data": [{"date": "2026-09-03", "value": "43.56"}, {"date": "2026-09-04", "value": None}],
    }}})
    publish_artifact("cn", {
        "structure": {"date": "2026-11-20", "closed": False, "market": {"top20AmountPct": "1"}},
        "structureHistory": [{"date": "2026-11-17", "top20AmountPct": "12.66"},
                             {"date": "2026-11-19", "top5PctAmountShare": "42.50"}],
    })

    source = read_monitor(["congestion"])["sources"]["congestion"]
    assert source["referenceEnd"] == "2026-09-03"
    assert source["platformStart"] == "2026-11-19"
    assert [(row["date"], row["value"]) for row in source["data"]] == [
        ("2026-09-03", "43.56"), ("2026-09-04", None), ("2026-11-18", None),
        ("2026-11-19", "42.50"),
    ]


def test_history_retained_and_same_date_revision():
    old = [{"date": "2026-09-01", "value": "1"}, {"date": "2026-10-30", "value": "2"}]
    assert merge_history(old, [{"date": "2026-10-30", "value": "3"}]) == [old[0], {"date": "2026-10-30", "value": "3"}]


def test_growth_industries_exclude_aggregate_and_compute_pp():
    def row(code, toggle=True):
        return f'''<tr class="sw-industry-item"><td><a href="/stockdata/sw-industry-2021?industryCode={code}">行业{code}</a>
        {f'<a class="sw-sub-toggle" data-code="{code}"></a>' if toggle else ''}</td>
        <td class="current-value">-3.36%</td><td class="before-value">-2.44%</td><td class="dif-value">-0.92%</td></tr>'''
    html = '<table class="middle-avg-indicator-table"><thead><tr><th>2026-09-30</th><th>2026-06-30</th></tr></thead><tbody>'
    html += ''.join(row(str(n)) for n in range(31)) + row('all', False) + '</tbody></table>'
    result = industry_growth(html)
    assert len(result) == 31
    assert result[0]['change'] == Decimal('-.92')
    assert result[0]['previousDate'] == '2026-06-30'
