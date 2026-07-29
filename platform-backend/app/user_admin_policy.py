from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.config import Settings
from app.user_repository import SessionSummaryRecord

REGULAR_HUMAN_ROLES = frozenset({"employee", "member"})
PROTECTED_HUMAN_ROLES = frozenset({"ceo", "tech_lead"})
ALL_HUMAN_ROLES = REGULAR_HUMAN_ROLES | PROTECTED_HUMAN_ROLES


class UserAdminPolicyError(RuntimeError):
    def __init__(self, status_code: int, code: str, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail


def target_role_for_policy(
    *,
    role_code: str | None,
    requested_role_code: str | None,
) -> str | None:
    return role_code or requested_role_code


def assert_can_manage_target(
    *,
    actor_user_id: str,
    actor_role: str,
    target_user_id: str,
    target_role: str | None,
    allow_self: bool = False,
) -> None:
    if actor_role not in {"ceo", "tech_lead"}:
        raise UserAdminPolicyError(403, "user_management_forbidden", "当前角色不能管理用户")
    if actor_user_id == target_user_id and not allow_self:
        raise UserAdminPolicyError(
            403,
            "self_admin_mutation_forbidden",
            "请通过个人账号页面修改本人资料",
        )
    if actor_role == "tech_lead" and target_role not in REGULAR_HUMAN_ROLES:
        raise UserAdminPolicyError(
            403,
            "protected_user_target_forbidden",
            "技术负责人不能管理 CEO 或其他技术负责人",
        )


def assert_can_assign_role(*, actor_role: str, role: str) -> None:
    if role not in ALL_HUMAN_ROLES:
        raise UserAdminPolicyError(422, "invalid_role", "目标角色无效")
    if actor_role == "ceo":
        return
    if actor_role == "tech_lead" and role in REGULAR_HUMAN_ROLES:
        return
    raise UserAdminPolicyError(403, "role_assignment_forbidden", "当前角色不能授予该角色")


def assert_recent_reauthentication(
    *,
    session: SessionSummaryRecord | None,
    settings: Settings,
    now: datetime | None = None,
) -> None:
    if session is None or session.last_reauthenticated_at is None:
        raise UserAdminPolicyError(
            403,
            "recent_reauthentication_required",
            "执行敏感操作前需要重新验证当前密码",
        )
    parsed = datetime.fromisoformat(session.last_reauthenticated_at)
    current = (now or datetime.now(UTC)).astimezone(UTC)
    if parsed.tzinfo is None or current - parsed.astimezone(UTC) > timedelta(
        minutes=settings.session_recent_reauth_minutes
    ):
        raise UserAdminPolicyError(
            403,
            "recent_reauthentication_required",
            "执行敏感操作前需要重新验证当前密码",
        )
