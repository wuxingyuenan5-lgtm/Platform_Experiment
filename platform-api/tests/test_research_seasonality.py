import json
from contextlib import nullcontext

import pytest

from app import research_seasonality as seasonal


@pytest.mark.parametrize("asset", ["gold", "btc"])
def test_existing_native_series_remain_unchanged(asset, monkeypatch):
    doc={"label":"原始序列","observations":[{"date":"2026-11-03","value":"1.23456"}],"status":"ready"}
    monkeypatch.setattr(seasonal,"read_local_json",lambda path:doc if path==seasonal.LOCAL[asset] else pytest.fail(path))
    assert seasonal.read_seasonality(asset) is doc


@pytest.mark.parametrize("asset", list(seasonal.US))
def test_us_projects_only_requested_native_symbol_without_total_return_substitution(asset, monkeypatch):
    symbol,label,unit=seasonal.US[asset]
    class DB:
        def execute(self,query,params):
            assert params==("Yahoo Finance:"+symbol,)
            assert "dataset='market_price'" in query and "LIMIT 40001" in query
            return self
        def fetchall(self):
            return [{"observed_at":"2025-12-31","payload_json":json.dumps({"symbol":symbol,"close":"100.123456","adjustedClose":"999"})},
                    {"observed_at":"2026-01-30","payload_json":json.dumps({"symbol":symbol,"close":None})}]
    monkeypatch.setattr(seasonal,"read_only_connection",lambda:nullcontext(DB()))
    result=seasonal.read_seasonality(asset)
    assert result["label"]==label and result["unit"]==unit
    assert result["observations"][0]["value"]=="100.123456"
    assert result["observations"][1]["value"] is None
    assert result["timezone"]=="America/New_York"


def test_cn_preserves_original_dates_missingness_and_source_quality(monkeypatch):
    from app import research_etf_native
    doc={"rows":[{"date":"2020-10-15","close":"4000.123"},{"date":"2026-11-04","close":None}],"status":"stale","sourceUrl":"https://example.com/original","retrievedAt":"2026-11-04T10:00:00Z"}
    calls=[]
    monkeypatch.setattr(research_etf_native,"read",lambda key:calls.append(key) or doc)
    monkeypatch.setattr(seasonal, "cached_sessions", lambda end: [
        "2020-10-14", "2020-10-15", "2026-11-03", end, "2026-11-05",
    ])
    result=seasonal.read_seasonality("cn-hs300")
    assert calls==["market/sh000300"]
    assert result["observations"]==[{"date":"2020-10-15","value":"4000.123"},{"date":"2026-11-04","value":None}]
    assert result["tradingDates"] == ["2020-10-15", "2026-11-03", "2026-11-04"]
    assert result["isStale"] is True and result["retrievedAt"]==doc["retrievedAt"]


def test_cn_does_not_present_partial_calendar_as_complete(monkeypatch):
    from app import research_etf_native
    monkeypatch.setattr(research_etf_native, "read", lambda key: {
        "rows": [{"date": "2020-09-30", "close": "4000"}, {"date": "2020-10-09", "close": "4100"}],
    })
    monkeypatch.setattr(seasonal, "cached_sessions", lambda end: [end])
    assert "tradingDates" not in seasonal.read_seasonality("cn-hs300")


def test_empty_history_does_not_create_returns(monkeypatch):
    from app import research_etf_native
    monkeypatch.setattr(research_etf_native,"read",lambda key:{})
    result=seasonal.read_seasonality("cn-star50")
    assert result["observations"]==[] and result["observationDate"] is None


def test_api_is_permission_checked_and_uses_local_inputs(monkeypatch):
    import httpx
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.auth import Principal, require_principal
    from app.research_routes import router
    monkeypatch.setattr(httpx,"Client",lambda **kw:pytest.fail("GET collected upstream"))
    monkeypatch.setattr(seasonal,"read_seasonality",lambda asset:{"seriesId":asset,"observations":[]})
    app=FastAPI();app.include_router(router);client=TestClient(app)
    path="/api/v1/research/seasonality/us-spy"
    assert client.get(path).status_code==401
    app.dependency_overrides[require_principal]=lambda:Principal("test",("admin",),"session")
    assert client.get(path).json()["seriesId"]=="us-spy"
    assert client.get('/api/v1/research/seasonality/unknown').status_code==404
    app.dependency_overrides[require_principal]=lambda:Principal("test",(),"session")
    assert client.get(path).status_code==403
