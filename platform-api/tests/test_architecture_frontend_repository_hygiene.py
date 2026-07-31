import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_ROOT = ROOT / "platform-web"
REPOSITORY_URL = "https://github.com/wuxingyuenan5-lgtm/Platform_Experiment"
EXPECTED_VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
FORBIDDEN_LOCAL_ARTIFACTS = (
    FRONTEND_ROOT / "CNAME",
    FRONTEND_ROOT / ".gitpod.yml",
    FRONTEND_ROOT / "home-2560-check.png",
    FRONTEND_ROOT / "src" / "file_structure.txt",
)
NESTED_GITHUB_ROOT = FRONTEND_ROOT / ".github"
FRONTEND_GITIGNORE = FRONTEND_ROOT / ".gitignore"
FRONTEND_LAUNCH_CONFIG = FRONTEND_ROOT / ".vscode" / "launch.json"
IDENTITY_FILES = (
    FRONTEND_ROOT / "package.json",
    FRONTEND_ROOT / "README.md",
    FRONTEND_ROOT / "README.zh-CN.md",
    FRONTEND_ROOT / "src" / "settings" / "siteSetting.ts",
    FRONTEND_ROOT / "src" / "views" / "sys" / "about" / "index.vue",
)
FORBIDDEN_UPSTREAM_IDENTITY_MARKERS = (
    "anncwb",
    "vben.vvbin.cn",
    "doc.vvbin.cn",
    "vbenjs/vue-vben-admin",
    "vben/123456",
    "gitpod.io/#https://github.com/anncwb",
)


@pytest.mark.architecture
def test_frontend_local_and_upstream_hosting_artifacts_do_not_return() -> None:
    existing = [
        str(path.relative_to(ROOT))
        for path in FORBIDDEN_LOCAL_ARTIFACTS
        if path.exists()
    ]
    assert not existing, f"Frontend local/upstream hosting artifacts returned: {existing}"

    assert not NESTED_GITHUB_ROOT.exists(), (
        "Repository GitHub metadata must live only under the root .github directory: "
        f"{NESTED_GITHUB_ROOT.relative_to(ROOT)}"
    )


@pytest.mark.architecture
def test_frontend_local_inspection_artifacts_are_ignored() -> None:
    ignore_source = FRONTEND_GITIGNORE.read_text(encoding="utf-8")
    assert "/home-*-check.png" in ignore_source
    assert "/src/file_structure.txt" in ignore_source


@pytest.mark.architecture
def test_frontend_package_identity_is_platform_owned() -> None:
    package = json.loads((FRONTEND_ROOT / "package.json").read_text(encoding="utf-8"))

    assert package["name"] == "vg-platform-web"
    assert package["version"] == EXPECTED_VERSION
    assert package["private"] is True
    assert package["homepage"] == REPOSITORY_URL
    assert package["bugs"]["url"] == f"{REPOSITORY_URL}/issues"
    assert package["repository"] == {
        "type": "git",
        "url": f"git+{REPOSITORY_URL}.git",
    }
    assert "author" not in package


@pytest.mark.architecture
def test_product_entry_points_do_not_claim_upstream_identity() -> None:
    violations: list[str] = []
    for path in IDENTITY_FILES:
        source = path.read_text(encoding="utf-8").lower()
        for marker in FORBIDDEN_UPSTREAM_IDENTITY_MARKERS:
            if marker.lower() in source:
                violations.append(f"{path.relative_to(ROOT)} contains {marker}")

    assert not violations, f"Upstream identity leaked into product entry points: {violations}"

    site_setting = (FRONTEND_ROOT / "src" / "settings" / "siteSetting.ts").read_text(
        encoding="utf-8"
    )
    assert REPOSITORY_URL in site_setting


@pytest.mark.architecture
def test_frontend_editor_launch_uses_the_authoritative_local_entry() -> None:
    launch = json.loads(FRONTEND_LAUNCH_CONFIG.read_text(encoding="utf-8"))
    configurations = launch["configurations"]

    assert len(configurations) == 1
    assert configurations[0]["name"] == "Launch Platform Web"
    assert configurations[0]["url"] == "http://127.0.0.1:4373/index.html"
    assert configurations[0]["webRoot"] == "${workspaceFolder}/src"
