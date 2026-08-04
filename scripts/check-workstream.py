#!/usr/bin/env python3
"""Validate repository workstreams, including bounded Platform release promotion."""

from __future__ import annotations

import re
import sys
from pathlib import Path

_CORE_PATH = Path(__file__).with_name("check-workstream-core.py")
_CORE_ENTRYPOINT = '\nif __name__ == "__main__":\n    sys.exit(main())\n'
_core_source = _CORE_PATH.read_text(encoding="utf-8")
if not _core_source.endswith(_CORE_ENTRYPOINT):
    raise RuntimeError("check-workstream core entrypoint changed unexpectedly")
exec(
    compile(_core_source.removesuffix(_CORE_ENTRYPOINT), str(_CORE_PATH), "exec"),
    globals(),
)
_CORE_MAIN = main

RELEASE_BRANCH_PATTERN = re.compile(
    r"^release/platform-(?P<major>\d+)-(?P<minor>\d+)-(?P<patch>\d+)$"
)
RELEASE_VERSION_PATHS = {
    "VERSION",
    "platform-web/package.json",
    "platform-web/.env.development",
    "platform-web/.env.production",
    "platform-api/pyproject.toml",
    "platform-api/app/application.py",
    "execution-runtime/pyproject.toml",
    "execution-runtime/app/version.py",
    "docs/codex/current-state.md",
}
RELEASE_SUPPORT_PATHS = {
    "scripts/bump-version.py": "modified",
    "scripts/check-workstream.py": "modified",
    "scripts/check-workstream-core.py": "added",
    "execution-runtime/tests/test_runtime_journal.py": "modified",
}


def validate_release_version_patch(path: str, patch: str | None) -> None:
    if path != "execution-runtime/app/version.py":
        validate_version_patch(path, patch)
        return
    lines = changed_patch_lines(patch)
    valid = bool(lines) and all(
        re.fullmatch(r'PLATFORM_VERSION\s*=\s*"\d+\.\d+\.\d+"', line.strip())
        for line in lines
    )
    if not valid:
        raise WorkstreamError(
            "execution-runtime/app/version.py: release mode permits only its version line"
        )


def validate_release_files(files: list[dict[str, object]]) -> list[str]:
    if not files:
        raise WorkstreamError("release PR must change at least one file")
    paths: list[str] = []
    changed_versions: set[str] = set()
    for item in files:
        path = str(item.get("filename") or "")
        status = str(item.get("status") or "")
        if path in RELEASE_VERSION_PATHS:
            if status != "modified":
                raise WorkstreamError(f"{path}: release version declarations may only be modified")
            validate_release_version_patch(path, item.get("patch"))
            changed_versions.add(path)
        elif path in RELEASE_SUPPORT_PATHS:
            expected_status = RELEASE_SUPPORT_PATHS[path]
            if status != expected_status:
                raise WorkstreamError(
                    f"{path}: expected release-support status {expected_status}, received {status}"
                )
        else:
            raise WorkstreamError(f"{path}: outside bounded Platform release promotion")
        paths.append(path)
    if changed_versions != RELEASE_VERSION_PATHS:
        raise WorkstreamError(
            "Platform release version update is incomplete; "
            f"missing {sorted(RELEASE_VERSION_PATHS - changed_versions)}"
        )
    return paths


def main() -> int:
    event = read_event()
    branch = current_branch(event)
    if not branch or RELEASE_BRANCH_PATTERN.fullmatch(branch) is None:
        return _CORE_MAIN()
    if not isinstance(event.get("pull_request"), dict):
        print("Workstream check skipped outside pull-request context")
        return 0
    workstream = requested_workstream(event)
    if workstream != "fast":
        raise WorkstreamError("Platform release PR must use Workstream: fast")
    validate_fast_body(event)
    pr_number = int(event["pull_request"].get("number", 0))
    files = pull_request_files(pr_number)
    validated = validate_release_files(files)
    print(
        "Platform release workstream valid: "
        f"branch={branch}, files={len(validated)}, behavior_change=none, safety_change=none"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except WorkstreamError as exc:
        print(f"Workstream check failed: {exc}", file=sys.stderr)
        sys.exit(1)
