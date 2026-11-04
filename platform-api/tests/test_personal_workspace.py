from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.auth import Principal, permission_for_request, require_principal
from app.database_connection import connection
from app.personal_workspace import Card, Event, read_document, router, save_document, visible_card
from app.research_rolling_correlation import positive_points, rolling
from app.schema_migrations import PLATFORM_MIGRATIONS

pytestmark = pytest.mark.unit


@pytest.fixture
def storage():
    with connection() as db:
        db.execute("CREATE TABLE users(id TEXT PRIMARY KEY)")
        db.executemany("INSERT INTO users VALUES (?)", [("alice",), ("bob",)])
        for sql in next(m for m in PLATFORM_MIGRATIONS if m.version == 47).statements:
            db.execute(sql)


def test_private_storage_and_optimistic_conflict(storage):
    item = {"id": "one", "title": "private"}
    assert save_document("alice", "events", [item], 0)["rowVersion"] == 1
    assert read_document("bob", "events")["items"] == []
    with pytest.raises(HTTPException) as exc:
        save_document("alice", "events", [], 0)
    assert exc.value.status_code == 409
    assert read_document("alice", "events")["items"] == [item]
    with pytest.raises(HTTPException):
        save_document("alice", "events", [item, item], 1)


def test_module_capabilities_and_unsafe_source():
    principal = Principal("bob", ("member",), "session")
    assert not visible_card({"type": "module", "path": "/risk/users"}, principal)
    with pytest.raises(HTTPException):
        visible_card({"type": "module", "path": "https://example.com"}, principal)
    with pytest.raises(ValueError):
        Event(id="one", date="2026-11-03", title="Event", sourceUrl="javascript:alert(1)")
    with pytest.raises(ValueError):
        Card(id="one", type="chart", title="Title", sql="select * from users")
    assert permission_for_request("PUT", "/api/v1/me/workspace/cards") == "profile.update_self"


def test_http_owner_and_permission_loss(storage, monkeypatch):
    from app import research_chart_catalog

    monkeypatch.setattr(research_chart_catalog, "series_catalog", lambda: [])
    app = FastAPI()
    app.include_router(router)
    identity = Principal("alice", ("ceo",), "session")
    app.dependency_overrides[require_principal] = lambda: identity
    client = TestClient(app)
    payload = {
        "expectedVersion": 0,
        "cards": [{"id": "risk", "type": "module", "title": "Risk", "path": "/risk/detail"}],
    }
    assert client.put("/api/v1/me/workspace/cards", json=payload).status_code == 200
    identity = Principal("bob", ("member",), "session")
    assert client.get("/api/v1/me/workspace/cards").json()["items"] == []
    assert client.put("/api/v1/me/workspace/cards", json=payload).status_code == 403
    identity = Principal("alice", ("member",), "session")
    assert client.get("/api/v1/me/workspace/cards").json()["items"] == []
    response = client.put("/api/v1/me/workspace/cards", json={"expectedVersion": 1, "cards": []})
    assert response.status_code == 200 and response.json()["items"] == []
    assert len(read_document("alice", "cards")["items"]) == 1


def test_common_session_weekend_returns_and_exact_window():
    days = [(date(2026, 8, 1) + timedelta(days=i)).isoformat() for i in range(70)]
    btc = {d: Decimal(100 + i * i) for i, d in enumerate(days)}
    benchmark = {d: v * 2 for d, v in btc.items() if date.fromisoformat(d).weekday() < 5}
    # Huge Sunday move cannot become Monday's independent BTC baseline.
    for d in days:
        if date.fromisoformat(d).weekday() == 6:
            btc[d] *= 20
    out = rolling(btc, benchmark, 20, "2027-01-01")
    assert all(r["correlation"] is None for r in out[:20])
    assert all(abs(r["correlation"] - 1) < Decimal("1e-25") for r in out[20:])
    assert out[-1]["samples"] == 20


def test_missing_price_breaks_window_and_constant_is_null():
    start = date(2026, 1, 1)
    points = {(start + timedelta(days=i)).isoformat(): Decimal(100 + i) for i in range(40)}
    btc = dict(points)
    btc[list(points)[20]] = None
    out = rolling(btc, points, 10, "2027-01-01")
    assert all(r["correlation"] is None for r in out[20:31])
    assert all(
        r["correlation"] is None
        for r in rolling({d: Decimal(100) for d in points}, points, 10, "2027-01-01")
    )
    with pytest.raises(ValueError):
        positive_points([{"date": "2026-01-01", "value": 1}, {"date": "2026-01-01", "value": 2}])


def test_chart_catalog_is_shared_allowlist_and_preserves_missing(tmp_path, monkeypatch):
    import json

    from app.research_chart_catalog import series_catalog, series_data

    monkeypatch.setenv("HEDGE_BOARD_DATA_ROOT", str(tmp_path))
    path = tmp_path / "public/v1/crypto/series/example.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "seriesId": "test",
                "label": "Test",
                "unit": "USD",
                "observations": [
                    {"date": "2026-01-01", "value": None},
                    {"date": "2026-01-02", "value": "123.456789"},
                ],
            }
        ),
        encoding="utf8",
    )
    metadata = next(s for s in series_catalog() if s["name"] == "Test")
    assert "observations" not in metadata
    data = series_data(metadata["id"])
    assert data["observations"][0]["value"] is None
    assert data["observations"][1]["value"] == "123.456789"
    assert data["asOf"] == "2026-01-02"
    with pytest.raises(HTTPException) as exc:
        series_data("../../users")
    assert exc.value.status_code == 404
    assert positive_points([{"date": "2026-01-01", "value": None}]) == {"2026-01-01": None}


def test_single_indicator_table_saved_per_account(storage, monkeypatch):
    from app import research_chart_catalog
    monkeypatch.setattr(research_chart_catalog, "series_catalog", lambda: [{"id":"known"}])
    app=FastAPI();app.include_router(router)
    app.dependency_overrides[require_principal]=lambda: Principal("alice",("ceo",),"session")
    client=TestClient(app)
    card={"id":"one","type":"chart","title":"单指标数据表","seriesA":"known","display":"table"}
    response=client.put("/api/v1/me/workspace/cards",json={"expectedVersion":0,"cards":[card]})
    assert response.status_code==200
    assert client.get("/api/v1/me/workspace/cards").json()["items"][0]["display"]=="table"
    assert read_document("bob","cards")["items"]==[]
    with pytest.raises(ValueError): Card(**{**card,"display":"full-page"})
