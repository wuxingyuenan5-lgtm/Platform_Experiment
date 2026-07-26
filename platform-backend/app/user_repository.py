from __future__ import annotations

import json
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


class ConcurrentUserUpdateError(UserRepositoryError):
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
class UserProfileRecord:
    id: str
    username: str
    display_name: str | None
    real_name: str | None
    avatar_key: str | None
    phone: str | None
    email: str | None
    role_code: str | None
    requested_role_code: str | None
    department: str | None
    member_type: str | None
    lifecycle_status: str
    registered_at: str
    last_login_at: str | None
    row_version: int


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


@dataclass(frozen=True, slots=True)
class SessionSummaryRecord:
    id: str
    created_at: str
    expires_at: str
    idle_expires_at: str
    last_seen_at: str
    last_reauthenticated_at: str | None
    ip_address: str | None
    user_agent: str | None


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


def _profile_from_row(row: sqlite3.Row | None) -> UserProfileRecord | None:
    if row is None:
        return None
    return UserProfileRecord(
        id=str(row["id"]),
        username=str(row["username"]),
        display_name=str(row["display_name"]) if row["display_name"] is not None else None,
        real_name=str(row["real_name"]) if row["real_name"] is not None else None,
        avatar_key=str(row["avatar_key"]) if row["avatar_key"] is not None else None,
        phone=str(row["phone"]) if row["phone"] is not None else None,
        email=str(row["email"]) if row["email"] is not None else None,
        role_code=str(row["role_code"]) if row["role_code"] is not None else None,
        requested_role_code=(
            str(row["requested_role_code"])
            if row["requested_role_code"] is not None
            else None
        ),
        department=str(row["department"]) if row["department"] is not None else None,
        member_type=str(row["member_type"]) if row["member_type"] is not None else None,
        lifecycle_status=str(row["lifecycle_status"]),
        registered_at=str(row["registered_at"]),
        last_login_at=str(row["last_login_at"]) if row["last_login_at"] is not None else None,
        row_version=int(row["row_version"]),
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


def get_user_profile(db: sqlite3.Connection, user_id: str) -> UserProfileRecord | None:
    row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _profile_from_row(row)


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


def create_pending_registration(
    db: sqlite3.Connection,
    *,
    username: str,
    password_hash: str,
    real_name: str,
    email: str | None,
    phone: str | None,
    requested_role_code: str,
    department: str | None,
    member_type: str | None,
    application_note: str | None,
    now: str,
) -> UserProfileRecord:
    user_id = str(uuid4())
    db.execute(
        """
        INSERT INTO users (
            id, username, username_normalized, password_hash,
            display_name, real_name, phone, phone_normalized,
            email, email_normalized, role_code, requested_role_code,
            department, member_type, application_note,
            lifecycle_status, registered_at, password_changed_at,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)
        """,
        (
            user_id,
            username.strip(),
            normalize_username(username),
            password_hash,
            real_name.strip(),
            real_name.strip(),
            phone,
            normalize_phone(phone),
            email,
            normalize_email(email),
            requested_role_code,
            department,
            member_type,
            application_note,
            now,
            now,
            now,
            now,
        ),
    )
    created = get_user_profile(db, user_id)
    if created is None:
        raise UserRepositoryError("Registration did not persist")
    return created


def record_login_failure(
    db: sqlite3.Connection,
    *,
    user_id: str,
    locked_until: str | None,
    now: str,
) -> int:
    cursor = db.execute(
        """
        UPDATE users
        SET failed_login_count = failed_login_count + 1,
            locked_until = COALESCE(?, locked_until),
            updated_at = ?
        WHERE id = ?
        """,
        (locked_until, now, user_id),
    )
    if cursor.rowcount != 1:
        raise UserNotFoundError("User does not exist")
    row = db.execute(
        "SELECT failed_login_count FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    return int(row["failed_login_count"])


def record_login_success(db: sqlite3.Connection, *, user_id: str, now: str) -> None:
    cursor = db.execute(
        """
        UPDATE users
        SET failed_login_count = 0,
            locked_until = NULL,
            last_login_at = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (now, now, user_id),
    )
    if cursor.rowcount != 1:
        raise UserNotFoundError("User does not exist")


def upgrade_password_hash(
    db: sqlite3.Connection,
    *,
    user_id: str,
    password_hash: str,
    now: str,
) -> None:
    db.execute(
        "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
        (password_hash, now, user_id),
    )


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


def get_session_owner(db: sqlite3.Connection, session_id: str) -> str | None:
    row = db.execute(
        "SELECT user_id FROM user_sessions WHERE id = ?",
        (session_id,),
    ).fetchone()
    return str(row["user_id"]) if row is not None else None


def list_active_user_sessions(
    db: sqlite3.Connection,
    user_id: str,
) -> list[SessionSummaryRecord]:
    rows = db.execute(
        """
        SELECT id, created_at, expires_at, idle_expires_at, last_seen_at,
               last_reauthenticated_at, ip_address, user_agent
        FROM user_sessions
        WHERE user_id = ? AND revoked_at IS NULL
        ORDER BY last_seen_at DESC, created_at DESC
        """,
        (user_id,),
    ).fetchall()
    return [
        SessionSummaryRecord(
            id=str(row["id"]),
            created_at=str(row["created_at"]),
            expires_at=str(row["expires_at"]),
            idle_expires_at=str(row["idle_expires_at"]),
            last_seen_at=str(row["last_seen_at"]),
            last_reauthenticated_at=(
                str(row["last_reauthenticated_at"])
                if row["last_reauthenticated_at"] is not None
                else None
            ),
            ip_address=str(row["ip_address"]) if row["ip_address"] is not None else None,
            user_agent=str(row["user_agent"]) if row["user_agent"] is not None else None,
        )
        for row in rows
    ]


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


def rotate_session_csrf(
    db: sqlite3.Connection,
    *,
    session_id: str,
    csrf_token_hash: str,
) -> None:
    cursor = db.execute(
        """
        UPDATE user_sessions SET csrf_token_hash = ?
        WHERE id = ? AND revoked_at IS NULL
        """,
        (csrf_token_hash, session_id),
    )
    if cursor.rowcount != 1:
        raise UserRepositoryError("Active Session does not exist")


def record_session_reauthentication(
    db: sqlite3.Connection,
    *,
    session_id: str,
    now: str,
) -> None:
    cursor = db.execute(
        """
        UPDATE user_sessions SET last_reauthenticated_at = ?
        WHERE id = ? AND revoked_at IS NULL
        """,
        (now, session_id),
    )
    if cursor.rowcount != 1:
        raise UserRepositoryError("Active Session does not exist")


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


def revoke_other_user_sessions(
    db: sqlite3.Connection,
    *,
    user_id: str,
    current_session_id: str,
    revoked_at: str,
    reason: str,
) -> int:
    cursor = db.execute(
        """
        UPDATE user_sessions
        SET revoked_at = ?, revoke_reason = ?
        WHERE user_id = ? AND id <> ? AND revoked_at IS NULL
        """,
        (revoked_at, reason, user_id, current_session_id),
    )
    return cursor.rowcount


def update_self_profile(
    db: sqlite3.Connection,
    *,
    user_id: str,
    display_name: str | None,
    email: str | None,
    phone: str | None,
    expected_version: int,
    now: str,
) -> UserProfileRecord:
    cursor = db.execute(
        """
        UPDATE users
        SET display_name = ?,
            email = ?,
            email_normalized = ?,
            phone = ?,
            phone_normalized = ?,
            row_version = row_version + 1,
            updated_at = ?
        WHERE id = ? AND row_version = ?
        """,
        (
            display_name,
            email,
            normalize_email(email),
            phone,
            normalize_phone(phone),
            now,
            user_id,
            expected_version,
        ),
    )
    if cursor.rowcount != 1:
        if get_user_by_id(db, user_id) is None:
            raise UserNotFoundError("User does not exist")
        raise ConcurrentUserUpdateError("User profile was changed by another request")
    updated = get_user_profile(db, user_id)
    if updated is None:
        raise UserNotFoundError("User does not exist")
    return updated


def change_password(
    db: sqlite3.Connection,
    *,
    user_id: str,
    password_hash: str,
    now: str,
) -> int:
    cursor = db.execute(
        """
        UPDATE users
        SET password_hash = ?,
            auth_version = auth_version + 1,
            row_version = row_version + 1,
            password_changed_at = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (password_hash, now, now, user_id),
    )
    if cursor.rowcount != 1:
        raise UserNotFoundError("User does not exist")
    return revoke_all_user_sessions(
        db,
        user_id=user_id,
        revoked_at=now,
        reason="password_changed",
    )


def insert_audit_event(
    db: sqlite3.Connection,
    *,
    event_type: str,
    subject_type: str,
    subject_id: str,
    actor_user_id: str | None,
    auth_method: str | None,
    result: str,
    details: dict[str, object],
    request_id: str | None,
    ip_address: str | None,
    now: str,
) -> None:
    db.execute(
        """
        INSERT INTO audit_events (
            id, event_type, subject_type, subject_id, details_json, created_at,
            actor_user_id, request_id, result, ip_address, auth_method
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid4()),
            event_type,
            subject_type,
            subject_id,
            json.dumps(details, ensure_ascii=False, sort_keys=True),
            now,
            actor_user_id,
            request_id,
            result,
            ip_address,
            auth_method,
        ),
    )
