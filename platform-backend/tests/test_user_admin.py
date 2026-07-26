from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database_bootstrap import bootstrap_database
from app.main import app
from app.schema_migrations import PLATFORM_MIGRATIONS, apply_migrations
from app.user_security import hash_secret_token
from app.user_service import create_initial_ceo

ORIGIN = "https://testserver"
OWNER_PASSWORD = "correct horse battery staple"
USER_PASSWORD = "new correct horse battery staple"


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


def reset_password(client: TestClient, username: str, ticket: str):
    return client.post(
        "/api/v1/auth/reset-password",
        headers={"Origin": ORIGIN},
        json={
            "username": username,
            "resetTicket": ticket,
            "newPassword": USER_PASSWORD,
            "newPasswordConfirmation": USER_PASSWORD,
        },
    )


@pytest.mark.integration
def test_ceo_creates_user_with_one_time_reset_ticket_and_audit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = prepare_database(monkeypatch, tmp_path, "admin-create.db")
    create_initial_ceo(username="owner", password=OWNER_PASSWORD, email="owner@example.test")

    with TestClient(app, base_url=ORIGIN) as owner_client:
        signed_in = login(owner_client, "owner", OWNER_PASSWORD)
        assert signed_in.status_code == 200
        csrf = signed_in.json()["csrfToken"]
        created = owner_client.post(
            "/api/v1/users",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={
                "username": "employee-one",
                "realName": "示例员工",
                "displayName": "员工一",
                "email": "employee-one@example.test",
                "role": "employee",
                "department": "operations",
            },
        )
        assert created.status_code == 201
        payload = created.json()
        assert payload["user"]["role"] == "employee"
        assert payload["user"]["status"] == "active"
        assert payload["resetTicket"]
        assert created.headers["cache-control"] == "no-store"
        raw_ticket = payload["resetTicket"]

    with sqlite3.connect(database_path) as db:
        db.row_factory = sqlite3.Row
        ticket = db.execute(
            """
            SELECT token_hash FROM password_reset_tickets
            WHERE user_id = ? AND consumed_at IS NULL AND revoked_at IS NULL
            """,
            (payload["user"]["userId"],),
        ).fetchone()
        audit_types = {
            str(row["event_type"])
            for row in db.execute(
                "SELECT event_type FROM audit_events WHERE subject_id = ?",
                (payload["user"]["userId"],),
            ).fetchall()
        }
    assert ticket["token_hash"] == hash_secret_token(raw_ticket)
    assert ticket["token_hash"] != raw_ticket
    assert "user.created" in audit_types
    assert "user.password_reset_ticket_issued" in audit_types

    with TestClient(app, base_url=ORIGIN) as employee_client:
        consumed = reset_password(employee_client, "employee-one", raw_ticket)
        assert consumed.status_code == 200
        replay = reset_password(employee_client, "employee-one", raw_ticket)
        assert replay.status_code == 400
        employee_login = login(employee_client, "employee-one", USER_PASSWORD)
        assert employee_login.status_code == 200


@pytest.mark.integration
def test_employee_user_list_is_masked_by_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepare_database(monkeypatch, tmp_path, "employee-mask.db")
    create_initial_ceo(username="owner-mask", password=OWNER_PASSWORD, email="owner@example.test")

    with TestClient(app, base_url=ORIGIN) as owner_client:
        signed_in = login(owner_client, "owner-mask", OWNER_PASSWORD)
        csrf = signed_in.json()["csrfToken"]
        created = owner_client.post(
            "/api/v1/users",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={
                "username": "employee-mask",
                "realName": "完整姓名",
                "email": "employee-mask@example.test",
                "phone": "+86 138 0013 8000",
                "role": "employee",
                "department": "research",
            },
        )
        assert created.status_code == 201
        ticket = created.json()["resetTicket"]

    with TestClient(app, base_url=ORIGIN) as employee_client:
        assert reset_password(employee_client, "employee-mask", ticket).status_code == 200
        assert login(employee_client, "employee-mask", USER_PASSWORD).status_code == 200
        users = employee_client.get("/api/v1/users", params={"search": "owner-mask"})
        assert users.status_code == 200
        item = users.json()["items"][0]
        assert item["contactMasked"] is True
        assert item["email"] != "owner@example.test"
        assert "***" in item["email"]
        assert item["realName"] != "Platform Owner"


@pytest.mark.integration
def test_technical_lead_cannot_manage_protected_targets(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepare_database(monkeypatch, tmp_path, "tech-target.db")
    owner = create_initial_ceo(
        username="owner-target",
        password=OWNER_PASSWORD,
        real_name="Platform Owner",
        email="owner@example.test",
    )

    with TestClient(app, base_url=ORIGIN) as owner_client:
        signed_in = login(owner_client, "owner-target", OWNER_PASSWORD)
        owner_csrf = signed_in.json()["csrfToken"]
        created = owner_client.post(
            "/api/v1/users",
            headers={"Origin": ORIGIN, "X-CSRF-Token": owner_csrf},
            json={
                "username": "technical-lead",
                "realName": "Technical Lead",
                "email": "tech@example.test",
                "role": "tech_lead",
            },
        )
        assert created.status_code == 201
        ticket = created.json()["resetTicket"]

    with TestClient(app, base_url=ORIGIN) as tech_client:
        assert reset_password(tech_client, "technical-lead", ticket).status_code == 200
        signed_in = login(tech_client, "technical-lead", USER_PASSWORD)
        assert signed_in.status_code == 200
        csrf = signed_in.json()["csrfToken"]

        owner_detail = tech_client.get(f"/api/v1/users/{owner.id}")
        assert owner_detail.status_code == 200
        forbidden = tech_client.post(
            f"/api/v1/users/{owner.id}/status",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={
                "status": "disabled",
                "reason": "not allowed",
                "expectedVersion": owner_detail.json()["rowVersion"],
            },
        )
        assert forbidden.status_code == 403
        assert forbidden.json()["detail"]["code"] == "protected_user_target_forbidden"

        forbidden_role = tech_client.post(
            f"/api/v1/users/{owner.id}/role",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={
                "role": "employee",
                "expectedVersion": owner_detail.json()["rowVersion"],
            },
        )
        assert forbidden_role.status_code == 403
        assert forbidden_role.json()["detail"]["code"] == "protected_user_target_forbidden"

        ordinary = tech_client.post(
            "/api/v1/users",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={
                "username": "member-by-tech",
                "realName": "Member By Tech",
                "email": "member-by-tech@example.test",
                "role": "member",
                "memberType": "individual",
            },
        )
        assert ordinary.status_code == 201
