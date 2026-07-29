from __future__ import annotations

import json
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
def test_ceo_updates_operational_note_with_version_and_redacted_audit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = prepare_database(monkeypatch, tmp_path, "admin-note.db")
    create_initial_ceo(username="owner-note", password=OWNER_PASSWORD, email="owner@example.test")

    with TestClient(app, base_url=ORIGIN) as client:
        signed_in = login(client, "owner-note", OWNER_PASSWORD)
        assert signed_in.status_code == 200
        csrf = signed_in.json()["csrfToken"]
        created = client.post(
            "/api/v1/users",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={
                "username": "member-note",
                "realName": "备注会员",
                "email": "member-note@example.test",
                "role": "member",
                "memberType": "individual",
            },
        )
        assert created.status_code == 201
        user = created.json()["user"]
        user_id = user["userId"]

        initial = client.get(f"/api/v1/users/{user_id}/admin-note")
        assert initial.status_code == 200
        assert initial.json()["adminNote"] is None
        assert initial.headers["cache-control"] == "no-store"

        note = "朋友介绍，优先安排产品说明。"
        updated = client.patch(
            f"/api/v1/users/{user_id}/admin-note",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={"adminNote": note, "expectedVersion": initial.json()["rowVersion"]},
        )
        assert updated.status_code == 200
        assert updated.json()["adminNote"] == note
        assert updated.json()["rowVersion"] == initial.json()["rowVersion"] + 1

        stale = client.patch(
            f"/api/v1/users/{user_id}/admin-note",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={"adminNote": "stale write", "expectedVersion": initial.json()["rowVersion"]},
        )
        assert stale.status_code == 409
        assert stale.json()["detail"]["code"] == "row_version_conflict"

    with sqlite3.connect(database_path) as db:
        db.row_factory = sqlite3.Row
        event = db.execute(
            """
            SELECT details_json
            FROM audit_events
            WHERE subject_id = ? AND event_type = 'user.admin_note_updated'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user_id,),
        ).fetchone()
    details = json.loads(str(event["details_json"]))
    assert details == {"changedFields": ["admin_note"], "cleared": False}
    assert note not in json.dumps(details, ensure_ascii=False)


@pytest.mark.integration
def test_employee_cannot_read_operational_notes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepare_database(monkeypatch, tmp_path, "admin-note-scope.db")
    create_initial_ceo(username="owner-scope", password=OWNER_PASSWORD, email="owner@example.test")

    with TestClient(app, base_url=ORIGIN) as owner_client:
        signed_in = login(owner_client, "owner-scope", OWNER_PASSWORD)
        csrf = signed_in.json()["csrfToken"]
        employee = owner_client.post(
            "/api/v1/users",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={
                "username": "employee-scope",
                "realName": "范围员工",
                "email": "employee-scope@example.test",
                "role": "employee",
                "department": "operations",
            },
        )
        member = owner_client.post(
            "/api/v1/users",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={
                "username": "member-scope",
                "realName": "范围会员",
                "email": "member-scope@example.test",
                "role": "member",
                "memberType": "individual",
            },
        )
        assert employee.status_code == 201
        assert member.status_code == 201
        employee_ticket = employee.json()["resetTicket"]
        member_id = member.json()["user"]["userId"]

    with TestClient(app, base_url=ORIGIN) as employee_client:
        assert reset_password(employee_client, "employee-scope", employee_ticket).status_code == 200
        assert login(employee_client, "employee-scope", USER_PASSWORD).status_code == 200
        forbidden = employee_client.get(f"/api/v1/users/{member_id}/admin-note")
        assert forbidden.status_code == 403
