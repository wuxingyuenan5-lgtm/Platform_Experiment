from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.config import get_settings
from app.database import connection
from app.user_repository import UserRecord, create_initial_ceo as insert_initial_ceo
from app.user_repository import create_session, get_user_by_id
from app.user_security import (
    generate_secret_token,
    hash_password,
    hash_secret_token,
    validate_password,
)


@dataclass(frozen=True, slots=True)
class IssuedBrowserSession:
    session_id: str
    session_token: str
    csrf_token: str
    expires_at: datetime


def create_initial_ceo(
    *,
    username: str,
    password: str,
    display_name: str | None = None,
    real_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
) -> UserRecord:
    validate_password(password, username=username, email=email, phone=phone)
    password_hash = hash_password(password)
    with connection() as db:
        created = insert_initial_ceo(
            db,
            username=username,
            password_hash=password_hash,
            display_name=display_name,
            real_name=real_name,
            email=email,
            phone=phone,
        )
        db.execute(
            """
            INSERT INTO audit_events (
                id, event_type, subject_type, subject_id, details_json, created_at,
                actor_user_id, result, auth_method
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                "user.initial_ceo_created",
                "user",
                created.id,
                json.dumps(
                    {"role": "ceo", "lifecycleStatus": "active"},
                    sort_keys=True,
                ),
                datetime.now(UTC).isoformat(),
                created.id,
                "succeeded",
                "bootstrap",
            ),
        )
        return created


def issue_browser_session(
    *,
    user_id: str,
    ip_address: str | None,
    user_agent: str | None,
    now: datetime | None = None,
) -> IssuedBrowserSession:
    settings = get_settings()
    current = (now or datetime.now(UTC)).astimezone(UTC)
    session_token = generate_secret_token()
    csrf_token = generate_secret_token()
    expires_at = current + timedelta(minutes=settings.session_absolute_ttl_minutes)
    idle_expires_at = current + timedelta(minutes=settings.session_idle_ttl_minutes)
    with connection() as db:
        user = get_user_by_id(db, user_id)
        if user is None:
            raise ValueError("User does not exist")
        if user.locked_until is not None:
            locked_until = datetime.fromisoformat(user.locked_until)
            if locked_until.tzinfo is None or locked_until.astimezone(UTC) > current:
                raise ValueError("User account is temporarily locked")
        session_id = create_session(
            db,
            user=user,
            token_hash=hash_secret_token(session_token),
            csrf_token_hash=hash_secret_token(csrf_token),
            created_at=current.isoformat(),
            expires_at=expires_at.isoformat(),
            idle_expires_at=idle_expires_at.isoformat(),
            ip_address=ip_address,
            user_agent=user_agent,
            max_active_sessions=settings.session_max_active_per_user,
        )
    return IssuedBrowserSession(
        session_id=session_id,
        session_token=session_token,
        csrf_token=csrf_token,
        expires_at=expires_at,
    )
