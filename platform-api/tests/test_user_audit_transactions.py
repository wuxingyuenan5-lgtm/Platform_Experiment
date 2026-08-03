from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.user_admin_service as admin_service
from app.config import get_settings
from app.database_bootstrap import bootstrap_database
from app.main import app
from app.schema_migrations import PLATFORM_MIGRATIONS, apply_migrations
from app.user_admin_schemas import UpdateManagedUserRequest
from app.user_admin_service import AdminRequestContext, UserAdminServiceError, get_user_detail
from app.user_service import create_initial_ceo

ORIGIN = "https://testserver"
PASSWORD = "correct horse battery staple"


def prepare_database(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Path:
    path = tmp_path / "audit-transaction.db"
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


@pytest.mark.integration
def test_sensitive_write_rolls_back_when_audit_insert_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = prepare_database(monkeypatch, tmp_path)
    owner = create_initial_ceo(
        username="audit-owner",
        password=PASSWORD,
        real_name="Audit Owner",
        email="audit-owner@example.test",
    )

    with TestClient(app, base_url=ORIGIN) as client:
        signed_in = client.post(
            "/api/v1/auth/login",
            headers={"Origin": ORIGIN},
            json={"username": "audit-owner", "password": PASSWORD},
        )
        csrf = signed_in.json()["csrfToken"]
        session_id = signed_in.json()["session"]["sessionId"]
        created = client.post(
            "/api/v1/users",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={
                "username": "audit-member",
                "realName": "Audit Member",
                "email": "audit-member@example.test",
                "role": "member",
                "memberType": "individual",
            },
        )
        target = created.json()["user"]

    context = AdminRequestContext(
        actor_user_id=owner.id,
        actor_role="ceo",
        session_id=session_id,
        request_id="audit-failure",
        ip_address="127.0.0.1",
    )
    before = get_user_detail(user_id=target["userId"], sensitive=True)

    def fail_audit(*args, **kwargs) -> None:
        raise sqlite3.OperationalError("audit storage unavailable")

    monkeypatch.setattr(admin_service, "insert_audit_event", fail_audit)
    with pytest.raises(UserAdminServiceError) as captured:
        admin_service.update_user(
            target["userId"],
            UpdateManagedUserRequest(
                displayName="Must Roll Back",
                expectedVersion=before.row_version,
            ),
            context=context,
        )
    assert captured.value.code == "user_admin_failure"

    with sqlite3.connect(database_path) as db:
        db.row_factory = sqlite3.Row
        row = db.execute(
            "SELECT display_name, row_version FROM users WHERE id = ?",
            (target["userId"],),
        ).fetchone()
    assert row["display_name"] == before.display_name
    assert int(row["row_version"]) == before.row_version
