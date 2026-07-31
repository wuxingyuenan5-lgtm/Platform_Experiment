#!/usr/bin/env python3
"""Fail when maintained release declarations drift from root VERSION."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
FRONTEND_VERSION_FILES = (
    "platform-web/.env.development",
    "platform-web/.env.production",
)


def project_version(path: str) -> str:
    with (ROOT / path).open("rb") as handle:
        return str(tomllib.load(handle)["project"]["version"])


def package_json_version(path: str) -> str:
    package = json.loads((ROOT / path).read_text(encoding="utf-8"))
    return str(package["version"])


def frontend_version(path: str) -> str:
    content = (ROOT / path).read_text(encoding="utf-8")
    match = re.search(r'VITE_GLOB_APP_VERSION\s*=\s*["\']([^"\']+)["\']', content)
    if match is None:
        raise SystemExit(f"Frontend release version declaration is missing from {path}")
    return match.group(1)


def main() -> None:
    actual = {
        "platform-api package": project_version("platform-api/pyproject.toml"),
        "execution-runtime package": project_version("execution-runtime/pyproject.toml"),
        "platform-web package": package_json_version("platform-web/package.json"),
        **{
            f"frontend display ({path})": frontend_version(path)
            for path in FRONTEND_VERSION_FILES
        },
    }
    drift = {name: value for name, value in actual.items() if value != EXPECTED}
    if drift:
        details = ", ".join(f"{name}={value}" for name, value in sorted(drift.items()))
        raise SystemExit(f"Version drift from VERSION={EXPECTED}: {details}")
    print(f"Maintained release versions are consistent: {EXPECTED}")


if __name__ == "__main__":
    main()
