"""Run zero-warning ESLint on every changed frontend source file.

The maintained trading surface is still linted in full by Platform CI. This gate
extends protection to the inherited frontend without requiring a mass cleanup:
any source file added or modified by a PR must be clean before merge.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = ROOT / "admin-risk"
SOURCE_PREFIXES = ("admin-risk/src/", "admin-risk/mock/")
SOURCE_SUFFIXES = (".js", ".jsx", ".ts", ".tsx", ".vue")
ZERO_SHA = "0" * 40


class FrontendDebtError(RuntimeError):
    """The changed-file lint gate could not determine or validate its scope."""


def select_frontend_files(paths: list[str]) -> list[str]:
    selected: list[str] = []
    for raw_path in paths:
        normalized = raw_path.replace("\\", "/").lstrip("./")
        if not normalized.startswith(SOURCE_PREFIXES):
            continue
        if not normalized.endswith(SOURCE_SUFFIXES):
            continue
        path = ROOT / normalized
        if path.is_file():
            selected.append(str(path.relative_to(FRONTEND_ROOT)).replace("\\", "/"))
    return sorted(set(selected))


def read_event() -> dict[str, Any]:
    event_path = os.getenv("GITHUB_EVENT_PATH")
    if not event_path:
        return {}
    path = Path(event_path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def event_base_sha(event: dict[str, Any]) -> tuple[str | None, bool]:
    pull_request = event.get("pull_request")
    if isinstance(pull_request, dict):
        base = pull_request.get("base")
        if isinstance(base, dict) and isinstance(base.get("sha"), str):
            return base["sha"], True

    before = event.get("before")
    if isinstance(before, str) and before != ZERO_SHA:
        return before, False
    return None, False


def changed_paths(base_sha: str, *, merge_base: bool) -> list[str]:
    separator = "..." if merge_base else ".."
    command = [
        "git",
        "diff",
        "--name-only",
        "--diff-filter=ACMR",
        f"{base_sha}{separator}HEAD",
    ]
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise FrontendDebtError(result.stderr.strip() or "git diff failed")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def run_eslint(files: list[str]) -> int:
    if not files:
        print("Frontend no-new-debt check passed: no changed source files")
        return 0
    command = ["pnpm", "exec", "eslint", "--max-warnings", "0", *files]
    print("Frontend no-new-debt files:")
    for path in files:
        print(f"- {path}")
    return subprocess.run(command, cwd=FRONTEND_ROOT, check=False).returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", help="Base commit SHA. GitHub event metadata is used by default.")
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Use base..HEAD instead of merge-base comparison.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    event = read_event()
    event_base, event_uses_merge_base = event_base_sha(event)
    base_sha = args.base or event_base
    merge_base = False if args.direct else event_uses_merge_base
    if base_sha is None:
        print(
            "Frontend no-new-debt check skipped: no base SHA outside GitHub CI",
            file=sys.stderr,
        )
        return 0

    try:
        files = select_frontend_files(changed_paths(base_sha, merge_base=merge_base))
    except FrontendDebtError as exc:
        print(f"Frontend no-new-debt check failed: {exc}", file=sys.stderr)
        return 1
    return run_eslint(files)


if __name__ == "__main__":
    raise SystemExit(main())
