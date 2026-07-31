from __future__ import annotations

from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse

from app.auth import Principal, require_permission
from app.config import get_settings
from app.user_avatar import (
    AvatarServiceError,
    current_avatar_path,
    delete_avatar,
    replace_avatar,
)
from app.user_avatar_schemas import AvatarMutationResponse

settings = get_settings()
router = APIRouter(prefix=settings.api_prefix)


def _request_id(request: Request) -> str:
    value = getattr(request.state, "request_id", None)
    if not isinstance(value, str) or not value:
        raise HTTPException(status_code=503, detail="Request identity is unavailable")
    return value


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _raise_avatar_error(exc: AvatarServiceError) -> NoReturn:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.detail},
    ) from exc


@router.get("/me/avatar", tags=["personal-account"])
def get_self_avatar(
    principal: Annotated[Principal, Depends(require_permission("profile.read_self"))],
) -> FileResponse:
    try:
        path = current_avatar_path(principal.user_id)
    except AvatarServiceError as exc:
        _raise_avatar_error(exc)
    return FileResponse(
        path,
        media_type="image/webp",
        headers={"Cache-Control": "private, max-age=300"},
    )


@router.post(
    "/me/avatar",
    response_model=AvatarMutationResponse,
    tags=["personal-account"],
)
async def upload_self_avatar(
    request: Request,
    file: Annotated[UploadFile, File()],
    expected_version: Annotated[int, Form(alias="expectedVersion", ge=1)],
    principal: Annotated[
        Principal,
        Depends(require_permission("profile.avatar.update_self")),
    ],
) -> AvatarMutationResponse:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > settings.avatar_max_bytes:
            raise HTTPException(
                status_code=413,
                detail={"code": "avatar_too_large", "message": "Avatar file exceeds 2 MB"},
            )
        chunks.append(chunk)
    try:
        result = replace_avatar(
            user_id=principal.user_id,
            raw_bytes=b"".join(chunks),
            expected_version=expected_version,
            request_id=_request_id(request),
            ip_address=_client_ip(request),
        )
    except AvatarServiceError as exc:
        _raise_avatar_error(exc)
    return AvatarMutationResponse(
        avatarKey=result.avatar_key,
        rowVersion=result.row_version,
    )


@router.delete(
    "/me/avatar",
    response_model=AvatarMutationResponse,
    tags=["personal-account"],
)
def delete_self_avatar(
    request: Request,
    expected_version: Annotated[int, Query(alias="expectedVersion", ge=1)],
    principal: Annotated[
        Principal,
        Depends(require_permission("profile.avatar.update_self")),
    ],
) -> AvatarMutationResponse:
    try:
        result = delete_avatar(
            user_id=principal.user_id,
            expected_version=expected_version,
            request_id=_request_id(request),
            ip_address=_client_ip(request),
        )
    except AvatarServiceError as exc:
        _raise_avatar_error(exc)
    return AvatarMutationResponse(
        avatarKey=result.avatar_key,
        rowVersion=result.row_version,
    )
