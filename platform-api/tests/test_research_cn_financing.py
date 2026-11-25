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


def test_broad_shares_and_margin_sum_members_without_multiplying_index_margin():
    dates = ["2026-10-12", "2026-10-13"]
    index = [{"date": day, "close": "100"} for day in dates]
    members = [
        {
            "meta": {"code": code, "name": code},
            "series": [
                {
                    "date": day,
                    "flow_yi": "1.1",
                    "etf_qfq_turnover_est_yi": "2.2",
                    "qfq_delta_units_yi": delta,
                    "qfq_total_units_yi": units,
                }
                for day in dates
            ],
            "margin": [
                {"date": day, "financing_balance_yi": balance, "financing_net_buy_yi": "0.1"}
                for day in dates
            ],
        }
        for code, delta, units, balance in [("a", "0.1", "10", "2"), ("b", "-0.3", "20", "3")]
    ]
    margin = [
        {
            "date": day,
            "index_financing_balance_yi": "99",
            "index_financing_net_buy_yi": "-1",
            "index_coverage_pct": "90",
        }
        for day in dates
    ]
    daily = daily_summary(members, index, margin)
    assert Decimal(daily[0]["deltaUnitsYi"]) == Decimal("-0.2")
    assert Decimal(daily[0]["unitsYi"]) == 30
    assert Decimal(daily[0]["financingBalanceYi"]) == 5
    assert Decimal(daily[0]["financingNetBuyYi"]) == Decimal("0.2")
    assert daily[0]["indexFinancingBalanceYi"] == "99"
    assert daily[0]["indexCoveragePct"] == "90"
    weekly = weekly_summary(members, index, margin)[0]
    assert Decimal(weekly["deltaUnitsYi"]) == Decimal("-0.4")
    assert Decimal(weekly["unitsYi"]) == 30  # Stock: last session, not sum.
    assert Decimal(weekly["financingBalanceYi"]) == 5
    assert Decimal(weekly["financingNetBuyYi"]) == Decimal("0.4")
    assert weekly["indexFinancingBalanceYi"] == "99"
    assert Decimal(weekly["indexFinancingNetBuyYi"]) == -2
    assert Decimal(weekly["funds"][1]["deltaUnitsYi"]) == Decimal("-0.6")

    members[1]["series"][1]["qfq_delta_units_yi"] = None
    members[1]["margin"].pop()
    broken = daily_summary(members, index, margin)
    assert broken[1]["deltaUnitsYi"] is None
    assert broken[1]["financingBalanceYi"] is None
    assert broken[1]["indexFinancingBalanceYi"] == "99"
    weekly = weekly_summary(members, index, margin)[0]
    assert weekly["deltaUnitsYi"] is None
    assert weekly["financingNetBuyYi"] is None
    assert weekly["financingBalanceYi"] is None
    assert weekly["funds"][0]["deltaUnitsYi"] == "0.2"


def test_weekly_share_baseline_precedes_first_session_not_last_session():
    dates = ["2026-10-09", "2026-10-12", "2026-10-13"]
    index = [{"date": day, "close": "100"} for day in dates]
    members = [
        {
            "meta": {"code": "a", "name": "A"},
            "series": [
                {"date": day, "flow_yi": "1", "qfq_total_units_yi": str(units)}
                for day, units in zip(dates, [10, 20, 30], strict=True)
            ],
        }
    ]
    daily = daily_summary(members, index)
    assert [r["previousUnitsYi"] for r in daily] == [None, "10", "20"]
    weekly = weekly_summary(members, index)
    assert weekly[1]["previousUnitsYi"] == "10"
    assert weekly[1]["unitsYi"] == "30"


def test_industry_collection_keeps_catalog_and_does_not_borrow_a_benchmark(monkeypatch):
    from app import research_cn_financing as module

    catalog = [
        {
            "code": code,
            "name": code,
            "display_group": "金融/稳定权重",
            "dashboard_eligible": enabled,
        }
        for code, enabled in [("a", True), ("b", True), ("c", False)]
    ]
    monkeypatch.setattr(
        module,
        "read",
        lambda key: (
            {"data": catalog}
            if key == "universe"
            else {"data": {"rows": [{"date": "2026-11-03", "close": "4000"}]}}
        ),
    )

    def detail(code, **kwargs):
        assert code != "c"
        return {
            "meta": next(m for m in catalog if m["code"] == code),
            "series": [{"date": "2026-11-03", "flow_yi": "2", "qfq_total_units_yi": "10"}],
            "margin": [],
            "groupMargin": [],
            "sources": {"market": {"status": "ready"}},
        }

    monkeypatch.setattr(module, "detail", detail)
    monkeypatch.setattr(module, "local", lambda _: {})
    result = module.broad_etfs("finance")
    assert len(result["members"]) == 3 and result["trackedMemberCount"] == 2
    assert result["hasIndex"] is False
    assert Decimal(result["daily"][0]["total"]) == 4
    assert result["daily"][0]["indexClose"] is None
    assert result["daily"][0]["indexFinancingBalanceYi"] is None
    assert any(o["key"] == "finance" and o["kind"] == "sector" for o in result["options"])
    monkeypatch.setattr(
        module, "detail", lambda *a, **k: pytest.fail("catalog must not load histories")
    )
    catalog_only = module.broad_etfs("finance", include_history=False)
    assert len(catalog_only["members"]) == 3
    assert catalog_only["daily"] == [] and catalog_only["weekly"] == []
    assert catalog_only["trackedMemberCount"] == 2


def test_domestic_financing_retains_margin_turnover_share_percent_values(monkeypatch):
    from app import research_cn_financing as module
    ratio = {"seriesId": "cn_margin_buy_share", "unit": "percent", "observations": [
        {"date": "2026-11-04", "value": "7.75"},
        {"date": "2026-11-05", "value": None},
    ]}
    monkeypatch.setattr(module, "local", lambda path: ratio if path.endswith("cn_margin_buy_share.json") else {})
    monkeypatch.setattr(module, "read", lambda _: {})
    result = module.domestic_financing()
    assert next(item for item in result["margin"] if item.get("seriesId") == "cn_margin_buy_share") == ratio


def test_option_iv_indices_map_all_underlyings_and_preserve_same_date_gaps(monkeypatch):
    from app import research_cn_financing as module

    def rows(codes):
        return [{"underlying": code, "date": day, "month": "2611"} for code in codes
                for day in ("2026-11-04", "2026-11-05", "2026-11-06")]

    docs = {
        "etf-option-iv.json": {"rows": rows(("510050", "510300", "510500", "588000", "588080"))},
        "szse-etf-option-iv.json": {
            "methodology": "nearest_delta_half_standard_calls_puts_vega_gamma_iv_252_sessions",
            "rows": rows(("159919", "159922", "159915", "159901")),
        },
    }
    monkeypatch.setattr(module, "local", lambda path: docs.get(path.rsplit("/", 1)[-1], {}))
    values = {"sse50": "2800.12", "hs300": "4000.34", "csi500": "6000.56", "star50": "1200.78",
              "chinext": "2400.10", "sz100": "5000.20"}
    monkeypatch.setattr(module, "read", lambda key: {
        "data": {"rows": [
            {"date": "2026-11-03", "close": "100"},
            {"date": "2026-11-04", "close": values[key.split("/")[-1]]},
            {"date": "2026-11-06", "close": "0"},
        ]}, "url": "https://example.test/index",
    } if key.split("/")[-1] in values else {})
    payload = module.domestic_financing()
    assert len(payload["iv"]["rows"]) == 27
    result = payload["ivIndices"]
    assert [(r["code"], r["underlyings"]) for r in result] == [
        ("000016", ["510050", "HO"]), ("000300", ["510300", "159919", "IO"]),
        ("000905", ["510500", "159922"]), ("000852", ["MO"]), ("000688", ["588000", "588080"]),
        ("399006", ["159915"]), ("399330", ["159901"]),
    ]
    assert next(item for item in result if item["code"] == "000852")["rows"] == []
    for item, value in zip((item for item in result if item["code"] != "000852"), values.values(), strict=True):
        assert item["rows"] == [
            {"date": "2026-11-04", "close": value},
            {"date": "2026-11-06", "close": None},
        ]
        assert item["sourceUrl"] == "https://example.test/index"


def test_margin_index_matches_margin_dates_and_never_fills_missing_prices(monkeypatch):
    from app import research_cn_financing as module

    monkeypatch.setattr(module, "local", lambda path: {
        "observations": [{"date": day, "value": "100"} for day in
                         ["2026-11-03", "2026-11-04", "2026-11-05"]]
    } if path.endswith("cn_margin_financing_balance.json") else {})
    monkeypatch.setattr(module, "read", lambda key: {"data": {"rows": [
        {"date": "2026-11-03", "close": "4054.28"},
        {"date": "2026-11-05", "close": "0"},
        {"date": "2026-11-06", "close": "4100"},
    ]}} if key.endswith("hs300") else {})
    result = module.domestic_financing()["marginIndex"]
    assert result["code"] == "000300"
    assert result["rows"] == [
        {"date": "2026-11-03", "close": "4054.28"},
        {"date": "2026-11-05", "close": None},
    ]


def test_iv_history_owns_timeline_and_uses_earlier_index_archive(monkeypatch):
    from app import research_cn_financing as module

    def local(path):
        if path.endswith('etf-option-iv.json'):
            return {'rows': [{'date': day, 'underlying': '510050', 'month': day[2:7].replace('-', '')} for day in
                             ['2015-02-09', '2015-02-10', '2026-11-06']]}
        if path.endswith('option-index-history.json'):
            return {'indices': {'sse50': {'rows': [
                {'date': '2015-02-09', 'close': '2300'},
                {'date': '2015-02-11', 'close': '2400'},
            ], 'sourceUrl': 'https://example.test/native-history'}}}
        return {}
    monkeypatch.setattr(module, 'local', local)
    monkeypatch.setattr(module, 'read', lambda key: {'data': {'rows': [
        {'date': '2026-11-06', 'close': '2787.41'}
    ]}} if key.endswith('sse50') else {})
    result = module.domestic_financing()['ivIndices'][0]
    assert result['rows'] == [
        {'date': '2015-02-09', 'close': '2300'},
        {'date': '2026-11-06', 'close': '2787.41'},
    ]
    assert result['historySourceUrl'] == 'https://example.test/native-history'
