from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.config import get_settings
from app.database import connection
from app.user_admin_policy import (
    UserAdminPolicyError,
    assert_can_assign_role,
    assert_can_manage_target,
    assert_recent_reauthentication,
    target_role_for_policy,
)
from app.user_admin_repository import (
    AdminAuditRecord,
    AdminUserRecord,
    approve_registration,
    change_managed_role,
    change_managed_status,
    create_managed_user,
    create_password_reset_ticket,
    get_admin_user,
    list_admin_users,
    list_user_audit_events,
    reject_registration,
    update_managed_user,
)
from app.user_admin_schemas import (
    ApproveRegistrationRequest,
    ChangeUserRoleRequest,
    ChangeUserStatusRequest,
    CreateManagedUserRequest,
    CreateManagedUserResponse,
    PasswordResetTicketResponse,
    RejectRegistrationRequest,
    UpdateManagedUserRequest,
    UserAdminDetailResponse,
    UserAdminPageResponse,
    UserAdminSummaryResponse,
    UserAuditEventResponse,
    UserAuditListResponse,
)
from app.user_authority import LastActiveCeoError, assert_active_ceo_remains
from app.user_permissions import permissions_for_roles
from app.user_repository import (
    ConcurrentUserUpdateError,
    UserNotFoundError,
    insert_audit_event,
    list_active_user_sessions,
    revoke_all_user_sessions,
)
from app.user_security import generate_secret_token, hash_password, hash_secret_token, normalize_phone


class UserAdminServiceError(RuntimeError):
    def __init__(self, status_code: int, code: str, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class AdminRequestContext:
    actor_user_id: str
    actor_role: str
    session_id: str
    request_id: str
    ip_address: str | None


def _now(value: datetime | None = None) -> datetime:
    return (value or datetime.now(UTC)).astimezone(UTC)


def _validate_email(value: str | None) -> None:
    if value is None:
        return
    if value.count("@") != 1 or " " in value:
        raise UserAdminServiceError(422, "invalid_email", "Email address is invalid")
    local, domain = value.rsplit("@", 1)
    if not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
        raise UserAdminServiceError(422, "invalid_email", "Email address is invalid")


def _validate_phone(value: str | None) -> None:
    if value is None:
        return
    normalized = normalize_phone(value)
    digits = "".join(character for character in (normalized or "") if character.isdigit())
    if len(digits) < 7 or len(digits) > 20:
        raise UserAdminServiceError(422, "invalid_phone", "Phone number is invalid")


def _mask_email(value: str | None) -> str | None:
    if value is None or "@" not in value:
        return None
    local, domain = value.rsplit("@", 1)
    prefix = local[:1] or "*"
    return f"{prefix}***@{domain}"


def _mask_phone(value: str | None) -> str | None:
    if value is None:
        return None
    compact = "".join(character for character in value if character.isdigit())
    return f"***{compact[-4:]}" if len(compact) >= 4 else "***"


def _mask_real_name(value: str | None) -> str | None:
    if not value:
        return value
    return value[0] + "*" * max(1, min(3, len(value) - 1))


def _summary(record: AdminUserRecord, *, sensitive: bool) -> UserAdminSummaryResponse:
    role = record.role_code if record.role_code in {"ceo", "tech_lead", "employee", "member"} else None
    requested_role = (
        record.requested_role_code
        if record.requested_role_code in {"employee", "member"}
        else None
    )
    return UserAdminSummaryResponse(
        userId=record.id,
        username=record.username,
        displayName=record.display_name,
        realName=record.real_name if sensitive else _mask_real_name(record.real_name),
        avatarKey=record.avatar_key,
        phone=record.phone if sensitive else _mask_phone(record.phone),
        email=record.email if sensitive else _mask_email(record.email),
        contactMasked=not sensitive,
        role=role,
        requestedRole=requested_role,
        department=record.department,
        memberType=record.member_type,
        status=record.lifecycle_status,
        registeredAt=datetime.fromisoformat(record.registered_at),
        lastLoginAt=(
            datetime.fromisoformat(record.last_login_at)
            if record.last_login_at is not None
            else None
        ),
        activeSessionCount=record.active_session_count,
        rowVersion=record.row_version,
    )


def _detail(record: AdminUserRecord, *, sensitive: bool) -> UserAdminDetailResponse:
    base = _summary(record, sensitive=sensitive)
    role_permissions = permissions_for_roles((record.role_code,)) if record.role_code else frozenset()
    return UserAdminDetailResponse(
        **base.model_dump(by_alias=True),
        applicationNote=record.application_note if sensitive else None,
        rejectionReason=record.rejection_reason if sensitive else None,
        permissions=sorted(role_permissions),
        createdAt=datetime.fromisoformat(record.created_at),
        updatedAt=datetime.fromisoformat(record.updated_at),
    )


def _audit_response(record: AdminAuditRecord) -> UserAuditEventResponse:
    return UserAuditEventResponse(
        eventId=record.id,
        eventType=record.event_type,
        actorUserId=record.actor_user_id,
        result=record.result,
        authMethod=record.auth_method,
        requestId=record.request_id,
        details=record.details,
        createdAt=datetime.fromisoformat(record.created_at),
    )


def _current_session(db: sqlite3.Connection, context: AdminRequestContext):
    return next(
        (
            session
            for session in list_active_user_sessions(db, context.actor_user_id)
            if session.id == context.session_id
        ),
        None,
    )


def _require_recent(db: sqlite3.Connection, context: AdminRequestContext, now: datetime) -> None:
    assert_recent_reauthentication(
        session=_current_session(db, context),
        settings=get_settings(),
        now=now,
    )


def _map_domain_error(exc: Exception) -> UserAdminServiceError:
    if isinstance(exc, UserAdminServiceError):
        return exc
    if isinstance(exc, UserAdminPolicyError):
        return UserAdminServiceError(exc.status_code, exc.code, exc.detail)
    if isinstance(exc, UserNotFoundError):
        return UserAdminServiceError(404, "user_not_found", str(exc))
    if isinstance(exc, ConcurrentUserUpdateError):
        return UserAdminServiceError(409, "row_version_conflict", str(exc))
    if isinstance(exc, LastActiveCeoError):
        return UserAdminServiceError(409, "last_active_ceo", str(exc))
    if isinstance(exc, sqlite3.IntegrityError):
        return UserAdminServiceError(
            409,
            "user_identity_conflict",
            "Username, email or phone is already in use",
        )
    if isinstance(exc, ValueError):
        return UserAdminServiceError(409, "invalid_user_state", str(exc))
    return UserAdminServiceError(500, "user_admin_failure", "User administration failed")


def list_users(
    *,
    search: str | None,
    role: str | None,
    status: str | None,
    created_from: str | None,
    created_to: str | None,
    sort_by: str,
    sort_direction: str,
    page: int,
    page_size: int,
    sensitive: bool,
) -> UserAdminPageResponse:
    with connection() as db:
        records, total = list_admin_users(
            db,
            search=search,
            role=role,
            status=status,
            created_from=created_from,
            created_to=created_to,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
    return UserAdminPageResponse(
        items=[_summary(record, sensitive=sensitive) for record in records],
        total=total,
        page=page,
        pageSize=page_size,
    )


def get_user_detail(*, user_id: str, sensitive: bool) -> UserAdminDetailResponse:
    with connection() as db:
        record = get_admin_user(db, user_id)
    if record is None:
        raise UserAdminServiceError(404, "user_not_found", "User does not exist")
    return _detail(record, sensitive=sensitive)


def create_user(
    request: CreateManagedUserRequest,
    *,
    context: AdminRequestContext,
    now: datetime | None = None,
) -> CreateManagedUserResponse:
    current = _now(now)
    timestamp = current.isoformat()
    _validate_email(request.email)
    _validate_phone(request.phone)
    try:
        assert_can_assign_role(actor_role=context.actor_role, role=request.role)
        raw_ticket = generate_secret_token()
        expires_at = current + timedelta(minutes=get_settings().password_reset_ticket_ttl_minutes)
        with connection() as db:
            if not db.in_transaction:
                db.execute("BEGIN IMMEDIATE")
            _require_recent(db, context, current)
            created = create_managed_user(
                db,
                username=request.username,
                password_hash=hash_password(generate_secret_token()),
                display_name=request.display_name,
                real_name=request.real_name,
                email=request.email,
                phone=request.phone,
                role_code=request.role,
                department=request.department,
                member_type=request.member_type,
                created_by=context.actor_user_id,
                now=timestamp,
            )
            create_password_reset_ticket(
                db,
                user_id=created.id,
                token_hash=hash_secret_token(raw_ticket),
                created_by=context.actor_user_id,
                created_at=timestamp,
                expires_at=expires_at.isoformat(),
            )
            insert_audit_event(
                db,
                event_type="user.created",
                subject_type="user",
                subject_id=created.id,
                actor_user_id=context.actor_user_id,
                auth_method="session",
                result="succeeded",
                details={"role": request.role, "changedFields": ["created"]},
                request_id=context.request_id,
                ip_address=context.ip_address,
                now=timestamp,
            )
            insert_audit_event(
                db,
                event_type="user.password_reset_ticket_issued",
                subject_type="user",
                subject_id=created.id,
                actor_user_id=context.actor_user_id,
                auth_method="session",
                result="succeeded",
                details={"expiresAt": expires_at.isoformat(), "revokedSessionCount": 0},
                request_id=context.request_id,
                ip_address=context.ip_address,
                now=timestamp,
            )
        return CreateManagedUserResponse(
            user=_detail(created, sensitive=True),
            resetTicket=raw_ticket,
            resetTicketExpiresAt=expires_at,
        )
    except Exception as exc:
        raise _map_domain_error(exc) from exc


def update_user(
    user_id: str,
    request: UpdateManagedUserRequest,
    *,
    context: AdminRequestContext,
    now: datetime | None = None,
) -> UserAdminDetailResponse:
    current = _now(now)
    timestamp = current.isoformat()
    try:
        with connection() as db:
            existing = get_admin_user(db, user_id)
            if existing is None:
                raise UserNotFoundError("User does not exist")
            target_role = target_role_for_policy(
                role_code=existing.role_code,
                requested_role_code=existing.requested_role_code,
            )
            assert_can_manage_target(
                actor_user_id=context.actor_user_id,
                actor_role=context.actor_role,
                target_user_id=user_id,
                target_role=target_role,
            )
            fields = request.model_fields_set
            display_name = request.display_name if "display_name" in fields else existing.display_name
            real_name = request.real_name if "real_name" in fields else existing.real_name
            email = request.email if "email" in fields else existing.email
            phone = request.phone if "phone" in fields else existing.phone
            department = request.department if "department" in fields else existing.department
            member_type = request.member_type if "member_type" in fields else existing.member_type
            _validate_email(email)
            _validate_phone(phone)
            if not real_name or not real_name.strip():
                raise UserAdminServiceError(422, "real_name_required", "Real name is required")
            if not email and not phone:
                raise UserAdminServiceError(422, "contact_required", "Email or phone is required")
            if target_role == "employee" and not department:
                raise UserAdminServiceError(422, "department_required", "Department is required")
            if target_role == "member" and not member_type:
                raise UserAdminServiceError(422, "member_type_required", "Member type is required")
            contact_changed = existing.email != email or existing.phone != phone
            protected_target = target_role in {"ceo", "tech_lead"}
            if contact_changed or protected_target:
                _require_recent(db, context, current)
            updated = update_managed_user(
                db,
                user_id=user_id,
                display_name=display_name,
                real_name=real_name,
                email=email,
                phone=phone,
                department=department,
                member_type=member_type,
                expected_version=request.expected_version,
                now=timestamp,
            )
            changed_fields = [
                name
                for name, before, after in (
                    ("display_name", existing.display_name, updated.display_name),
                    ("real_name", existing.real_name, updated.real_name),
                    ("email", existing.email, updated.email),
                    ("phone", existing.phone, updated.phone),
                    ("department", existing.department, updated.department),
                    ("member_type", existing.member_type, updated.member_type),
                )
                if before != after
            ]
            insert_audit_event(
                db,
                event_type="user.updated",
                subject_type="user",
                subject_id=user_id,
                actor_user_id=context.actor_user_id,
                auth_method="session",
                result="succeeded",
                details={"changedFields": changed_fields},
                request_id=context.request_id,
                ip_address=context.ip_address,
                now=timestamp,
            )
        return _detail(updated, sensitive=True)
    except Exception as exc:
        raise _map_domain_error(exc) from exc


def approve_user_registration(
    user_id: str,
    request: ApproveRegistrationRequest,
    *,
    context: AdminRequestContext,
    now: datetime | None = None,
) -> UserAdminDetailResponse:
    timestamp = _now(now).isoformat()
    try:
        assert_can_assign_role(actor_role=context.actor_role, role=request.final_role)
        with connection() as db:
            existing = get_admin_user(db, user_id)
            if existing is None:
                raise UserNotFoundError("User does not exist")
            assert_can_manage_target(
                actor_user_id=context.actor_user_id,
                actor_role=context.actor_role,
                target_user_id=user_id,
                target_role=target_role_for_policy(
                    role_code=existing.role_code,
                    requested_role_code=existing.requested_role_code,
                ),
            )
            approved = approve_registration(
                db,
                user_id=user_id,
                final_role=request.final_role,
                approved_by=context.actor_user_id,
                expected_version=request.expected_version,
                now=timestamp,
            )
            insert_audit_event(
                db,
                event_type="user.registration_approved",
                subject_type="user",
                subject_id=user_id,
                actor_user_id=context.actor_user_id,
                auth_method="session",
                result="succeeded",
                details={"finalRole": request.final_role, "changedFields": ["role", "status"]},
                request_id=context.request_id,
                ip_address=context.ip_address,
                now=timestamp,
            )
        return _detail(approved, sensitive=True)
    except Exception as exc:
        raise _map_domain_error(exc) from exc


def reject_user_registration(
    user_id: str,
    request: RejectRegistrationRequest,
    *,
    context: AdminRequestContext,
    now: datetime | None = None,
) -> UserAdminDetailResponse:
    timestamp = _now(now).isoformat()
    try:
        with connection() as db:
            existing = get_admin_user(db, user_id)
            if existing is None:
                raise UserNotFoundError("User does not exist")
            assert_can_manage_target(
                actor_user_id=context.actor_user_id,
                actor_role=context.actor_role,
                target_user_id=user_id,
                target_role=target_role_for_policy(
                    role_code=existing.role_code,
                    requested_role_code=existing.requested_role_code,
                ),
            )
            rejected = reject_registration(
                db,
                user_id=user_id,
                reason=request.reason.strip(),
                expected_version=request.expected_version,
                now=timestamp,
            )
            insert_audit_event(
                db,
                event_type="user.registration_rejected",
                subject_type="user",
                subject_id=user_id,
                actor_user_id=context.actor_user_id,
                auth_method="session",
                result="succeeded",
                details={"reason": request.reason.strip(), "changedFields": ["status"]},
                request_id=context.request_id,
                ip_address=context.ip_address,
                now=timestamp,
            )
        return _detail(rejected, sensitive=True)
    except Exception as exc:
        raise _map_domain_error(exc) from exc


def change_user_role(
    user_id: str,
    request: ChangeUserRoleRequest,
    *,
    context: AdminRequestContext,
    now: datetime | None = None,
) -> UserAdminDetailResponse:
    current = _now(now)
    timestamp = current.isoformat()
    try:
        assert_can_assign_role(actor_role=context.actor_role, role=request.role)
        with connection() as db:
            if not db.in_transaction:
                db.execute("BEGIN IMMEDIATE")
            existing = get_admin_user(db, user_id)
            if existing is None:
                raise UserNotFoundError("User does not exist")
            current_target_role = target_role_for_policy(
                role_code=existing.role_code,
                requested_role_code=existing.requested_role_code,
            )
            assert_can_manage_target(
                actor_user_id=context.actor_user_id,
                actor_role=context.actor_role,
                target_user_id=user_id,
                target_role=current_target_role,
            )
            if context.actor_role == "tech_lead" and request.role not in {"employee", "member"}:
                raise UserAdminPolicyError(403, "role_assignment_forbidden", "不能授予该角色")
            _require_recent(db, context, current)
            assert_active_ceo_remains(
                db,
                target_user_id=user_id,
                resulting_role=request.role,
                resulting_status=existing.lifecycle_status,
            )
            updated = change_managed_role(
                db,
                user_id=user_id,
                role_code=request.role,
                expected_version=request.expected_version,
                now=timestamp,
            )
            revoked_count = revoke_all_user_sessions(
                db,
                user_id=user_id,
                revoked_at=timestamp,
                reason="role_changed",
            )
            insert_audit_event(
                db,
                event_type="user.role_changed",
                subject_type="user",
                subject_id=user_id,
                actor_user_id=context.actor_user_id,
                auth_method="session",
                result="succeeded",
                details={
                    "fromRole": existing.role_code,
                    "toRole": request.role,
                    "revokedSessionCount": revoked_count,
                    "changedFields": ["role"],
                },
                request_id=context.request_id,
                ip_address=context.ip_address,
                now=timestamp,
            )
        return _detail(updated, sensitive=True)
    except Exception as exc:
        raise _map_domain_error(exc) from exc


def change_user_status(
    user_id: str,
    request: ChangeUserStatusRequest,
    *,
    context: AdminRequestContext,
    now: datetime | None = None,
) -> UserAdminDetailResponse:
    current = _now(now)
    timestamp = current.isoformat()
    try:
        with connection() as db:
            if not db.in_transaction:
                db.execute("BEGIN IMMEDIATE")
            existing = get_admin_user(db, user_id)
            if existing is None:
                raise UserNotFoundError("User does not exist")
            target_role = target_role_for_policy(
                role_code=existing.role_code,
                requested_role_code=existing.requested_role_code,
            )
            assert_can_manage_target(
                actor_user_id=context.actor_user_id,
                actor_role=context.actor_role,
                target_user_id=user_id,
                target_role=target_role,
            )
            _require_recent(db, context, current)
            assert_active_ceo_remains(
                db,
                target_user_id=user_id,
                resulting_role=existing.role_code,
                resulting_status=request.status,
            )
            updated = change_managed_status(
                db,
                user_id=user_id,
                lifecycle_status=request.status,
                expected_version=request.expected_version,
                now=timestamp,
            )
            revoked_count = revoke_all_user_sessions(
                db,
                user_id=user_id,
                revoked_at=timestamp,
                reason="status_changed",
            )
            insert_audit_event(
                db,
                event_type="user.status_changed",
                subject_type="user",
                subject_id=user_id,
                actor_user_id=context.actor_user_id,
                auth_method="session",
                result="succeeded",
                details={
                    "fromStatus": existing.lifecycle_status,
                    "toStatus": request.status,
                    "reason": request.reason.strip(),
                    "revokedSessionCount": revoked_count,
                    "changedFields": ["status"],
                },
                request_id=context.request_id,
                ip_address=context.ip_address,
                now=timestamp,
            )
        return _detail(updated, sensitive=True)
    except Exception as exc:
        raise _map_domain_error(exc) from exc


def issue_password_reset_ticket(
    user_id: str,
    *,
    context: AdminRequestContext,
    now: datetime | None = None,
) -> PasswordResetTicketResponse:
    current = _now(now)
    timestamp = current.isoformat()
    expires_at = current + timedelta(minutes=get_settings().password_reset_ticket_ttl_minutes)
    raw_ticket = generate_secret_token()
    try:
        with connection() as db:
            if not db.in_transaction:
                db.execute("BEGIN IMMEDIATE")
            existing = get_admin_user(db, user_id)
            if existing is None:
                raise UserNotFoundError("User does not exist")
            target_role = target_role_for_policy(
                role_code=existing.role_code,
                requested_role_code=existing.requested_role_code,
            )
            assert_can_manage_target(
                actor_user_id=context.actor_user_id,
                actor_role=context.actor_role,
                target_user_id=user_id,
                target_role=target_role,
            )
            if existing.lifecycle_status not in {"active", "disabled"}:
                raise ValueError("Password reset is available only for approved users")
            _require_recent(db, context, current)
            revoked_count = revoke_all_user_sessions(
                db,
                user_id=user_id,
                revoked_at=timestamp,
                reason="password_reset_ticket_issued",
            )
            create_password_reset_ticket(
                db,
                user_id=user_id,
                token_hash=hash_secret_token(raw_ticket),
                created_by=context.actor_user_id,
                created_at=timestamp,
                expires_at=expires_at.isoformat(),
            )
            insert_audit_event(
                db,
                event_type="user.password_reset_ticket_issued",
                subject_type="user",
                subject_id=user_id,
                actor_user_id=context.actor_user_id,
                auth_method="session",
                result="succeeded",
                details={
                    "expiresAt": expires_at.isoformat(),
                    "revokedSessionCount": revoked_count,
                },
                request_id=context.request_id,
                ip_address=context.ip_address,
                now=timestamp,
            )
        return PasswordResetTicketResponse(
            resetTicket=raw_ticket,
            expiresAt=expires_at,
            revokedSessionCount=revoked_count,
        )
    except Exception as exc:
        raise _map_domain_error(exc) from exc


def revoke_user_sessions(
    user_id: str,
    *,
    context: AdminRequestContext,
    now: datetime | None = None,
) -> int:
    current = _now(now)
    timestamp = current.isoformat()
    try:
        with connection() as db:
            existing = get_admin_user(db, user_id)
            if existing is None:
                raise UserNotFoundError("User does not exist")
            assert_can_manage_target(
                actor_user_id=context.actor_user_id,
                actor_role=context.actor_role,
                target_user_id=user_id,
                target_role=target_role_for_policy(
                    role_code=existing.role_code,
                    requested_role_code=existing.requested_role_code,
                ),
            )
            _require_recent(db, context, current)
            revoked_count = revoke_all_user_sessions(
                db,
                user_id=user_id,
                revoked_at=timestamp,
                reason="revoked_by_administrator",
            )
            insert_audit_event(
                db,
                event_type="user.sessions_revoked_by_admin",
                subject_type="user",
                subject_id=user_id,
                actor_user_id=context.actor_user_id,
                auth_method="session",
                result="succeeded",
                details={"revokedSessionCount": revoked_count},
                request_id=context.request_id,
                ip_address=context.ip_address,
                now=timestamp,
            )
        return revoked_count
    except Exception as exc:
        raise _map_domain_error(exc) from exc


def get_user_audit(*, user_id: str, limit: int) -> UserAuditListResponse:
    with connection() as db:
        if get_admin_user(db, user_id) is None:
            raise UserAdminServiceError(404, "user_not_found", "User does not exist")
        records = list_user_audit_events(db, user_id=user_id, limit=limit)
    return UserAuditListResponse(items=[_audit_response(record) for record in records])
