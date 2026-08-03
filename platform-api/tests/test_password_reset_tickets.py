from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import connection
from app.database_bootstrap import bootstrap_database
from app.main import app
from app.schema_migrations import PLATFORM_MIGRATIONS, apply_migrations
from app.user_rate_limit import get_public_auth_rate_limiter
from app.user_security import generate_secret_token, hash_secret_token
from app.user_service import create_initial_ceo

ORIGIN = "https://testserver"


def prepare(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> tuple[str, str]:
    settings = get_settings()
    database_path = tmp_path / "password-reset.db"
    monkeypatch.setattr(settings, "database_path", str(database_path))
    monkeypatch.setattr(settings, "environment", "live")
    monkeypatch.setattr(settings, "auth_mode", "api_key")
    monkeypatch.setattr(settings, "auth_credentials_json", "[]")
    monkeypatch.setattr(settings, "cors_origins", ORIGIN)
    get_public_auth_rate_limiter(settings.public_rate_limit_max_keys).clear()
    with sqlite3.connect(database_path) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        bootstrap_database(db)
        apply_migrations(db, PLATFORM_MIGRATIONS)
        db.commit()
    user = create_initial_ceo(
        username="owner",
        password="correct horse battery staple",
        email="owner@example.test",
    )
    raw_ticket = generate_secret_token()
    now = datetime.now(UTC)
    with connection() as db:
        db.execute(
            """
            INSERT INTO password_reset_tickets (
                id, user_id, token_hash, expires_at, created_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                user.id,
                hash_secret_token(raw_ticket),
                (now + timedelta(minutes=30)).isoformat(),
                user.id,
                now.isoformat(),
            ),
        )
    return user.id, raw_ticket


def login(client: TestClient, password: str):
    return client.post(
        "/api/v1/auth/login",
        headers={"Origin": ORIGIN},
        json={"username": "owner", "password": password},
    )


@pytest.mark.integration
def test_reset_ticket_is_single_use_and_revokes_old_sessions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    user_id, raw_ticket = prepare(monkeypatch, tmp_path)
    with TestClient(app, base_url=ORIGIN) as client:
        signed_in = login(client, "correct horse battery staple")
        assert signed_in.status_code == 200

        reset = client.post(
            "/api/v1/auth/reset-password",
            headers={"Origin": ORIGIN},
            json={
                "username": "owner",
                "resetTicket": raw_ticket,
                "newPassword": "new correct horse battery staple",
                "newPasswordConfirmation": "new correct horse battery staple",
            },
        )
        assert reset.status_code == 200
        assert reset.headers["cache-control"] == "no-store"
        assert reset.json()["revokedSessionCount"] == 1
        assert get_settings().session_cookie_name not in client.cookies

        old_password = login(client, "correct horse battery staple")
        assert old_password.status_code == 401
        new_password = login(client, "new correct horse battery staple")
        assert new_password.status_code == 200

        reused = client.post(
            "/api/v1/auth/reset-password",
            headers={"Origin": ORIGIN},
            json={
                "username": "owner",
                "resetTicket": raw_ticket,
                "newPassword": "third correct horse battery staple",
                "newPasswordConfirmation": "third correct horse battery staple",
            },
        )
        assert reused.status_code == 400
        assert reused.json()["detail"]["code"] == "password_reset_ticket_invalid"

    with connection() as db:
        ticket = db.execute(
            "SELECT consumed_at FROM password_reset_tickets WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        audit = db.execute(
            """
            SELECT event_type, result, auth_method
            FROM audit_events
            WHERE event_type = 'user.password_reset_consumed'
            """
        ).fetchone()
    assert ticket["consumed_at"] is not None
    assert audit["result"] == "succeeded"
    assert audit["auth_method"] == "password_reset_ticket"


@pytest.mark.integration
def test_reset_ticket_rejects_wrong_username_without_consuming(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    user_id, raw_ticket = prepare(monkeypatch, tmp_path)
    with TestClient(app, base_url=ORIGIN) as client:
        response = client.post(
            "/api/v1/auth/reset-password",
            headers={"Origin": ORIGIN},
            json={
                "username": "someone-else",
                "resetTicket": raw_ticket,
                "newPassword": "new correct horse battery staple",
                "newPasswordConfirmation": "new correct horse battery staple",
            },
        )
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "password_reset_ticket_invalid"

    with connection() as db:
        ticket = db.execute(
            "SELECT consumed_at FROM password_reset_tickets WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    assert ticket["consumed_at"] is None
