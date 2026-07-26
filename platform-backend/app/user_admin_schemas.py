from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.user_schemas import HumanRole, UserLifecycleStatus

RegularHumanRole = Literal["employee", "member"]
ManageableLifecycleStatus = Literal["active", "disabled"]
UserSortField = Literal["username", "registered_at", "last_login_at", "updated_at"]
SortDirection = Literal["asc", "desc"]


class UserAdminSummaryResponse(BaseModel):
    user_id: str = Field(alias="userId")
    username: str
    display_name: str | None = Field(default=None, alias="displayName")
    real_name: str | None = Field(default=None, alias="realName")
    avatar_key: str | None = Field(default=None, alias="avatarKey")
    phone: str | None = None
    email: str | None = None
    contact_masked: bool = Field(alias="contactMasked")
    role: HumanRole | None = None
    requested_role: RegularHumanRole | None = Field(default=None, alias="requestedRole")
    department: str | None = None
    member_type: str | None = Field(default=None, alias="memberType")
    status: UserLifecycleStatus
    registered_at: datetime = Field(alias="registeredAt")
    last_login_at: datetime | None = Field(default=None, alias="lastLoginAt")
    active_session_count: int = Field(alias="activeSessionCount")
    row_version: int = Field(alias="rowVersion")


class UserAdminPageResponse(BaseModel):
    items: list[UserAdminSummaryResponse]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")


class UserAdminDetailResponse(UserAdminSummaryResponse):
    application_note: str | None = Field(default=None, alias="applicationNote")
    rejection_reason: str | None = Field(default=None, alias="rejectionReason")
    permissions: list[str]
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class CreateManagedUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    display_name: str | None = Field(default=None, alias="displayName", max_length=128)
    real_name: str = Field(alias="realName", min_length=1, max_length=128)
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=32)
    role: HumanRole
    department: str | None = Field(default=None, max_length=128)
    member_type: str | None = Field(default=None, alias="memberType", max_length=128)

    @model_validator(mode="after")
    def validate_managed_user(self) -> "CreateManagedUserRequest":
        if not self.email and not self.phone:
            raise ValueError("email or phone is required")
        if self.role == "employee" and not self.department:
            raise ValueError("department is required for employee users")
        if self.role == "member" and not self.member_type:
            raise ValueError("memberType is required for member users")
        return self


class CreateManagedUserResponse(BaseModel):
    user: UserAdminDetailResponse
    reset_ticket: str = Field(alias="resetTicket")
    reset_ticket_expires_at: datetime = Field(alias="resetTicketExpiresAt")


class UpdateManagedUserRequest(BaseModel):
    display_name: str | None = Field(default=None, alias="displayName", max_length=128)
    real_name: str | None = Field(default=None, alias="realName", max_length=128)
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=32)
    department: str | None = Field(default=None, max_length=128)
    member_type: str | None = Field(default=None, alias="memberType", max_length=128)
    expected_version: int = Field(alias="expectedVersion", ge=1)


class ApproveRegistrationRequest(BaseModel):
    final_role: RegularHumanRole = Field(alias="finalRole")
    expected_version: int = Field(alias="expectedVersion", ge=1)


class RejectRegistrationRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)
    expected_version: int = Field(alias="expectedVersion", ge=1)


class ChangeUserRoleRequest(BaseModel):
    role: HumanRole
    expected_version: int = Field(alias="expectedVersion", ge=1)


class ChangeUserStatusRequest(BaseModel):
    status: ManageableLifecycleStatus
    reason: str = Field(min_length=1, max_length=1000)
    expected_version: int = Field(alias="expectedVersion", ge=1)


class PasswordResetTicketResponse(BaseModel):
    reset_ticket: str = Field(alias="resetTicket")
    expires_at: datetime = Field(alias="expiresAt")
    revoked_session_count: int = Field(alias="revokedSessionCount")


class UserAuditEventResponse(BaseModel):
    event_id: str = Field(alias="eventId")
    event_type: str = Field(alias="eventType")
    actor_user_id: str | None = Field(default=None, alias="actorUserId")
    result: str | None = None
    auth_method: str | None = Field(default=None, alias="authMethod")
    request_id: str | None = Field(default=None, alias="requestId")
    details: dict[str, object]
    created_at: datetime = Field(alias="createdAt")


class UserAuditListResponse(BaseModel):
    items: list[UserAuditEventResponse]
