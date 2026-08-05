from app.user_permissions import (
    HUMAN_ROLE_PERMISSIONS,
    PRODUCT_READ_PERMISSIONS,
    SELF_SERVICE_PERMISSIONS,
    has_permission,
)


def test_every_browser_role_has_product_and_self_service_access() -> None:
    for role in ("ceo", "tech_lead", "employee", "member"):
        for permission in PRODUCT_READ_PERMISSIONS | SELF_SERVICE_PERMISSIONS:
            assert has_permission((role,), permission), (role, permission)


def test_internal_risk_and_account_visibility_is_role_bounded() -> None:
    for role in ("ceo", "tech_lead", "employee"):
        assert has_permission((role,), "risk.read")
        assert has_permission((role,), "user.read")
    assert not has_permission(("member",), "risk.read")
    assert not has_permission(("member",), "user.read")
    assert not has_permission(("member",), "member.read_all")


def test_read_only_roles_do_not_receive_business_write_capabilities() -> None:
    write_permissions = {
        "strategy.write",
        "trading.write",
        "research.write",
        "finance.write",
        "risk.write",
        "settings.write",
        "user.update",
    }
    for role in ("employee", "member"):
        assert HUMAN_ROLE_PERMISSIONS[role].isdisjoint(write_permissions)


def test_ceo_wildcard_does_not_remove_domain_safety_checks() -> None:
    assert HUMAN_ROLE_PERMISSIONS["ceo"] == frozenset({"*"})
    assert has_permission(("ceo",), "organization.ceo.manage")
    assert has_permission(("ceo",), "strategy.write")


def test_tech_lead_does_not_receive_ceo_identity_governance() -> None:
    assert not has_permission(("tech_lead",), "user.assign_role")
    assert not has_permission(("tech_lead",), "organization.ceo.manage")
