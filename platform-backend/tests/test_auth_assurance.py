from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.auth import AuthenticationMiddleware
from app.config import get_settings
from app.database_bootstrap import bootstrap_database
from app.schema_migrations import PLATFORM_MIGRATIONS, apply_migrations
from app.user_service import create_initial_ceo, issue_browser_session


def initialize_user_database(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        bootstrap_database(db)
        apply_migrations(db, PLATFORM_MIGRATIONS)
        db.commit()


def credential(token: str) -> dict[str, object]:
    return {
        "credentialId": "credential-admin",
        "userId": "api-admin",
        "tokenSha256": hashlib.sha256(token.encode("utf-8")).hexdigest(),
        "roles": ["admin"],
        "status": "active",
    }


def build_app() -> FastAPI:
    app = FastAPI()

    @app.get("/api/v1/system/info")
    def info(request: Request) -> dict[str, str]:
        return {"user": request.state.principal.user_id}

    @app.post("/api/v1/system/write")
    def write(request: Request) -> dict[str, str]:
        return {"user": request.state.principal.user_id}

    @app.get("/api/v1/me")
    def me(request: Request) -> dict[str, str]:
        return {"user": request.state.principal.user_id}

    app.add_middleware(AuthenticationMiddleware)
    return app


def configure_live_auth(
    monkeypatch: pytest.MonkeyPatch,
    database_path: Path,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(database_path))
    monkeypatch.setattr(settings, "environment", "live")
    monkeypatch.setattr(settings, "auth_mode", "api_key")
    monkeypatch.setattr(
        settings,
        "auth_credentials_json",
        json.dumps([credential("api-token")]),
    )


def seed_browser_session() -> tuple[str, str]:
    created = create_initial_ceo(
        username="Owner",
        password="correct horse battery staple",
    )
    issued = issue_browser_session(
        user_id=created.id,
        ip_address="127.0.0.1",
        user_agent="pytest",
        now=datetime.now(UTC),
    )
    return issued.session_token, issued.csrf_token


def assert_auth_error(
    response,
    *,
    status_code: int,
    code: str,
    message_fragment: str,
) -> None:
    assert response.status_code == status_code
    payload = response.json()
    assert payload["detail"]["code"] == code
    assert message_fragment in payload["detail"]["message"]
    assert payload["requestId"] == response.headers["x-request-id"]


def latest_denial_audit(database_path: Path) -> dict[str, object]:
    with sqlite3.connect(database_path) as db:
        db.row_factory = sqlite3.Row
        row = db.execute(
            """
            SELECT details_json
            FROM audit_events
            WHERE event_type = 'authentication_or_authorization_denied'
            ORDER BY created_at DESC
            LIMIT 1
            """
        ).fetchone()
    assert row is not None
    return json.loads(str(row["details_json"]))


def test_ambiguous_cookie_and_bearer_are_rejected_and_audited(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "ambiguous-auth.db"
    initialize_user_database(database_path)
    configure_live_auth(monkeypatch, database_path)
    session_token, _ = seed_browser_session()

    with TestClient(build_app()) as client:
        client.cookies.set(get_settings().session_cookie_name, session_token)
        response = client.get(
            "/api/v1/system/info",
            headers={"Authorization": "Bearer api-token"},
        )

    assert_auth_error(
        response,
        status_code=400,
        code="ambiguous_credentials",
        message_fragment="Ambiguous",
    )
    audit = latest_denial_audit(database_path)
    assert audit["code"] == "ambiguous_credentials"
    assert audit["path"] == "/api/v1/system/info"
    assert audit["permission"] == "platform:read"
    serialized = json.dumps(audit, ensure_ascii=False)
    assert "api-token" not in serialized
    assert session_token not in serialized


def test_customer_identity_domain_rejects_api_key_wildcard(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "human-domain.db"
    initialize_user_database(database_path)
    configure_live_auth(monkeypatch, database_path)

    with TestClient(build_app()) as client:
        response = client.get(
            "/api/v1/me",
            headers={"Authorization": "Bearer api-token"},
        )

    assert_auth_error(
        response,
        status_code=403,
        code="human_session_required",
        message_fragment="browser session",
    )


def test_live_write_rejects_browser_session_but_allows_platform_read(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "live-write-assurance.db"
    initialize_user_database(database_path)
    configure_live_auth(monkeypatch, database_path)
    session_token, csrf_token = seed_browser_session()

    with TestClient(build_app()) as client:
        client.cookies.set(get_settings().session_cookie_name, session_token)
        read_response = client.get("/api/v1/system/info")
        write_response = client.post(
            "/api/v1/system/write",
            headers={
                "Origin": "http://localhost:5173",
                "X-CSRF-Token": csrf_token,
            },
        )

    assert read_response.status_code == 200
    assert_auth_error(
        write_response,
        status_code=403,
        code="live_api_key_required",
        message_fragment="API-key",
    )
