"""Native ETF date/unit contracts and source-failure isolation."""

import json
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest

from app import research_etf_native as native


def test_cumulative_gap_repairs_only_missing_closed_session_and_reuses_verified_cache(monkeypatch):
    from app.research_etf_cumulative import MINUTES, SLOTS

    symbol, day = "sh512050", "2026-11-05"
    now = datetime(2026, 11, 6, 1, tzinfo=UTC)
    prior = [{"day": "2026-11-04 " + slot + ":00", "amount": "1000000"} for slot in SLOTS]
    docs = {"market/" + symbol: {"rows": [
        {"date": "2026-11-04", "amount": "48000000"},
        {"date": day, "amount": "48000000"},
        {"date": "2026-11-06", "amount": "999999999"},
    ]}, "minutes-5m/" + symbol: {"days": {"2026-11-04": prior}},
        "minutes/" + symbol: {"days": {day: [
            {"day": day + " " + slot + ":00", "amount": "1000000"}
            for slot in MINUTES if slot not in {"14:26", "14:58", "14:59"}
        ]}}}
    calls = []
    monkeypatch.setattr(native, "read", lambda name: docs.get(name, {}))
    monkeypatch.setattr(native, "write_local_json", lambda path, payload: docs.__setitem__(path.removeprefix(native.ROOT).removesuffix(".json"), payload))

    def get(_client, url, **kwargs):
        calls.append(kwargs["params"])
        return httpx.Response(200, request=httpx.Request("GET", url, params=kwargs["params"]), json={"data": {
            "code": "512050", "market": 1,
            "klines": [day + " " + slot + ",1,1,1,1,1,1000000" for slot in SLOTS],
        }})

    monkeypatch.setattr(native, "get", get)
    assert native.repair_cumulative_history(None, symbol, now) == [day]
    assert len(calls) == 1 and calls[0]["klt"] == 5
    assert calls[0]["beg"] == calls[0]["end"] == "20261105"
    stored = docs["minutes-5m/" + symbol]
    assert stored["days"]["2026-11-04"] == prior
    assert len(stored["days"][day]) == 48
    assert Decimal(stored["dailyChecks"][day]["dailyRelativeError"]) == 0
    assert stored["sourcesByDate"][day]["sha256"] == stored["sha256"]
    assert native.repair_cumulative_history(None, symbol, now) == []
    assert len(calls) == 1
    assert "14:26" not in {r["day"][11:16] for r in docs["minutes/" + symbol]["days"][day]}


@pytest.mark.parametrize("fault", ["identity", "bar", "amount"])
def test_cumulative_repair_rejects_invalid_inputs_without_overwriting_old_data(monkeypatch, fault):
    from app.research_etf_cumulative import SLOTS

    docs = {"market/sh512050": {"rows": [{"date": "2026-11-05", "amount": "48000000"}]},
            "minutes-5m/sh512050": {"days": {"retained": []}}}
    monkeypatch.setattr(native, "read", lambda key: docs.get(key, {}))
    writes = []
    monkeypatch.setattr(native, "write_local_json", lambda *args: writes.append(args))
    lines = ["2026-11-05 " + slot + ",1,1,1,1,1," + ("2000000" if fault == "amount" else "1000000") for slot in SLOTS]
    if fault == "bar": lines.pop()
    response = httpx.Response(200, request=httpx.Request("GET", native.DAILY_MARKET), json={"data": {
        "code": "wrong" if fault == "identity" else "512050", "market": 1, "klines": lines}})
    monkeypatch.setattr(native, "get", lambda *args, **kwargs: response)
    with pytest.raises(ValueError):
        native.repair_cumulative_history(None, "sh512050", datetime(2026, 11, 6, 1, tzinfo=UTC))
    assert writes == []
    assert docs["minutes-5m/sh512050"] == {"days": {"retained": []}}


def test_tracking_rejoins_archived_shares_without_overwriting_or_changing_basis():
    data = {"series": [
        {"date": "2025-11-11", "qfq_total_units_yi": "406.3972", "qfq_delta_units_yi": "-0.432"},
        {"date": "2025-11-12", "etf_qfq_close": "4.839", "qfq_total_units_yi": None, "qfq_delta_units_yi": None},
    ]}
    archive = {"sourceUrls": ["exchange"], "rows": [
        {"date": "2025-11-11", "shares": "40639716676", "previousShares": "40682916676"},
        {"date": "2025-11-12", "shares": "40582116676", "previousShares": "40639716676", "shareConversionFactor": "1"},
    ]}
    repaired = native.restore_tracking_shares(data, archive)
    assert repaired["series"][0] == data["series"][0]
    row = repaired["series"][1]
    assert row["qfq_total_units_yi"] == "405.82116676"
    assert row["qfq_delta_units_yi"] == "-0.576"
    assert row["etf_qfq_close"] == "4.839"
    assert row["share_recovery_source"] == "exchange_native_archive"
    assert data["series"][1]["qfq_total_units_yi"] is None
    archive["rows"][0]["shares"] = "100"
    assert native.restore_tracking_shares(data, archive) == data
    assert native.restore_tracking_shares(data, {"rows": archive["rows"][1:]}) == data


def test_fixed_basket_ratios_preserve_signed_values_zero_and_missingness():
    codes = list(native.INNOVATION_CODES) + [str(510001 + i) for i in range(20)]
    basket = ("sh000001", *("sh" + code for code in codes))
    funds = {
        code: {"2026-11-03": {"flowYi": "2" if i < 5 else "-1"}} for i, code in enumerate(codes)
    }
    markets = {"sh" + code: {"2026-11-03": {"amount": "10"}} for code in codes}
    row = native.build_innovation_ratio(funds, markets, basket)["rows"][0]
    assert Decimal(row["netSubscriptionPct"]) == -100
    assert Decimal(row["turnoverPct"]) == 20
    funds[codes[5]]["2026-11-03"]["flowYi"] = "11"
    row = native.build_innovation_ratio(funds, markets, basket)["rows"][0]
    assert Decimal(row["netSubscriptionPct"]) == 500
    funds[codes[5]]["2026-11-03"]["flowYi"] = "9"
    assert (
        native.build_innovation_ratio(funds, markets, basket)["rows"][0]["netSubscriptionPct"]
        is None
    )
    funds[codes[5]]["2026-11-03"]["flowYi"] = None
    row = native.build_innovation_ratio(funds, markets, basket)["rows"][0]
    assert row["netSubscriptionPct"] is None and row["turnoverPct"] == "20.0"
    markets["sh" + codes[0]]["2026-11-03"]["amount"] = None
    assert native.build_innovation_ratio(funds, markets, basket)["rows"][0]["turnoverPct"] is None


def test_sse_units_dates_and_duplicates():
    row = {"STAT_DATE": "2026-11-03", "SEC_CODE": "510310", "TOT_VOL": "123.4567"}
    assert native.parse_sse({"result": [row]}, "2026-11-03") == {"510310": "1234567.0000"}
    with pytest.raises(ValueError):
        native.parse_sse({"result": [row]}, "2026-11-02")
    with pytest.raises(ValueError):
        native.parse_sse({"result": [row, row]}, "2026-11-03")


@pytest.mark.parametrize("unit,factor", [("基金规模(份)", 1), ("基金规模(万份)", 10000)])
def test_szse_declared_units_are_not_inferred_from_value(monkeypatch, unit, factor):
    monkeypatch.setattr(
        native,
        "xlsx_rows",
        lambda _: iter(
            [
                ["日期", "基金代码", "基金简称", unit],
                ["2026-11-03", "159915", "创业板ETF", "1,234.56"],
            ]
        ),
    )
    result = native.parse_szse(b"fixture")
    assert Decimal(result["2026-11-03"]["159915"]) == Decimal("1234.56") * factor


def test_szse_padded_codes_preserve_identity_and_duplicate_rejection(monkeypatch):
    rows = [
        ["日期", "基金代码", "基金简称", "基金规模(份)"],
        ["2026-11-04", "159915  ", "创业板ETF", "1234.56"],
        ["2026-11-04", "\t159919 ", "沪深300ETF", "789.00"],
    ]
    monkeypatch.setattr(native, "xlsx_rows", lambda _: iter(rows))
    assert native.parse_szse(b"fixture") == {
        "2026-11-04": {"159915": "1234.56", "159919": "789.00"}
    }
    rows.append(["2026-11-04", "159915", "创业板ETF", "1234.56"])
    with pytest.raises(ValueError, match="duplicate SZSE share code/date"):
        native.parse_szse(b"fixture")
    rows[-1][1] = "159 915"
    with pytest.raises(ValueError, match="invalid SZSE fund code"):
        native.parse_szse(b"fixture")


def test_closed_daily_quotes_exclude_intraday_and_do_not_invent_amount():
    rows = [{"day": d, "close": "3.123456", "volume": "200"} for d in ("2026-11-03", "2026-11-04")]
    assert native.parse_market(rows, "2026-11-04") == [
        {"date": "2026-11-03", "close": "3.123456", "volume": "200", "amount": None}
    ]


@pytest.mark.parametrize(
    "name,expected",
    [
        ("沪深300ETF易方达", "沪深300"),
        ("沪深300ETF联接A", None),
        ("中证500红利ETF", None),
        ("中证A500ETF增强", None),
        ("创业板50ETF", "创业板50"),
        ("创业板成长ETF", None),
        ("科创创业50ETF", "双创50"),
    ],
)
def test_native_broad_classification_excludes_links_and_style_indices(name, expected):
    assert native.category(name) == expected


def test_native_refresh_uses_dated_exchange_and_nav_inputs_when_other_exchange_fails(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 4, 6, tzinfo=UTC)

    monkeypatch.setattr(native, "datetime", Clock)
    catalog = [["510310", "", "沪深300ETF易方达", "指数型-股票", ""]]
    catalog += [[str(i).zfill(6), "", "普通混合基金", "混合型", ""] for i in range(100)]
    seen = set()

    def transport(request):
        seen.add(request.url.host)
        if request.url.host == "fund.eastmoney.com":
            return httpx.Response(200, text="var r = " + json.dumps(catalog) + ";")
        if request.url.host == "query.sse.com.cn":
            day = request.url.params["STAT_DATE"]
            return httpx.Response(
                200,
                json={
                    "result": [
                        {
                            "STAT_DATE": day,
                            "SEC_CODE": "510310",
                            "TOT_VOL": "12000" if day.endswith("03") else "10000",
                        }
                    ]
                },
            )
        if request.url.host == "www.szse.cn":
            assert request.headers["Cache-Control"] == "no-cache"
            return httpx.Response(503)
        if request.url.host == "api.fund.eastmoney.com":
            return httpx.Response(
                200, json={"Data": {"LSJZList": [{"FSRQ": "2026-11-03", "DWJZ": "2"}]}}
            )
        if request.url.host == "push2his.eastmoney.com":
            code = request.url.params["secid"].split(".")[1]
            return httpx.Response(
                200,
                json={
                    "data": {
                        "code": code,
                        "klines": [
                            d + ",2,2,2,2,100000,200000000" for d in ("2026-11-02", "2026-11-03")
                        ],
                    }
                },
            )
        if request.url.host == "quotes.sina.cn":
            return httpx.Response(
                200,
                json=[
                    {"day": d + " 15:00:00", "close": "2", "volume": "100", "amount": "10"}
                    for d in ("2026-11-02", "2026-11-03")
                ],
            )
        pytest.fail("unexpected data host: " + request.url.host)

    real_client = httpx.Client
    monkeypatch.setattr(
        native.httpx, "Client", lambda **_: real_client(transport=httpx.MockTransport(transport))
    )
    from app.research_local_data import write_local_json

    write_local_json(
        native.ROOT + "market/sh000300.json",
        {"rows": [{"date": "2023-11-03", "close": "3500.1234", "volume": "100", "amount": None}]},
    )
    state = native.refresh(
        [{"code": "510310", "dashboard_eligible": True}], ("sh000001", "sh510310")
    )
    fund = native.read("funds/510310")
    assert state["status"] == "partial"
    assert fund["status"] == "ready"
    assert Decimal(fund["rows"][-1]["flowYi"]) == Decimal("0.4")
    data = native.build_reference({}, ("sh000001", "sh510310"))
    assert data["dailyData"]["netflow"][-1] == 0.4
    assert data["dailyData"]["amount"][-1] == 2
    # Empty categories have no members; available members still contribute.
    assert Decimal(data["broadData"]["total"][-1]) == Decimal("0.4")
    assert "wangwang-etf.com" not in seen
    assert "etf-fund-flow-board.app.workbuddy.host" not in seen
    assert native.read("market/sh510310")["rows"][-1]["volume"] == "10000000"
    assert data["indexPrices"]["hs300"]["rows"][0] == {"date": "2023-11-03", "close": "3500.1234"}
    retained = {
        "broadData": {
            "dates": ["2023-11-03"],
            "cats": list(native.CATEGORIES),
            "series": {c: ["1.2300"] for c in native.CATEGORIES},
            "colors": ["#123456"],
            "total": ["14.76"],
            "totalCum": ["14.76"],
        },
        **{k: v for k, v in data.items() if k != "broadData"},
    }
    refreshed = native.build_reference(retained, ("sh000001", "sh510310"))
    assert Decimal(refreshed["broadData"]["total"][0]) == Decimal("14.76")


def test_expanding_basket_rebuilds_all_dates_and_never_relabels_old_totals(monkeypatch):
    from app.research_etf_observation import SYMBOLS

    days = ["2023-11-01", "2026-11-02", "2026-11-03"]
    catalog = [{"code": s[2:], "name": s[2:], "category": "沪深300"} for s in SYMBOLS[1:]]
    documents = {
        "refresh": {"sessions": days[-2:], "catalog": catalog},
        "shares": {"days": {days[-1]: {m["code"]: "100" for m in catalog}}},
    }
    for symbol in SYMBOLS[1:]:
        documents["funds/" + symbol[2:]] = {
            "status": "ready",
            "rows": [{"date": d, "flowYi": "5"} for d in days],
        }
        documents["market/" + symbol] = {
            "rows": [{"date": d, "amount": "100000000", "close": "2"} for d in days]
        }
    monkeypatch.setattr(native, "read", lambda name: documents.get(name, {}))
    previous = {
        "initData": {"table": [{"code": s[2:]} for s in SYMBOLS[1:21]], "bars": [999]},
        "dailyData": {"dates": days, "amount": [999]*3, "netflow": [999]*3, "idx": [3000]*3},
        "broadData": {"dates": [], "cats": [], "series": {}},
        "cmpData": {"support": [{"date": "2020-01-01", "netflow": 999}]},
        "typData": {"slots": ["09:45"], "supAmt": [20]},
        "cumData": {"prev": [999], "avg20": [999]},
    }
    result = native.build_reference(previous, SYMBOLS)
    assert len(result["initData"]["table"]) == 25
    assert result["basketCodes"] == [s[2:] for s in SYMBOLS[1:]]
    assert result["dailyData"]["netflow"] == [125]*3
    assert result["dailyData"]["amount"] == [25]*3
    assert result["dailyData"]["idx"] == [3000]*3
    assert result["nativeFrom"] == days[0]
    assert [r["date"] for r in result["cmpData"]["support"]] == days
    assert result["cmpData"]["sample"] == {"n": 3, "amtMed": 25}
    assert result["nativeCoverage"]["basket"][days[0]] == {"expected": 25, "flow": 25, "turnover": 25}
    assert result["typData"]["basketCount"] == 20
    assert result["cumData"]["prev"] == []
    assert result["cumData"]["avg20"] == []  # old 20-fund comparison is never presented as 25
    del documents["funds/159977"]["rows"][0]["flowYi"]
    del documents["market/sz159977"]["rows"][0]["amount"]
    result = native.build_reference(previous, SYMBOLS)
    assert result["dailyData"]["netflow"][0] is None
    assert result["dailyData"]["amount"][0] is None
    assert result["innovationRatio"]["rows"][0]["netSubscriptionPct"] is None
    assert result["innovationRatio"]["rows"][0]["turnoverPct"] is None


@pytest.mark.parametrize("hour,minute,cutoff", [(7,0,"2026-11-04"),(7,9,"2026-11-04"),(7,10,"2026-11-05"),(14,0,"2026-11-05")])
def test_closed_cutoff_includes_today_only_after_the_actual_close(hour, minute, cutoff):
    now = datetime(2026,11,4,hour,minute,tzinfo=UTC)
    assert native.closed_market_cutoff(now) == cutoff
    rows = [{"day":"2026-11-04","close":"2","volume":"1","amount":"10"}]
    if (hour, minute) < (7, 10):
        with pytest.raises(ValueError): native.parse_market(rows, cutoff)
    else:
        assert native.parse_market(rows, cutoff)[0]["date"] == "2026-11-04"


def test_pending_retry_queries_only_missing_exchange_date_then_catches_up_without_refetching_successes(
    tmp_path, monkeypatch
):
    from app.research_local_data import write_local_json

    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 4, 14, tzinfo=UTC)

    monkeypatch.setattr(native, "datetime", Clock)
    days = ["2026-11-03", "2026-11-04"]
    baseline_calls = []
    original_repair = native.repair_cumulative_history

    def repair(client, symbol, now):
        baseline_calls.append(symbol)
        return original_repair(client, symbol, now)

    monkeypatch.setattr(native, "repair_cumulative_history", repair)
    catalog = [
        {"code": "510310", "name": "沪深300ETF", "category": "沪深300", "symbol": "sh510310"},
        {"code": "159915", "name": "创业板ETF", "category": "创业板指", "symbol": "sz159915"},
    ]
    listing = [[m["code"], "", m["name"], "指数型-股票", ""] for m in catalog]
    listing += [[str(i).zfill(6), "", "普通混合基金", "混合型", ""] for i in range(100)]
    write_local_json(native.ROOT + "refresh.json", {"sessions": days, "catalog": catalog})
    write_local_json(native.ROOT + "shares.json", {
        "days": {days[0]: {"510310": "100", "159915": "100"}, days[1]: {"510310": "120"}}
    })
    successful = {"status": "ready", "meta": catalog[0], "retrievedAt": "retained",
                  "rows": [{"date": days[1], "shares": "120", "unitNav": "2", "flowYi": "0.0000004"}]}
    write_local_json(native.ROOT + "funds/510310.json", successful)
    write_local_json(native.ROOT + "funds/159915.json", {
        "status": "stale", "meta": catalog[1], "rows": [{"date": days[0], "flowYi": "0"}]
    })
    symbols = set(native.INDEX_SYMBOLS.values()) | {"sh000001", "sh510310", "sz159915"}
    for symbol in symbols:
        write_local_json(native.ROOT + "market/" + symbol + ".json", {
            "status": "ready", "rows": [{"date": days[1], "close": "2", "amount": "10"}]
        })
    published = False
    calls = []

    def transport(request):
        calls.append(str(request.url))
        if request.url.host == "fund.eastmoney.com":
            return httpx.Response(200, text="var r = " + json.dumps(listing) + ";")
        if request.url.host == "quotes.sina.cn":
            assert request.url.params["symbol"] == "sh000001"
            return httpx.Response(200, json=[
                {"day": d + " 15:00:00", "close": "2", "volume": "1", "amount": "10"}
                for d in days
            ])
        if request.url.host == "www.szse.cn":
            assert request.url.params["txtStart"] == days[1]
            assert request.url.params["txtEnd"] == days[1]
            assert request.headers["Cache-Control"] == "no-cache"
            return httpx.Response(200, content=b"published" if published else b"pending")
        if request.url.host == "api.fund.eastmoney.com":
            assert published
            assert request.url.params["fundCode"] == "159915"
            return httpx.Response(200, json={"Data": {"LSJZList": [
                {"FSRQ": d, "DWJZ": "2"} for d in days
            ]}})
        pytest.fail("already complete source was fetched: " + str(request.url))

    monkeypatch.setattr(native, "xlsx_rows", lambda body: iter(
        [["日期", "基金代码", "基金简称", "基金规模(份)"]]
        + ([[days[1], "159915  ", "创业板ETF", "200"]] if body == b"published" else [])
    ))
    real_client = httpx.Client
    monkeypatch.setattr(native.httpx, "Client", lambda **kwargs: real_client(transport=httpx.MockTransport(transport)))
    universe = [{"code": m["code"], "dashboard_eligible": True} for m in catalog]
    basket = ("sh000001", "sh510310", "sz159915")
    pending = native.refresh(universe, basket, pending_only=True)
    assert pending["status"] == "partial"
    assert native.read("funds/159915")["rows"][-1]["date"] == days[0]
    assert not any("api.fund.eastmoney.com" in url for url in calls)
    assert native.read("funds/510310") == successful
    published = True
    calls.clear()
    complete = native.refresh(universe, basket, pending_only=True)
    assert complete["status"] == "ready"
    assert Decimal(native.read("funds/159915")["rows"][-1]["flowYi"]) == Decimal("0.000002")
    assert native.read("funds/510310") == successful
    assert sum("api.fund.eastmoney.com" in url for url in calls) == 1
    data = native.build_reference({}, basket)
    assert data["nativeCoverage"]["basket"][days[1]]["flow"] == 2
    assert Decimal(str(data["dailyData"]["netflow"][-1])) == Decimal("0.0000024")
    calls.clear()
    assert native.refresh(universe, basket, pending_only=True)["status"] == "ready"
    assert len(calls) == 2  # catalog and source trading calendar only
    assert baseline_calls.count("sh510310") == baseline_calls.count("sz159915") == 3


def test_complete_margin_inputs_do_not_refetch_during_pending_nav_retry(tmp_path, monkeypatch):
    from app import research_etf_tracking as tracking
    from app import research_etf_native_margin as margin

    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    day = "2026-11-04"
    universe = [{"code": "510310", "dashboard_eligible": True}]
    for path in ["margin/etfs/510310", *("margin/" + key for key in native.INDEX_SYMBOLS)]:
        tracking.write(path, {"status": "ready", "data": {"rows": [{"date": day}]}})
    monkeypatch.setattr(margin, "collect_day", lambda *args: pytest.fail("complete margin source fetched"))
    assert margin.refresh(None, {"sessions": ["2026-11-03", day]}, universe, pending_only=True) == []


def test_daily_target_switches_at_1510_using_the_existing_exchange_calendar(monkeypatch):
    from contextlib import nullcontext
    from app import data_audit_calendar, database_connection

    monkeypatch.setattr(database_connection, "read_only_connection", lambda: nullcontext(None))
    monkeypatch.setattr(data_audit_calendar, "calendar_snapshot", lambda *args: {
        "days": ["2026-11-02", "2026-11-03", "2026-11-04"]
    })
    assert native.closed_session_target(datetime(2026, 11, 4, 7, 9, tzinfo=UTC)) == "2026-11-03"
    assert native.closed_session_target(datetime(2026, 11, 4, 7, 10, tzinfo=UTC)) == "2026-11-04"


def test_unpublished_exchange_members_never_disappear_from_broad_coverage(monkeypatch):
    from app.research_etf_observation import SYMBOLS
    days=["2026-11-03","2026-11-04"]
    catalog=[{"code":s[2:],"name":s[2:],"category":"沪深300"} for s in SYMBOLS[1:]]
    previous={m["code"]:"100" for m in catalog}
    documents={"refresh":{"sessions":days,"catalog":catalog},"shares":{"days":{days[0]:previous,days[1]:{k:v for k,v in previous.items() if k!="159915"}}}}
    for s in SYMBOLS[1:]:
        documents["funds/"+s[2:]]={"status":"ready","rows":[{"date":days[1],"flowYi":None if s=="sz159915" else "1"}]}
    monkeypatch.setattr(native,"read",lambda name:documents.get(name,{}))
    result=native.build_reference({},SYMBOLS)
    assert result["broadData"]["series"]["沪深300"][-1] == 24
    assert result["nativeCoverage"]["broad"][days[1]]["沪深300"] == {"expected":25,"covered":24,"missingCodes":["159915"]}



def test_after_close_today_is_not_reused_as_its_own_previous_day_curve(monkeypatch):
    class Clock(datetime):
        day=4
        @classmethod
        def now(cls,tz=None):return datetime(2026,11,cls.day,14,tzinfo=UTC)
    monkeypatch.setattr(native,"datetime",Clock)
    slots=[f"{h:02d}:{m:02d}" for h in (9,10,11,13,14,15) for m in range(60) if (571<=h*60+m<=690 or 781<=h*60+m<=900)]
    days=["2026-11-03","2026-11-04"]
    docs={"refresh":{"sessions":days,"catalog":[{"code":"510310","name":"ETF","category":"沪深300"}]},"minutes/sh510310":{"days":{d:[{"day":d+" "+slot+":00","amount":"1000000"} for slot in slots] for d in days}}}
    docs["funds/510310"] = {"rows": [{"date": d, "flowYi": "1"} for d in days]}
    monkeypatch.setattr(native,"read",lambda name:docs.get(name,{}))
    data=native.build_reference({},("sh000001","sh510310"))
    assert data["cumData"]["prevDate"]=="2026-11-03" and data["cumData"]["avgDays"]==1
    Clock.day=5
    data=native.build_reference({},("sh000001","sh510310"))
    assert data["cumData"]["prevDate"]=="2026-11-04" and data["cumData"]["avgDays"]==2
