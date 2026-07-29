from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.auth import AuthenticationMiddleware
from app.config import get_settings
from app.database_bootstrap import bootstrap_database
from app.main import app
from app.schema_migrations import PLATFORM_MIGRATIONS, apply_migrations
from app.user_cache_control import UserNoStoreMiddleware, is_sensitive_identity_path
from app.user_service import create_initial_ceo

ORIGIN = "https://testserver"
PASSWORD = "correct horse battery staple"


@pytest.mark.unit
def test_sensitive_identity_path_classifier_is_bounded() -> None:
    assert is_sensitive_identity_path("/api/v1/auth/login")
    assert is_sensitive_identity_path("/api/v1/me")
    assert is_sensitive_identity_path("/api/v1/me/holdings")
    assert is_sensitive_identity_path("/api/v1/users/example")
    assert not is_sensitive_identity_path("/api/v1/trading/orders")
    assert not is_sensitive_identity_path("/api/v1/users-public")


@pytest.mark.unit
def test_no_store_middleware_wraps_authentication_middleware() -> None:
    middleware_classes = [middleware.cls for middleware in app.user_middleware]
    assert middleware_classes.index(UserNoStoreMiddleware) < middleware_classes.index(
        AuthenticationMiddleware
    )


def prepare_database(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path = tmp_path / "identity-cache-control.db"
    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(path))
    monkeypatch.setattr(settings, "environment", "live")
    monkeypatch.setattr(settings, "auth_mode", "api_key")
    monkeypatch.setattr(settings, "auth_credentials_json", "[]")
    monkeypatch.setattr(settings, "cors_origins", ORIGIN)
    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        bootstrap_database(db)
        apply_migrations(db, PLATFORM_MIGRATIONS)
        db.commit()


@pytest.mark.integration
def test_identity_success_and_failure_responses_are_not_cacheable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepare_database(monkeypatch, tmp_path)
    create_initial_ceo(
        username="cache-owner",
        password=PASSWORD,
        email="cache-owner@example.test",
    )

    with TestClient(app, base_url=ORIGIN) as client:
        unauthorized = client.get("/api/v1/users")
        assert unauthorized.status_code == 401
        assert unauthorized.json()["detail"]["code"] == "bearer_required"
        assert unauthorized.json()["requestId"] == unauthorized.headers["x-request-id"]
        assert unauthorized.headers["cache-control"] == "no-store"
        assert unauthorized.headers["pragma"] == "no-cache"

        login = client.post(
            "/api/v1/auth/login",
            headers={"Origin": ORIGIN},
            json={"username": "cache-owner", "password": PASSWORD},
        )
        assert login.status_code == 200
        assert login.headers["cache-control"] == "no-store"

        profile = client.get("/api/v1/me")
        assert profile.status_code == 200
        assert profile.headers["cache-control"] == "no-store"
        assert profile.headers["pragma"] == "no-cache"
