from __future__ import annotations

from datetime import datetime
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.auth import Principal, require_permission
from app.config import get_settings
from app.user_admin_policy import (
    REGULAR_HUMAN_ROLES,
    UserAdminPolicyError,
    assert_can_assign_role,
    assert_can_manage_target,
    target_role_for_policy,
)
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


def _raise_service_error(exc: UserAdminServiceError) -> NoReturn:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.detail},
    ) from exc


def _raise_policy_error(exc: UserAdminPolicyError) -> NoReturn:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.detail},
    ) from exc


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


def _detail_target_role(detail: UserAdminDetailResponse) -> str | None:
    return target_role_for_policy(
        role_code=detail.role,
        requested_role_code=detail.requested_role,
    )


def _read_user_detail_for_actor(
    *,
    user_id: str,
    principal: Principal,
) -> UserAdminDetailResponse:
    actor_role = _human_role(principal)
    may_read_sensitive = principal.has_permission("user.sensitive.read")
    if actor_role == "ceo" and may_read_sensitive:
        return get_user_detail(user_id=user_id, sensitive=True)

    masked = get_user_detail(user_id=user_id, sensitive=False)
    if (
        actor_role != "tech_lead"
        or not may_read_sensitive
        or _detail_target_role(masked) not in REGULAR_HUMAN_ROLES
    ):
        return masked

    full = get_user_detail(user_id=user_id, sensitive=True)
    if (
        full.row_version != masked.row_version
        or _detail_target_role(full) not in REGULAR_HUMAN_ROLES
    ):
        return masked
    return full


def _assert_role_profile_requirements(
    user_id: str,
    role: HumanRole,
    *,
    context: AdminRequestContext,
) -> None:
    try:
        assert_can_assign_role(actor_role=context.actor_role, role=role)
        detail = get_user_detail(user_id=user_id, sensitive=False)
        assert_can_manage_target(
            actor_user_id=context.actor_user_id,
            actor_role=context.actor_role,
            target_user_id=user_id,
            target_role=target_role_for_policy(
                role_code=detail.role,
                requested_role_code=detail.requested_role,
            ),
        )
    except UserAdminServiceError as exc:
        _raise_service_error(exc)
    except UserAdminPolicyError as exc:
        _raise_policy_error(exc)

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
    actor_role = _human_role(principal)
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
        sensitive=actor_role == "ceo" and principal.has_permission("user.sensitive.read"),
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
        result = _read_user_detail_for_actor(user_id=user_id, principal=principal)
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
    context = _session_context(request, principal)
    _assert_role_profile_requirements(user_id, request_body.final_role, context=context)
    try:
        result = approve_user_registration(
            user_id,
            request_body,
            context=context,
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
    context = _session_context(request, principal)
    _assert_role_profile_requirements(user_id, request_body.role, context=context)
    try:
        result = change_user_role(
            user_id,
            request_body,
            context=context,
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
