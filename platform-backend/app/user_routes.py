from __future__ import annotations

from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.auth import Principal, require_permission
from app.config import get_settings
from app.user_logout import LogoutError, logout_session_idempotently
from app.user_password_reset import PasswordResetError, consume_password_reset_ticket
from app.user_rate_limit import get_public_auth_rate_limiter
from app.user_schemas import (
    ActionResponse,
    AuthenticationResponse,
    ChangePasswordRequest,
    LoginRequest,
    ReauthenticationRequest,
    RegistrationRequest,
    RegistrationResponse,
    ResetPasswordRequest,
    UpdateSelfProfileRequest,
    UserSelfResponse,
    UserSessionListResponse,
)
from app.user_service import (
    UserServiceError,
    change_self_password,
    get_current_authentication,
    get_self_profile,
    get_session_list,
    login_user,
    reauthenticate_user,
    register_user,
    revoke_other_sessions,
    revoke_own_session,
    update_profile,
)

settings = get_settings()
router = APIRouter(prefix=settings.api_prefix)


def _request_id(request: Request) -> str:
    value = getattr(request.state, "request_id", None)
    if not isinstance(value, str) or not value:
        raise HTTPException(status_code=503, detail="Request identity is unavailable")
    return value


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _require_trusted_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin is None or origin not in settings.allowed_cors_origins:
        raise HTTPException(
            status_code=403,
            detail={"code": "untrusted_origin", "message": "Request origin is not trusted"},
        )


def _enforce_public_rate_limit(
    request: Request,
    *,
    scope: str,
    identity: str,
    limit: int,
) -> None:
    source = _client_ip(request) or "unknown"
    normalized_identity = identity.strip().casefold() or "unknown"
    limiter = get_public_auth_rate_limiter(settings.public_rate_limit_max_keys)
    decision = limiter.check(
        f"{scope}:{source}:{normalized_identity}",
        limit=limit,
        window_seconds=settings.public_auth_rate_window_seconds,
    )
    if not decision.allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "rate_limit_exceeded",
                "message": "请求过于频繁，请稍后重试",
            },
            headers={"Retry-After": str(decision.retry_after_seconds)},
        )


def _raise_service_error(exc: UserServiceError) -> NoReturn:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.detail},
    ) from exc


def _raise_logout_error(exc: LogoutError) -> NoReturn:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.detail},
    ) from exc


def _raise_password_reset_error(exc: PasswordResetError) -> NoReturn:
    raise HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.detail},
    ) from exc


def _require_session_id(principal: Principal) -> str:
    if principal.auth_method != "session" or principal.session_id is None:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "human_session_required",
                "message": "Human browser session authentication is required",
            },
        )
    return principal.session_id


def _set_session_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_token,
        max_age=settings.session_absolute_ttl_minutes * 60,
        httponly=True,
        secure=settings.environment.lower() in {"live", "production"},
        samesite="lax",
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.environment.lower() in {"live", "production"},
        samesite="lax",
        path="/",
    )


@router.post(
    "/auth/register",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["user-auth"],
)
def register(request_body: RegistrationRequest, request: Request) -> RegistrationResponse:
    _require_trusted_origin(request)
    _enforce_public_rate_limit(
        request,
        scope="register",
        identity="public",
        limit=settings.public_registration_rate_limit,
    )
    try:
        return register_user(
            request_body,
            request_id=_request_id(request),
            ip_address=_client_ip(request),
        )
    except UserServiceError as exc:
        _raise_service_error(exc)


@router.post(
    "/auth/login",
    response_model=AuthenticationResponse,
    tags=["user-auth"],
)
def login(
    request_body: LoginRequest,
    request: Request,
    response: Response,
) -> AuthenticationResponse:
    _require_trusted_origin(request)
    _enforce_public_rate_limit(
        request,
        scope="login",
        identity=request_body.username,
        limit=settings.public_login_rate_limit,
    )
    try:
        result = login_user(
            username=request_body.username,
            password=request_body.password,
            request_id=_request_id(request),
            ip_address=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except UserServiceError as exc:
        _raise_service_error(exc)
    _set_session_cookie(response, result.session_token)
    response.headers["Cache-Control"] = "no-store"
    return result.response


@router.post(
    "/auth/reset-password",
    response_model=ActionResponse,
    tags=["user-auth"],
)
def reset_password(
    request_body: ResetPasswordRequest,
    request: Request,
    response: Response,
) -> ActionResponse:
    _require_trusted_origin(request)
    _enforce_public_rate_limit(
        request,
        scope="password-reset",
        identity=request_body.username,
        limit=settings.public_password_reset_rate_limit,
    )
    try:
        revoked_count = consume_password_reset_ticket(
            username=request_body.username,
            raw_ticket=request_body.reset_ticket,
            new_password=request_body.new_password,
            request_id=_request_id(request),
            ip_address=_client_ip(request),
        )
    except PasswordResetError as exc:
        _raise_password_reset_error(exc)
    _clear_session_cookie(response)
    response.headers["Cache-Control"] = "no-store"
    return ActionResponse(revokedSessionCount=revoked_count)


@router.get(
    "/auth/me",
    response_model=AuthenticationResponse,
    tags=["user-auth"],
)
def current_authentication(
    response: Response,
    principal: Annotated[Principal, Depends(require_permission("profile.read_self"))],
) -> AuthenticationResponse:
    try:
        result = get_current_authentication(
            user_id=principal.user_id,
            session_id=_require_session_id(principal),
        )
    except UserServiceError as exc:
        _raise_service_error(exc)
    response.headers["Cache-Control"] = "no-store"
    return result


@router.post(
    "/auth/logout",
    response_model=ActionResponse,
    tags=["user-auth"],
)
def logout(request: Request, response: Response) -> ActionResponse:
    _require_trusted_origin(request)
    try:
        logout_session_idempotently(
            raw_session_token=request.cookies.get(settings.session_cookie_name),
            supplied_csrf_token=request.headers.get("x-csrf-token"),
            request_id=_request_id(request),
            ip_address=_client_ip(request),
        )
    except LogoutError as exc:
        _raise_logout_error(exc)
    _clear_session_cookie(response)
    response.headers["Cache-Control"] = "no-store"
    return ActionResponse()


@router.post(
    "/auth/reauth",
    response_model=ActionResponse,
    tags=["user-auth"],
)
def reauthenticate(
    request_body: ReauthenticationRequest,
    request: Request,
    principal: Annotated[Principal, Depends(require_permission("profile.read_self"))],
) -> ActionResponse:
    try:
        reauthenticate_user(
            user_id=principal.user_id,
            session_id=_require_session_id(principal),
            password=request_body.password,
            request_id=_request_id(request),
            ip_address=_client_ip(request),
        )
    except UserServiceError as exc:
        _raise_service_error(exc)
    return ActionResponse()


@router.get("/me", response_model=UserSelfResponse, tags=["personal-account"])
def self_profile(
    principal: Annotated[Principal, Depends(require_permission("profile.read_self"))],
) -> UserSelfResponse:
    try:
        return get_self_profile(principal.user_id)
    except UserServiceError as exc:
        _raise_service_error(exc)


@router.patch("/me", response_model=UserSelfResponse, tags=["personal-account"])
def patch_self_profile(
    request_body: UpdateSelfProfileRequest,
    request: Request,
    principal: Annotated[Principal, Depends(require_permission("profile.update_self"))],
) -> UserSelfResponse:
    try:
        return update_profile(
            user_id=principal.user_id,
            session_id=_require_session_id(principal),
            request=request_body,
            request_id=_request_id(request),
            ip_address=_client_ip(request),
        )
    except UserServiceError as exc:
        _raise_service_error(exc)


@router.post(
    "/me/password",
    response_model=ActionResponse,
    tags=["personal-account"],
)
def change_password(
    request_body: ChangePasswordRequest,
    request: Request,
    response: Response,
    principal: Annotated[
        Principal,
        Depends(require_permission("profile.password.change_self")),
    ],
) -> ActionResponse:
    try:
        revoked_count = change_self_password(
            user_id=principal.user_id,
            current_password=request_body.current_password,
            new_password=request_body.new_password,
            request_id=_request_id(request),
            ip_address=_client_ip(request),
        )
    except UserServiceError as exc:
        _raise_service_error(exc)
    _clear_session_cookie(response)
    response.headers["Cache-Control"] = "no-store"
    return ActionResponse(revokedSessionCount=revoked_count)


@router.get(
    "/me/sessions",
    response_model=UserSessionListResponse,
    tags=["personal-account"],
)
def self_sessions(
    principal: Annotated[Principal, Depends(require_permission("session.read_self"))],
) -> UserSessionListResponse:
    return get_session_list(
        user_id=principal.user_id,
        current_session_id=_require_session_id(principal),
    )


@router.delete(
    "/me/sessions/{session_id}",
    response_model=ActionResponse,
    tags=["personal-account"],
)
def delete_self_session(
    session_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(require_permission("session.revoke_self"))],
) -> ActionResponse:
    try:
        revoke_own_session(
            user_id=principal.user_id,
            current_session_id=_require_session_id(principal),
            target_session_id=session_id,
            request_id=_request_id(request),
            ip_address=_client_ip(request),
        )
    except UserServiceError as exc:
        _raise_service_error(exc)
    return ActionResponse()


@router.post(
    "/me/sessions/revoke-others",
    response_model=ActionResponse,
    tags=["personal-account"],
)
def revoke_other_self_sessions(
    request: Request,
    principal: Annotated[Principal, Depends(require_permission("session.revoke_self"))],
) -> ActionResponse:
    try:
        revoked_count = revoke_other_sessions(
            user_id=principal.user_id,
            current_session_id=_require_session_id(principal),
            request_id=_request_id(request),
            ip_address=_client_ip(request),
        )
    except UserServiceError as exc:
        _raise_service_error(exc)
    return ActionResponse(revokedSessionCount=revoked_count)
