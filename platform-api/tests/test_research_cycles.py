import pytest

from app import research_cycles as cycles
from app.research_provider_errors import ResearchProviderError


def test_native_observations_and_partial_sources_are_preserved(monkeypatch):
    doc = {"label": "native", "status": "stale", "isStale": True,
           "observations": [{"date": "2024-01-01", "value": "1.234567"}, {"date": "2024-02-01", "value": None}]}
    calls = []
    monkeypatch.setattr(cycles, "read_local_json", lambda path: calls.append(path) or doc)
    monkeypatch.setattr(cycles, "read_seasonality", lambda asset: doc)
    result = cycles.read_cycles()
    assert result["indicators"]["usGrowth"] is doc
    assert result["assets"]["btc-usd"] is doc
    assert all("binance" not in path for path in calls)
    assert len(result["assets"]) == 4


def test_missing_input_is_visible_not_zero_filled(monkeypatch):
    def read(path):
        if "us_cpi_yoy" in path:
            raise ResearchProviderError("local_data_not_found:test")
        return {"observations": [], "status": "no_data"}
    monkeypatch.setattr(cycles, "read_local_json", read)
    monkeypatch.setattr(cycles, "read_seasonality", lambda asset: {"observations": []})
    result = cycles.read_cycles()
    assert result["indicators"]["usInflation"]["status"] == "error"
    assert result["indicators"]["usInflation"]["observations"] == []


def test_unexpected_corruption_is_not_disguised_as_missing(monkeypatch):
    monkeypatch.setattr(cycles, "read_local_json", lambda path: {"observations": []})
    def broken(asset):
        raise ValueError("instrument_mismatch")
    monkeypatch.setattr(cycles, "read_seasonality", broken)
    with pytest.raises(ValueError, match="instrument_mismatch"):
        cycles.read_cycles()


def test_read_route_keeps_permission_and_never_collects(monkeypatch):
    import httpx
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.auth import Principal, require_principal
    from app.research_routes import router
    monkeypatch.setattr(httpx, "Client", lambda **kw: pytest.fail("unexpected upstream"))
    monkeypatch.setattr(cycles, "read_cycles", lambda: {"assets": {}, "indicators": {}})
    app = FastAPI(); app.include_router(router)
    client = TestClient(app)
    assert client.get('/api/v1/research/cycles').status_code == 401
    app.dependency_overrides[require_principal] = lambda: Principal("test", ("admin",), "session")
    result = client.get('/api/v1/research/cycles')
    assert result.status_code == 200 and result.headers['cache-control'] == 'no-store'
    app.dependency_overrides[require_principal] = lambda: Principal("test", (), "session")
    assert client.get('/api/v1/research/cycles').status_code == 403
