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


def prepare_database(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    name: str,
) -> Path:
    path = tmp_path / name
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
    return path


def login(client: TestClient, username: str, password: str):
    return client.post(
        "/api/v1/auth/login",
        headers={"Origin": ORIGIN},
        json={"username": username, "password": password},
    )


@pytest.mark.integration
def test_public_registration_is_pending_and_cannot_request_privileged_role(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = prepare_database(monkeypatch, tmp_path, "registration.db")
    with TestClient(app, base_url=ORIGIN) as client:
        response = client.post(
            "/api/v1/auth/register",
            headers={"Origin": ORIGIN},
            json={
                "username": "member-applicant",
                "realName": "示例会员",
                "email": "member@example.test",
                "requestedRole": "member",
                "memberType": "individual",
                "applicationNote": "test application",
                "password": "correct horse battery staple",
                "passwordConfirmation": "correct horse battery staple",
                "privacyAccepted": True,
            },
        )
        assert response.status_code == 201
        assert response.json()["status"] == "pending"

        pending_login = login(
            client,
            "member-applicant",
            "correct horse battery staple",
        )
        assert pending_login.status_code == 403
        assert pending_login.json()["detail"]["code"] == "account_pending"

        privileged = client.post(
            "/api/v1/auth/register",
            headers={"Origin": ORIGIN},
            json={
                "username": "forged-ceo",
                "realName": "Forged CEO",
                "email": "forged@example.test",
                "requestedRole": "ceo",
                "memberType": "individual",
                "password": "another correct horse battery staple",
                "passwordConfirmation": "another correct horse battery staple",
                "privacyAccepted": True,
            },
        )
        assert privileged.status_code == 422

    with sqlite3.connect(database_path) as db:
        db.row_factory = sqlite3.Row
        row = db.execute(
            """
            SELECT role_code, requested_role_code, lifecycle_status
            FROM users WHERE username_normalized = 'member-applicant'
            """
        ).fetchone()
    assert row["role_code"] is None
    assert row["requested_role_code"] == "member"
    assert row["lifecycle_status"] == "pending"


@pytest.mark.integration
def test_browser_session_profile_devices_and_password_change(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepare_database(monkeypatch, tmp_path, "browser-flow.db")
    create_initial_ceo(
        username="owner",
        password="correct horse battery staple",
        display_name="Owner",
        real_name="Platform Owner",
        email="owner@example.test",
    )

    with TestClient(app, base_url=ORIGIN) as client:
        signed_in = login(client, "owner", "correct horse battery staple")
        assert signed_in.status_code == 200
        assert signed_in.headers["cache-control"] == "no-store"
        assert get_settings().session_cookie_name in signed_in.cookies
        first_csrf = signed_in.json()["csrfToken"]

        hydrated = client.get("/api/v1/auth/me")
        assert hydrated.status_code == 200
        second_csrf = hydrated.json()["csrfToken"]
        assert second_csrf != first_csrf
        assert hydrated.json()["user"]["role"] == "ceo"
        permissions = set(hydrated.json()["permissions"])
        assert "*" not in permissions
        assert "profile.read_self" in permissions
        assert "user.assign_role" in permissions
        assert "member.holding.update" in permissions
        assert "trade:submit" not in permissions
        assert "risk:manage" not in permissions

        profile = client.get("/api/v1/me")
        assert profile.status_code == 200
        version = profile.json()["rowVersion"]

        updated = client.patch(
            "/api/v1/me",
            headers={"Origin": ORIGIN, "X-CSRF-Token": second_csrf},
            json={
                "displayName": "New Owner",
                "email": "new-owner@example.test",
                "phone": "+86 138 0013 8000",
                "expectedVersion": version,
            },
        )
        assert updated.status_code == 200
        assert updated.json()["displayName"] == "New Owner"
        assert updated.json()["rowVersion"] == version + 1

        stale_update = client.patch(
            "/api/v1/me",
            headers={"Origin": ORIGIN, "X-CSRF-Token": second_csrf},
            json={
                "displayName": "Stale Write",
                "email": "stale@example.test",
                "phone": "+86 138 0013 8001",
                "expectedVersion": version,
            },
        )
        assert stale_update.status_code == 409
        assert stale_update.json()["detail"]["code"] == "row_version_conflict"

        sessions = client.get("/api/v1/me/sessions")
        assert sessions.status_code == 200
        assert len(sessions.json()["items"]) == 1
        assert sessions.json()["items"][0]["current"] is True
        assert sessions.json()["items"][0]["ipSummary"] is not None

        reauthenticated = client.post(
            "/api/v1/auth/reauth",
            headers={"Origin": ORIGIN, "X-CSRF-Token": second_csrf},
            json={"password": "correct horse battery staple"},
        )
        assert reauthenticated.status_code == 200

        changed = client.post(
            "/api/v1/me/password",
            headers={"Origin": ORIGIN, "X-CSRF-Token": second_csrf},
            json={
                "currentPassword": "correct horse battery staple",
                "newPassword": "new correct horse battery staple",
                "newPasswordConfirmation": "new correct horse battery staple",
            },
        )
        assert changed.status_code == 200
        assert changed.json()["revokedSessionCount"] == 1

        after_change = client.get("/api/v1/me")
        assert after_change.status_code == 401
        old_login = login(client, "owner", "correct horse battery staple")
        assert old_login.status_code == 401
        new_login = login(client, "owner", "new correct horse battery staple")
        assert new_login.status_code == 200


@pytest.mark.integration
def test_login_failure_threshold_temporarily_locks_account(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepare_database(monkeypatch, tmp_path, "login-lock.db")
    create_initial_ceo(
        username="owner",
        password="correct horse battery staple",
    )

    with TestClient(app, base_url=ORIGIN) as client:
        for _ in range(get_settings().login_failure_limit):
            failed = login(client, "owner", "wrong password")
            assert failed.status_code == 401
            assert failed.json()["detail"]["code"] == "invalid_credentials"

        locked = login(client, "owner", "correct horse battery staple")
        assert locked.status_code == 423
        assert locked.json()["detail"]["code"] == "account_temporarily_locked"
