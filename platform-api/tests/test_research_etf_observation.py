import copy
import json
from datetime import UTC, datetime

import httpx
import pytest

from app import research_etf_observation as etf


@pytest.fixture(autouse=True)
def native_reference_inputs(monkeypatch):
    from app import research_etf_native as native

    def build(*_):
        data = reference()
        data["dailyData"]["netflow"][-1] = 2
        return data

    monkeypatch.setattr(native, "build_reference", build)
    monkeypatch.setattr(native, "read", lambda *_: {"retrievedAt": "2026-11-03T00:00:00Z"})


def quote_text(rows, day):
    lines = []
    for row in rows:
        values = [""] * 38
        for index, value in {
            1: row["f14"],
            2: row["f12"],
            3: row["f2"],
            4: row["f18"],
            30: day.replace("-", "") + "093100",
            32: row["f3"],
            37: str(float(row["f6"]) / 10000),
        }.items():
            values[index] = str(value)
        symbol = next(s for s in etf.LIVE_SYMBOLS if s[2:] == row["f12"])
        lines.append("v_" + symbol + '="' + "~".join(values) + '";')
    return "\n".join(lines)


def reference():
    return {
        "dailyData": {
            "dates": ["2026-10-29", "2026-10-30"],
            "amount": [100, 200],
            "netflow": [1, None],
            "idx": [3000, 3001],
        },
        "broadData": {
            "dates": ["2026-10-30"],
            "cats": ["沪深300"],
            "colors": ["#123456"],
            "series": {"沪深300": [-1]},
            "total": [-1],
            "totalCum": [-1],
        },
        "initData": {
            "date": "2026-10-30",
            "times": ["09:31"],
            "bars": [1],
            "closes": [3000],
            "table": [{"code": symbol[2:], "name": symbol} for symbol in etf.SYMBOLS[1:]],
        },
        "cmpData": {"support": [{"date": "2026-10-29", "amount": 100, "netflow": 101}]},
        "typData": {"slots": ["09:45"], "supAmt": [1], "supIdx": [1], "norAmt": [1], "norIdx": [1]},
        "cumData": {"slots": ["09:30"], "prev": [1], "avg20": [1]},
    }


def text(data):
    return "/* data only */\nwindow.__ISLANDS = " + json.dumps(data, ensure_ascii=False) + ";"


def test_literal_is_data_not_executable_and_keeps_null_zero_negative():
    data = reference()
    data["dailyData"]["netflow"] = [0, None]
    result = etf.parse_reference(text(data))
    assert result["dailyData"]["netflow"] == [0, None]
    assert result["broadData"]["total"] == [-1]
    with pytest.raises((ValueError, json.JSONDecodeError)):
        etf.parse_reference(text(data) + 'require("bad")')


@pytest.fixture
def overview_inputs(monkeypatch):
    from app import research_etf_native as native
    from app import research_national_etf as national

    days = [f"2026-10-{i:02d}" for i in range(1, 21)]
    daily = {"dailyData": {"dates": days, "netflow": ["1.1"] * 19 + ["-2.1"]}}
    documents = {}
    for symbol in etf.SYMBOLS[1:]:
        documents["funds/" + symbol[2:]] = {"rows": [{"date": days[-1], "shares": "100000000"}]}
        documents["market/" + symbol] = {"rows": [{"date": days[-1], "close": "2.5"}]}
    snapshot = {
        "status": "stale", "sourceUrl": national.SOURCE,
        "data": {"baseline": {
            "asof": "2025-12-31", "source": "published report", "note": "original scope",
            "total_value_yi": 15400,
            "holders": [{"name": "holder", "etf_count": 21, "shares_yi": 0, "value_yi": 1, "avg_pct": None}],
        }, "futures": {"member": "中信期货", "latest": {
            "date": "2026-10-21",
            "contracts": {p: [[p + "2611", 10, -2, 20, 3]] for p in ("IH", "IF", "IC", "IM")},
        }}},
    }
    monkeypatch.setattr(native, "read", lambda name: documents.get(name, {}))
    monkeypatch.setattr(national, "read", lambda: snapshot)
    return daily, documents, snapshot


def test_overview_summary_fixed_basket_units_windows_and_independent_futures(overview_inputs):
    daily, _, snapshot = overview_inputs
    result = etf.intraday_summary(daily)
    assert [result[k] for k in ("flow1Yi", "flow5Yi", "flow20Yi")] == ["-2.1", "2.3", "18.8"]
    assert (result["basketCount"], result["sharesYi"], result["scaleYi"]) == (25, "25", "62.5")
    assert result["date"] == "2026-10-20"
    assert result["futures"]["date"] == "2026-10-21"
    assert result["futures"]["netShortChange"] == "20"
    assert result["futures"]["status"] == "stale"
    assert result["baseline"] == snapshot["data"]["baseline"]
    assert result["baselineStatus"] == "stale"


def test_overview_matches_broad_chart_categories_while_intraday_keeps_25_funds(overview_inputs, monkeypatch):
    daily, _, _ = overview_inputs
    dates = daily["dailyData"]["dates"]
    daily["broadData"] = {"dates": dates, "cats": ["A", "B"],
                          "series": {"A": ["2.25"] * 19 + ["-3.5"], "B": ["1.75"] * 20},
                          "total": ["999"] * 20}
    daily["nativeCoverage"] = {"broad": {dates[-1]: {
        "A": {"expected": 110, "covered": 110}, "B": {"expected": 110, "covered": 110}}}}
    monkeypatch.setattr(etf, "_READ_CACHE", None)
    monkeypatch.setattr(etf, "local_json_revision", lambda _: None)
    monkeypatch.setattr(etf, "_read", lambda name: {"data": daily} if name == "reference" else {})
    result = etf.read_observation()
    broad, fixed = result["summary"], result["intradaySummary"]
    assert [broad[k] for k in ("flow1Yi", "flow5Yi", "flow20Yi")] == ["-1.75", "14.25", "74.25"]
    assert broad["basketCount"] == 220 and fixed["basketCount"] == 25
    assert fixed["flow1Yi"] == "-2.1" and fixed["flow5Yi"] == "2.3"
    assert broad["sharesYi"] is None and broad["scaleYi"] is None
    assert broad["futures"] == fixed["futures"] and broad["baseline"] == fixed["baseline"]


def test_broad_summary_keeps_observed_members_but_never_fills_an_unknown_day(overview_inputs):
    daily, _, _ = overview_inputs
    dates = daily["dailyData"]["dates"]
    daily["broadData"] = {"dates": dates, "cats": ["A", "B"],
                          "series": {"A": ["0"] * 20, "B": ["0"] * 19 + [None]}}
    result = etf.overview_summary(daily)
    assert result["date"] == dates[-1] and result["flow1Yi"] == "0"
    assert result["flow20Yi"] == "0"
    daily["broadData"]["series"]["B"][-3] = None
    assert etf.overview_summary(daily)["flow5Yi"] == "0"
    daily["broadData"]["series"]["A"][-3] = None
    assert etf.overview_summary(daily)["flow5Yi"] is None
    for invalid in ({}, {"dates": dates, "cats": ["A", "A"], "series": {"A": [0] * 20}},
                    {"dates": dates, "cats": ["A"], "series": {"A": [0]}}):
        daily["broadData"] = invalid
        empty = etf.overview_summary(daily)
        assert empty["date"] is None and empty["flow1Yi"] is None


def test_overview_missing_day_price_or_futures_product_does_not_use_older_values(overview_inputs):
    daily, documents, snapshot = overview_inputs
    daily["dailyData"]["netflow"][-3] = None
    documents["market/" + etf.SYMBOLS[1]]["rows"][0]["date"] = "2026-10-19"
    del snapshot["data"]["futures"]["latest"]["contracts"]["IM"]
    result = etf.intraday_summary(daily)
    assert result["flow1Yi"] == "-2.1"
    assert result["flow5Yi"] is None and result["flow20Yi"] is None
    assert result["sharesYi"] == "25" and result["scaleYi"] is None
    assert result["futures"]["netShortChange"] is None


def test_overview_short_window_zero_and_api_projection(overview_inputs, monkeypatch):
    daily, _, _ = overview_inputs
    daily["dailyData"]["dates"] = daily["dailyData"]["dates"][-1:]
    daily["dailyData"]["netflow"] = [0]
    monkeypatch.setattr(etf, "_read", lambda name: {"data": daily} if name == "reference" else {})
    result = etf.read_observation()["intradaySummary"]
    assert result["flow1Yi"] == "0"
    assert result["flow5Yi"] is None and result["flow20Yi"] is None


@pytest.mark.parametrize("kind", ["dates", "length", "identity", "total", "html", "nonfinite"])
def test_rejects_invalid_references(kind):
    data = reference()
    if kind == "dates":
        data["dailyData"]["dates"].reverse()
    if kind == "length":
        data["dailyData"]["amount"].pop()
    if kind == "identity":
        data["initData"]["table"][0]["code"] = "999999"
    if kind == "total":
        data["broadData"]["total"][0] = 99
    if kind == "html":
        data["initData"]["table"][0]["name"] = "<img onerror=evil>"
    if kind == "nonfinite":
        data["dailyData"]["idx"][0] = float("nan")
    with pytest.raises(ValueError):
        etf.parse_reference(text(data))


def test_minutes_keep_decimal_precision_and_last_native_day():
    rows = [
        {"day": day, "close": "3.123456", "amount": "100.1000"}
        for day in ["2026-10-29 15:00:00", "2026-10-30 09:31:00"]
    ]
    assert etf.parse_minutes(rows) == [rows[-1]]
    with pytest.raises(ValueError):
        etf.parse_minutes(rows + [rows[-1]])


def test_failed_collection_preserves_last_success_and_does_not_block_reference(
    tmp_path, monkeypatch
):
    from app.database import initialize_database

    initialize_database()
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    old = {
        "data": {"klines": {"sh000001": ["old"]}},
        "status": "ready",
        "retrievedAt": "2026-10-30T00:00:00Z",
    }
    etf.write_local_json(etf.ROOT + "live.json", copy.deepcopy(old))
    real_client = httpx.Client

    def transport(request):
        if request.url.path == "/data.js":
            return httpx.Response(200, text=text(reference()))
        return httpx.Response(503)

    monkeypatch.setattr(
        etf.httpx, "Client", lambda **kwargs: real_client(transport=httpx.MockTransport(transport))
    )
    assert etf.refresh(force=True) == "partial"
    current = etf._read("live")
    assert current["data"] == old["data"]
    assert current["retrievedAt"] == old["retrievedAt"]
    assert current["status"] == "stale"
    assert etf._read("reference")["status"] == "ready"


def test_read_projection_never_fetches(monkeypatch, tmp_path):
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    monkeypatch.setattr(
        etf.httpx, "Client", lambda **kwargs: pytest.fail("read initiated upstream collection")
    )
    assert etf.read_observation()["reference"] == {}


def test_hs300_case_projection_uses_actual_candles_and_keeps_etf_amounts():
    original = {
        "dailyData": {"dates": ["2026-07-10", "2026-07-13"]},
        "typData": {"range": ["2026-07-10", "2026-07-13"], "slots": ["09:45", "10:00"],
                    "supDays": ["2026-07-13"], "supAmt": [3, 4], "norAmt": [1, 2],
                    "supIdx": [99, 99], "norIdx": [99, 99]},
    }
    document = {"symbol": "sh000300", "scale": 15, "sourceUrl": "https://example.com/hs300", "rows": [
        {"day": "2026-07-10 09:45:00", "open": "100", "close": "101"},
        {"day": "2026-07-10 10:00:00", "open": "101", "close": "102"},
        {"day": "2026-07-13 09:45:00", "open": "200", "close": "198"},
        {"day": "2026-07-13 10:00:00", "open": "198", "close": "204"},
    ]}
    result = etf.project_intraday_cases(original, document)["typData"]
    assert result["supIdx"] == [-1.0, 2.0]
    assert result["norIdx"] == [1.0, 2.0]
    assert result["supAmt"] == [3, 4] and result["norAmt"] == [1, 2]
    assert result["indexStatus"] == "ready" and result["indexSymbol"] == "sh000300"
    assert original["typData"]["supIdx"] == [99, 99]
    document["rows"].pop()
    missing = etf.project_intraday_cases(original, document)["typData"]
    assert missing["supIdx"] == [None, None]
    assert missing["norIdx"] == [1.0, 2.0]
    assert missing["indexStatus"] == "partial"
    wrong = etf.project_intraday_cases(original, {**document, "symbol": "sh000001"})["typData"]
    assert wrong["supIdx"] == wrong["norIdx"] == [None, None]
    assert etf.SYMBOLS[0] == "sh000001" and etf.LIVE_SYMBOLS[0] == "sh000300"


@pytest.mark.parametrize("index_quote,expected", [("4101.34", "ready"), ("4101.35", "partial")])
def test_retained_hs300_matches_quote_precision_without_rewriting_minutes(tmp_path, monkeypatch, index_quote, expected):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 5, tzinfo=UTC)

    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    monkeypatch.setattr(etf, "datetime", Clock)
    monkeypatch.setattr(etf, "_trading_window", lambda _: False)
    real_client = httpx.Client

    def transport(request):
        if request.url.host == "qt.gtimg.cn":
            rows = [{"f12": s[2:], "f14": s,
                     "f2": index_quote if s == etf.INTRADAY_INDEX else "3.123456",
                     "f3": 1, "f6": 100, "f18": "4008.87" if s == etf.INTRADAY_INDEX else "3.2"}
                    for s in etf.LIVE_SYMBOLS]
            return httpx.Response(200, text=quote_text(rows, "2026-11-04"))
        if request.url.path.endswith("trends2/get"):
            from app.research_etf_cumulative import MINUTES
            return httpx.Response(200, json={"data": {"code": "510180", "market": 1,
                "trends": [f"2026-11-04 {slot},0,3.123456,0,0,0,100.10,0" for slot in MINUTES]}})
        value = "4101.335" if request.url.params.get("symbol") == etf.INTRADAY_INDEX else "3.123456"
        from app.research_etf_cumulative import MINUTES
        return httpx.Response(200, json=[{"day": f"2026-11-04 {slot}:00", "close": value, "amount": "100.10"} for slot in MINUTES])

    monkeypatch.setattr(etf.httpx, "Client", lambda **kwargs: real_client(transport=httpx.MockTransport(transport)))
    assert etf.refresh(force=True) == expected
    if expected == "ready":
        data = etf._read("live")["data"]
        assert data["klines"][etf.INTRADAY_INDEX][-1]["close"] == "4101.335"
        assert data["hq"]["data"]["diff"][0]["f2"] == "4101.34"
        assert data["hq"]["data"]["diff"][0]["f18"] == "4008.87"


def test_refresh_clock_rejects_future_attempt():
    assert not etf._recent(
        {"attemptedAt": "2026-11-03T00:00:00Z"}, datetime(2026, 11, 2, tzinfo=UTC), 60
    )


@pytest.mark.parametrize("failure", ["mixed_minute_days", "reset_quotes", "missing_quote"])
def test_incoherent_etf_basket_keeps_last_good_native_session(tmp_path, monkeypatch, failure):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 3, 1, 31, tzinfo=UTC)

    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    monkeypatch.setattr(etf, "datetime", Clock)
    monkeypatch.setattr(etf, "_trading_window", lambda _: False)
    old = {
        "data": {"klines": {"sh000001": [{"day": "2026-11-02 15:00:00", "close": "3.123456"}]}},
        "status": "ready",
        "observationDate": "2026-11-02",
        "retrievedAt": "2026-11-02T07:00:00Z",
        "sourceUrl": etf.SOURCE,
    }
    etf.write_local_json(etf.ROOT + "live.json", copy.deepcopy(old))
    real_client = httpx.Client

    def transport(request):
        if request.url.path == "/data.js":
            return httpx.Response(200, text=text(reference()))
        if request.url.path.endswith("trends2/get"):
            stamp = "2026-11-02 15:00" if failure else "2026-11-03 09:31"
            return httpx.Response(200, json={"data": {
                "code": "510180", "market": 1,
                "trends": [stamp + ",0,3.123456,0,0,0,100.10,0"],
            }})
        if request.url.path.endswith("CN_MarketDataService.getKLineData"):
            day = "2026-11-02 15:00:00" if failure else "2026-11-03 09:31:00"
            if failure == "mixed_minute_days" and request.url.params["symbol"] == etf.SYMBOLS[-1]:
                day = "2026-11-03 09:31:00"
            return httpx.Response(200, json=[{"day": day, "close": "3.123456", "amount": "100.10"}])
        assert request.url.host == "qt.gtimg.cn"
        rows = [
            {"f12": s[2:], "f14": s, "f2": "3.123456", "f3": 0, "f6": 100, "f18": 3}
            for s in etf.LIVE_SYMBOLS
        ]
        if failure == "reset_quotes":
            rows[-1]["f6"] = 0
        if failure == "missing_quote":
            rows.pop()
        return httpx.Response(200, text=quote_text(rows, "2026-11-02" if failure else "2026-11-03"))

    monkeypatch.setattr(
        etf.httpx, "Client", lambda **kwargs: real_client(transport=httpx.MockTransport(transport))
    )
    assert etf.refresh(force=True) == "partial"
    current = etf._read("live")
    assert current["status"] == "stale"
    assert current["error"] == "ValueError"
    assert current["data"] == old["data"]
    assert current["retrievedAt"] == old["retrievedAt"]
    assert current["observationDate"] == old["observationDate"]
    assert etf._read("reference")["status"] == "ready"
    assert not (tmp_path / "history/research/etf-observation/2026-11-03.json").exists()
    projection = etf.read_observation()
    assert projection["live"] == old["data"]
    assert projection["sources"]["live"]["status"] == "stale"
    assert projection["sources"]["live"]["observationDate"] == "2026-11-02"
    # A coherent next response must succeed: rejecting every basket is not a valid fix.
    failure = None
    assert etf.refresh(force=True) == "ready"
    recovered = etf.read_observation()
    assert recovered["sources"]["live"]["status"] == "ready"
    assert recovered["sources"]["live"]["observationDate"] == "2026-11-03"
    assert recovered["live"] != old["data"]
    assert set(recovered["live"]["klines"]) == set(etf.LIVE_SYMBOLS)
    assert (tmp_path / "history/research/etf-observation/2026-11-03.json").exists()


def test_endpoint_requires_permission_and_reads_only_local(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.auth import Principal, require_principal
    from app.research_routes import router

    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    monkeypatch.setattr(etf.httpx, "Client", lambda **kwargs: pytest.fail("GET collected upstream"))
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    url = "/api/v1/research/a-share/etf-observation"
    assert client.get(url).status_code == 401
    app.dependency_overrides[require_principal] = lambda: Principal("test", ("admin",), "session")
    response = client.get(url)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["reference"] == {}
    app.dependency_overrides[require_principal] = lambda: Principal("test", (), "session")
    assert client.get(url).status_code == 403


@pytest.mark.parametrize("bad", ["missing", "duplicate", "identity", "nan"])
def test_native_quote_basket_identity_precision_and_units(bad):
    rows = [
        {"f12": s[2:], "f14": s, "f2": "3.123456", "f3": "-1.25", "f6": "12345.67", "f18": "3.2"}
        for s in etf.LIVE_SYMBOLS
    ]
    body = quote_text(rows, "2026-11-04")
    parsed = etf.parse_quotes(body)["data"]["diff"]
    assert parsed[0]["f2"] == "3.123456"
    assert parsed[0]["f6"] == "12345.670000"
    assert parsed[0]["observedAt"] == "2026-11-04T09:31:00"
    if bad == "missing":
        body = quote_text(rows[:-1], "2026-11-04")
    if bad == "duplicate":
        body += body.splitlines()[0]
    if bad == "identity":
        body = body.replace("~000300~", "~000002~", 1)
    if bad == "nan":
        body = body.replace("3.123456", "NaN", 1)
    with pytest.raises(ValueError):
        etf.parse_quotes(body)


def test_read_marks_stopped_intraday_collector_delayed_without_relabelling_time(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 4, 5, 54, tzinfo=UTC)

    monkeypatch.setattr(etf, "datetime", Clock)
    monkeypatch.setattr(etf, "_trading_window", lambda _: True)
    etf.write_local_json(
        etf.ROOT + "live.json",
        {"data": {}, "status": "ready", "observationTime": "2026-11-04 10:17:00"},
    )
    result = etf.read_observation()["sources"]["live"]
    assert result["status"] == "stale"
    assert result["observationTime"] == "2026-11-04 10:17:00"


def test_sse180_explicit_zero_minutes_keep_native_values_and_validate_identity():
    url, params = etf.minute_request("sh510180", 1023)
    assert url == etf.TRENDS_SOURCE and params["ndays"] == 5
    payload = {"data": {"code": "510180", "market": 1, "trends": [
        "2026-11-03 09:55,3.7,3.7,3.7,3.7,0,0.000,3.65",
        "2026-11-03 09:56,3.7,3.7,3.7,3.7,10,3700.000,3.65",
    ]}}
    rows = etf.parse_minutes(etf.minute_response("sh510180", payload))
    assert rows[0]["amount"] == "0.000" and rows[1]["amount"] == "3700.000"
    payload["data"]["code"] = "510300"
    with pytest.raises(ValueError):
        etf.minute_response("sh510180", payload)


def test_sse180_opening_auction_is_included_once_in_the_common_first_interval():
    payload = {"data": {"code": "510180", "market": 1, "trends": [
        "2026-11-04 09:30,0,3.636,0,0,0,54904.000,0",
        "2026-11-04 09:31,0,3.640,0,0,0,454299.000,0",
    ]}}
    rows = etf.parse_minutes(etf.minute_response("sh510180", payload))
    assert len(rows) == 1 and rows[0]["day"] == "2026-11-04 09:31:00"
    assert rows[0]["amount"] == "509203.000"
    payload["data"]["trends"].pop()
    with pytest.raises(ValueError):
        etf.minute_response("sh510180", payload)



def test_summary_keeps_latest_complete_day_when_today_inputs_are_pending(overview_inputs):
    daily,_,_=overview_inputs
    daily["dailyData"]["dates"].append("2026-10-21")
    daily["dailyData"]["netflow"].append(None)
    result=etf.intraday_summary(daily)
    assert result["date"]=="2026-10-20"
    assert result["flow1Yi"]=="-2.1" and result["flow5Yi"]=="2.3"


def test_read_cache_invalidates_atomically_and_freshness_clock_still_advances(tmp_path,monkeypatch):
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT",str(tmp_path))
    monkeypatch.setattr(etf,"_READ_CACHE",None)
    calls=[]
    monkeypatch.setattr(etf,"overview_summary",lambda r, intraday=None:calls.append(True) or {"date":"2026-11-04"})
    class Clock(datetime):
        hour=2
        @classmethod
        def now(cls,tz=None):return datetime(2026,11,4,cls.hour,18,tzinfo=UTC)
    monkeypatch.setattr(etf,"datetime",Clock)
    monkeypatch.setattr(etf,"_trading_window",lambda _:True)
    etf.write_local_json(etf.ROOT+"reference.json",{"data":{}})
    etf.write_local_json(etf.ROOT+"live.json",{"data":{},"status":"ready","observationTime":"2026-11-04 10:17:00"})
    assert etf.read_observation()["sources"]["live"]["status"]=="ready"
    Clock.hour=3
    assert etf.read_observation()["sources"]["live"]["status"]=="stale"
    assert len(calls)==1
    etf.write_local_json(etf.ROOT+"reference.json",{"data":{"revision":2}})
    assert etf.read_observation()["reference"]["revision"]==2
    assert len(calls)==2
