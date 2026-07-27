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
    store_source = (FRONTEND_ROOT / "store/modules/user.ts").read_text(encoding="utf-8-sig")
    api_source = (FRONTEND_ROOT / "api/platform/userSystem.ts").read_text(
        encoding="utf-8-sig"
    )
    forbidden = (
        "TOKEN_KEY",
        "setAuthCache(TOKEN_KEY",
        "getAuthCache<string>(TOKEN_KEY",
        "localStorage.setItem",
        "sessionStorage.setItem",
    )
    assert [token for token in forbidden if token in store_source or token in api_source] == []
    assert "getCurrentAuthentication" in store_source
    assert "loginUser" in store_source
    assert "BroadcastChannel" in api_source
    assert "vg-user-session-memory" in api_source


@pytest.mark.architecture
def test_frontend_session_state_fails_closed_after_unauthorized_response() -> None:
    user_api_source = (FRONTEND_ROOT / "api/platform/userSystem.ts").read_text(
        encoding="utf-8-sig"
    )
    holding_api_source = (FRONTEND_ROOT / "api/platform/memberHoldings.ts").read_text(
        encoding="utf-8-sig"
    )
    store_source = (FRONTEND_ROOT / "store/modules/user.ts").read_text(
        encoding="utf-8-sig"
    )
    guard_source = (FRONTEND_ROOT / "router/guard/permissionGuard.ts").read_text(
        encoding="utf-8-sig"
    )

    for source in (user_api_source, holding_api_source):
        assert "if (status === 401" in source
        assert "SESSION_INVALIDATION_CODES" in source
        assert "legacyCsrfFailure" in source
        assert "clearUserSystemSessionMemory();" in source
    assert "getUserSystemCsrfToken" in store_source
    assert "state.authenticated && Boolean(getUserSystemCsrfToken())" in store_source
    assert "if (this.authenticated && getUserSystemCsrfToken()) return true;" in store_source
    assert "if (this.authenticated) {" in store_source
    assert "this.resetState();" in store_source
    assert "this.hydrationAttempted = false;" in store_source
    assert "await this.getUserInfoAction();" in store_source
    assert "const authenticated = await userStore.hydrateSession();" in guard_source
    assert "if (!userStore.getIsAuthenticated)" not in guard_source


@pytest.mark.architecture
def test_profile_patch_clients_preserve_explicit_clear_semantics() -> None:
    source = (FRONTEND_ROOT / "api/platform/userSystem.ts").read_text(encoding="utf-8-sig")

    assert "normalizeSelfProfilePatch" in source
    assert "normalizeAdminProfilePatch" in source
    assert "Object.prototype.hasOwnProperty.call(payload, field)" in source
    assert "normalized[field] = null;" in source
    assert "data: normalizeSelfProfilePatch(payload)" in source
    assert "data: normalizeAdminProfilePatch(payload)" in source


@pytest.mark.architecture
def test_user_api_client_preserves_browser_generated_multipart_boundary() -> None:
    source = (FRONTEND_ROOT / "api/platform/userSystem.ts").read_text(encoding="utf-8-sig")

    assert "new FormData()" in source
    assert "headers: { 'Content-Type': 'application/json' }" not in source
    assert 'headers: { "Content-Type": "application/json" }' not in source


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
