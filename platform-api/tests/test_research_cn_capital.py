import asyncio
import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from app import research_cn_capital as capital


def test_capital_broad_etf_card_reuses_overview_scope_not_25_fund_values(monkeypatch):
    dates = [f'2026-11-{i:02d}' for i in range(2, 7)]
    reference = {'dailyData': {'dates': dates, 'netflow': [999] * 5},
                 'broadData': {'dates': dates, 'cats': ['a', 'b'],
                               'series': {'a': [1, 2, 3, 4, 5], 'b': [10, 20, 30, 40, 50]}},
                 'nativeCoverage': {'broad': {dates[-1]: {
                     'a': {'expected': 110, 'covered': 110}, 'b': {'expected': 110, 'covered': 110}}}}}
    monkeypatch.setattr(capital, 'read_artifact', lambda _: {})
    monkeypatch.setattr(capital, 'local', lambda path: {'status': 'ready', 'data': reference}
                        if 'etf-observation' in path else {})
    monkeypatch.setattr('app.data_audit_calendar.cached_sessions', lambda _: dates)
    data = capital.read_capital()
    assert data['broadEtf']['basketCount'] == 220
    assert data['broadEtf']['flow1Yi'] == '55'
    assert data['broadEtf']['flow5Yi'] == '165'
    assert data['broadEtf']['date'] == dates[-1]
    # An unavailable broad source never falls back to the different 25-fund basket.
    reference['broadData']['series']['a'] = []
    missing = capital.read_capital()['broadEtf']
    assert missing['flow1Yi'] is None and missing['flow5Yi'] is None


def issuance_html(value="--"):
    # The live source omits closing tr tags. The parser must still read one month per row.
    return f"""<table><thead><tr><th>月份</th><th>募集资金(亿元)</th>
      <th>首发募集资金(亿元)</th><th>增发募集资金(亿元)</th><th>配股募集资金(亿元)</th>
      </tr></thead><tbody><tr><td>2026-10</td><td>12.30</td><td>{value}</td>
      <td>12.30</td><td>--</td><tr><td>2026-09</td><td>0</td><td>0</td>
      <td>0</td><td>0</td></tbody></table>"""


def test_issuance_missing_is_not_zero_and_source_revisions_are_decimal():
    rows = capital.parse_issuance(issuance_html())
    assert [r["date"] for r in rows] == ["2026-09-01", "2026-10-01"]
    assert rows[0]["ipo"] == "0"
    assert rows[1]["ipo"] is None
    assert Decimal(rows[1]["total"]) == Decimal("12.30")
    with pytest.raises(ValueError, match="columns_changed"):
        capital.parse_issuance(issuance_html().replace("亿元", "万元"))


def test_buyback_actual_amount_is_not_plan_amount_and_ids_must_be_unique():
    raw = {
        "REPURCODE": "1",
        "DIM_SCODE": "000001",
        "SECURITYSHORTNAME": "公司",
        "UPD": "2026-11-03",
        "DIM_DATE": "2026-01-01",
        "DIM_DATE3": "2026-10-31",
        "REPURPROGRESS": "004",
        "REPURAMOUNT": 123456789,
        "REPURAMOUNTLOWER": 200000000,
        "REPURAMOUNTLIMIT": 400000000,
    }
    row = capital.parse_records("buybacks", [raw])[0]
    assert row["amount"] == "1.23456789"
    assert row["lower"] == "2" and row["upper"] == "4"
    assert row["asOf"] == "2026-10-31" and row["date"] == "2026-11-03"
    with pytest.raises(ValueError, match="duplicate_repurchase"):
        capital.parse_records("buybacks", [raw, raw])


def test_unlock_units_and_shareholder_missing_period_remain_explicit():
    row = capital.parse_records(
        "unlocks",
        [
            {
                "SECURITY_CODE": "000001",
                "SECURITY_NAME_ABBR": "公司",
                "FREE_DATE": "2026-11-20",
                "FREE_SHARES_TYPE": "首发",
                "CURRENT_FREE_SHARES": 200,
                "LIFT_MARKET_CAP": 40000,
                "TOTAL_RATIO": "0.05",
            }
        ],
    )[0]
    assert row["amount"] == "4" and row["shares"] == "200" and row["ratio"] == "5.00"
    holder = capital.parse_records(
        "holders",
        [
            {
                "SECURITY_CODE": "000001",
                "SECURITY_NAME_ABBR": "公司",
                "HOLDER_NAME": "股东",
                "NOTICE_DATE": "2026-11-03",
                "START_DATE": None,
                "END_DATE": "2026-11-01",
                "DIRECTION": "减持",
                "CHANGE_NUM": 100,
            }
        ],
    )[0]
    assert holder["start"] is None and holder["price"] is None
    assert holder["direction"] == "减持" and holder["shares"] == "100"
    assert "amount" not in holder


def fund_payload():
    rows = []
    for code, name, kind in [
        ("000001", "基金A", "混合型"),
        ("000002", "基金C", "混合型"),
        ("000003", "海外基金", "QDII-股票"),
        ("000004", "债基", "债券型"),
    ]:
        rows.append([code, name, "管理人", "", kind, "1.2", "2026-10-30", *([""] * 12)])
    return "var newfunddata={datas:" + json.dumps(rows) + ",record:7000,pages:24,curpage:1}"


def test_fund_share_classes_are_never_summed_and_js_is_not_executed():
    rows, total = capital.parse_funds(fund_payload())
    assert [r["code"] for r in rows] == ["000001", "000002"]
    assert [r["shares"] for r in rows] == ["1.2", "1.2"]
    assert total == 7000
    with pytest.raises(ValueError):
        capital.parse_funds("var newfunddata={datas:alert('x'),record:1}")


def test_monthly_gap_joins_period_and_keeps_missing_not_latest_available():
    series = {
        "m": {
            "observations": [
                {"date": "2026-08-01", "value": "7.2"},
                {"date": "2026-09-01", "value": "7.1"},
            ]
        },
        "s": {"observations": [{"date": "2026-08-31", "value": "7.0"}]},
    }
    assert capital.aligned_difference(series, "m", "s", monthly=True) == [
        {"date": "2026-08-01", "value": "0.2"},
        {"date": "2026-09-01", "value": None},
    ]


def test_pagination_rejects_incomplete_counts(monkeypatch):
    class Response:
        content = json.dumps(
            {"success": True, "result": {"data": [], "count": 1, "pages": 1}}
        ).encode()

        def raise_for_status(self):
            pass

    class Client:
        async def get(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr(capital, "archive", lambda *args: "hash")
    with pytest.raises(ValueError, match="incomplete_pages"):
        asyncio.run(capital.fetch_records(Client(), "holders", date(2026, 11, 4)))


def test_source_failure_retains_previous_success_and_does_not_block_others(monkeypatch):
    old = {
        "sources": {
            "buybacks": {
                "status": "ready",
                "fetchedAt": "2026-10-30T00:00:00+00:00",
                "rows": [{"date": "2026-10-30", "amount": "2"}],
            }
        }
    }
    monkeypatch.setattr(capital, "read_artifact", lambda _: old)
    monkeypatch.setattr(capital, "archive", lambda *args: "hash")
    writes = []
    monkeypatch.setattr(capital, "publish_artifact", lambda *args: writes.append(args))

    class Response:
        def __init__(self, text):
            self.text, self.content = text, text.encode()

        def raise_for_status(self):
            pass

    class Client:
        def __init__(self, **kwargs):
            assert kwargs["verify"].verify_mode == 2

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url, **kwargs):
            return Response(issuance_html() if "10jqka" in url else fund_payload())

    async def records(client, key, today):
        if key == "buybacks":
            raise TimeoutError("upstream unavailable")
        return [{"date": "2026-11-04", "amount": None}], ["hash"], "2026-08-06", "2026-11-04"

    monkeypatch.setattr(capital.httpx, "AsyncClient", Client)
    monkeypatch.setattr(capital, "fetch_records", records)
    doc = asyncio.run(capital.collect(force=True))
    assert doc["sources"]["buybacks"]["status"] == "error"
    assert doc["sources"]["buybacks"]["rows"][0]["amount"] == "2"
    assert doc["sources"]["buybacks"]["fetchedAt"] == "2026-10-30T00:00:00+00:00"
    assert all(
        doc["sources"][k]["status"] == "ready" for k in ["issuance", "holders", "unlocks", "funds"]
    )
    assert len(writes) == 5


def test_reads_do_not_fetch_and_malformed_etf_cannot_block_capital_sources(monkeypatch):
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    upcoming = (today + timedelta(days=2)).isoformat()
    old = {
        "sources": {
            "unlocks": {
                "status": "ready",
                "rows": [
                    {"date": upcoming, "amount": "1"},
                    {"date": upcoming, "amount": None},
                    {"date": (today + timedelta(days=30)).isoformat(), "amount": "10"},
                ],
            }
        }
    }
    monkeypatch.setattr(capital, "read_artifact", lambda _: old)
    monkeypatch.setattr(
        capital,
        "local",
        lambda path: (
            {"data": {"dailyData": {"dates": ["2026-11-03"], "netflow": []}}}
            if "etf-observation" in path
            else {}
        ),
    )

    def forbidden(*args, **kwargs):
        pytest.fail("GET must never fetch upstream")

    monkeypatch.setattr(capital.httpx, "AsyncClient", forbidden)
    data = capital.read_capital()
    assert data["sources"]["unlocks"]["isStale"] is True
    assert data["unlockWeeks"][0]["value"] is None
    assert data["unlockWeeks"][0]["events"] == 2
    assert len(data["unlockWeeks"]) == 1
    assert data["etf"]["status"] == "error" and data["etf"]["rows"] == []
