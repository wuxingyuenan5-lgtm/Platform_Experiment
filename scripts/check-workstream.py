"""Validate engineering and lightweight maintenance workstream discipline.

The check is intentionally dependency-free so it can run locally and in GitHub Actions.
Engineering work keeps the one-Issue/one-task/one-branch/one-PR model. Explicit,
bounded maintenance PRs may omit an Issue and task packet, but only for Markdown
and tightly validated product-version declarations.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TASKS = ROOT / "tasks"
ENGINEERING_BRANCH_PATTERN = re.compile(
    r"^(?:feature|fix|refactor|hardening|docs|chore)/issue-(?P<issue>\d+)-"
    r"(?P<slug>[a-z0-9][a-z0-9-]*)$"
)
MAINTENANCE_BRANCH_PATTERN = re.compile(
    r"^(?:docs|chore)/(?P<slug>[a-z0-9][a-z0-9-]*)$"
)
ISSUE_LINE_PATTERN = re.compile(r"(?mi)^Issue:\s*#(?P<issue>\d+)\s*$")
PR_ISSUE_PATTERN = re.compile(
    r"(?mi)^(?:Issue|Closes|Fixes|Resolves):?\s*#(?P<issue>\d+)\s*$"
)
MAINTENANCE_LINE_PATTERN = re.compile(r"(?mi)^Maintenance:\s*true\s*$")
BEHAVIOR_NONE_PATTERN = re.compile(r"(?mi)^Behavior change:\s*none\s*$")
SAFETY_NONE_PATTERN = re.compile(r"(?mi)^Safety change:\s*none\s*$")
SEMVER_PATTERN = re.compile(r"\d+\.\d+\.\d+")

VERSION_PATHS = {
    "VERSION",
    "platform-backend/pyproject.toml",
    "execution-runtime/pyproject.toml",
    "admin-risk/.env",
}
MAINTENANCE_MAX_FILES = 20
FORBIDDEN_MARKDOWN_PATHS = {
    "AGENTS.md",
}
FORBIDDEN_MARKDOWN_PREFIXES = (
    ".github/",
    "tasks/",
)


class WorkstreamError(RuntimeError):
    """A repository workstream rule was violated."""


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_event() -> dict[str, Any]:
    event_path = os.getenv("GITHUB_EVENT_PATH")
    if not event_path:
        return {}
    path = Path(event_path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def current_branch(event: dict[str, Any]) -> str | None:
    pull_request = event.get("pull_request")
    if isinstance(pull_request, dict):
        head = pull_request.get("head")
        if isinstance(head, dict) and isinstance(head.get("ref"), str):
            return head["ref"]
    return os.getenv("GITHUB_HEAD_REF") or os.getenv("GITHUB_REF_NAME")


def pull_request_body(event: dict[str, Any]) -> str:
    pull_request = event.get("pull_request")
    if not isinstance(pull_request, dict):
        return ""
    return str(pull_request.get("body") or "")


def maintenance_requested(event: dict[str, Any]) -> bool:
    body = pull_request_body(event)
    return bool(MAINTENANCE_LINE_PATTERN.search(body)) or (
        os.getenv("WORKSTREAM_MAINTENANCE", "").lower() == "true"
    )


def branch_issue(branch: str) -> int:
    match = ENGINEERING_BRANCH_PATTERN.fullmatch(branch)
    if match is None:
        raise WorkstreamError(
            "engineering branch must use <type>/issue-<number>-<slug>; "
            f"received {branch!r}"
        )
    return int(match.group("issue"))


def validate_maintenance_branch(branch: str) -> None:
    if ENGINEERING_BRANCH_PATTERN.fullmatch(branch):
        raise WorkstreamError(
            "Maintenance: true cannot be used on an Issue-numbered engineering branch"
        )
    if MAINTENANCE_BRANCH_PATTERN.fullmatch(branch) is None:
        raise WorkstreamError(
            "maintenance branch must use docs/<slug> or chore/<slug> with only "
            f"lowercase letters, numbers and hyphens; received {branch!r}"
        )


def find_task_packet(issue_number: int) -> Path:
    matches = sorted(TASKS.glob(f"issue-{issue_number}-*.md"))
    if len(matches) != 1:
        relative = [display_path(path) for path in matches]
        raise WorkstreamError(
            f"Issue #{issue_number} must have exactly one task packet; found {relative}"
        )
    return matches[0]


def validate_task_packet(path: Path, issue_number: int, branch: str) -> None:
    content = path.read_text(encoding="utf-8")
    issue_match = ISSUE_LINE_PATTERN.search(content)
    if issue_match is None or int(issue_match.group("issue")) != issue_number:
        raise WorkstreamError(
            f"{display_path(path)} must declare exactly 'Issue: #{issue_number}'"
        )
    expected_branch = f"Branch: `{branch}`"
    if expected_branch not in content:
        raise WorkstreamError(
            f"{display_path(path)} must declare {expected_branch!r}"
        )


def pull_request_issue(event: dict[str, Any], expected_issue: int) -> int | None:
    pull_request = event.get("pull_request")
    if not isinstance(pull_request, dict):
        return None
    body = pull_request_body(event)
    matches = {int(match.group("issue")) for match in PR_ISSUE_PATTERN.finditer(body)}
    if matches != {expected_issue}:
        raise WorkstreamError(
            "pull request body must contain one standalone linkage line such as "
            f"'Issue: #{expected_issue}'; found {sorted(matches)}"
        )
    return int(pull_request.get("number", 0)) or None


def validate_maintenance_body(event: dict[str, Any]) -> int:
    pull_request = event.get("pull_request")
    if not isinstance(pull_request, dict):
        raise WorkstreamError(
            "maintenance mode requires pull-request context; local callers must use the "
            "pure validators or provide a GitHub event"
        )
    body = pull_request_body(event)
    required = (
        (MAINTENANCE_LINE_PATTERN, "Maintenance: true"),
        (BEHAVIOR_NONE_PATTERN, "Behavior change: none"),
        (SAFETY_NONE_PATTERN, "Safety change: none"),
    )
    missing = [label for pattern, label in required if pattern.search(body) is None]
    if missing:
        raise WorkstreamError(
            f"maintenance PR body is missing standalone declaration(s): {missing}"
        )
    linked_issues = sorted(
        {int(match.group("issue")) for match in PR_ISSUE_PATTERN.finditer(body)}
    )
    if linked_issues:
        raise WorkstreamError(
            "maintenance PR must not link an engineering Issue; use the full engineering "
            f"track instead (found {linked_issues})"
        )
    number = int(pull_request.get("number", 0))
    if number <= 0:
        raise WorkstreamError("maintenance PR event is missing a valid pull request number")
    return number


def github_json(url: str, token: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "variable-global-workstream-check",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise WorkstreamError(f"GitHub API failed with {exc.code}: {details}") from exc
    except urllib.error.URLError as exc:
        raise WorkstreamError(f"GitHub API unavailable: {exc.reason}") from exc


def validate_issue_and_unique_pr(issue_number: int, current_pr: int | None) -> None:
    repository = os.getenv("GITHUB_REPOSITORY")
    token = os.getenv("GITHUB_TOKEN")
    if not repository or not token:
        return

    issue = github_json(
        f"https://api.github.com/repos/{repository}/issues/{issue_number}", token
    )
    if not isinstance(issue, dict) or "pull_request" in issue:
        raise WorkstreamError(f"#{issue_number} is not an engineering Issue")
    if issue.get("state") != "open":
        raise WorkstreamError(f"Issue #{issue_number} must remain open until its PR merges")

    pulls = github_json(
        f"https://api.github.com/repos/{repository}/pulls?state=open&per_page=100", token
    )
    duplicates: list[int] = []
    for pull in pulls:
        number = int(pull["number"])
        if current_pr is not None and number == current_pr:
            continue
        body = pull.get("body") or ""
        linked = {int(match.group("issue")) for match in PR_ISSUE_PATTERN.finditer(body)}
        if issue_number in linked:
            duplicates.append(number)
    if duplicates:
        raise WorkstreamError(
            f"Issue #{issue_number} already has another open PR: {duplicates}. "
            "Close and mark the old PR as superseded before opening a replacement."
        )


def pull_request_files(pr_number: int) -> list[dict[str, Any]]:
    repository = os.getenv("GITHUB_REPOSITORY")
    token = os.getenv("GITHUB_TOKEN")
    if not repository or not token:
        raise WorkstreamError(
            "maintenance changed-file validation requires GITHUB_REPOSITORY and GITHUB_TOKEN"
        )
    files = github_json(
        f"https://api.github.com/repos/{repository}/pulls/{pr_number}/files?per_page=100",
        token,
    )
    if not isinstance(files, list):
        raise WorkstreamError("GitHub PR files response must be a list")
    return [item for item in files if isinstance(item, dict)]


def changed_patch_lines(patch: str | None) -> list[str]:
    if not patch:
        raise WorkstreamError("version declaration change is missing a readable text patch")
    return [
        line[1:]
        for line in patch.splitlines()
        if (line.startswith("+") or line.startswith("-"))
        and not line.startswith("+++")
        and not line.startswith("---")
    ]


def validate_version_patch(path: str, patch: str | None) -> None:
    lines = changed_patch_lines(patch)
    if not lines:
        raise WorkstreamError(f"{path}: version declaration patch contains no changed lines")
    if path == "VERSION":
        valid = all(SEMVER_PATTERN.fullmatch(line.strip()) for line in lines)
    elif path in {
        "platform-backend/pyproject.toml",
        "execution-runtime/pyproject.toml",
    }:
        valid = all(
            re.fullmatch(r'version\s*=\s*"\d+\.\d+\.\d+"', line.strip())
            for line in lines
        )
    elif path == "admin-risk/.env":
        valid = all(
            re.fullmatch(r"VITE_APP_VERSION=\d+\.\d+\.\d+", line.strip())
            for line in lines
        )
    else:
        valid = False
    if not valid:
        raise WorkstreamError(
            f"{path}: maintenance mode permits only the maintained product-version line"
        )


def markdown_allowed(path: str) -> bool:
    if not path.endswith(".md"):
        return False
    if path in FORBIDDEN_MARKDOWN_PATHS:
        return False
    return not path.startswith(FORBIDDEN_MARKDOWN_PREFIXES)


def validate_maintenance_files(files: list[dict[str, Any]]) -> list[str]:
    if not files:
        raise WorkstreamError("maintenance PR must change at least one file")
    if len(files) > MAINTENANCE_MAX_FILES:
        raise WorkstreamError(
            f"maintenance PR may change at most {MAINTENANCE_MAX_FILES} files; found {len(files)}"
        )

    paths: list[str] = []
    changed_version_paths: set[str] = set()
    for item in files:
        path = str(item.get("filename") or "")
        status = str(item.get("status") or "")
        if not path:
            raise WorkstreamError("maintenance PR contains a file without a path")
        if status == "renamed":
            raise WorkstreamError(f"{path}: renames require the full engineering track")
        if path in VERSION_PATHS:
            if status != "modified":
                raise WorkstreamError(
                    f"{path}: maintained version declarations may only be modified"
                )
            validate_version_patch(path, item.get("patch"))
            changed_version_paths.add(path)
        elif not markdown_allowed(path):
            raise WorkstreamError(
                f"{path}: maintenance mode permits Markdown and maintained version "
                "declarations only; use the full engineering track"
            )
        paths.append(path)

    if changed_version_paths and changed_version_paths != VERSION_PATHS:
        missing = sorted(VERSION_PATHS - changed_version_paths)
        raise WorkstreamError(
            "product version maintenance must update all maintained declarations; "
            f"missing {missing}"
        )
    return paths


def main() -> int:
    event = read_event()
    branch = current_branch(event)
    if not branch or branch == "main":
        print("Workstream check skipped for main/no branch context")
        return 0

    try:
        if maintenance_requested(event):
            validate_maintenance_branch(branch)
            current_pr = validate_maintenance_body(event)
            paths = validate_maintenance_files(pull_request_files(current_pr))
            print(
                f"Maintenance workstream check passed: PR #{current_pr}, branch {branch}, "
                f"files {paths}"
            )
            return 0

        issue_number = branch_issue(branch)
        packet = find_task_packet(issue_number)
        validate_task_packet(packet, issue_number, branch)
        current_pr = pull_request_issue(event, issue_number)
        validate_issue_and_unique_pr(issue_number, current_pr)
    except WorkstreamError as exc:
        print(f"Workstream check failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"Engineering workstream check passed: Issue #{issue_number}, branch {branch}, "
        f"packet {display_path(packet)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
