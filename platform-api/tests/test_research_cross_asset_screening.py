import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import research_cross_asset_screening
from app.auth import Principal, require_principal
from app.research_cross_asset_screening import read_screening_archive
from app.research_routes import router


def test_archive_preserves_native_periods_dates_and_missing_completion():
    value = read_screening_archive()
    assert value["mode"] == "historical-archive" and value["isStale"] is True
    assert value["snapshot"]["generatedAt"] == "2026-10-27T19:58:52.633Z"
    assert len(value["assets"]) == 12 and len(value["snapshot"]["series"]) == 48
    symbols = {s["symbol"] for s in value["assets"]}
    seen = set()
    for series in value["snapshot"]["series"]:
        assert series["symbol"] in symbols
        assert series["frame"] in {"1D", "3D", "1W", "M"}
        assert (series["symbol"], series["frame"]) not in seen
        seen.add((series["symbol"], series["frame"]))
        assert series.get("lastBarComplete") is not True
        assert series["hash"] and series["fetchedAt"]
        assert all(b["t"] < c["t"] for b, c in zip(
            series["bars"], series["bars"][1:], strict=False
        ))
    assert value["caps"]["date"] == "2026-10-26"
    assert set(value["caps"]["rows"]) == {"AAPL", "NVDA"}
    assert value["legacyResearch"]["rulesVersion"] != "trend-framework-3.0-zlma"


def test_route_requires_research_permission_and_performs_no_upstream_io(monkeypatch, tmp_path):
    import httpx

    monkeypatch.setattr(httpx, "Client", lambda **kw: (_ for _ in ()).throw(
        AssertionError("unexpected upstream request")))
    file = tmp_path / "cross-asset-workbooks.json"
    monkeypatch.setattr(research_cross_asset_screening, "WORKBOOK_SNAPSHOT", file)
    workbook = {
        "version": 1, "date": "2026-11-20",
        "pools": {
            "core": {"file": "core.xlsx", "sheet": "核心数据", "rows": [{"code": "000688"}]},
            "tools": {"file": "tools.xlsx", "sheet": "押注工具", "rows": [{"code": "588000"}]},
        },
    }
    file.write_text(json.dumps(workbook), encoding="utf-8")
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    url = "/api/v1/research/macro/cross-asset-screening"
    assert client.get(url).status_code == 401
    app.dependency_overrides[require_principal] = lambda: Principal("test", (), "session")
    assert client.get(url).status_code == 403
    app.dependency_overrides[require_principal] = lambda: Principal(
        "development-user", ("admin",), "development"
    )
    development_response = client.get(url)
    assert development_response.status_code == 200
    assert "workbookSnapshot" not in development_response.json()
    app.dependency_overrides[require_principal] = lambda: Principal("test", ("admin",), "session")
    response = client.get(url)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    payload = response.json()
    assert len(payload["snapshot"]["series"]) == 48
    assert payload["workbookSnapshot"] == workbook
    file.write_text("{", encoding="utf-8")
    unavailable = client.get(url).json()
    assert unavailable["workbookSnapshotUnavailable"] is True
    assert len(unavailable["snapshot"]["series"]) == 48
