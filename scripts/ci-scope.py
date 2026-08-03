#!/usr/bin/env python3
"""Classify changed paths so pull requests run only affected application jobs."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Iterable

FULL_PATHS = {
    ".github/workflows/platform-ci.yml",
    "scripts/ci-scope.py",
}
FULL_PREFIXES = (
    "docs/contracts/",
    "platform-api/app/runtime_contracts.py",
    "execution-runtime/app/runtime_contracts.py",
)
FRONTEND_PREFIXES = (
    "platform-web/src/",
    "platform-web/mock/",
    "platform-web/scripts/",
    "platform-web/package.json",
    "platform-web/pnpm-lock.yaml",
    "platform-web/tsconfig",
)


def classify_paths(paths: Iterable[str], *, force_full: bool = False) -> dict[str, bool]:
    normalized = {path.strip().replace("\\", "/") for path in paths if path.strip()}
    full = force_full or any(
        path in FULL_PATHS or path.startswith(FULL_PREFIXES) for path in normalized
    )
    backend = full or any(path.startswith("platform-api/") for path in normalized)
    runtime = full or any(path.startswith("execution-runtime/") for path in normalized)
    frontend = full or any(path.startswith(FRONTEND_PREFIXES) for path in normalized)
    return {
        "backend": backend,
        "runtime": runtime,
        "frontend": frontend,
        "docs_only": bool(normalized)
        and not backend
        and not runtime
        and not frontend,
    }


def changed_paths(base: str, head: str) -> list[str]:
    completed = subprocess.run(
        ["git", "diff", "--name-only", base, head],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.splitlines()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    paths = [] if args.full else changed_paths(args.base, args.head)
    result = classify_paths(paths, force_full=args.full)
    lines = [f"{name}={'true' if value else 'false'}" for name, value in result.items()]
    output = "\n".join(lines) + "\n"
    if args.github_output:
        args.github_output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")


if __name__ == "__main__":
    main()
