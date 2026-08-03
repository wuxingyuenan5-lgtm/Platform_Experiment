from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime

from app.database import connection
from app.user_admin_policy import (
    UserAdminPolicyError,
    assert_can_manage_target,
    target_role_for_policy,
)
from app.user_admin_service import AdminRequestContext
from app.user_repository import insert_audit_event


@dataclass(frozen=True, slots=True)
class UserAdminNoteRecord:
    user_id: str
    role_code: str | None
    requested_role_code: str | None
    admin_note: str | None
    row_version: int
    updated_at: str


class UserAdminNoteError(RuntimeError):
    def __init__(self, status_code: int, code: str, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail


def _load(db: sqlite3.Connection, user_id: str) -> UserAdminNoteRecord:
    row = db.execute(
        """
        SELECT id, role_code, requested_role_code, admin_note, row_version, updated_at
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()
    if row is None:
        raise UserAdminNoteError(404, "user_not_found", "User does not exist")
    return UserAdminNoteRecord(
        user_id=str(row["id"]),
        role_code=str(row["role_code"]) if row["role_code"] is not None else None,
        requested_role_code=(
            str(row["requested_role_code"])
            if row["requested_role_code"] is not None
            else None
        ),
        admin_note=str(row["admin_note"]) if row["admin_note"] is not None else None,
        row_version=int(row["row_version"]),
        updated_at=str(row["updated_at"]),
    )


def _assert_access(context: AdminRequestContext, target: UserAdminNoteRecord) -> None:
    try:
        assert_can_manage_target(
            actor_user_id=context.actor_user_id,
            actor_role=context.actor_role,
            target_user_id=target.user_id,
            target_role=target_role_for_policy(
                role_code=target.role_code,
                requested_role_code=target.requested_role_code,
            ),
        )
    except UserAdminPolicyError as exc:
        raise UserAdminNoteError(exc.status_code, exc.code, exc.detail) from exc


def get_user_admin_note(
    user_id: str,
    *,
    context: AdminRequestContext,
) -> UserAdminNoteRecord:
    with connection() as db:
        target = _load(db, user_id)
        _assert_access(context, target)
    return target


def update_user_admin_note(
    user_id: str,
    *,
    admin_note: str | None,
    expected_version: int,
    context: AdminRequestContext,
    now: datetime | None = None,
) -> UserAdminNoteRecord:
    normalized_note = admin_note.strip() if admin_note is not None and admin_note.strip() else None
    timestamp = (now or datetime.now(UTC)).astimezone(UTC).isoformat()
    with connection() as db:
        if not db.in_transaction:
            db.execute("BEGIN IMMEDIATE")
        target = _load(db, user_id)
        _assert_access(context, target)
        cursor = db.execute(
            """
            UPDATE users
            SET admin_note = ?, row_version = row_version + 1, updated_at = ?
            WHERE id = ? AND row_version = ?
            """,
            (normalized_note, timestamp, user_id, expected_version),
        )
        if cursor.rowcount != 1:
            current = _load(db, user_id)
            if current.row_version != expected_version:
                raise UserAdminNoteError(
                    409,
                    "row_version_conflict",
                    "User was changed by another request",
                )
            raise UserAdminNoteError(409, "user_update_failed", "User note was not updated")
        insert_audit_event(
            db,
            event_type="user.admin_note_updated",
            subject_type="user",
            subject_id=user_id,
            actor_user_id=context.actor_user_id,
            auth_method="session",
            result="succeeded",
            details={"changedFields": ["admin_note"], "cleared": normalized_note is None},
            request_id=context.request_id,
            ip_address=context.ip_address,
            now=timestamp,
        )
        return _load(db, user_id)
