from __future__ import annotations

from datetime import datetime
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app import user_admin_notes
from app.auth import Principal, require_permission
from app.config import get_settings
from app.user_admin_service import AdminRequestContext


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


def _session_context(request: Request, principal: Principal) -> AdminRequestContext:
    return AdminRequestContext(
        actor_user_id=principal.user_id,
        actor_role=_human_role(principal),
        session_id=principal.session_id or "",
        request_id=_request_id(request),
        ip_address=request.client.host if request.client else None,
    )


def _raise_service_error(exc: user_admin_notes.UserAdminNoteError) -> NoReturn:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.detail},
    ) from exc


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


def _response(record: user_admin_notes.UserAdminNoteRecord) -> UserAdminNoteResponse:
    return UserAdminNoteResponse(
        userId=record.user_id,
        adminNote=record.admin_note,
        rowVersion=record.row_version,
        updatedAt=datetime.fromisoformat(record.updated_at),
    )


@router.get("/{user_id}/admin-note", response_model=UserAdminNoteResponse)
def user_admin_note(
    user_id: str,
    request: Request,
    response: Response,
    principal: Annotated[Principal, Depends(require_permission("user.sensitive.read"))],
) -> UserAdminNoteResponse:
    try:
        record = user_admin_notes.get_user_admin_note(
            user_id,
            context=_session_context(request, principal),
        )
    except user_admin_notes.UserAdminNoteError as exc:
        _raise_service_error(exc)
    _no_store(response)
    return _response(record)


@router.patch("/{user_id}/admin-note", response_model=UserAdminNoteResponse)
def patch_user_admin_note(
    user_id: str,
    request_body: UpdateUserAdminNoteRequest,
    request: Request,
    response: Response,
    principal: Annotated[Principal, Depends(require_permission("user.update"))],
) -> UserAdminNoteResponse:
    try:
        record = user_admin_notes.update_user_admin_note(
            user_id,
            admin_note=request_body.admin_note,
            expected_version=request_body.expected_version,
            context=_session_context(request, principal),
        )
    except user_admin_notes.UserAdminNoteError as exc:
        _raise_service_error(exc)
    _no_store(response)
    return _response(record)
