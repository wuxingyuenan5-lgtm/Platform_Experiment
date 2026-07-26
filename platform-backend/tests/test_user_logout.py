from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database_bootstrap import bootstrap_database
from app.main import app
from app.schema_migrations import PLATFORM_MIGRATIONS, apply_migrations
from app.user_service import create_initial_ceo

ORIGIN = "https://testserver"


def prepare(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = get_settings()
    database_path = tmp_path / "logout.db"
    monkeypatch.setattr(settings, "database_path", str(database_path))
    monkeypatch.setattr(settings, "environment", "live")
    monkeypatch.setattr(settings, "auth_mode", "api_key")
    monkeypatch.setattr(settings, "auth_credentials_json", "[]")
    monkeypatch.setattr(settings, "cors_origins", ORIGIN)
    with sqlite3.connect(database_path) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        bootstrap_database(db)
        apply_migrations(db, PLATFORM_MIGRATIONS)
        db.commit()
    create_initial_ceo(
        username="owner",
        password="correct horse battery staple",
    )


@pytest.mark.integration
def test_valid_logout_requires_csrf_and_revokes_session(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepare(monkeypatch, tmp_path)
    with TestClient(app, base_url=ORIGIN) as client:
        login = client.post(
            "/api/v1/auth/login",
            headers={"Origin": ORIGIN},
            json={"username": "owner", "password": "correct horse battery staple"},
        )
        assert login.status_code == 200
        csrf = login.json()["csrfToken"]

        missing = client.post("/api/v1/auth/logout", headers={"Origin": ORIGIN})
        assert missing.status_code == 403
        assert missing.json()["detail"]["code"] == "csrf_required"

        success = client.post(
            "/api/v1/auth/logout",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
        )
        assert success.status_code == 200
        assert client.get("/api/v1/auth/me").status_code == 401


@pytest.mark.integration
def test_stale_logout_still_clears_cookie(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepare(monkeypatch, tmp_path)
    with TestClient(app, base_url=ORIGIN) as client:
        client.cookies.set(get_settings().session_cookie_name, "stale-session-token")
        response = client.post("/api/v1/auth/logout", headers={"Origin": ORIGIN})
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert get_settings().session_cookie_name not in client.cookies
