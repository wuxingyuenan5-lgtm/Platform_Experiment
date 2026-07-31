from __future__ import annotations

from datetime import datetime
from typing import cast

from app.user_admin_repository import AdminAuditRecord, AdminUserRecord
from app.user_admin_schemas import (
    RegularHumanRole,
    UserAdminDetailResponse,
    UserAdminSummaryResponse,
    UserAuditEventResponse,
)
from app.user_permissions import permissions_for_roles
from app.user_schemas import HumanRole, UserLifecycleStatus


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


def admin_user_summary(
    record: AdminUserRecord,
    *,
    sensitive: bool,
) -> UserAdminSummaryResponse:
    role = cast(
        HumanRole | None,
        record.role_code
        if record.role_code in {"ceo", "tech_lead", "employee", "member"}
        else None,
    )
    requested_role = cast(
        RegularHumanRole | None,
        record.requested_role_code
        if record.requested_role_code in {"employee", "member"}
        else None,
    )
    lifecycle_status = cast(UserLifecycleStatus, record.lifecycle_status)
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
        status=lifecycle_status,
        registeredAt=datetime.fromisoformat(record.registered_at),
        lastLoginAt=(
            datetime.fromisoformat(record.last_login_at)
            if record.last_login_at is not None
            else None
        ),
        activeSessionCount=record.active_session_count,
        rowVersion=record.row_version,
    )


def admin_user_detail(
    record: AdminUserRecord,
    *,
    sensitive: bool,
) -> UserAdminDetailResponse:
    base = admin_user_summary(record, sensitive=sensitive)
    role_permissions = (
        permissions_for_roles((record.role_code,)) if record.role_code else frozenset()
    )
    return UserAdminDetailResponse(
        **base.model_dump(by_alias=True),
        applicationNote=record.application_note if sensitive else None,
        rejectionReason=record.rejection_reason if sensitive else None,
        permissions=sorted(role_permissions),
        createdAt=datetime.fromisoformat(record.created_at),
        updatedAt=datetime.fromisoformat(record.updated_at),
    )


def admin_audit_response(record: AdminAuditRecord) -> UserAuditEventResponse:
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
