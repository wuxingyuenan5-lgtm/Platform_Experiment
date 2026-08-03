#!/usr/bin/env python3
"""Update all maintained product-version declarations in one command."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r"\d+\.\d+\.\d+")
FRONTEND_VERSION_FILES = (
    "admin-risk/.env.development",
    "admin-risk/.env.production",
)


def replace_once(path: Path, pattern: str, replacement: str) -> None:
    content = path.read_text(encoding="utf-8")
    updated, count = re.subn(pattern, replacement, content, count=1, flags=re.MULTILINE)
    if count != 1:
        raise SystemExit(f"Expected one version declaration in {path}")
    path.write_text(updated, encoding="utf-8")


def update_versions(root: Path, version: str) -> None:
    if SEMVER.fullmatch(version) is None:
        raise SystemExit(f"Invalid semantic version: {version}")
    (root / "VERSION").write_text(version + "\n", encoding="utf-8")
    for relative in ("platform-backend/pyproject.toml", "execution-runtime/pyproject.toml"):
        replace_once(
            root / relative,
            r'^version\s*=\s*"\d+\.\d+\.\d+"$',
            f'version = "{version}"',
        )
    for relative in FRONTEND_VERSION_FILES:
        replace_once(
            root / relative,
            r'^VITE_GLOB_APP_VERSION\s*=\s*["\']\d+\.\d+\.\d+["\']$',
            f'VITE_GLOB_APP_VERSION = "{version}"',
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version")
    args = parser.parse_args()
    update_versions(ROOT, args.version)
    print(f"Updated maintained product version declarations to {args.version}")


if __name__ == "__main__":
    main()
