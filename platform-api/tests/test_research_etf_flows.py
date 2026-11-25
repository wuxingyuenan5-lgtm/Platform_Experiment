from decimal import Decimal

import pytest

from app import research_etf_flows as flows


def test_window_preserves_missing_days_and_zero():
    result = flows.window({"2026-01-05": {"flowYi": "0"}}, ["2026-01-05", "2026-01-06"], "2026-01-05", "2026-01-06", None)
    assert result["flow"] == "0"
    assert (result["covered"], result["expected"], result["complete"]) == (1, 2, False)


def test_all_missing_is_not_zero():
    result = flows.window({}, ["2026-01-05"], "2026-01-05", "2026-01-05", None)
    assert result["flow"] is None
    assert not result["complete"]


def test_listing_excludes_pre_listing_days():
    result = flows.window({"2026-01-06": {"flowYi": "1.2"}}, ["2026-01-05", "2026-01-06"], "2026-01-05", "2026-01-06", "2026-01-06")
    assert result["complete"] and result["expected"] == 1
    assert result["scale"] == "0"


def test_future_listing_is_zero_with_no_denominator():
    p = flows.window({}, ["2026-01-05"], "2026-01-05", "2026-01-05", "2026-01-06")
    result = flows.aggregate([{"current": p, "previous": p}])
    assert result["current"]["flow"] == "0"
    assert result["current"]["ratio"] is None


def test_ratios_require_complete_inputs_and_positive_scale():
    def period(value, complete=True):
        return {"flow": value, "scale": "100", "covered": 2 if complete else 1, "expected": 2, "complete": complete}
    a = {"current": period("25.1"), "previous": period("-10")}
    b = {"current": period("4.9"), "previous": period("-5")}
    result = flows.aggregate([a, b])
    assert Decimal(result["current"]["ratio"]) == 15
    assert Decimal(result["recovery"]) == 200
    b["current"] = period("4.9", False)
    result = flows.aggregate([a, b])
    assert result["current"]["flow"] == "30.0"
    assert result["current"]["ratio"] is None and result["recovery"] is None


def test_scale_uses_exact_prior_session_not_last_available():
    rows = {"2026-01-02": {"shares": "100000000", "unitNav": "1.5"}, "2026-01-06": {"flowYi": "2"}}
    p = flows.window(rows, ["2026-01-02", "2026-01-05", "2026-01-06"], "2026-01-06", "2026-01-06", None)
    assert p["scale"] is None
    rows["2026-01-05"] = {"shares": "200000000", "unitNav": "1.5"}
    assert flows.window(rows, ["2026-01-02", "2026-01-05", "2026-01-06"], "2026-01-06", "2026-01-06", None)["scale"] == "3.0"


@pytest.fixture
def archive(monkeypatch):
    docs = {
        "refresh": {"sessions": ["2026-01-02", "2026-01-05", "2026-01-06"], "catalog": [{"code": "510300", "name": "沪深300ETF", "category": "沪深300"}]},
        "listing": {"dates": {"510300": "2012-01-01"}},
        "funds/510300": {"status": "ready", "rows": [
            {"date": "2026-01-02", "shares": "100000000", "unitNav": "2", "flowYi": "-1.1"},
            {"date": "2026-01-05", "shares": "110000000", "unitNav": "2", "flowYi": "0.2"},
            {"date": "2026-01-06", "shares": "120000000", "unitNav": "2", "flowYi": "0.2"},
        ]},
    }
    monkeypatch.setattr(flows, "read", lambda key: docs.get(key, {}))
    monkeypatch.setattr(flows, "read_tracking", lambda _: {"data": []})


def test_default_periods_are_disjoint_and_aggregate_exactly(archive):
    result = flows.flow_analysis(days=1)
    assert (result["start"], result["previousStart"], result["previousEnd"]) == ("2026-01-06", "2026-01-05", "2026-01-05")
    assert result["assets"][0]["current"]["flow"] == result["summary"]["current"]["flow"] == "0.2"
    assert result["summary"]["count"] == 1


@pytest.mark.parametrize("args", [
    {"start": "2026-01-05", "previous_end": "2026-01-05"},
    {"start": "2026-01-07", "end": "2026-01-06"},
    {"end": "bad-date"},
])
def test_invalid_periods_rejected(archive, args):
    with pytest.raises(ValueError):
        flows.flow_analysis(**args)


def test_route_permissions_and_validation(archive):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.auth import Principal, require_principal
    from app.research_routes import router

    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    url = "/api/v1/research/a-share/etf-flow-analysis"
    assert client.get(url).status_code == 401
    app.dependency_overrides[require_principal] = lambda: Principal("test", ("admin",), "session")
    response = client.get(url, params={"days": 1})
    assert response.status_code == 200
    assert response.json()["summary"]["current"]["flow"] == "0.2"
    assert response.headers["cache-control"] == "no-store"
    assert client.get(url, params={"days": 0}).status_code == 422
    assert client.get(url, params={"start": "2026-01-07", "end": "2026-01-06"}).status_code == 422
    app.dependency_overrides[require_principal] = lambda: Principal("test", (), "session")
    assert client.get(url).status_code == 403
