#!/usr/bin/env python3
"""Fail when maintained Platform candidate declarations drift from root VERSION."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_VERSION_FILES = (
    "platform-web/.env.development",
    "platform-web/.env.production",
)
RUNTIME_VERSION_OWNER = "execution-runtime/app/version.py"
RUNTIME_VERSION_DIRECTORY = "execution-runtime/app"
CURRENT_DOCUMENTS = {
    "current candidate target": (
        "docs/codex/current-state.md",
        r"Current candidate target: Platform `([^`]+)`\.",
    ),
}
MAINTAINED_VERSION_PATHS = (
    "VERSION",
    "platform-web/package.json",
    *FRONTEND_VERSION_FILES,
    "platform-api/pyproject.toml",
    "platform-api/app/application.py",
    "execution-runtime/pyproject.toml",
    RUNTIME_VERSION_OWNER,
    "docs/codex/current-state.md",
)
VERSION_USAGE_PATHS = (
    "platform-web/internal/vite-config/src/config/application.ts",
    "platform-web/src/views/sys/about/index.vue",
    "execution-runtime/app/main.py",
    "execution-runtime/app/system_routes.py",
    "execution-runtime/app/models.py",
)


def read_text(root: Path, path: str) -> str:
    return (root / path).read_text(encoding="utf-8")


def project_version(root: Path, path: str) -> str:
    with (root / path).open("rb") as handle:
        return str(tomllib.load(handle)["project"]["version"])


def package_json_version(root: Path, path: str) -> str:
    package = json.loads(read_text(root, path))
    return str(package["version"])


def frontend_version(root: Path, path: str) -> str:
    content = read_text(root, path)
    match = re.search(r'VITE_GLOB_APP_VERSION\s*=\s*["\']([^"\']+)["\']', content)
    if match is None:
        raise SystemExit(f"Frontend candidate version declaration is missing from {path}")
    return match.group(1)


def source_constant(root: Path, path: str, name: str) -> str:
    content = read_text(root, path)
    match = re.search(
        rf'^{re.escape(name)}\s*=\s*["\']([^"\']+)["\']$',
        content,
        re.MULTILINE,
    )
    if match is None:
        raise SystemExit(f"{name} declaration is missing from {path}")
    return match.group(1)


def require_single_source_owner(
    root: Path,
    *,
    directory: str,
    name: str,
    owner: str,
) -> None:
    declaration = re.compile(rf"^{re.escape(name)}\s*=", re.MULTILINE)
    declarations = [
        path.relative_to(root).as_posix()
        for path in sorted((root / directory).glob("*.py"))
        if declaration.search(path.read_text(encoding="utf-8"))
    ]
    if declarations != [owner]:
        raise SystemExit(
            f"{name} must have exactly one owner at {owner}; found {declarations}"
        )


def require_source_usage(root: Path, path: str, *snippets: str) -> None:
    content = read_text(root, path)
    missing = [snippet for snippet in snippets if snippet not in content]
    if missing:
        raise SystemExit(f"Version source usage is missing from {path}: {missing}")


def require_pattern_usage(root: Path, path: str, label: str, pattern: str) -> None:
    if re.search(pattern, read_text(root, path), re.MULTILINE | re.DOTALL) is None:
        raise SystemExit(f"{label} version source usage is missing from {path}")


def document_version(root: Path, path: str, pattern: str) -> str:
    match = re.search(pattern, read_text(root, path))
    if match is None:
        raise SystemExit(f"Current candidate version declaration is missing from {path}")
    return match.group(1)


def collect_versions(root: Path) -> tuple[str, dict[str, str]]:
    expected = read_text(root, "VERSION").strip()

    require_source_usage(
        root,
        "platform-web/internal/vite-config/src/config/application.ts",
        "const { dependencies, devDependencies, name, version } = pkgJson;",
        "pkg: { dependencies, devDependencies, name, version },",
    )
    require_source_usage(
        root,
        "platform-web/src/views/sys/about/index.vue",
        "const { dependencies, devDependencies, version } = pkg;",
        "version,",
    )

    api_version = source_constant(root, "platform-api/app/application.py", "PLATFORM_VERSION")
    require_source_usage(
        root,
        "platform-api/app/application.py",
        "version=PLATFORM_VERSION",
        '"version": PLATFORM_VERSION',
    )

    runtime_version = source_constant(root, RUNTIME_VERSION_OWNER, "PLATFORM_VERSION")
    require_single_source_owner(
        root,
        directory=RUNTIME_VERSION_DIRECTORY,
        name="PLATFORM_VERSION",
        owner=RUNTIME_VERSION_OWNER,
    )
    require_source_usage(
        root,
        "execution-runtime/app/main.py",
        "from app.version import PLATFORM_VERSION",
        "version=PLATFORM_VERSION",
    )
    require_source_usage(
        root,
        "execution-runtime/app/system_routes.py",
        "from app.version import PLATFORM_VERSION",
    )
    require_pattern_usage(
        root,
        "execution-runtime/app/system_routes.py",
        "Platform Execution Runtime /status",
        r"RuntimeStatusResponse\([^)]*version=PLATFORM_VERSION",
    )
    require_pattern_usage(
        root,
        "execution-runtime/app/models.py",
        "Platform Execution Runtime status response",
        r"class RuntimeStatusResponse\(BaseModel\):.*?^\s+version:\s+str\s*$",
    )

    actual = {
        "platform-web package": package_json_version(root, "platform-web/package.json"),
        **{
            f"platform-web display ({path})": frontend_version(root, path)
            for path in FRONTEND_VERSION_FILES
        },
        "platform-api package": project_version(root, "platform-api/pyproject.toml"),
        "platform-api OpenAPI": api_version,
        "platform-api /system/info": api_version,
        "execution-runtime package": project_version(
            root,
            "execution-runtime/pyproject.toml",
        ),
        "execution-runtime OpenAPI": runtime_version,
        "execution-runtime /status": runtime_version,
        **{
            name: document_version(root, path, pattern)
            for name, (path, pattern) in CURRENT_DOCUMENTS.items()
        },
    }
    return expected, actual


def check_versions(root: Path = ROOT) -> None:
    expected, actual = collect_versions(root)
    drift = {name: value for name, value in actual.items() if value != expected}
    if drift:
        details = ", ".join(f"{name}={value}" for name, value in sorted(drift.items()))
        raise SystemExit(f"Version drift from VERSION={expected}: {details}")
    print(f"Maintained Platform candidate versions are consistent: {expected}")


def main() -> None:
    check_versions(ROOT)


if __name__ == "__main__":
    main()
