import copy
import json
from datetime import UTC, datetime

import httpx
import pytest

from app import research_etf_observation as etf


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
        "status": "ready", "observationDate": "2026-11-02",
        "retrievedAt": "2026-11-02T07:00:00Z", "sourceUrl": etf.SOURCE,
    }
    etf.write_local_json(etf.ROOT + "live.json", copy.deepcopy(old))
    real_client = httpx.Client

    def transport(request):
        if request.url.path == "/data.js":
            return httpx.Response(200, text=text(reference()))
        if request.url.path == "/api/kline":
            day = "2026-11-02 15:00:00" if failure else "2026-11-03 09:31:00"
            if failure == "mixed_minute_days" and request.url.params["symbol"] == etf.SYMBOLS[-1]:
                day = "2026-11-03 09:31:00"
            return httpx.Response(200, json=[{"day": day, "close": "3.123456", "amount": "100.10"}])
        assert request.url.path == "/api/hq"
        rows = [{"f12": s[2:], "f14": s, "f2": "3.123456", "f3": 0, "f6": 100, "f18": 3}
                for s in etf.SYMBOLS]
        if failure == "reset_quotes":
            rows[-1]["f6"] = 0
        if failure == "missing_quote":
            rows.pop()
        return httpx.Response(200, json={"data": {"diff": rows}})

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
    assert set(recovered["live"]["klines"]) == set(etf.SYMBOLS)
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
