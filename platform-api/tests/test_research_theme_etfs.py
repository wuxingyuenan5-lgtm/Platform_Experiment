from decimal import Decimal

from app import data_audit_calendar
from app import research_theme_etfs as theme


def test_theme_total_requires_every_member_and_common_week_endpoints(monkeypatch):
    dates = [f"2026-11-{i:02}" for i in range(2, 8)]
    monkeypatch.setattr(
        theme,
        "CN_REFERENCES",
        {
            "theme": [("a", "A", "", "", ""), ("b", "B", "", "", "")],
            "other": [("c", "C", "", "", "")],
        },
    )
    monkeypatch.setattr(data_audit_calendar, "cached_sessions", lambda _: dates)
    archive = {
        "funds": {
            "a": {d: str((10 + i) * 100000000) for i, d in enumerate(dates)},
            "b": {dates[0]: "2000000000", dates[-1]: "2200000000"},
            "c": {dates[0]: "100000000", dates[-2]: "500000000"},
        }
    }
    monkeypatch.setattr(theme, "read", lambda name: archive if name == "theme-shares" else {})
    result = theme.panorama()
    first, second = result["themes"]
    assert result["start"] == dates[0] and result["date"] == dates[-1]
    assert first["series"][1]["units"] is None
    assert Decimal(first["series"][-1]["units"]) == 37
    assert Decimal(first["delta"]) == 7
    assert second["delta"] is None  # no stale-date ranking

    monkeypatch.setattr(
        theme,
        "read",
        lambda name: archive if name == "theme-shares" else {"days": {dates[-1]: {"a": "1"}}},
    )
    assert theme.panorama()["themes"][0]["delta"] is None
    monkeypatch.setattr(data_audit_calendar, "cached_sessions", lambda _: [])
    assert theme.panorama()["start"] is None


def test_empty_archive_has_no_invented_zero(monkeypatch):
    monkeypatch.setattr(theme, "read", lambda _: {})
    result = theme.panorama()
    assert result["date"] is None and result["status"] == "no_data"
    assert all(t["delta"] is None and t["series"] == [] for t in result["themes"])


def test_twenty_sessions_and_small_summary_keep_the_same_ranking(monkeypatch):
    from datetime import date, timedelta

    dates = [(date(2026, 9, 1) + timedelta(days=i)).isoformat() for i in range(21)]
    monkeypatch.setattr(
        theme, "CN_REFERENCES", {"one": [("a", "A", "", "", "")], "two": [("b", "B", "", "", "")]}
    )
    monkeypatch.setattr(data_audit_calendar, "cached_sessions", lambda _: dates)
    archive = {
        "funds": {
            "a": {d: str((10 + i) * 100000000) for i, d in enumerate(dates)},
            "b": {dates[0]: "100000000"},
        }
    }
    monkeypatch.setattr(theme, "read", lambda name: archive if name == "theme-shares" else {})
    full = theme.panorama()
    slim = theme.panorama(include_series=False)
    assert slim["start20"] == dates[0] and slim["start"] == dates[-6]
    assert Decimal(slim["themes"][0]["delta20"]) == 20
    assert slim["themes"][1]["delta20"] is None
    assert slim["themes"][0]["delta"] == full["themes"][0]["delta"]
    assert not any(f["series"] for f in slim["funds"] + slim["themes"])
    chart = theme.panorama(theme="one", days=7)
    assert [t["code"] for t in chart["themes"]] == ["one"]
    assert len(chart["themes"][0]["series"]) == 8
    assert chart["funds"][0]["series"] == []


def test_theme_route_uses_research_permission_and_no_store(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.auth import Principal, require_principal
    from app.research_routes import router

    monkeypatch.setattr(theme, "read", lambda _: {})
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    url = "/api/v1/research/a-share/theme-etfs"
    assert client.get(url).status_code == 401
    app.dependency_overrides[require_principal] = lambda: Principal("test", ("admin",), "session")
    response = client.get(url)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert len(response.json()["themes"]) == len(theme.CN_REFERENCES)
    app.dependency_overrides[require_principal] = lambda: Principal("test", (), "session")
    assert client.get(url).status_code == 403
