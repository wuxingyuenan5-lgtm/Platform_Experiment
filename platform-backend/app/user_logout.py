from __future__ import annotations

import hmac
from datetime import UTC, datetime

from app.database import connection
from app.user_repository import (
    get_session_with_user_by_token_hash,
    insert_audit_event,
    revoke_session,
)
from app.user_security import hash_secret_token


class LogoutError(RuntimeError):
    def __init__(self, status_code: int, code: str, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail


def logout_session_idempotently(
    *,
    raw_session_token: str | None,
    supplied_csrf_token: str | None,
    request_id: str,
    ip_address: str | None,
) -> None:
    if not raw_session_token:
        return
    timestamp = datetime.now(UTC).isoformat()
    with connection() as db:
        session = get_session_with_user_by_token_hash(
            db,
            hash_secret_token(raw_session_token),
        )
        # Missing, expired-by-cleanup, or already revoked credentials must not prevent
        # the response from deleting the browser cookie.
        if session is None or session.revoked_at is not None:
            return
        if not supplied_csrf_token:
            raise LogoutError(403, "csrf_required", "CSRF token is required")
        if not hmac.compare_digest(
            hash_secret_token(supplied_csrf_token),
            session.csrf_token_hash,
        ):
            raise LogoutError(403, "csrf_invalid", "CSRF token is invalid")
        revoke_session(
            db,
            session_id=session.id,
            revoked_at=timestamp,
            reason="logout",
        )
        insert_audit_event(
            db,
            event_type="auth.logout",
            subject_type="user_session",
            subject_id=session.id,
            actor_user_id=session.user_id,
            auth_method="session",
            result="succeeded",
            details={},
            request_id=request_id,
            ip_address=ip_address,
            now=timestamp,
        )
