from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STARTUP_SCRIPT = REPO_ROOT / "scripts" / "dev-platform.ps1"


def test_local_startup_never_refreshes_existing_demo_credentials() -> None:
    source = STARTUP_SCRIPT.read_text(encoding="utf-8")

    assert "$env:USER_SYSTEM_DEMO_REFRESH = '0'" in source
    assert "$env:USER_SYSTEM_DEMO_REFRESH = '1'" not in source
    assert "$DemoPassword" not in source
    assert "PLATFORM_DEMO_PASSWORD" in source


def test_existing_account_smoke_does_not_depend_on_owner_password() -> None:
    source = STARTUP_SCRIPT.read_text(encoding="utf-8")

    assert "if ($SeedResult.Created)" in source
    assert "startup_probe_" in source
    assert "auth route accepted an invalid startup probe" in source


def test_core_startup_does_not_depend_on_external_account_snapshot() -> None:
    source = STARTUP_SCRIPT.read_text(encoding="utf-8")

    assert "/venue/account-snapshot?accountId=" not in source
