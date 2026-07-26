from __future__ import annotations

import hmac
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import Request

from app.config import Settings
from app.database import connection
from app.user_repository import (
    SessionRecord,
    get_session_with_user_by_token_hash,
    revoke_session,
    touch_session,
)
from app.user_security import hash_secret_token


class BrowserSessionError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class AuthenticatedBrowserSession:
    session_id: str
    user_id: str
    role_code: str
    csrf_token_hash: str
    last_reauthenticated_at: datetime | None


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise BrowserSessionError(503, "Session timestamp configuration is invalid")
    return parsed.astimezone(UTC)


def authenticate_browser_session(
    raw_token: str,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> AuthenticatedBrowserSession:
    if not settings.browser_sessions_enabled:
        raise BrowserSessionError(503, "Browser sessions are disabled")
    current = (now or datetime.now(UTC)).astimezone(UTC)
    digest = hash_secret_token(raw_token)
    record: SessionRecord | None = None
    failure: BrowserSessionError | None = None
    with connection() as db:
        record = get_session_with_user_by_token_hash(db, digest)
        if record is None or record.revoked_at is not None:
            failure = BrowserSessionError(401, "Browser session is invalid")
        elif record.lifecycle_status != "active":
            revoke_session(
                db,
                session_id=record.id,
                revoked_at=current.isoformat(),
                reason="user_inactive",
            )
            failure = BrowserSessionError(403, "User account is not active")
        elif record.locked_until is not None and _parse_time(record.locked_until) > current:
            failure = BrowserSessionError(423, "User account is temporarily locked")
        elif record.auth_version != record.user_auth_version:
            revoke_session(
                db,
                session_id=record.id,
                revoked_at=current.isoformat(),
                reason="auth_version_changed",
            )
            failure = BrowserSessionError(401, "Browser session is invalid")
        else:
            absolute_expired = _parse_time(record.expires_at) <= current
            idle_expired = _parse_time(record.idle_expires_at) <= current
            if absolute_expired or idle_expired:
                revoke_session(
                    db,
                    session_id=record.id,
                    revoked_at=current.isoformat(),
                    reason="expired",
                )
                failure = BrowserSessionError(401, "Browser session is invalid")
            else:
                last_seen = _parse_time(record.last_seen_at)
                write_step = timedelta(minutes=settings.session_last_seen_write_minutes)
                if current - last_seen >= write_step:
                    touch_session(
                        db,
                        session_id=record.id,
                        last_seen_at=current.isoformat(),
                        idle_expires_at=(
                            current + timedelta(minutes=settings.session_idle_ttl_minutes)
                        ).isoformat(),
                    )
    if failure is not None:
        raise failure
    if record is None:
        raise BrowserSessionError(401, "Browser session is invalid")
    return AuthenticatedBrowserSession(
        session_id=record.id,
        user_id=record.user_id,
        role_code=record.role_code,
        csrf_token_hash=record.csrf_token_hash,
        last_reauthenticated_at=(
            _parse_time(record.last_reauthenticated_at)
            if record.last_reauthenticated_at is not None
            else None
        ),
    )


def validate_session_csrf(
    request: Request,
    session: AuthenticatedBrowserSession,
    settings: Settings,
) -> None:
    if request.method.upper() in {"GET", "HEAD", "OPTIONS", "TRACE"}:
        return
    origin = request.headers.get("origin")
    if origin is None or origin not in settings.allowed_cors_origins:
        raise BrowserSessionError(403, "Request origin is not trusted")
    supplied_token = request.headers.get("x-csrf-token")
    if not supplied_token:
        raise BrowserSessionError(403, "CSRF token is required")
    supplied_hash = hash_secret_token(supplied_token)
    if not hmac.compare_digest(supplied_hash, session.csrf_token_hash):
        raise BrowserSessionError(403, "CSRF token is invalid")
