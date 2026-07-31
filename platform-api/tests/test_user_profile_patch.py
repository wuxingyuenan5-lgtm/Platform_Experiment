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
PASSWORD = "correct horse battery staple"


def prepare_database(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path = tmp_path / "self-profile-patch.db"
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
def test_self_profile_patch_preserves_omitted_fields_and_allows_explicit_clear(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepare_database(monkeypatch, tmp_path)
    create_initial_ceo(
        username="profile-patch-owner",
        password=PASSWORD,
        display_name="Original Name",
        real_name="Profile Patch Owner",
        email="profile-patch@example.test",
        phone="+86 138 0013 8000",
    )

    with TestClient(app, base_url=ORIGIN) as client:
        signed_in = client.post(
            "/api/v1/auth/login",
            headers={"Origin": ORIGIN},
            json={"username": "profile-patch-owner", "password": PASSWORD},
        )
        assert signed_in.status_code == 200
        csrf = signed_in.json()["csrfToken"]

        profile = client.get("/api/v1/me")
        assert profile.status_code == 200

        display_only = client.patch(
            "/api/v1/me",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={
                "displayName": "Updated Name",
                "expectedVersion": profile.json()["rowVersion"],
            },
        )
        assert display_only.status_code == 200
        assert display_only.json()["displayName"] == "Updated Name"
        assert display_only.json()["email"] == "profile-patch@example.test"
        assert display_only.json()["phone"] == "+86 138 0013 8000"

        reauthenticated = client.post(
            "/api/v1/auth/reauth",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={"password": PASSWORD},
        )
        assert reauthenticated.status_code == 200

        cleared_phone = client.patch(
            "/api/v1/me",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={
                "phone": None,
                "expectedVersion": display_only.json()["rowVersion"],
            },
        )
        assert cleared_phone.status_code == 200
        assert cleared_phone.json()["phone"] is None
        assert cleared_phone.json()["email"] == "profile-patch@example.test"

        no_contact = client.patch(
            "/api/v1/me",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={
                "email": None,
                "expectedVersion": cleared_phone.json()["rowVersion"],
            },
        )
        assert no_contact.status_code == 422
        assert no_contact.json()["detail"]["code"] == "contact_required"
