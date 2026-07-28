from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.auth import token_hash
from app.config import get_settings
from app.database_bootstrap import bootstrap_database
from app.database_seeds import seed_reference_data
from app.main import app
from app.schema_migrations import PLATFORM_MIGRATIONS, apply_migrations
from app.user_rate_limit import get_public_auth_rate_limiter
from app.user_service import create_initial_ceo

ORIGIN = "https://testserver"
OWNER_PASSWORD = "correct horse battery staple"
USER_PASSWORD = "another correct horse battery staple"
API_TOKEN = "api-key-admin-holding-scope-test-token"


def prepare_database(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Path:
    path = tmp_path / "holding-scope.db"
    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(path))
    monkeypatch.setattr(settings, "environment", "live")
    monkeypatch.setattr(settings, "auth_mode", "api_key")
    monkeypatch.setattr(settings, "cors_origins", ORIGIN)
    monkeypatch.setattr(settings, "public_login_rate_limit", 1000)
    monkeypatch.setattr(settings, "public_password_reset_rate_limit", 1000)
    monkeypatch.setattr(
        settings,
        "auth_credentials_json",
        json.dumps(
            [
                {
                    "credentialId": "holding-api-admin",
                    "userId": "automation-admin",
                    "tokenSha256": token_hash(API_TOKEN),
                    "roles": ["admin"],
                    "status": "active",
                }
            ]
        ),
    )
    get_public_auth_rate_limiter(settings.public_rate_limit_max_keys).clear()
    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        bootstrap_database(db)
        apply_migrations(db, PLATFORM_MIGRATIONS)
        seed_reference_data(db)
        db.commit()
    return path


def login(client: TestClient, username: str, password: str):
    return client.post(
        "/api/v1/auth/login",
        headers={"Origin": ORIGIN},
        json={"username": username, "password": password},
    )


def create_user(
    owner_client: TestClient,
    csrf: str,
    *,
    username: str,
    role: str,
) -> tuple[str, str]:
    body: dict[str, object] = {
        "username": username,
        "realName": f"Fictional {username}",
        "email": f"{username}@example.test",
        "role": role,
    }
    if role == "member":
        body["memberType"] = "individual"
    if role == "employee":
        body["department"] = "operations"
    created = owner_client.post(
        "/api/v1/users",
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
        json=body,
    )
    assert created.status_code == 201
    payload = created.json()
    return payload["user"]["userId"], payload["resetTicket"]


def activate_and_login(
    client: TestClient,
    *,
    username: str,
    ticket: str,
):
    reset = client.post(
        "/api/v1/auth/reset-password",
        headers={"Origin": ORIGIN},
        json={
            "username": username,
            "resetTicket": ticket,
            "newPassword": USER_PASSWORD,
            "newPasswordConfirmation": USER_PASSWORD,
        },
    )
    assert reset.status_code == 200
    signed_in = login(client, username, USER_PASSWORD)
    assert signed_in.status_code == 200
    return signed_in


@pytest.mark.integration
def test_holding_scope_is_enforced_by_backend_and_api_key_wildcard_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = prepare_database(monkeypatch, tmp_path)
    create_initial_ceo(
        username="scope-owner",
        password=OWNER_PASSWORD,
        real_name="Scope Owner",
        email="scope-owner@example.test",
    )

    with TestClient(app, base_url=ORIGIN) as owner_client:
        owner_login = login(owner_client, "scope-owner", OWNER_PASSWORD)
        owner_csrf = owner_login.json()["csrfToken"]
        member_one_id, member_one_ticket = create_user(
            owner_client,
            owner_csrf,
            username="scope-member-one",
            role="member",
        )
        member_two_id, member_two_ticket = create_user(
            owner_client,
            owner_csrf,
            username="scope-member-two",
            role="member",
        )
        _, employee_ticket = create_user(
            owner_client,
            owner_csrf,
            username="scope-employee",
            role="employee",
        )
        _, tech_ticket = create_user(
            owner_client,
            owner_csrf,
            username="scope-tech",
            role="tech_lead",
        )

        holding = owner_client.put(
            f"/api/v1/users/{member_one_id}/holdings/fund_default",
            headers={"Origin": ORIGIN, "X-CSRF-Token": owner_csrf},
            json={
                "shareQuantity": "10",
                "cumulativeInvested": "100",
                "asOf": datetime.now(UTC).isoformat(),
                "source": "manual_admin",
                "status": "active",
            },
        )
        assert holding.status_code == 200

        complete = owner_client.get(f"/api/v1/users/{member_one_id}/holdings")
        assert complete.status_code == 200
        assert complete.json()["items"][0]["memberUserId"] == member_one_id

    with TestClient(app, base_url=ORIGIN) as member_one_client:
        activate_and_login(
            member_one_client,
            username="scope-member-one",
            ticket=member_one_ticket,
        )
        own = member_one_client.get("/api/v1/me/holdings")
        assert own.status_code == 200
        assert own.json()["items"][0]["memberUserId"] == member_one_id
        other = member_one_client.get(f"/api/v1/users/{member_two_id}/holdings")
        assert other.status_code == 403

    with TestClient(app, base_url=ORIGIN) as member_two_client:
        activate_and_login(
            member_two_client,
            username="scope-member-two",
            ticket=member_two_ticket,
        )
        own = member_two_client.get("/api/v1/me/holdings")
        assert own.status_code == 200
        assert own.json()["items"] == []

    with TestClient(app, base_url=ORIGIN) as employee_client:
        activate_and_login(
            employee_client,
            username="scope-employee",
            ticket=employee_ticket,
        )
        denied = employee_client.get(f"/api/v1/users/{member_one_id}/holdings")
        assert denied.status_code == 403

    with TestClient(app, base_url=ORIGIN) as tech_client:
        activate_and_login(
            tech_client,
            username="scope-tech",
            ticket=tech_ticket,
        )
        denied = tech_client.get(f"/api/v1/users/{member_one_id}/holdings")
        assert denied.status_code == 403

    with TestClient(app, base_url=ORIGIN) as api_client:
        denied = api_client.get(
            f"/api/v1/users/{member_one_id}/holdings",
            headers={"Authorization": f"Bearer {API_TOKEN}"},
        )
        assert denied.status_code == 403
        assert "Human browser session" in denied.json()["detail"]["message"]

    with sqlite3.connect(database_path) as db:
        db.row_factory = sqlite3.Row
        event = db.execute(
            """
            SELECT event_type, actor_user_id FROM audit_events
            WHERE event_type = 'member.holdings_viewed_by_admin'
              AND subject_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (member_one_id,),
        ).fetchone()
    assert event["event_type"] == "member.holdings_viewed_by_admin"


@pytest.mark.integration
def test_holding_write_requires_recent_reauthentication(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = prepare_database(monkeypatch, tmp_path)
    create_initial_ceo(
        username="reauth-owner",
        password=OWNER_PASSWORD,
        real_name="Reauth Owner",
        email="reauth-owner@example.test",
    )

    with TestClient(app, base_url=ORIGIN) as owner_client:
        owner_login = login(owner_client, "reauth-owner", OWNER_PASSWORD)
        owner_csrf = owner_login.json()["csrfToken"]
        member_id, _ = create_user(
            owner_client,
            owner_csrf,
            username="reauth-member",
            role="member",
        )

        with sqlite3.connect(database_path) as db:
            db.execute(
                """
                UPDATE user_sessions
                SET last_reauthenticated_at = ?
                WHERE id = ?
                """,
                (
                    (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
                    owner_login.json()["session"]["sessionId"],
                ),
            )
            db.commit()

        denied = owner_client.put(
            f"/api/v1/users/{member_id}/holdings/fund_default",
            headers={"Origin": ORIGIN, "X-CSRF-Token": owner_csrf},
            json={
                "shareQuantity": "10",
                "cumulativeInvested": "100",
                "asOf": datetime.now(UTC).isoformat(),
                "source": "manual_admin",
                "status": "active",
            },
        )
        assert denied.status_code == 403
        assert denied.json()["detail"]["code"] == "recent_reauthentication_required"

        reauthenticated = owner_client.post(
            "/api/v1/auth/reauth",
            headers={"Origin": ORIGIN, "X-CSRF-Token": owner_csrf},
            json={"password": OWNER_PASSWORD},
        )
        assert reauthenticated.status_code == 200

        allowed = owner_client.put(
            f"/api/v1/users/{member_id}/holdings/fund_default",
            headers={"Origin": ORIGIN, "X-CSRF-Token": owner_csrf},
            json={
                "shareQuantity": "10",
                "cumulativeInvested": "100",
                "asOf": datetime.now(UTC).isoformat(),
                "source": "manual_admin",
                "status": "active",
            },
        )
        assert allowed.status_code == 200
        assert allowed.json()["memberUserId"] == member_id
