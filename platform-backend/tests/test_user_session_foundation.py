from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi import Request

from app.config import get_settings
from app.database import connection
from app.database_bootstrap import bootstrap_database
from app.schema_migrations import PLATFORM_MIGRATIONS, apply_migrations
from app.user_authority import LastActiveCeoError, assert_active_ceo_remains
from app.user_repository import InitialCeoAlreadyExistsError
from app.user_service import create_initial_ceo, issue_browser_session
from app.user_session_auth import (
    BrowserSessionError,
    authenticate_browser_session,
    validate_session_csrf,
)


def initialize_user_database(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        bootstrap_database(db)
        apply_migrations(db, PLATFORM_MIGRATIONS)
        db.commit()


def request(
    method: str,
    *,
    origin: str | None = None,
    csrf_token: str | None = None,
) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if origin is not None:
        headers.append((b"origin", origin.encode("utf-8")))
    if csrf_token is not None:
        headers.append((b"x-csrf-token", csrf_token.encode("utf-8")))
    return Request(
        {
            "type": "http",
            "method": method,
            "path": "/api/v1/me",
            "headers": headers,
        }
    )


@pytest.mark.integration
def test_initial_ceo_is_single_and_audited(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "initial-ceo.db"
    initialize_user_database(database_path)
    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(database_path))

    created = create_initial_ceo(
        username="Owner",
        password="correct horse battery staple",
        display_name="Owner",
        real_name="Platform Owner",
        email="owner@example.test",
    )
    assert created.role_code == "ceo"
    assert created.lifecycle_status == "active"

    with pytest.raises(InitialCeoAlreadyExistsError):
        create_initial_ceo(
            username="OwnerTwo",
            password="another correct horse battery staple",
        )

    with connection() as db:
        audit = db.execute(
            """
            SELECT event_type, subject_id, actor_user_id, result, auth_method
            FROM audit_events
            WHERE event_type = 'user.initial_ceo_created'
            """
        ).fetchone()
    assert audit["subject_id"] == created.id
    assert audit["actor_user_id"] == created.id
    assert audit["result"] == "succeeded"
    assert audit["auth_method"] == "bootstrap"


@pytest.mark.integration
def test_browser_session_uses_hashes_expiry_and_csrf(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "browser-session.db"
    initialize_user_database(database_path)
    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(database_path))
    monkeypatch.setattr(settings, "session_absolute_ttl_minutes", 720)
    monkeypatch.setattr(settings, "session_idle_ttl_minutes", 30)
    monkeypatch.setattr(settings, "session_last_seen_write_minutes", 5)

    created = create_initial_ceo(
        username="Owner",
        password="correct horse battery staple",
    )
    now = datetime.now(UTC)
    issued = issue_browser_session(
        user_id=created.id,
        ip_address="127.0.0.1",
        user_agent="pytest",
        now=now,
    )

    with connection() as db:
        stored = db.execute(
            "SELECT token_hash, csrf_token_hash FROM user_sessions WHERE id = ?",
            (issued.session_id,),
        ).fetchone()
    assert stored["token_hash"] != issued.session_token
    assert stored["csrf_token_hash"] != issued.csrf_token

    authenticated = authenticate_browser_session(
        issued.session_token,
        settings,
        now=now + timedelta(minutes=1),
    )
    assert authenticated.user_id == created.id
    validate_session_csrf(
        request(
            "POST",
            origin="http://localhost:5173",
            csrf_token=issued.csrf_token,
        ),
        authenticated,
        settings,
    )

    with pytest.raises(BrowserSessionError, match="CSRF token") as missing_csrf:
        validate_session_csrf(
            request("POST", origin="http://localhost:5173"),
            authenticated,
            settings,
        )
    assert missing_csrf.value.code == "csrf_required"

    with pytest.raises(BrowserSessionError, match="origin") as untrusted_origin:
        validate_session_csrf(
            request(
                "POST",
                origin="https://untrusted.example",
                csrf_token=issued.csrf_token,
            ),
            authenticated,
            settings,
        )
    assert untrusted_origin.value.code == "untrusted_origin"

    with pytest.raises(BrowserSessionError, match="invalid") as expired_session:
        authenticate_browser_session(
            issued.session_token,
            settings,
            now=now + timedelta(hours=13),
        )
    assert expired_session.value.code == "invalid_session"

    with connection() as db:
        revoked = db.execute(
            "SELECT revoked_at, revoke_reason FROM user_sessions WHERE id = ?",
            (issued.session_id,),
        ).fetchone()
    assert revoked["revoked_at"] is not None
    assert revoked["revoke_reason"] == "expired"


@pytest.mark.integration
def test_last_active_ceo_guard_is_transactional(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "last-ceo.db"
    initialize_user_database(database_path)
    settings = get_settings()
    monkeypatch.setattr(settings, "database_path", str(database_path))
    created = create_initial_ceo(
        username="Owner",
        password="correct horse battery staple",
    )

    with connection() as db:
        with pytest.raises(LastActiveCeoError):
            assert_active_ceo_remains(
                db,
                target_user_id=created.id,
                resulting_role="employee",
                resulting_status="active",
            )
        assert_active_ceo_remains(
            db,
            target_user_id=created.id,
            resulting_role="ceo",
            resulting_status="active",
        )
