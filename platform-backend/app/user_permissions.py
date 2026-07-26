from __future__ import annotations

from collections.abc import Iterable

API_KEY_ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "viewer": frozenset({"platform:read"}),
    "researcher": frozenset({"platform:read", "strategy:run"}),
    "trader": frozenset({"platform:read", "trade:submit", "live_session:request"}),
    "risk_officer": frozenset(
        {
            "platform:read",
            "audit:read",
            "risk:manage",
            "reconciliation:review",
            "eod:review",
            "live_session:approve",
            "live_session:revoke",
        }
    ),
    "operations": frozenset(
        {
            "platform:read",
            "audit:read",
            "operations:run",
            "reconciliation:review",
            "eod:run",
            "live_session:operate",
        }
    ),
    "admin": frozenset({"*"}),
}

HUMAN_ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "ceo": frozenset({"*"}),
    "tech_lead": frozenset(
        {
            "platform:read",
            "audit:read",
            "system.read",
            "system.manage",
            "risk.read",
            "trade.read",
            "user.read",
            "user.sensitive.read",
            "user.create",
            "user.update",
            "user.disable",
            "user.reset_password",
            "user.assign_role",
            "user.session.revoke",
            "user.audit.read",
            "profile.read_self",
            "profile.update_self",
            "profile.avatar.update_self",
            "profile.password.change_self",
            "session.read_self",
            "session.revoke_self",
            "member.read_self",
            "member.read_all",
            "member.holding.read_self",
        }
    ),
    "employee": frozenset(
        {
            "platform:read",
            "risk.read",
            "trade.read",
            "user.read",
            "profile.read_self",
            "profile.update_self",
            "profile.avatar.update_self",
            "profile.password.change_self",
            "session.read_self",
            "session.revoke_self",
            "member.read_self",
            "member.holding.read_self",
        }
    ),
    "member": frozenset(
        {
            "profile.read_self",
            "profile.update_self",
            "profile.avatar.update_self",
            "profile.password.change_self",
            "session.read_self",
            "session.revoke_self",
            "member.read_self",
            "member.holding.read_self",
        }
    ),
}

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    **API_KEY_ROLE_PERMISSIONS,
    **HUMAN_ROLE_PERMISSIONS,
}

API_KEY_ROLES = frozenset(API_KEY_ROLE_PERMISSIONS)
HUMAN_ROLES = frozenset(HUMAN_ROLE_PERMISSIONS)
PUBLIC_REGISTRATION_ROLES = frozenset({"employee", "member"})
PROTECTED_HUMAN_ROLES = frozenset({"ceo", "tech_lead"})


def permissions_for_roles(roles: Iterable[str]) -> frozenset[str]:
    permissions: set[str] = set()
    for role in roles:
        permissions.update(ROLE_PERMISSIONS.get(role, ()))
    return frozenset(permissions)


def has_permission(roles: Iterable[str], permission: str) -> bool:
    permissions = permissions_for_roles(roles)
    return "*" in permissions or permission in permissions


def are_known_roles(roles: Iterable[str]) -> bool:
    values = tuple(roles)
    return bool(values) and all(role in ROLE_PERMISSIONS for role in values)


def is_human_role(role: str) -> bool:
    return role in HUMAN_ROLES


def is_api_key_role(role: str) -> bool:
    return role in API_KEY_ROLES
