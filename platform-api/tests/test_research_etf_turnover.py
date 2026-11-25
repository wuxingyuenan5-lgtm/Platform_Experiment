import copy
import json
from datetime import date, timedelta

import pytest

from app import research_etf_turnover as turnover
from app.research_etf_cumulative import SLOTS


def baseline():
    history = [{"date": (date(2026, 10, 1)+timedelta(days=i)).isoformat(), "amount_yi": 1} for i in range(21)]
    return {"trade_date": "20261104", "generated_at": "2026-11-04 17:20:17", "items": [
        {**dict.fromkeys(turnover.FIELDS, 1), "code": str(510300+i), "tcode": "sh"+str(510300+i),
         "name": "ETF", "index": "指数", "group": "core" if i<20 else "watch",
         "avg20_yi": 1, "shape": [[stamp, (j+1)/48] for j, stamp in enumerate(SLOTS)], "hist": history,
         "date": "20261104", "ts": "20261104150000", "prev_shares": 100, "tail_ratio": 0.2}
        for i in range(24)], "shares_history": {"20261103": {"510300": None}}}


def quote(symbol="sh510300", day="20261105"):
    parts = ["0"]*73
    for key, value in {2:symbol[2:], 3:"4.123456", 4:"4", 7:"200", 8:"100", 30:day+"110000", 32:"3.1", 37:"12345.6789", 45:"50", 72:"100000001"}.items():
        parts[key] = value
    return 'v_'+symbol+'="'+"~".join(parts)+'";'


def test_snapshot_is_json_only_and_preserves_missing_shares():
    data = baseline()
    assert turnover.parse_snapshot("window.SNAPSHOT = "+json.dumps(data)+";")["shares_history"]["20261103"]["510300"] is None
    with pytest.raises(ValueError):
        turnover.parse_snapshot("window.SNAPSHOT = "+json.dumps(data)+";alert(1)")


@pytest.mark.parametrize("kind", ["duplicate", "groups", "nonfinite", "shape", "date"])
def test_rejects_invalid_reference(kind):
    data = baseline()
    if kind == "duplicate": data["items"][1]["code"] = data["items"][0]["code"]
    if kind == "groups": data["items"][0]["group"] = "watch"
    if kind == "nonfinite": data["items"][0]["huijin_yi"] = float("nan")
    if kind == "shape": data["items"][0]["shape"].pop()
    if kind == "date": data["trade_date"] = "today"
    with pytest.raises(ValueError): turnover.validate(data)


def test_quote_units_and_identity_are_exact_until_presentation():
    row = turnover.parse_quotes(quote(), ["sh510300"])["sh510300"]
    assert row["price"] == "4.123456"
    assert row["amount_wan"] == "12345.6789"
    assert row["amount_yi"] == "1.23456789"
    assert row["shares_yi"] == "1.00000001"
    for text, symbols in [(quote(), ["sh510300", "sh510310"]), (quote()+quote(), ["sh510300"]),
                          (quote()+quote("sh510310", "20261104"), ["sh510300", "sh510310"])]:
        with pytest.raises(ValueError): turnover.parse_quotes(text, symbols)


def test_projection_preserves_baseline_and_escapes_strings(monkeypatch):
    original = baseline()
    original["items"][0]["name"] = '<img onerror="evil">'
    rows = turnover.parse_quotes(quote(), ["sh510300"])
    monkeypatch.setattr(turnover, "read_doc", lambda name: {"data": original} if name=="baseline" else {"data":rows,"status":"stale"})
    result = turnover.read_turnover()["data"]
    assert result["items"][0]["amount_yi"] == 1.23456789
    assert result["items"][0]["tail_ratio"] is None
    assert "<img" not in result["items"][0]["name"]
    assert original["items"][0]["amount_yi"] == 1
    assert original["items"][0]["tail_ratio"] == 0.2


def test_failed_refresh_retains_old_values_dates_and_retrieval_time(tmp_path, monkeypatch):
    import httpx
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    old={"data":baseline(),"status":"ready","retrievedAt":"2026-11-04T12:00:00+00:00"}
    turnover.write_local_json(turnover.ROOT+"baseline.json",old)
    live={"data":turnover.parse_quotes(quote(),["sh510300"]),"status":"ready","retrievedAt":old["retrievedAt"]}
    turnover.write_local_json(turnover.ROOT+"live.json",live)
    real_client=httpx.Client
    monkeypatch.setattr(turnover.httpx,"Client",lambda **kwargs:real_client(transport=httpx.MockTransport(lambda request:httpx.Response(503))))
    assert turnover.refresh(force=True) == "stale"
    retained=turnover.read_doc("baseline")
    assert retained["data"] == old["data"] and retained["retrievedAt"] == old["retrievedAt"]
    assert turnover.read_doc("live")["data"] == live["data"]


def test_endpoint_is_permission_checked_and_never_collects(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.auth import Principal, require_principal
    from app.research_routes import router
    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT",str(tmp_path))
    monkeypatch.setattr(turnover.httpx,"Client",lambda **kwargs:pytest.fail("read-only GET collected"))
    app=FastAPI(); app.include_router(router); client=TestClient(app)
    url="/api/v1/research/a-share/etf-turnover"
    assert client.get(url).status_code==401
    app.dependency_overrides[require_principal]=lambda:Principal("test",("admin",),"session")
    response=client.get(url)
    assert response.status_code==200 and response.json()["data"] is None
    assert response.headers["cache-control"]=="no-store"
    app.dependency_overrides[require_principal]=lambda:Principal("test",(),"session")
    assert client.get(url).status_code==403
