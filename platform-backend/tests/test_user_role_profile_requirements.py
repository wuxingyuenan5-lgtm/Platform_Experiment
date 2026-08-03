from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database_bootstrap import bootstrap_database
from app.main import app
from app.schema_migrations import PLATFORM_MIGRATIONS, apply_migrations
from app.user_rate_limit import get_public_auth_rate_limiter
from app.user_service import create_initial_ceo

ORIGIN = "https://testserver"
PASSWORD = "correct horse battery staple"


def prepare_database(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Path:
    path = tmp_path / "role-profile-requirements.db"
    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(path))
    monkeypatch.setattr(settings, "environment", "live")
    monkeypatch.setattr(settings, "auth_mode", "api_key")
    monkeypatch.setattr(settings, "auth_credentials_json", "[]")
    monkeypatch.setattr(settings, "cors_origins", ORIGIN)
    monkeypatch.setattr(settings, "public_registration_rate_limit", 1000)
    monkeypatch.setattr(settings, "public_login_rate_limit", 1000)
    get_public_auth_rate_limiter(settings.public_rate_limit_max_keys).clear()
    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        bootstrap_database(db)
        apply_migrations(db, PLATFORM_MIGRATIONS)
        db.commit()
    return path


def login(client: TestClient):
    return client.post(
        "/api/v1/auth/login",
        headers={"Origin": ORIGIN},
        json={"username": "profile-owner", "password": PASSWORD},
    )


@pytest.mark.integration
def test_role_change_requires_role_specific_profile_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = prepare_database(monkeypatch, tmp_path)
    create_initial_ceo(
        username="profile-owner",
        password=PASSWORD,
        real_name="Profile Owner",
        email="profile-owner@example.test",
    )

    with TestClient(app, base_url=ORIGIN) as client:
        signed_in = login(client)
        assert signed_in.status_code == 200
        csrf = signed_in.json()["csrfToken"]

        employee = client.post(
            "/api/v1/users",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={
                "username": "profile-employee",
                "realName": "Fictional Employee",
                "email": "profile-employee@example.test",
                "role": "employee",
                "department": "operations",
            },
        )
        assert employee.status_code == 201
        employee_detail = employee.json()["user"]
        user_id = employee_detail["userId"]

        # Simulate an incomplete historical/imported row. Normal profile APIs already
        # prevent an employee from clearing the required department field.
        with sqlite3.connect(database_path) as db:
            db.execute(
                """
                UPDATE users
                SET department = NULL,
                    row_version = row_version + 1,
                    updated_at = '2026-07-26T00:00:00+00:00'
                WHERE id = ?
                """,
                (user_id,),
            )
            db.commit()

        incomplete = client.get(f"/api/v1/users/{user_id}")
        assert incomplete.status_code == 200
        incomplete_detail = incomplete.json()

        denied_member = client.post(
            f"/api/v1/users/{user_id}/role",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={
                "role": "member",
                "expectedVersion": incomplete_detail["rowVersion"],
            },
        )
        assert denied_member.status_code == 422
        assert denied_member.json()["detail"]["code"] == "member_type_required"

        completed = client.patch(
            f"/api/v1/users/{user_id}",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={
                "displayName": incomplete_detail.get("displayName"),
                "realName": incomplete_detail.get("realName"),
                "email": incomplete_detail.get("email"),
                "phone": incomplete_detail.get("phone"),
                "department": "operations",
                "memberType": "individual",
                "expectedVersion": incomplete_detail["rowVersion"],
            },
        )
        assert completed.status_code == 200

        changed = client.post(
            f"/api/v1/users/{user_id}/role",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={
                "role": "member",
                "expectedVersion": completed.json()["rowVersion"],
            },
        )
        assert changed.status_code == 200
        assert changed.json()["role"] == "member"

        member_without_department = client.patch(
            f"/api/v1/users/{user_id}",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={
                "displayName": changed.json().get("displayName"),
                "realName": changed.json().get("realName"),
                "email": changed.json().get("email"),
                "phone": changed.json().get("phone"),
                "department": None,
                "memberType": "individual",
                "expectedVersion": changed.json()["rowVersion"],
            },
        )
        assert member_without_department.status_code == 200

        denied_employee = client.post(
            f"/api/v1/users/{user_id}/role",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={
                "role": "employee",
                "expectedVersion": member_without_department.json()["rowVersion"],
            },
        )
        assert denied_employee.status_code == 422
        assert denied_employee.json()["detail"]["code"] == "department_required"


@pytest.mark.integration
def test_pending_approval_rechecks_role_specific_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = prepare_database(monkeypatch, tmp_path)
    create_initial_ceo(
        username="profile-owner",
        password=PASSWORD,
        real_name="Profile Owner",
        email="profile-owner@example.test",
    )

    with TestClient(app, base_url=ORIGIN) as client:
        signed_in = login(client)
        csrf = signed_in.json()["csrfToken"]

        with sqlite3.connect(database_path) as db:
            db.row_factory = sqlite3.Row
            now = "2026-07-26T00:00:00+00:00"
            db.execute(
                """
                INSERT INTO users (
                    id, username, username_normalized, password_hash,
                    real_name, email, email_normalized,
                    requested_role_code, lifecycle_status,
                    registered_at, created_at, updated_at
                ) VALUES (
                    'pending-incomplete-member',
                    'pending-incomplete-member',
                    'pending-incomplete-member',
                    'test-hash',
                    'Fictional Pending Member',
                    'pending-incomplete-member@example.test',
                    'pending-incomplete-member@example.test',
                    'member', 'pending', ?, ?, ?
                )
                """,
                (now, now, now),
            )
            db.commit()

        detail = client.get("/api/v1/users/pending-incomplete-member")
        assert detail.status_code == 200
        denied = client.post(
            "/api/v1/users/pending-incomplete-member/approve",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={
                "finalRole": "member",
                "expectedVersion": detail.json()["rowVersion"],
            },
        )
        assert denied.status_code == 422
        assert denied.json()["detail"]["code"] == "member_type_required"
