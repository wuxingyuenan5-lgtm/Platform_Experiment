#!/usr/bin/env python3
"""Fail when maintained release declarations drift from root VERSION."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def project_version(path: str) -> str:
    with (ROOT / path).open("rb") as handle:
        return str(tomllib.load(handle)["project"]["version"])


def frontend_version() -> str:
    content = (ROOT / "admin-risk/.env").read_text(encoding="utf-8")
    match = re.search(r'VITE_GLOB_APP_VERSION\s*=\s*"([^"]+)"', content)
    if match is None:
        raise SystemExit("Frontend release version declaration is missing")
    return match.group(1)


def main() -> None:
    actual = {
        "platform-backend package": project_version("platform-backend/pyproject.toml"),
        "execution-runtime package": project_version("execution-runtime/pyproject.toml"),
        "frontend display": frontend_version(),
    }
    drift = {name: value for name, value in actual.items() if value != EXPECTED}
    if drift:
        details = ", ".join(f"{name}={value}" for name, value in sorted(drift.items()))
        raise SystemExit(f"Version drift from VERSION={EXPECTED}: {details}")
    print(f"Maintained release versions are consistent: {EXPECTED}")


if __name__ == "__main__":
    main()
