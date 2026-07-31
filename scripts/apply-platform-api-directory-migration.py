#!/usr/bin/env python3
"""Apply the one-time Platform API mechanical directory migration."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

LEGACY = "platform" + "-backend"
REPLACEMENT = "platform-api"
ACTIVE_CATEGORIES = {
    "active_ci",
    "active_root_contract",
    "active_service_tree",
    "active_tooling",
    "current_documentation",
}


def run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(args), cwd=cwd, check=True, text=True)


def replace_active_reference(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    output = [line.replace(LEGACY, REPLACEMENT).rstrip() for line in content.splitlines()]
    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def inventory(root: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "directory-migration.json"
        run(
            sys.executable,
            "scripts/audit-directory-migration.py",
            "--root",
            ".",
            "--format",
            "json",
            "--output",
            str(output),
            "--fail-on-unclassified",
            cwd=root,
        )
        return json.loads(output.read_text(encoding="utf-8"))


def update_package_identity(root: Path) -> None:
    path = root / REPLACEMENT / "pyproject.toml"
    content = path.read_text(encoding="utf-8")
    content = content.replace(
        'name = "variable-global-platform-backend"',
        'name = "variable-global-platform-api"',
    )
    content = content.replace(
        'description = "Variable-Global modular monolith backend"',
        'description = "Variable-Global Platform API modular monolith"',
    )
    if 'name = "variable-global-platform-api"' not in content:
        raise RuntimeError("Platform API project identity was not updated")
    path.write_text(content, encoding="utf-8")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    legacy_root = root / LEGACY
    replacement_root = root / REPLACEMENT

    if not legacy_root.exists() and replacement_root.is_dir():
        print("Platform API directory is already migrated; no changes required.")
        return 0
    if not legacy_root.is_dir() or replacement_root.exists():
        raise RuntimeError("Expected legacy Platform API directory only before migration")

    before = inventory(root)
    references = before["references"]
    assert isinstance(references, list)
    active_paths = sorted(
        {
            str(reference["path"])
            for reference in references
            if reference["legacy_name"] == LEGACY
            and reference["category"] in ACTIVE_CATEGORIES
        }
    )

    run("git", "mv", LEGACY, REPLACEMENT, cwd=root)
    for raw_path in active_paths:
        path = Path(raw_path)
        if raw_path.startswith(f"{LEGACY}/"):
            path = Path(REPLACEMENT) / path.relative_to(LEGACY)
        replace_active_reference(root / path)

    update_package_identity(root)
    run("git", "add", "-A", cwd=root)
    run(
        sys.executable,
        "scripts/audit-directory-migration.py",
        "--root",
        ".",
        "--mode",
        "post-rename",
        "--target",
        REPLACEMENT,
        "--fail-on-unclassified",
        cwd=root,
    )
    print(f"Platform API migration staged with {len(active_paths)} active files updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
