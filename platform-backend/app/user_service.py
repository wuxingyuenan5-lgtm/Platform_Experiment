from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.config import Settings, get_settings
from app.database import connection
from app.user_permissions import permissions_for_roles
from app.user_repository import (
    ConcurrentUserUpdateError,
    SessionSummaryRecord,
    UserProfileRecord,
    UserRecord,
    change_password,
    create_initial_ceo as insert_initial_ceo,
    create_pending_registration,
    create_session,
    get_session_owner,
    get_session_with_user_by_token_hash,
    get_user_by_id,
    get_user_by_username,
    get_user_profile,
    insert_audit_event,
    list_active_user_sessions,
    record_login_failure,
    record_login_success,
    record_session_reauthentication,
    revoke_other_user_sessions,
    revoke_session,
    rotate_session_csrf,
    update_self_profile,
    upgrade_password_hash,
)
from app.user_schemas import (
    AuthenticationResponse,
    CurrentSessionResponse,
    RegistrationRequest,
    RegistrationResponse,
    UpdateSelfProfileRequest,
    UserSelfResponse,
    UserSessionListResponse,
    UserSessionSummaryResponse,
)
from app.user_security import (
    PasswordPolicyError,
    generate_secret_token,
    hash_password,
    hash_secret_token,
    normalize_phone,
    validate_password,
    verify_password,
)

_DUMMY_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$2xMBmgg0RiTeit3ch92gFg$"
    "Ye9VC3hu2UnvPouTMElSbwJwB8yCRoZ1uiHLUV5itZ0"
)


class UserServiceError(RuntimeError):
    def __init__(self, status_code: int, code: str, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class IssuedBrowserSession:
    session_id: str
    session_token: str
    csrf_token: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class LoginResult:
    response: AuthenticationResponse
    session_token: str


def _now(value: datetime | None = None) -> datetime:
    return (value or datetime.now(UTC)).astimezone(UTC)


def _source_ip(value: str | None) -> str | None:
    return value if value and len(value) <= 128 else None


def _validate_email(value: str | None) -> None:
    if value is None:
        return
    if value.count("@") != 1 or " " in value:
        raise UserServiceError(422, "invalid_email", "Email address is invalid")
    local, domain = value.rsplit("@", 1)
    if not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
        raise UserServiceError(422, "invalid_email", "Email address is invalid")


def _validate_phone(value: str | None) -> None:
    if value is None:
        return
    normalized = normalize_phone(value)
    digits = "".join(character for character in (normalized or "") if character.isdigit())
    if len(digits) < 7 or len(digits) > 20:
        raise UserServiceError(422, "invalid_phone", "Phone number is invalid")


def _profile_response(profile: UserProfileRecord) -> UserSelfResponse:
    if profile.role_code not in {"ceo", "tech_lead", "employee", "member"}:
        raise UserServiceError(503, "invalid_user_role", "User role configuration is invalid")
    return UserSelfResponse(
        userId=profile.id,
        username=profile.username,
        displayName=profile.display_name,
        realName=profile.real_name,
        avatarKey=profile.avatar_key,
        phone=profile.phone,
        email=profile.email,
        role=profile.role_code,
        department=profile.department,
        memberType=profile.member_type,
        status=profile.lifecycle_status,
        registeredAt=datetime.fromisoformat(profile.registered_at),
        lastLoginAt=(
            datetime.fromisoformat(profile.last_login_at)
            if profile.last_login_at is not None
            else None
        ),
        rowVersion=profile.row_version,
    )


def _find_current_session(
    sessions: list[SessionSummaryRecord],
    session_id: str,
) -> SessionSummaryRecord:
    current = next((session for session in sessions if session.id == session_id), None)
    if current is None:
        raise UserServiceError(401, "session_invalid", "Browser session is invalid")
    return current


def _authentication_response(
    *,
    profile: UserProfileRecord,
    current_session: SessionSummaryRecord,
    csrf_token: str,
) -> AuthenticationResponse:
    return AuthenticationResponse(
        user=_profile_response(profile),
        permissions=sorted(permissions_for_roles((profile.role_code or "",))),
        session=CurrentSessionResponse(
            sessionId=current_session.id,
            expiresAt=datetime.fromisoformat(current_session.expires_at),
            lastReauthenticatedAt=(
                datetime.fromisoformat(current_session.last_reauthenticated_at)
                if current_session.last_reauthenticated_at is not None
                else None
            ),
        ),
        csrfToken=csrf_token,
    )


def _is_recently_reauthenticated(
    session: SessionSummaryRecord,
    settings: Settings,
    now: datetime,
) -> bool:
    if session.last_reauthenticated_at is None:
        return False
    last_reauthenticated = datetime.fromisoformat(session.last_reauthenticated_at)
    if last_reauthenticated.tzinfo is None:
        return False
    return now - last_reauthenticated.astimezone(UTC) <= timedelta(
        minutes=settings.session_recent_reauth_minutes
    )


def _mask_ip(value: str | None) -> str | None:
    if value is None:
        return None
    if "." in value:
        parts = value.split(".")
        if len(parts) == 4:
            return ".".join((*parts[:3], "*"))
    if ":" in value:
        parts = [part for part in value.split(":") if part]
        return ":".join(parts[:4]) + "::*"
    return "***"


def _summarize_user_agent(value: str | None) -> str | None:
    if value is None:
        return None
    compact = " ".join(value.split())
    return compact[:160]


def create_initial_ceo(
    *,
    username: str,
    password: str,
    display_name: str | None = None,
    real_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
) -> UserRecord:
    _validate_email(email)
    _validate_phone(phone)
    validate_password(password, username=username, email=email, phone=phone)
    password_hash = hash_password(password)
    now = _now().isoformat()
    with connection() as db:
        created = insert_initial_ceo(
            db,
            username=username,
            password_hash=password_hash,
            display_name=display_name,
            real_name=real_name,
            email=email,
            phone=phone,
            now=now,
        )
        insert_audit_event(
            db,
            event_type="user.initial_ceo_created",
            subject_type="user",
            subject_id=created.id,
            actor_user_id=created.id,
            auth_method="bootstrap",
            result="succeeded",
            details={"role": "ceo", "lifecycleStatus": "active"},
            request_id=None,
            ip_address=None,
            now=now,
        )
        return created


def register_user(
    request: RegistrationRequest,
    *,
    request_id: str,
    ip_address: str | None,
    now: datetime | None = None,
) -> RegistrationResponse:
    _validate_email(request.email)
    _validate_phone(request.phone)
    try:
        validate_password(
            request.password,
            username=request.username,
            email=request.email,
            phone=request.phone,
        )
    except PasswordPolicyError as exc:
        raise UserServiceError(422, "password_policy_failed", str(exc)) from exc
    timestamp = _now(now).isoformat()
    try:
        with connection() as db:
            created = create_pending_registration(
                db,
                username=request.username,
                password_hash=hash_password(request.password),
                real_name=request.real_name,
                email=request.email,
                phone=request.phone,
                requested_role_code=request.requested_role,
                department=request.department,
                member_type=request.member_type,
                application_note=request.application_note,
                now=timestamp,
            )
            insert_audit_event(
                db,
                event_type="user.registered",
                subject_type="user",
                subject_id=created.id,
                actor_user_id=None,
                auth_method="public",
                result="succeeded",
                details={"requestedRole": request.requested_role},
                request_id=request_id,
                ip_address=_source_ip(ip_address),
                now=timestamp,
            )
    except sqlite3.IntegrityError as exc:
        raise UserServiceError(
            409,
            "registration_conflict",
            "Registration cannot be completed with the supplied identity",
        ) from exc
    return RegistrationResponse(
        applicationId=created.id,
        status="pending",
        message="申请已提交，审核通过后方可登录",
    )


def login_user(
    *,
    username: str,
    password: str,
    request_id: str,
    ip_address: str | None,
    user_agent: str | None,
    now: datetime | None = None,
) -> LoginResult:
    settings = get_settings()
    current = _now(now)
    timestamp = current.isoformat()
    session_token = generate_secret_token()
    csrf_token = generate_secret_token()
    failure: UserServiceError | None = None
    profile: UserProfileRecord | None = None
    session_id: str | None = None
    with connection() as db:
        user = get_user_by_username(db, username)
        verification = verify_password(
            user.password_hash if user is not None else _DUMMY_PASSWORD_HASH,
            password,
        )
        if user is None or not verification.valid:
            if user is not None:
                next_count = user.failed_login_count + 1
                locked_until = (
                    current + timedelta(minutes=settings.login_lock_minutes)
                ).isoformat() if next_count >= settings.login_failure_limit else None
                record_login_failure(
                    db,
                    user_id=user.id,
                    locked_until=locked_until,
                    now=timestamp,
                )
            insert_audit_event(
                db,
                event_type="auth.login_failed",
                subject_type="user",
                subject_id=user.id if user is not None else "unknown",
                actor_user_id=user.id if user is not None else None,
                auth_method="password",
                result="denied",
                details={"reason": "credential_mismatch"},
                request_id=request_id,
                ip_address=_source_ip(ip_address),
                now=timestamp,
            )
            failure = UserServiceError(401, "invalid_credentials", "账号或密码错误")
        elif user.locked_until is not None:
            locked_until = datetime.fromisoformat(user.locked_until)
            if locked_until.tzinfo is None or locked_until.astimezone(UTC) > current:
                insert_audit_event(
                    db,
                    event_type="auth.login_failed",
                    subject_type="user",
                    subject_id=user.id,
                    actor_user_id=user.id,
                    auth_method="password",
                    result="denied",
                    details={"reason": "temporarily_locked"},
                    request_id=request_id,
                    ip_address=_source_ip(ip_address),
                    now=timestamp,
                )
                failure = UserServiceError(
                    423,
                    "account_temporarily_locked",
                    "账号已临时锁定，请稍后重试",
                )
        if failure is None and user is not None and user.lifecycle_status != "active":
            state_messages = {
                "pending": "账号正在等待审核",
                "disabled": "账号已停用",
                "rejected": "注册申请未通过",
            }
            insert_audit_event(
                db,
                event_type="auth.login_failed",
                subject_type="user",
                subject_id=user.id,
                actor_user_id=user.id,
                auth_method="password",
                result="denied",
                details={"reason": f"account_{user.lifecycle_status}"},
                request_id=request_id,
                ip_address=_source_ip(ip_address),
                now=timestamp,
            )
            failure = UserServiceError(
                403,
                f"account_{user.lifecycle_status}",
                state_messages.get(user.lifecycle_status, "账号不可登录"),
            )
        if failure is None and user is not None:
            if user.role_code is None:
                failure = UserServiceError(
                    503,
                    "active_user_missing_role",
                    "User role configuration is invalid",
                )
            else:
                if verification.needs_rehash:
                    upgrade_password_hash(
                        db,
                        user_id=user.id,
                        password_hash=hash_password(password),
                        now=timestamp,
                    )
                record_login_success(db, user_id=user.id, now=timestamp)
                refreshed_user = get_user_by_id(db, user.id)
                if refreshed_user is None:
                    raise UserServiceError(503, "user_disappeared", "User record is unavailable")
                expires_at = current + timedelta(
                    minutes=settings.session_absolute_ttl_minutes
                )
                session_id = create_session(
                    db,
                    user=refreshed_user,
                    token_hash=hash_secret_token(session_token),
                    csrf_token_hash=hash_secret_token(csrf_token),
                    created_at=timestamp,
                    expires_at=expires_at.isoformat(),
                    idle_expires_at=(
                        current + timedelta(minutes=settings.session_idle_ttl_minutes)
                    ).isoformat(),
                    ip_address=_source_ip(ip_address),
                    user_agent=_summarize_user_agent(user_agent),
                    max_active_sessions=settings.session_max_active_per_user,
                )
                profile = get_user_profile(db, user.id)
                insert_audit_event(
                    db,
                    event_type="auth.login_succeeded",
                    subject_type="user",
                    subject_id=user.id,
                    actor_user_id=user.id,
                    auth_method="password",
                    result="succeeded",
                    details={"sessionId": session_id},
                    request_id=request_id,
                    ip_address=_source_ip(ip_address),
                    now=timestamp,
                )
    if failure is not None:
        raise failure
    if profile is None or session_id is None:
        raise UserServiceError(503, "login_state_invalid", "Login state is unavailable")
    sessions = list_user_sessions(profile.id)
    current_session = _find_current_session(sessions, session_id)
    return LoginResult(
        response=_authentication_response(
            profile=profile,
            current_session=current_session,
            csrf_token=csrf_token,
        ),
        session_token=session_token,
    )


def issue_browser_session(
    *,
    user_id: str,
    ip_address: str | None,
    user_agent: str | None,
    now: datetime | None = None,
) -> IssuedBrowserSession:
    settings = get_settings()
    current = _now(now)
    session_token = generate_secret_token()
    csrf_token = generate_secret_token()
    expires_at = current + timedelta(minutes=settings.session_absolute_ttl_minutes)
    idle_expires_at = current + timedelta(minutes=settings.session_idle_ttl_minutes)
    with connection() as db:
        user = get_user_by_id(db, user_id)
        if user is None:
            raise ValueError("User does not exist")
        if user.locked_until is not None:
            locked_until = datetime.fromisoformat(user.locked_until)
            if locked_until.tzinfo is None or locked_until.astimezone(UTC) > current:
                raise ValueError("User account is temporarily locked")
        session_id = create_session(
            db,
            user=user,
            token_hash=hash_secret_token(session_token),
            csrf_token_hash=hash_secret_token(csrf_token),
            created_at=current.isoformat(),
            expires_at=expires_at.isoformat(),
            idle_expires_at=idle_expires_at.isoformat(),
            ip_address=_source_ip(ip_address),
            user_agent=_summarize_user_agent(user_agent),
            max_active_sessions=settings.session_max_active_per_user,
        )
    return IssuedBrowserSession(
        session_id=session_id,
        session_token=session_token,
        csrf_token=csrf_token,
        expires_at=expires_at,
    )


def list_user_sessions(user_id: str) -> list[SessionSummaryRecord]:
    with connection() as db:
        return list_active_user_sessions(db, user_id)


def get_current_authentication(
    *,
    user_id: str,
    session_id: str,
) -> AuthenticationResponse:
    csrf_token = generate_secret_token()
    with connection() as db:
        profile = get_user_profile(db, user_id)
        if profile is None:
            raise UserServiceError(404, "user_not_found", "User does not exist")
        sessions = list_active_user_sessions(db, user_id)
        current_session = _find_current_session(sessions, session_id)
        rotate_session_csrf(
            db,
            session_id=session_id,
            csrf_token_hash=hash_secret_token(csrf_token),
        )
    return _authentication_response(
        profile=profile,
        current_session=current_session,
        csrf_token=csrf_token,
    )


def logout_by_token(
    *,
    raw_session_token: str | None,
    request_id: str,
    ip_address: str | None,
    now: datetime | None = None,
) -> None:
    if not raw_session_token:
        return
    timestamp = _now(now).isoformat()
    with connection() as db:
        session = get_session_with_user_by_token_hash(
            db,
            hash_secret_token(raw_session_token),
        )
        if session is None:
            return
        revoke_session(
            db,
            session_id=session.id,
            revoked_at=timestamp,
            reason="logout",
        )
        insert_audit_event(
            db,
            event_type="auth.logout",
            subject_type="user_session",
            subject_id=session.id,
            actor_user_id=session.user_id,
            auth_method="session",
            result="succeeded",
            details={},
            request_id=request_id,
            ip_address=_source_ip(ip_address),
            now=timestamp,
        )


def reauthenticate_user(
    *,
    user_id: str,
    session_id: str,
    password: str,
    request_id: str,
    ip_address: str | None,
    now: datetime | None = None,
) -> None:
    timestamp = _now(now).isoformat()
    failure: UserServiceError | None = None
    with connection() as db:
        user = get_user_by_id(db, user_id)
        if user is None or not verify_password(user.password_hash, password).valid:
            insert_audit_event(
                db,
                event_type="auth.reauthentication_failed",
                subject_type="user",
                subject_id=user_id,
                actor_user_id=user_id,
                auth_method="session",
                result="denied",
                details={"reason": "credential_mismatch"},
                request_id=request_id,
                ip_address=_source_ip(ip_address),
                now=timestamp,
            )
            failure = UserServiceError(401, "invalid_credentials", "当前密码错误")
        else:
            record_session_reauthentication(db, session_id=session_id, now=timestamp)
            insert_audit_event(
                db,
                event_type="auth.reauthenticated",
                subject_type="user_session",
                subject_id=session_id,
                actor_user_id=user_id,
                auth_method="session",
                result="succeeded",
                details={},
                request_id=request_id,
                ip_address=_source_ip(ip_address),
                now=timestamp,
            )
    if failure is not None:
        raise failure


def get_self_profile(user_id: str) -> UserSelfResponse:
    with connection() as db:
        profile = get_user_profile(db, user_id)
    if profile is None:
        raise UserServiceError(404, "user_not_found", "User does not exist")
    return _profile_response(profile)


def update_profile(
    *,
    user_id: str,
    session_id: str,
    request: UpdateSelfProfileRequest,
    request_id: str,
    ip_address: str | None,
    now: datetime | None = None,
) -> UserSelfResponse:
    _validate_email(request.email)
    _validate_phone(request.phone)
    settings = get_settings()
    current = _now(now)
    timestamp = current.isoformat()
    try:
        with connection() as db:
            existing = get_user_profile(db, user_id)
            if existing is None:
                raise UserServiceError(404, "user_not_found", "User does not exist")
            contact_changed = existing.email != request.email or existing.phone != request.phone
            sessions = list_active_user_sessions(db, user_id)
            current_session = _find_current_session(sessions, session_id)
            if contact_changed and not _is_recently_reauthenticated(
                current_session,
                settings,
                current,
            ):
                raise UserServiceError(
                    403,
                    "recent_reauthentication_required",
                    "修改联系方式前需要重新验证当前密码",
                )
            updated = update_self_profile(
                db,
                user_id=user_id,
                display_name=request.display_name,
                email=request.email,
                phone=request.phone,
                expected_version=request.expected_version,
                now=timestamp,
            )
            changed_fields = [
                field
                for field, before, after in (
                    ("display_name", existing.display_name, updated.display_name),
                    ("email", existing.email, updated.email),
                    ("phone", existing.phone, updated.phone),
                )
                if before != after
            ]
            insert_audit_event(
                db,
                event_type="user.profile_updated",
                subject_type="user",
                subject_id=user_id,
                actor_user_id=user_id,
                auth_method="session",
                result="succeeded",
                details={"changedFields": changed_fields},
                request_id=request_id,
                ip_address=_source_ip(ip_address),
                now=timestamp,
            )
    except ConcurrentUserUpdateError as exc:
        raise UserServiceError(409, "row_version_conflict", str(exc)) from exc
    except sqlite3.IntegrityError as exc:
        raise UserServiceError(
            409,
            "contact_conflict",
            "Email or phone is already in use",
        ) from exc
    return _profile_response(updated)


def change_self_password(
    *,
    user_id: str,
    current_password: str,
    new_password: str,
    request_id: str,
    ip_address: str | None,
    now: datetime | None = None,
) -> int:
    timestamp = _now(now).isoformat()
    with connection() as db:
        user = get_user_by_id(db, user_id)
        profile = get_user_profile(db, user_id)
        if user is None or profile is None:
            raise UserServiceError(404, "user_not_found", "User does not exist")
        if not verify_password(user.password_hash, current_password).valid:
            raise UserServiceError(401, "invalid_current_password", "当前密码错误")
        try:
            validate_password(
                new_password,
                username=user.username,
                email=profile.email,
                phone=profile.phone,
            )
        except PasswordPolicyError as exc:
            raise UserServiceError(422, "password_policy_failed", str(exc)) from exc
        revoked_count = change_password(
            db,
            user_id=user_id,
            password_hash=hash_password(new_password),
            now=timestamp,
        )
        insert_audit_event(
            db,
            event_type="user.password_changed",
            subject_type="user",
            subject_id=user_id,
            actor_user_id=user_id,
            auth_method="session",
            result="succeeded",
            details={"revokedSessionCount": revoked_count},
            request_id=request_id,
            ip_address=_source_ip(ip_address),
            now=timestamp,
        )
    return revoked_count


def get_session_list(*, user_id: str, current_session_id: str) -> UserSessionListResponse:
    sessions = list_user_sessions(user_id)
    return UserSessionListResponse(
        items=[
            UserSessionSummaryResponse(
                sessionId=session.id,
                current=session.id == current_session_id,
                createdAt=datetime.fromisoformat(session.created_at),
                expiresAt=datetime.fromisoformat(session.expires_at),
                idleExpiresAt=datetime.fromisoformat(session.idle_expires_at),
                lastSeenAt=datetime.fromisoformat(session.last_seen_at),
                lastReauthenticatedAt=(
                    datetime.fromisoformat(session.last_reauthenticated_at)
                    if session.last_reauthenticated_at is not None
                    else None
                ),
                ipSummary=_mask_ip(session.ip_address),
                userAgentSummary=_summarize_user_agent(session.user_agent),
            )
            for session in sessions
        ]
    )


def revoke_own_session(
    *,
    user_id: str,
    current_session_id: str,
    target_session_id: str,
    request_id: str,
    ip_address: str | None,
    now: datetime | None = None,
) -> None:
    if target_session_id == current_session_id:
        raise UserServiceError(409, "use_logout_for_current_session", "请使用退出登录结束当前设备")
    timestamp = _now(now).isoformat()
    with connection() as db:
        owner = get_session_owner(db, target_session_id)
        if owner != user_id:
            raise UserServiceError(404, "session_not_found", "Session does not exist")
        revoke_session(
            db,
            session_id=target_session_id,
            revoked_at=timestamp,
            reason="revoked_by_owner",
        )
        insert_audit_event(
            db,
            event_type="user.session_revoked",
            subject_type="user_session",
            subject_id=target_session_id,
            actor_user_id=user_id,
            auth_method="session",
            result="succeeded",
            details={},
            request_id=request_id,
            ip_address=_source_ip(ip_address),
            now=timestamp,
        )


def revoke_other_sessions(
    *,
    user_id: str,
    current_session_id: str,
    request_id: str,
    ip_address: str | None,
    now: datetime | None = None,
) -> int:
    timestamp = _now(now).isoformat()
    with connection() as db:
        revoked_count = revoke_other_user_sessions(
            db,
            user_id=user_id,
            current_session_id=current_session_id,
            revoked_at=timestamp,
            reason="revoke_others",
        )
        insert_audit_event(
            db,
            event_type="user.other_sessions_revoked",
            subject_type="user",
            subject_id=user_id,
            actor_user_id=user_id,
            auth_method="session",
            result="succeeded",
            details={"revokedSessionCount": revoked_count},
            request_id=request_id,
            ip_address=_source_ip(ip_address),
            now=timestamp,
        )
    return revoked_count
