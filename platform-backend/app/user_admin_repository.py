from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from uuid import uuid4

from app.user_repository import ConcurrentUserUpdateError, UserNotFoundError
from app.user_security import normalize_email, normalize_phone, normalize_username


@dataclass(frozen=True, slots=True)
class AdminUserRecord:
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
    application_note: str | None
    rejection_reason: str | None
    lifecycle_status: str
    registered_at: str
    last_login_at: str | None
    row_version: int
    active_session_count: int
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class AdminAuditRecord:
    id: str
    event_type: str
    actor_user_id: str | None
    result: str | None
    auth_method: str | None
    request_id: str | None
    details: dict[str, object]
    created_at: str


def _admin_user_from_row(row: sqlite3.Row | None) -> AdminUserRecord | None:
    if row is None:
        return None
    return AdminUserRecord(
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
        application_note=(
            str(row["application_note"]) if row["application_note"] is not None else None
        ),
        rejection_reason=(
            str(row["rejection_reason"]) if row["rejection_reason"] is not None else None
        ),
        lifecycle_status=str(row["lifecycle_status"]),
        registered_at=str(row["registered_at"]),
        last_login_at=str(row["last_login_at"]) if row["last_login_at"] is not None else None,
        row_version=int(row["row_version"]),
        active_session_count=int(row["active_session_count"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _select_sql(where_sql: str = "") -> str:
    return f"""
        SELECT
            u.*,
            (
                SELECT COUNT(*)
                FROM user_sessions AS s
                WHERE s.user_id = u.id AND s.revoked_at IS NULL
            ) AS active_session_count
        FROM users AS u
        {where_sql}
    """


def get_admin_user(db: sqlite3.Connection, user_id: str) -> AdminUserRecord | None:
    row = db.execute(_select_sql("WHERE u.id = ?"), (user_id,)).fetchone()
    return _admin_user_from_row(row)


def list_admin_users(
    db: sqlite3.Connection,
    *,
    search: str | None,
    role: str | None,
    status: str | None,
    created_from: str | None,
    created_to: str | None,
    sort_by: str,
    sort_direction: str,
    limit: int,
    offset: int,
) -> tuple[list[AdminUserRecord], int]:
    conditions: list[str] = []
    parameters: list[object] = []
    if search:
        pattern = f"%{search.strip().casefold()}%"
        conditions.append(
            "(" 
            "u.username_normalized LIKE ? OR "
            "LOWER(COALESCE(u.display_name, '')) LIKE ? OR "
            "LOWER(COALESCE(u.real_name, '')) LIKE ? OR "
            "LOWER(COALESCE(u.email_normalized, '')) LIKE ? OR "
            "LOWER(COALESCE(u.phone_normalized, '')) LIKE ?"
            ")"
        )
        parameters.extend([pattern] * 5)
    if role:
        conditions.append("COALESCE(u.role_code, u.requested_role_code) = ?")
        parameters.append(role)
    if status:
        conditions.append("u.lifecycle_status = ?")
        parameters.append(status)
    if created_from:
        conditions.append("u.created_at >= ?")
        parameters.append(created_from)
    if created_to:
        conditions.append("u.created_at < ?")
        parameters.append(created_to)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    total_row = db.execute(
        f"SELECT COUNT(*) AS count FROM users AS u {where_clause}",
        tuple(parameters),
    ).fetchone()
    total = int(total_row["count"])
    sort_columns = {
        "username": "u.username_normalized",
        "registered_at": "u.registered_at",
        "last_login_at": "u.last_login_at",
        "updated_at": "u.updated_at",
    }
    sort_column = sort_columns[sort_by]
    direction = "ASC" if sort_direction == "asc" else "DESC"
    rows = db.execute(
        _select_sql(where_clause)
        + f" ORDER BY {sort_column} {direction}, u.id ASC LIMIT ? OFFSET ?",
        (*parameters, limit, offset),
    ).fetchall()
    return [record for row in rows if (record := _admin_user_from_row(row)) is not None], total


def create_managed_user(
    db: sqlite3.Connection,
    *,
    username: str,
    password_hash: str,
    display_name: str | None,
    real_name: str,
    email: str | None,
    phone: str | None,
    role_code: str,
    department: str | None,
    member_type: str | None,
    created_by: str,
    now: str,
) -> AdminUserRecord:
    user_id = str(uuid4())
    db.execute(
        """
        INSERT INTO users (
            id, username, username_normalized, password_hash,
            display_name, real_name, phone, phone_normalized,
            email, email_normalized, role_code, requested_role_code,
            department, member_type, lifecycle_status,
            registered_at, approved_at, approved_by, password_changed_at,
            created_by, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, 'active', ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            username.strip(),
            normalize_username(username),
            password_hash,
            display_name,
            real_name.strip(),
            phone,
            normalize_phone(phone),
            email,
            normalize_email(email),
            role_code,
            department,
            member_type,
            now,
            now,
            created_by,
            now,
            created_by,
            now,
            now,
        ),
    )
    created = get_admin_user(db, user_id)
    if created is None:
        raise UserNotFoundError("Created user is unavailable")
    return created


def update_managed_user(
    db: sqlite3.Connection,
    *,
    user_id: str,
    display_name: str | None,
    real_name: str | None,
    email: str | None,
    phone: str | None,
    department: str | None,
    member_type: str | None,
    expected_version: int,
    now: str,
) -> AdminUserRecord:
    cursor = db.execute(
        """
        UPDATE users
        SET display_name = ?, real_name = ?,
            email = ?, email_normalized = ?,
            phone = ?, phone_normalized = ?,
            department = ?, member_type = ?,
            row_version = row_version + 1,
            updated_at = ?
        WHERE id = ? AND row_version = ?
        """,
        (
            display_name,
            real_name,
            email,
            normalize_email(email),
            phone,
            normalize_phone(phone),
            department,
            member_type,
            now,
            user_id,
            expected_version,
        ),
    )
    if cursor.rowcount != 1:
        if get_admin_user(db, user_id) is None:
            raise UserNotFoundError("User does not exist")
        raise ConcurrentUserUpdateError("User was changed by another request")
    updated = get_admin_user(db, user_id)
    if updated is None:
        raise UserNotFoundError("User does not exist")
    return updated


def approve_registration(
    db: sqlite3.Connection,
    *,
    user_id: str,
    final_role: str,
    approved_by: str,
    expected_version: int,
    now: str,
) -> AdminUserRecord:
    cursor = db.execute(
        """
        UPDATE users
        SET role_code = ?, requested_role_code = NULL,
            lifecycle_status = 'active', approved_at = ?, approved_by = ?,
            rejection_reason = NULL,
            auth_version = auth_version + 1,
            row_version = row_version + 1,
            updated_at = ?
        WHERE id = ? AND lifecycle_status = 'pending' AND row_version = ?
        """,
        (final_role, now, approved_by, now, user_id, expected_version),
    )
    if cursor.rowcount != 1:
        existing = get_admin_user(db, user_id)
        if existing is None:
            raise UserNotFoundError("User does not exist")
        if existing.lifecycle_status != "pending":
            raise ValueError("Only pending registrations may be approved")
        raise ConcurrentUserUpdateError("User was changed by another request")
    approved = get_admin_user(db, user_id)
    if approved is None:
        raise UserNotFoundError("User does not exist")
    return approved


def reject_registration(
    db: sqlite3.Connection,
    *,
    user_id: str,
    reason: str,
    expected_version: int,
    now: str,
) -> AdminUserRecord:
    cursor = db.execute(
        """
        UPDATE users
        SET requested_role_code = NULL,
            lifecycle_status = 'rejected', rejection_reason = ?,
            auth_version = auth_version + 1,
            row_version = row_version + 1,
            updated_at = ?
        WHERE id = ? AND lifecycle_status = 'pending' AND row_version = ?
        """,
        (reason, now, user_id, expected_version),
    )
    if cursor.rowcount != 1:
        existing = get_admin_user(db, user_id)
        if existing is None:
            raise UserNotFoundError("User does not exist")
        if existing.lifecycle_status != "pending":
            raise ValueError("Only pending registrations may be rejected")
        raise ConcurrentUserUpdateError("User was changed by another request")
    rejected = get_admin_user(db, user_id)
    if rejected is None:
        raise UserNotFoundError("User does not exist")
    return rejected


def change_managed_role(
    db: sqlite3.Connection,
    *,
    user_id: str,
    role_code: str,
    expected_version: int,
    now: str,
) -> AdminUserRecord:
    cursor = db.execute(
        """
        UPDATE users
        SET role_code = ?, auth_version = auth_version + 1,
            row_version = row_version + 1, updated_at = ?
        WHERE id = ? AND lifecycle_status IN ('active', 'disabled') AND row_version = ?
        """,
        (role_code, now, user_id, expected_version),
    )
    if cursor.rowcount != 1:
        existing = get_admin_user(db, user_id)
        if existing is None:
            raise UserNotFoundError("User does not exist")
        if existing.lifecycle_status not in {"active", "disabled"}:
            raise ValueError("Pending or rejected users cannot change role")
        raise ConcurrentUserUpdateError("User was changed by another request")
    updated = get_admin_user(db, user_id)
    if updated is None:
        raise UserNotFoundError("User does not exist")
    return updated


def change_managed_status(
    db: sqlite3.Connection,
    *,
    user_id: str,
    lifecycle_status: str,
    expected_version: int,
    now: str,
) -> AdminUserRecord:
    cursor = db.execute(
        """
        UPDATE users
        SET lifecycle_status = ?, auth_version = auth_version + 1,
            row_version = row_version + 1, updated_at = ?
        WHERE id = ? AND lifecycle_status IN ('active', 'disabled') AND row_version = ?
        """,
        (lifecycle_status, now, user_id, expected_version),
    )
    if cursor.rowcount != 1:
        existing = get_admin_user(db, user_id)
        if existing is None:
            raise UserNotFoundError("User does not exist")
        if existing.lifecycle_status not in {"active", "disabled"}:
            raise ValueError("Pending or rejected users cannot change status")
        raise ConcurrentUserUpdateError("User was changed by another request")
    updated = get_admin_user(db, user_id)
    if updated is None:
        raise UserNotFoundError("User does not exist")
    return updated


def create_password_reset_ticket(
    db: sqlite3.Connection,
    *,
    user_id: str,
    token_hash: str,
    created_by: str,
    created_at: str,
    expires_at: str,
) -> str:
    db.execute(
        """
        UPDATE password_reset_tickets
        SET revoked_at = ?
        WHERE user_id = ? AND consumed_at IS NULL AND revoked_at IS NULL
        """,
        (created_at, user_id),
    )
    ticket_id = str(uuid4())
    db.execute(
        """
        INSERT INTO password_reset_tickets (
            id, user_id, token_hash, created_by, created_at, expires_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (ticket_id, user_id, token_hash, created_by, created_at, expires_at),
    )
    return ticket_id


def list_user_audit_events(
    db: sqlite3.Connection,
    *,
    user_id: str,
    limit: int,
) -> list[AdminAuditRecord]:
    rows = db.execute(
        """
        SELECT id, event_type, actor_user_id, result, auth_method,
               request_id, details_json, created_at
        FROM audit_events
        WHERE subject_type = 'user' AND subject_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    records: list[AdminAuditRecord] = []
    for row in rows:
        parsed = json.loads(str(row["details_json"]))
        details = parsed if isinstance(parsed, dict) else {}
        records.append(
            AdminAuditRecord(
                id=str(row["id"]),
                event_type=str(row["event_type"]),
                actor_user_id=(
                    str(row["actor_user_id"]) if row["actor_user_id"] is not None else None
                ),
                result=str(row["result"]) if row["result"] is not None else None,
                auth_method=(
                    str(row["auth_method"]) if row["auth_method"] is not None else None
                ),
                request_id=str(row["request_id"]) if row["request_id"] is not None else None,
                details=details,
                created_at=str(row["created_at"]),
            )
        )
    return records
