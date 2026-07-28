from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.auth import Principal, require_permission
from app.config import get_settings
from app.database import connection
from app.user_admin_policy import (
    UserAdminPolicyError,
    assert_can_manage_target,
    target_role_for_policy,
)
from app.user_repository import ConcurrentUserUpdateError, insert_audit_event


settings = get_settings()
router = APIRouter(prefix=f"{settings.api_prefix}/users", tags=["user-administration"])


class UserAdminNoteResponse(BaseModel):
    user_id: str = Field(alias="userId")
    admin_note: str | None = Field(default=None, alias="adminNote")
    row_version: int = Field(alias="rowVersion")
    updated_at: datetime = Field(alias="updatedAt")


class UpdateUserAdminNoteRequest(BaseModel):
    admin_note: str | None = Field(default=None, alias="adminNote", max_length=1000)
    expected_version: int = Field(alias="expectedVersion", ge=1)


class _TargetRecord(BaseModel):
    user_id: str
    role_code: str | None
    requested_role_code: str | None
    admin_note: str | None
    row_version: int
    updated_at: str


def _request_id(request: Request) -> str:
    value = getattr(request.state, "request_id", None)
    if not isinstance(value, str) or not value:
        raise HTTPException(status_code=503, detail="Request identity is unavailable")
    return value


def _human_role(principal: Principal) -> str:
    if principal.auth_method != "session" or principal.session_id is None or len(principal.roles) != 1:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "human_session_required",
                "message": "Human browser session authentication is required",
            },
        )
    return principal.roles[0]


def _raise_policy_error(exc: UserAdminPolicyError) -> NoReturn:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.detail},
    ) from exc


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


def _load_target(db: sqlite3.Connection, user_id: str) -> _TargetRecord:
    row = db.execute(
        """
        SELECT id, role_code, requested_role_code, admin_note, row_version, updated_at
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "user_not_found", "message": "User does not exist"},
        )
    return _TargetRecord(
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


def _assert_target_access(
    *,
    principal: Principal,
    target: _TargetRecord,
) -> None:
    try:
        assert_can_manage_target(
            actor_user_id=principal.user_id,
            actor_role=_human_role(principal),
            target_user_id=target.user_id,
            target_role=target_role_for_policy(
                role_code=target.role_code,
                requested_role_code=target.requested_role_code,
            ),
        )
    except UserAdminPolicyError as exc:
        _raise_policy_error(exc)


def _response(target: _TargetRecord) -> UserAdminNoteResponse:
    return UserAdminNoteResponse(
        userId=target.user_id,
        adminNote=target.admin_note,
        rowVersion=target.row_version,
        updatedAt=datetime.fromisoformat(target.updated_at),
    )


@router.get("/{user_id}/admin-note", response_model=UserAdminNoteResponse)
def get_user_admin_note(
    user_id: str,
    response: Response,
    principal: Annotated[Principal, Depends(require_permission("user.sensitive.read"))],
) -> UserAdminNoteResponse:
    with connection() as db:
        target = _load_target(db, user_id)
        _assert_target_access(principal=principal, target=target)
    _no_store(response)
    return _response(target)


@router.patch("/{user_id}/admin-note", response_model=UserAdminNoteResponse)
def patch_user_admin_note(
    user_id: str,
    request_body: UpdateUserAdminNoteRequest,
    request: Request,
    response: Response,
    principal: Annotated[Principal, Depends(require_permission("user.update"))],
) -> UserAdminNoteResponse:
    normalized_note = (
        request_body.admin_note.strip()
        if request_body.admin_note is not None and request_body.admin_note.strip()
        else None
    )
    now = datetime.now().astimezone().isoformat()
    with connection() as db:
        if not db.in_transaction:
            db.execute("BEGIN IMMEDIATE")
        target = _load_target(db, user_id)
        _assert_target_access(principal=principal, target=target)
        cursor = db.execute(
            """
            UPDATE users
            SET admin_note = ?, row_version = row_version + 1, updated_at = ?
            WHERE id = ? AND row_version = ?
            """,
            (normalized_note, now, user_id, request_body.expected_version),
        )
        if cursor.rowcount != 1:
            current = _load_target(db, user_id)
            if current.row_version != request_body.expected_version:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "row_version_conflict",
                        "message": str(
                            ConcurrentUserUpdateError("User was changed by another request")
                        ),
                    },
                )
            raise HTTPException(
                status_code=409,
                detail={"code": "user_update_failed", "message": "User note was not updated"},
            )
        insert_audit_event(
            db,
            event_type="user.admin_note_updated",
            subject_type="user",
            subject_id=user_id,
            actor_user_id=principal.user_id,
            auth_method="session",
            result="succeeded",
            details={"changedFields": ["admin_note"], "cleared": normalized_note is None},
            request_id=_request_id(request),
            ip_address=request.client.host if request.client else None,
            now=now,
        )
        updated = _load_target(db, user_id)
    _no_store(response)
    return _response(updated)
