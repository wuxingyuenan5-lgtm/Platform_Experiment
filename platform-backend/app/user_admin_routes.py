from __future__ import annotations

from datetime import datetime
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.auth import Principal, require_permission
from app.config import get_settings
from app.user_admin_schemas import (
    ApproveRegistrationRequest,
    ChangeUserRoleRequest,
    ChangeUserStatusRequest,
    CreateManagedUserRequest,
    CreateManagedUserResponse,
    PasswordResetTicketResponse,
    RejectRegistrationRequest,
    SortDirection,
    UpdateManagedUserRequest,
    UserAdminDetailResponse,
    UserAdminPageResponse,
    UserAuditListResponse,
    UserSortField,
)
from app.user_admin_service import (
    AdminRequestContext,
    UserAdminServiceError,
    approve_user_registration,
    change_user_role,
    change_user_status,
    create_user,
    get_user_audit,
    get_user_detail,
    issue_password_reset_ticket,
    list_users,
    reject_user_registration,
    revoke_user_sessions,
    update_user,
)
from app.user_schemas import ActionResponse, HumanRole, UserLifecycleStatus

settings = get_settings()
router = APIRouter(prefix=f"{settings.api_prefix}/users", tags=["user-administration"])


def _request_id(request: Request) -> str:
    value = getattr(request.state, "request_id", None)
    if not isinstance(value, str) or not value:
        raise HTTPException(status_code=503, detail="Request identity is unavailable")
    return value


def _session_context(request: Request, principal: Principal) -> AdminRequestContext:
    if principal.auth_method != "session" or principal.session_id is None or len(principal.roles) != 1:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "human_session_required",
                "message": "Human browser session authentication is required",
            },
        )
    return AdminRequestContext(
        actor_user_id=principal.user_id,
        actor_role=principal.roles[0],
        session_id=principal.session_id,
        request_id=_request_id(request),
        ip_address=request.client.host if request.client else None,
    )


def _raise_service_error(exc: UserAdminServiceError) -> NoReturn:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.detail},
    ) from exc


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


def _assert_role_profile_requirements(user_id: str, role: HumanRole) -> None:
    try:
        detail = get_user_detail(user_id=user_id, sensitive=True)
    except UserAdminServiceError as exc:
        _raise_service_error(exc)
    if role == "employee" and not detail.department:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "department_required",
                "message": "员工账号必须先填写部门",
            },
        )
    if role == "member" and not detail.member_type:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "member_type_required",
                "message": "会员账号必须先填写会员类型",
            },
        )


@router.get("", response_model=UserAdminPageResponse)
def users_page(
    response: Response,
    principal: Annotated[Principal, Depends(require_permission("user.read"))],
    search: str | None = Query(default=None, max_length=128),
    role: HumanRole | None = Query(default=None),
    lifecycle_status: UserLifecycleStatus | None = Query(default=None, alias="status"),
    created_from: datetime | None = Query(default=None, alias="createdFrom"),
    created_to: datetime | None = Query(default=None, alias="createdTo"),
    sort_by: UserSortField = Query(default="registered_at", alias="sortBy"),
    sort_direction: SortDirection = Query(default="desc", alias="sortDirection"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, alias="pageSize", ge=1, le=200),
) -> UserAdminPageResponse:
    _no_store(response)
    return list_users(
        search=search,
        role=role,
        status=lifecycle_status,
        created_from=created_from.isoformat() if created_from is not None else None,
        created_to=created_to.isoformat() if created_to is not None else None,
        sort_by=sort_by,
        sort_direction=sort_direction,
        page=page,
        page_size=page_size,
        sensitive=principal.has_permission("user.sensitive.read"),
    )


@router.post("", response_model=CreateManagedUserResponse, status_code=status.HTTP_201_CREATED)
def create_managed_user_route(
    request_body: CreateManagedUserRequest,
    request: Request,
    response: Response,
    principal: Annotated[Principal, Depends(require_permission("user.create"))],
) -> CreateManagedUserResponse:
    try:
        result = create_user(
            request_body,
            context=_session_context(request, principal),
        )
    except UserAdminServiceError as exc:
        _raise_service_error(exc)
    _no_store(response)
    return result


@router.get("/{user_id}", response_model=UserAdminDetailResponse)
def user_detail(
    user_id: str,
    response: Response,
    principal: Annotated[Principal, Depends(require_permission("user.read"))],
) -> UserAdminDetailResponse:
    try:
        result = get_user_detail(
            user_id=user_id,
            sensitive=principal.has_permission("user.sensitive.read"),
        )
    except UserAdminServiceError as exc:
        _raise_service_error(exc)
    _no_store(response)
    return result


@router.patch("/{user_id}", response_model=UserAdminDetailResponse)
def patch_user(
    user_id: str,
    request_body: UpdateManagedUserRequest,
    request: Request,
    response: Response,
    principal: Annotated[Principal, Depends(require_permission("user.update"))],
) -> UserAdminDetailResponse:
    try:
        result = update_user(
            user_id,
            request_body,
            context=_session_context(request, principal),
        )
    except UserAdminServiceError as exc:
        _raise_service_error(exc)
    _no_store(response)
    return result


@router.post("/{user_id}/approve", response_model=UserAdminDetailResponse)
def approve_registration_route(
    user_id: str,
    request_body: ApproveRegistrationRequest,
    request: Request,
    response: Response,
    principal: Annotated[Principal, Depends(require_permission("user.update"))],
) -> UserAdminDetailResponse:
    _assert_role_profile_requirements(user_id, request_body.final_role)
    try:
        result = approve_user_registration(
            user_id,
            request_body,
            context=_session_context(request, principal),
        )
    except UserAdminServiceError as exc:
        _raise_service_error(exc)
    _no_store(response)
    return result


@router.post("/{user_id}/reject", response_model=UserAdminDetailResponse)
def reject_registration_route(
    user_id: str,
    request_body: RejectRegistrationRequest,
    request: Request,
    response: Response,
    principal: Annotated[Principal, Depends(require_permission("user.update"))],
) -> UserAdminDetailResponse:
    try:
        result = reject_user_registration(
            user_id,
            request_body,
            context=_session_context(request, principal),
        )
    except UserAdminServiceError as exc:
        _raise_service_error(exc)
    _no_store(response)
    return result


@router.post("/{user_id}/role", response_model=UserAdminDetailResponse)
def update_role_route(
    user_id: str,
    request_body: ChangeUserRoleRequest,
    request: Request,
    response: Response,
    principal: Annotated[Principal, Depends(require_permission("user.assign_role"))],
) -> UserAdminDetailResponse:
    _assert_role_profile_requirements(user_id, request_body.role)
    try:
        result = change_user_role(
            user_id,
            request_body,
            context=_session_context(request, principal),
        )
    except UserAdminServiceError as exc:
        _raise_service_error(exc)
    _no_store(response)
    return result


@router.post("/{user_id}/status", response_model=UserAdminDetailResponse)
def update_status_route(
    user_id: str,
    request_body: ChangeUserStatusRequest,
    request: Request,
    response: Response,
    principal: Annotated[Principal, Depends(require_permission("user.disable"))],
) -> UserAdminDetailResponse:
    try:
        result = change_user_status(
            user_id,
            request_body,
            context=_session_context(request, principal),
        )
    except UserAdminServiceError as exc:
        _raise_service_error(exc)
    _no_store(response)
    return result


@router.post("/{user_id}/password-reset-tickets", response_model=PasswordResetTicketResponse)
def create_password_reset_ticket_route(
    user_id: str,
    request: Request,
    response: Response,
    principal: Annotated[Principal, Depends(require_permission("user.reset_password"))],
) -> PasswordResetTicketResponse:
    try:
        result = issue_password_reset_ticket(
            user_id,
            context=_session_context(request, principal),
        )
    except UserAdminServiceError as exc:
        _raise_service_error(exc)
    _no_store(response)
    return result


@router.post("/{user_id}/sessions/revoke", response_model=ActionResponse)
def revoke_user_sessions_route(
    user_id: str,
    request: Request,
    response: Response,
    principal: Annotated[Principal, Depends(require_permission("user.session.revoke"))],
) -> ActionResponse:
    try:
        revoked_count = revoke_user_sessions(
            user_id,
            context=_session_context(request, principal),
        )
    except UserAdminServiceError as exc:
        _raise_service_error(exc)
    _no_store(response)
    return ActionResponse(revokedSessionCount=revoked_count)


@router.get("/{user_id}/audit", response_model=UserAuditListResponse)
def user_audit_route(
    user_id: str,
    response: Response,
    _: Annotated[Principal, Depends(require_permission("user.audit.read"))],
    limit: int = Query(default=50, ge=1, le=200),
) -> UserAuditListResponse:
    try:
        result = get_user_audit(user_id=user_id, limit=limit)
    except UserAdminServiceError as exc:
        _raise_service_error(exc)
    _no_store(response)
    return result
