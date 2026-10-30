from decimal import Decimal

import pytest

from app.research_cn_financing import daily_summary, weekly_summary

pytestmark = pytest.mark.unit


def test_daily_preserves_sessions_negative_flow_and_missing_member():
    index = [
        {"date": "2026-10-09", "close": "100"},
        {"date": "2026-10-12", "close": "110"},
        {"date": "2026-10-13", "close": "99"},
    ]
    members = [
        {
            "meta": {"code": "a", "name": "A"},
            "series": [
                {"date": "2026-10-12", "flow_yi": "1.25", "etf_qfq_turnover_est_yi": "2.1"},
                {"date": "2026-10-13", "flow_yi": "-0.25", "etf_qfq_turnover_est_yi": "3.1"},
            ],
        },
        {
            "meta": {"code": "b", "name": "B"},
            "series": [
                {"date": "2026-10-12", "flow_yi": "-2.5", "etf_qfq_turnover_est_yi": "1.1"},
            ],
        },
    ]
    rows = daily_summary(members, index)
    assert [r["date"] for r in rows] == [r["date"] for r in index]
    assert rows[0]["total"] is None and rows[0]["indexReturnPct"] is None
    assert rows[1]["total"] == "-1.25"
    assert rows[1]["turnoverYi"] == "3.2"
    assert Decimal(rows[1]["indexReturnPct"]) == 10
    assert Decimal(rows[2]["indexReturnPct"]) == -10
    assert rows[2]["funds"][0]["value"] == "-0.25"
    assert rows[2]["total"] is None and rows[2]["turnoverYi"] is None


def test_weekly_uses_actual_sessions_and_keeps_missing_member_null():
    members = [
        {
            "meta": {"code": "a", "name": "A"},
            "series": [
                {"date": "2026-10-08", "flow_yi": "1.25"},
                {"date": "2026-10-09", "flow_yi": "-0.25"},
                {"date": "2026-10-12", "flow_yi": "0"},
            ],
        },
        {
            "meta": {"code": "b", "name": "B"},
            "series": [
                {"date": "2026-10-08", "flow_yi": "3"},
                {"date": "2026-10-12", "flow_yi": "-1"},
            ],
        },
    ]
    index = [{"date": d, "close": "4000"} for d in ["2026-10-08", "2026-10-09", "2026-10-12"]]
    weeks = weekly_summary(members, index)
    assert weeks[0]["weekStart"] == "2026-10-05"
    assert weeks[0]["sessions"] == 2  # National Day holidays are not zero flows.
    assert Decimal(weeks[0]["funds"][0]["value"]) == 1
    assert weeks[0]["funds"][1]["value"] is None
    assert weeks[0]["total"] is None
    assert weeks[1]["total"] == "-1"
    assert weeks[1]["funds"][0]["value"] == "0"


def test_weekly_index_return_uses_previous_session_not_sum_of_daily_returns():
    index = [
        {"date": "2026-10-09", "close": "100"},
        {"date": "2026-10-12", "close": "110"},
        {"date": "2026-10-13", "close": "99"},
    ]
    members = [
        {
            "meta": {"code": "a", "name": "A"},
            "series": [
                {"date": row["date"], "flow_yi": "0", "etf_qfq_turnover_est_yi": "2.2"}
                for row in index
            ],
        }
    ]
    weeks = weekly_summary(members, index)
    assert weeks[0]["indexReturnPct"] is None
    assert Decimal(weeks[1]["indexReturnPct"]) == -1
    assert Decimal(weeks[1]["turnoverYi"]) == Decimal("4.4")


def test_basis_matches_same_date_and_does_not_splice_contracts(monkeypatch):
    from app import research_cn_financing as module

    def local(path):
        if "cffex-contracts" in path:
            return {
                "rows": [
                    {"date": "2026-10-26", "contract": "IF2611", "close": "4077"},
                    {"date": "2026-10-26", "contract": "IF2612", "close": "4049"},
                    {"date": "2026-10-27", "contract": "IF2611", "close": "4090"},
                ]
            }
        return {}

    monkeypatch.setattr(module, "local", local)
    monkeypatch.setattr(
        module,
        "read",
        lambda key: (
            {"data": {"rows": [{"date": "2026-10-26", "close": "4103.54"}]}}
            if key.endswith("hs300")
            else {}
        ),
    )
    result = module.domestic_financing()
    assert len(result["basis"]) == 2
    assert result["basis"][0]["contract"] == "IF2611"
    assert Decimal(result["basis"][0]["basis"]) == Decimal("-26.54")
    assert result["basis"][1]["contract"] == "IF2612"
