from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

HumanRole = Literal["ceo", "tech_lead", "employee", "member"]
PublicRegistrationRole = Literal["employee", "member"]
UserLifecycleStatus = Literal["pending", "active", "disabled", "rejected"]


class RegistrationRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    real_name: str = Field(alias="realName", min_length=1, max_length=128)
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=32)
    requested_role: PublicRegistrationRole = Field(alias="requestedRole")
    department: str | None = Field(default=None, max_length=128)
    member_type: str | None = Field(default=None, alias="memberType", max_length=128)
    application_note: str | None = Field(
        default=None,
        alias="applicationNote",
        max_length=1000,
    )
    password: str = Field(min_length=12, max_length=128)
    password_confirmation: str = Field(
        alias="passwordConfirmation",
        min_length=12,
        max_length=128,
    )
    privacy_accepted: bool = Field(alias="privacyAccepted")

    @model_validator(mode="after")
    def validate_registration(self) -> "RegistrationRequest":
        if self.password != self.password_confirmation:
            raise ValueError("passwordConfirmation must match password")
        if not self.privacy_accepted:
            raise ValueError("privacyAccepted must be true")
        if not self.email and not self.phone:
            raise ValueError("email or phone is required")
        if self.requested_role == "employee" and not self.department:
            raise ValueError("department is required for employee applications")
        if self.requested_role == "member" and not self.member_type:
            raise ValueError("memberType is required for member applications")
        return self


class RegistrationResponse(BaseModel):
    application_id: str = Field(alias="applicationId")
    status: Literal["pending"]
    message: str


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class ReauthenticationRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class ResetPasswordRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    reset_ticket: str = Field(alias="resetTicket", min_length=32, max_length=512)
    new_password: str = Field(alias="newPassword", min_length=12, max_length=128)
    new_password_confirmation: str = Field(
        alias="newPasswordConfirmation",
        min_length=12,
        max_length=128,
    )

    @model_validator(mode="after")
    def validate_confirmation(self) -> "ResetPasswordRequest":
        if self.new_password != self.new_password_confirmation:
            raise ValueError("newPasswordConfirmation must match newPassword")
        return self


class UserSelfResponse(BaseModel):
    user_id: str = Field(alias="userId")
    username: str
    display_name: str | None = Field(default=None, alias="displayName")
    real_name: str | None = Field(default=None, alias="realName")
    avatar_key: str | None = Field(default=None, alias="avatarKey")
    phone: str | None = None
    email: str | None = None
    role: HumanRole
    department: str | None = None
    member_type: str | None = Field(default=None, alias="memberType")
    status: UserLifecycleStatus
    registered_at: datetime = Field(alias="registeredAt")
    last_login_at: datetime | None = Field(default=None, alias="lastLoginAt")
    row_version: int = Field(alias="rowVersion")


class CurrentSessionResponse(BaseModel):
    session_id: str = Field(alias="sessionId")
    expires_at: datetime = Field(alias="expiresAt")
    last_reauthenticated_at: datetime | None = Field(
        default=None,
        alias="lastReauthenticatedAt",
    )


class AuthenticationResponse(BaseModel):
    user: UserSelfResponse
    permissions: list[str]
    session: CurrentSessionResponse
    csrf_token: str = Field(alias="csrfToken")


class UpdateSelfProfileRequest(BaseModel):
    display_name: str | None = Field(default=None, alias="displayName", max_length=128)
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=32)
    expected_version: int = Field(alias="expectedVersion", ge=1)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(alias="currentPassword", min_length=1, max_length=128)
    new_password: str = Field(alias="newPassword", min_length=12, max_length=128)
    new_password_confirmation: str = Field(
        alias="newPasswordConfirmation",
        min_length=12,
        max_length=128,
    )

    @model_validator(mode="after")
    def validate_confirmation(self) -> "ChangePasswordRequest":
        if self.new_password != self.new_password_confirmation:
            raise ValueError("newPasswordConfirmation must match newPassword")
        if self.current_password == self.new_password:
            raise ValueError("newPassword must differ from currentPassword")
        return self


class UserSessionSummaryResponse(BaseModel):
    session_id: str = Field(alias="sessionId")
    current: bool
    created_at: datetime = Field(alias="createdAt")
    expires_at: datetime = Field(alias="expiresAt")
    idle_expires_at: datetime = Field(alias="idleExpiresAt")
    last_seen_at: datetime = Field(alias="lastSeenAt")
    last_reauthenticated_at: datetime | None = Field(
        default=None,
        alias="lastReauthenticatedAt",
    )
    ip_summary: str | None = Field(default=None, alias="ipSummary")
    user_agent_summary: str | None = Field(default=None, alias="userAgentSummary")


class UserSessionListResponse(BaseModel):
    items: list[UserSessionSummaryResponse]


class ActionResponse(BaseModel):
    status: Literal["ok"] = "ok"
    revoked_session_count: int | None = Field(default=None, alias="revokedSessionCount")
