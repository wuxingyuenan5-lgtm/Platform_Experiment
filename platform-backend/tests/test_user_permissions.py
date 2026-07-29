from __future__ import annotations

import pytest

from app.user_permissions import (
    API_KEY_ROLES,
    HUMAN_ROLES,
    PUBLIC_REGISTRATION_ROLES,
    are_known_human_roles,
    are_known_roles,
    has_permission,
    permissions_for_roles,
)


@pytest.mark.unit
def test_existing_api_key_role_permissions_remain_compatible() -> None:
    assert has_permission(("viewer",), "platform:read")
    assert not has_permission(("viewer",), "trade:submit")
    assert has_permission(("trader",), "trade:submit")
    assert has_permission(("risk_officer",), "risk:manage")
    assert has_permission(("operations",), "operations:run")
    assert has_permission(("admin",), "any.future.permission")


@pytest.mark.unit
def test_human_roles_are_distinct_from_api_key_roles() -> None:
    assert HUMAN_ROLES == frozenset({"ceo", "tech_lead", "employee", "member"})
    assert API_KEY_ROLES.isdisjoint(HUMAN_ROLES)
    assert PUBLIC_REGISTRATION_ROLES == frozenset({"employee", "member"})
    assert are_known_human_roles(("ceo",))
    assert not are_known_roles(("ceo",))


@pytest.mark.unit
def test_ceo_browser_permissions_are_explicit_and_business_scoped() -> None:
    permissions = permissions_for_roles(("ceo",))
    assert "*" not in permissions
    assert "user.assign_role" in permissions
    assert "member.holding.read_all" in permissions
    assert "member.holding.update" in permissions
    assert "trade:submit" not in permissions
    assert "risk:manage" not in permissions


@pytest.mark.unit
def test_technical_lead_default_boundary_excludes_live_and_all_holdings() -> None:
    roles = ("tech_lead",)
    assert has_permission(roles, "user.update")
    assert has_permission(roles, "user.sensitive.read")
    assert has_permission(roles, "member.read_all")
    assert not has_permission(roles, "member.holding.read_all")
    assert not has_permission(roles, "member.holding.update")
    assert not has_permission(roles, "trade:submit")
    assert not has_permission(roles, "risk:manage")


@pytest.mark.unit
def test_employee_and_member_permissions_are_read_or_self_scoped() -> None:
    assert has_permission(("employee",), "user.read")
    assert not has_permission(("employee",), "user.update")
    assert has_permission(("member",), "member.holding.read_self")
    assert not has_permission(("member",), "platform:read")
    assert not has_permission(("member",), "user.read")


@pytest.mark.unit
def test_unknown_roles_never_gain_permissions() -> None:
    assert permissions_for_roles(("unknown",)) == frozenset()
    assert not has_permission(("unknown",), "platform:read")
    assert not are_known_roles(("unknown",))
    assert not are_known_roles(())
