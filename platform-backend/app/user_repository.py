from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from app.user_security import normalize_email, normalize_phone, normalize_username


class UserRepositoryError(RuntimeError):
    pass


class InitialCeoAlreadyExistsError(UserRepositoryError):
    pass


class UserNotFoundError(UserRepositoryError):
    pass


@dataclass(frozen=True, slots=True)
class UserRecord:
    id: str
    username: str
    password_hash: str
    role_code: str | None
    lifecycle_status: str
    auth_version: int
    failed_login_count: int
    locked_until: str | None


@dataclass(frozen=True, slots=True)
class SessionRecord:
    id: str
    user_id: str
    token_hash: str
    csrf_token_hash: str
    auth_version: int
    created_at: str
    expires_at: str
    idle_expires_at: str
    last_seen_at: str
    last_reauthenticated_at: str | None
    revoked_at: str | None
    role_code: str
    lifecycle_status: str
    user_auth_version: int
    locked_until: str | None


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _user_from_row(row: sqlite3.Row | None) -> UserRecord | None:
    if row is None:
        return None
    return UserRecord(
        id=str(row["id"]),
        username=str(row["username"]),
        password_hash=str(row["password_hash"]),
        role_code=str(row["role_code"]) if row["role_code"] is not None else None,
        lifecycle_status=str(row["lifecycle_status"]),
        auth_version=int(row["auth_version"]),
        failed_login_count=int(row["failed_login_count"]),
        locked_until=str(row["locked_until"]) if row["locked_until"] is not None else None,
    )


def get_user_by_id(db: sqlite3.Connection, user_id: str) -> UserRecord | None:
    row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _user_from_row(row)


def get_user_by_username(db: sqlite3.Connection, username: str) -> UserRecord | None:
    row = db.execute(
        "SELECT * FROM users WHERE username_normalized = ?",
        (normalize_username(username),),
    ).fetchone()
    return _user_from_row(row)


def count_active_ceos(db: sqlite3.Connection) -> int:
    row = db.execute(
        "SELECT COUNT(*) AS count FROM users "
        "WHERE role_code = 'ceo' AND lifecycle_status = 'active'"
    ).fetchone()
    return int(row["count"])


def create_initial_ceo(
    db: sqlite3.Connection,
    *,
    username: str,
    password_hash: str,
    display_name: str | None,
    real_name: str | None,
    email: str | None,
    phone: str | None,
    now: str | None = None,
) -> UserRecord:
    timestamp = now or utc_now_iso()
    if not db.in_transaction:
        db.execute("BEGIN IMMEDIATE")
    if count_active_ceos(db) > 0:
        raise InitialCeoAlreadyExistsError("An active CEO already exists")
    user_id = str(uuid4())
    db.execute(
        """
        INSERT INTO users (
            id, username, username_normalized, password_hash,
            display_name, real_name, phone, phone_normalized,
            email, email_normalized, role_code, requested_role_code,
            lifecycle_status, registered_at, approved_at,
            password_changed_at, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ceo', NULL, 'active', ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            username.strip(),
            normalize_username(username),
            password_hash,
            display_name,
            real_name,
            phone,
            normalize_phone(phone),
            email,
            normalize_email(email),
            timestamp,
            timestamp,
            timestamp,
            timestamp,
            timestamp,
        ),
    )
    created = get_user_by_id(db, user_id)
    if created is None:
        raise UserRepositoryError("Initial CEO creation did not persist")
    return created


def create_session(
    db: sqlite3.Connection,
    *,
    user: UserRecord,
    token_hash: str,
    csrf_token_hash: str,
    created_at: str,
    expires_at: str,
    idle_expires_at: str,
    ip_address: str | None,
    user_agent: str | None,
    max_active_sessions: int,
) -> str:
    if user.role_code is None or user.lifecycle_status != "active":
        raise UserRepositoryError("Only active users with a role may create sessions")
    if max_active_sessions < 1:
        raise ValueError("max_active_sessions must be positive")
    active_rows = db.execute(
        """
        SELECT id FROM user_sessions
        WHERE user_id = ? AND revoked_at IS NULL
        ORDER BY created_at ASC, id ASC
        """,
        (user.id,),
    ).fetchall()
    revoke_count = max(0, len(active_rows) - max_active_sessions + 1)
    for row in active_rows[:revoke_count]:
        db.execute(
            "UPDATE user_sessions SET revoked_at = ?, revoke_reason = ? WHERE id = ?",
            (created_at, "session_limit", str(row["id"])),
        )
    session_id = str(uuid4())
    db.execute(
        """
        INSERT INTO user_sessions (
            id, user_id, token_hash, csrf_token_hash, auth_version,
            created_at, expires_at, idle_expires_at, last_seen_at,
            last_reauthenticated_at, ip_address, user_agent
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            user.id,
            token_hash,
            csrf_token_hash,
            user.auth_version,
            created_at,
            expires_at,
            idle_expires_at,
            created_at,
            created_at,
            ip_address,
            user_agent,
        ),
    )
    return session_id


def get_session_with_user_by_token_hash(
    db: sqlite3.Connection,
    token_hash: str,
) -> SessionRecord | None:
    row = db.execute(
        """
        SELECT
            s.id, s.user_id, s.token_hash, s.csrf_token_hash, s.auth_version,
            s.created_at, s.expires_at, s.idle_expires_at, s.last_seen_at,
            s.last_reauthenticated_at, s.revoked_at,
            u.role_code, u.lifecycle_status,
            u.auth_version AS user_auth_version, u.locked_until
        FROM user_sessions AS s
        JOIN users AS u ON u.id = s.user_id
        WHERE s.token_hash = ?
        """,
        (token_hash,),
    ).fetchone()
    if row is None or row["role_code"] is None:
        return None
    return SessionRecord(
        id=str(row["id"]),
        user_id=str(row["user_id"]),
        token_hash=str(row["token_hash"]),
        csrf_token_hash=str(row["csrf_token_hash"]),
        auth_version=int(row["auth_version"]),
        created_at=str(row["created_at"]),
        expires_at=str(row["expires_at"]),
        idle_expires_at=str(row["idle_expires_at"]),
        last_seen_at=str(row["last_seen_at"]),
        last_reauthenticated_at=(
            str(row["last_reauthenticated_at"])
            if row["last_reauthenticated_at"] is not None
            else None
        ),
        revoked_at=str(row["revoked_at"]) if row["revoked_at"] is not None else None,
        role_code=str(row["role_code"]),
        lifecycle_status=str(row["lifecycle_status"]),
        user_auth_version=int(row["user_auth_version"]),
        locked_until=str(row["locked_until"]) if row["locked_until"] is not None else None,
    )


def touch_session(
    db: sqlite3.Connection,
    *,
    session_id: str,
    last_seen_at: str,
    idle_expires_at: str,
) -> None:
    db.execute(
        """
        UPDATE user_sessions
        SET last_seen_at = ?, idle_expires_at = ?
        WHERE id = ? AND revoked_at IS NULL
        """,
        (last_seen_at, idle_expires_at, session_id),
    )


def revoke_session(
    db: sqlite3.Connection,
    *,
    session_id: str,
    revoked_at: str,
    reason: str,
) -> None:
    db.execute(
        """
        UPDATE user_sessions
        SET revoked_at = COALESCE(revoked_at, ?),
            revoke_reason = CASE WHEN revoked_at IS NULL THEN ? ELSE revoke_reason END
        WHERE id = ?
        """,
        (revoked_at, reason, session_id),
    )


def revoke_all_user_sessions(
    db: sqlite3.Connection,
    *,
    user_id: str,
    revoked_at: str,
    reason: str,
) -> int:
    cursor = db.execute(
        """
        UPDATE user_sessions
        SET revoked_at = ?, revoke_reason = ?
        WHERE user_id = ? AND revoked_at IS NULL
        """,
        (revoked_at, reason, user_id),
    )
    return cursor.rowcount
