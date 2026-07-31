from __future__ import annotations

from datetime import UTC, datetime

from app.database import connection
from app.user_repository import (
    change_password,
    insert_audit_event,
)
from app.user_security import (
    PasswordPolicyError,
    hash_password,
    hash_secret_token,
    normalize_username,
    validate_password,
)


class PasswordResetError(RuntimeError):
    def __init__(self, status_code: int, code: str, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail


def consume_password_reset_ticket(
    *,
    username: str,
    raw_ticket: str,
    new_password: str,
    request_id: str,
    ip_address: str | None,
    now: datetime | None = None,
) -> int:
    current = (now or datetime.now(UTC)).astimezone(UTC)
    timestamp = current.isoformat()
    failure = PasswordResetError(
        400,
        "password_reset_ticket_invalid",
        "重置凭证无效或已过期",
    )
    with connection() as db:
        if not db.in_transaction:
            db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            """
            SELECT
                t.id AS ticket_id,
                t.user_id,
                t.expires_at,
                t.consumed_at,
                t.revoked_at,
                u.username,
                u.username_normalized,
                u.email,
                u.phone,
                u.lifecycle_status
            FROM password_reset_tickets AS t
            JOIN users AS u ON u.id = t.user_id
            WHERE t.token_hash = ?
            """,
            (hash_secret_token(raw_ticket),),
        ).fetchone()
        if row is None:
            raise failure
        expires_at = datetime.fromisoformat(str(row["expires_at"]))
        valid = (
            expires_at.tzinfo is not None
            and expires_at.astimezone(UTC) > current
            and row["consumed_at"] is None
            and row["revoked_at"] is None
            and str(row["lifecycle_status"]) in {"active", "disabled"}
            and str(row["username_normalized"]) == normalize_username(username)
        )
        if not valid:
            raise failure
        try:
            validate_password(
                new_password,
                username=str(row["username"]),
                email=str(row["email"]) if row["email"] is not None else None,
                phone=str(row["phone"]) if row["phone"] is not None else None,
            )
        except PasswordPolicyError as exc:
            raise PasswordResetError(422, "password_policy_failed", str(exc)) from exc

        consumed = db.execute(
            """
            UPDATE password_reset_tickets
            SET consumed_at = ?
            WHERE id = ? AND consumed_at IS NULL AND revoked_at IS NULL
            """,
            (timestamp, str(row["ticket_id"])),
        )
        if consumed.rowcount != 1:
            raise failure
        revoked_count = change_password(
            db,
            user_id=str(row["user_id"]),
            password_hash=hash_password(new_password),
            now=timestamp,
        )
        insert_audit_event(
            db,
            event_type="user.password_reset_consumed",
            subject_type="user",
            subject_id=str(row["user_id"]),
            actor_user_id=str(row["user_id"]),
            auth_method="password_reset_ticket",
            result="succeeded",
            details={"revokedSessionCount": revoked_count},
            request_id=request_id,
            ip_address=ip_address,
            now=timestamp,
        )
    return revoked_count
