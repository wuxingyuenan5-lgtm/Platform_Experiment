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
    path = tmp_path / "target-scope.db"
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
def test_self_admin_mutation_and_stale_versions_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepare_database(monkeypatch, tmp_path)
    owner = create_initial_ceo(
        username="owner-scope",
        password=PASSWORD,
        real_name="Owner Scope",
        email="owner-scope@example.test",
    )

    with TestClient(app, base_url=ORIGIN) as client:
        signed_in = client.post(
            "/api/v1/auth/login",
            headers={"Origin": ORIGIN},
            json={"username": "owner-scope", "password": PASSWORD},
        )
        assert signed_in.status_code == 200
        csrf = signed_in.json()["csrfToken"]

        self_detail = client.get(f"/api/v1/users/{owner.id}")
        self_disable = client.post(
            f"/api/v1/users/{owner.id}/status",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={
                "status": "disabled",
                "reason": "self mutation must fail",
                "expectedVersion": self_detail.json()["rowVersion"],
            },
        )
        assert self_disable.status_code == 403
        assert self_disable.json()["detail"]["code"] == "self_admin_mutation_forbidden"

        created = client.post(
            "/api/v1/users",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={
                "username": "version-member",
                "realName": "Version Member",
                "email": "version-member@example.test",
                "role": "member",
                "memberType": "individual",
            },
        )
        assert created.status_code == 201
        member = created.json()["user"]
        version = member["rowVersion"]

        first_update = client.patch(
            f"/api/v1/users/{member['userId']}",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={"displayName": "First Update", "expectedVersion": version},
        )
        assert first_update.status_code == 200
        assert first_update.json()["rowVersion"] == version + 1

        stale_update = client.patch(
            f"/api/v1/users/{member['userId']}",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            json={"displayName": "Stale Update", "expectedVersion": version},
        )
        assert stale_update.status_code == 409
        assert stale_update.json()["detail"]["code"] == "row_version_conflict"
