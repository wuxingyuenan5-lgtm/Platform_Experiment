from __future__ import annotations

from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_ROOT = REPOSITORY_ROOT / "admin-risk" / "src"
CANONICAL_USER_FILES = (
    FRONTEND_ROOT / "store/modules/user.ts",
    FRONTEND_ROOT / "views/sys/login/LoginForm.vue",
    FRONTEND_ROOT / "views/sys/register/index.vue",
    FRONTEND_ROOT / "views/sys/reset-password/index.vue",
    FRONTEND_ROOT / "views/account/index.vue",
    FRONTEND_ROOT / "views/account/components/HoldingsPanel.vue",
    FRONTEND_ROOT / "views/users/index.vue",
    FRONTEND_ROOT / "views/users/components/UserDetailDrawer.vue",
    FRONTEND_ROOT / "views/users/components/UserHoldingsPanel.vue",
)


@pytest.mark.architecture
def test_canonical_user_frontend_does_not_import_legacy_auth_client() -> None:
    violations: list[str] = []
    for path in CANONICAL_USER_FILES:
        source = path.read_text(encoding="utf-8-sig")
        if "@/api/sys/user" in source or "/api/auth" in source:
            violations.append(str(path.relative_to(REPOSITORY_ROOT)))
    assert violations == []


@pytest.mark.architecture
def test_user_store_does_not_persist_browser_authentication_token() -> None:
    source = (FRONTEND_ROOT / "store/modules/user.ts").read_text(encoding="utf-8-sig")
    forbidden = (
        "TOKEN_KEY",
        "setAuthCache(TOKEN_KEY",
        "getAuthCache<string>(TOKEN_KEY",
        "localStorage.setItem",
        "sessionStorage.setItem",
    )
    assert [token for token in forbidden if token in source] == []
    assert "getCurrentAuthentication" in source
    assert "loginUser" in source


@pytest.mark.architecture
def test_holding_frontend_keeps_decimal_business_values_as_strings() -> None:
    paths = (
        FRONTEND_ROOT / "api/platform/memberHoldings.ts",
        FRONTEND_ROOT / "views/account/components/HoldingsPanel.vue",
        FRONTEND_ROOT / "views/users/components/UserHoldingsPanel.vue",
        FRONTEND_ROOT / "utils/decimalDisplay.ts",
    )
    forbidden = ("parseFloat(", "parseInt(", "Number(", ".toFixed(")
    violations: list[str] = []
    for path in paths:
        source = path.read_text(encoding="utf-8-sig")
        for token in forbidden:
            if token in source:
                violations.append(f"{path.relative_to(REPOSITORY_ROOT)}: {token}")
    assert violations == []
