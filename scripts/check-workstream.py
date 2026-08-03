#!/usr/bin/env python3
"""Validate Fast, Standard and Critical pull-request workstreams."""

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

CRITICAL_BRANCH_PATTERN = re.compile(
    r"^(?:feature|fix|refactor|hardening|docs|chore)/issue-(?P<issue>\d+)-"
    r"(?P<slug>[a-z0-9][a-z0-9-]*)$"
)
FAST_BRANCH_PATTERN = re.compile(r"^(?:docs|chore)/(?P<slug>[a-z0-9][a-z0-9-]*)$")
STANDARD_BRANCH_PATTERN = re.compile(
    r"^(?:feature|fix|refactor|chore)/(?P<slug>[a-z0-9][a-z0-9-]*)$"
)
WORKSTREAM_PATTERN = re.compile(r"(?mi)^Workstream:\s*(fast|standard|critical)\s*$")
ISSUE_LINE_PATTERN = re.compile(r"(?mi)^Issue:\s*#(?P<issue>\d+)\s*$")
PR_ISSUE_PATTERN = re.compile(
    r"(?mi)^(?:Issue|Closes|Fixes|Resolves):?\s*#(?P<issue>\d+)\s*$"
)
BEHAVIOR_NONE_PATTERN = re.compile(r"(?mi)^Behavior change:\s*none\s*$")
SAFETY_NONE_PATTERN = re.compile(r"(?mi)^Safety change:\s*none\s*$")
SEMVER_PATTERN = re.compile(r"\d+\.\d+\.\d+")

VERSION_PATHS = {
    "VERSION",
    "platform-api/pyproject.toml",
    "execution-runtime/pyproject.toml",
    "platform-web/.env",
}
FAST_MAX_FILES = 20
FORBIDDEN_FAST_MARKDOWN = {"AGENTS.md"}
FORBIDDEN_FAST_PREFIXES = (".github/", "tasks/")

CRITICAL_EXACT_PATHS = {
    "AGENTS.md",
    ".github/pull_request_template.md",
    "platform-api/app/auth.py",
    "platform-api/app/live_trading_sessions.py",
    "platform-api/app/runtime_contracts.py",
    "platform-api/app/schema_governance.py",
    "platform-api/app/schema_migrations.py",
    "platform-api/app/trade_command_execution.py",
    "platform-api/app/order_execution_intents.py",
    "scripts/check-workstream.py",
    "scripts/check-repository-structure.py",
    "scripts/check-documentation-consistency.py",
    "scripts/scan-secrets.py",
}
CRITICAL_PREFIXES = (
    ".github/",
    "tasks/",
    "execution-runtime/",
    "docs/contracts/",
    "platform-api/app/cross_spread",
    "platform-api/app/database",
    "platform-api/app/eod_",
    "platform-api/app/execution_",
    "platform-api/app/financial_",
    "platform-api/app/risk",
    "platform-api/app/venue_reconciliation",
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


def requested_workstream(event: dict[str, Any]) -> str:
    matches = [
        match.group(1).lower()
        for match in WORKSTREAM_PATTERN.finditer(pull_request_body(event))
    ]
    if len(matches) != 1:
        raise WorkstreamError(
            "pull request body must contain exactly one standalone "
            "'Workstream: fast|standard|critical' line"
        )
    return matches[0]


def critical_branch_issue(branch: str) -> int:
    match = CRITICAL_BRANCH_PATTERN.fullmatch(branch)
    if match is None:
        raise WorkstreamError(
            "critical branch must use <type>/issue-<number>-<slug>; "
            f"received {branch!r}"
        )
    return int(match.group("issue"))


def validate_fast_branch(branch: str) -> None:
    if CRITICAL_BRANCH_PATTERN.fullmatch(branch):
        raise WorkstreamError("fast workstream cannot use an Issue-numbered branch")
    if FAST_BRANCH_PATTERN.fullmatch(branch) is None:
        raise WorkstreamError("fast branch must use docs/<slug> or chore/<slug>")


def validate_standard_branch(branch: str) -> None:
    if CRITICAL_BRANCH_PATTERN.fullmatch(branch):
        raise WorkstreamError("standard workstream cannot use an Issue-numbered branch")
    if STANDARD_BRANCH_PATTERN.fullmatch(branch) is None:
        raise WorkstreamError(
            "standard branch must use feature/<slug>, fix/<slug>, refactor/<slug> or chore/<slug>"
        )


def find_task_packet(issue_number: int) -> Path:
    matches = sorted(TASKS.glob(f"issue-{issue_number}-*.md"))
    if len(matches) != 1:
        raise WorkstreamError(
            f"Critical Issue #{issue_number} must have exactly one task packet; "
            f"found {[display_path(path) for path in matches]}"
        )
    return matches[0]


def validate_task_packet(path: Path, issue_number: int, branch: str) -> None:
    content = path.read_text(encoding="utf-8")
    issue_match = ISSUE_LINE_PATTERN.search(content)
    if issue_match is None or int(issue_match.group("issue")) != issue_number:
        raise WorkstreamError(f"{display_path(path)} must declare 'Issue: #{issue_number}'")
    expected_branch = f"Branch: `{branch}`"
    if expected_branch not in content:
        raise WorkstreamError(f"{display_path(path)} must declare {expected_branch!r}")


def pull_request_issue(event: dict[str, Any], expected_issue: int) -> int | None:
    pull_request = event.get("pull_request")
    if not isinstance(pull_request, dict):
        return None
    matches = {
        int(match.group("issue"))
        for match in PR_ISSUE_PATTERN.finditer(pull_request_body(event))
    }
    if matches != {expected_issue}:
        raise WorkstreamError(
            f"critical PR must contain one standalone 'Issue: #{expected_issue}' linkage line; "
            f"found {sorted(matches)}"
        )
    return int(pull_request.get("number", 0)) or None


def validate_fast_body(event: dict[str, Any]) -> int:
    body = pull_request_body(event)
    missing = []
    if BEHAVIOR_NONE_PATTERN.search(body) is None:
        missing.append("Behavior change: none")
    if SAFETY_NONE_PATTERN.search(body) is None:
        missing.append("Safety change: none")
    if missing:
        raise WorkstreamError(f"fast PR body is missing standalone declaration(s): {missing}")
    linked = sorted({int(match.group("issue")) for match in PR_ISSUE_PATTERN.finditer(body)})
    if linked:
        raise WorkstreamError(f"fast PR must not link a Critical Issue; found {linked}")
    pull_request = event.get("pull_request")
    if not isinstance(pull_request, dict) or int(pull_request.get("number", 0)) <= 0:
        raise WorkstreamError("fast workstream requires pull-request context")
    return int(pull_request["number"])


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
    issue = github_json(f"https://api.github.com/repos/{repository}/issues/{issue_number}", token)
    if not isinstance(issue, dict) or "pull_request" in issue:
        raise WorkstreamError(f"#{issue_number} is not a Critical engineering Issue")
    if issue.get("state") != "open":
        raise WorkstreamError(f"Issue #{issue_number} must remain open until merge")
    pulls = github_json(
        f"https://api.github.com/repos/{repository}/pulls?state=open&per_page=100",
        token,
    )
    duplicates: list[int] = []
    for pull in pulls if isinstance(pulls, list) else []:
        number = int(pull["number"])
        if current_pr is not None and number == current_pr:
            continue
        linked = {
            int(match.group("issue"))
            for match in PR_ISSUE_PATTERN.finditer(str(pull.get("body") or ""))
        }
        if issue_number in linked:
            duplicates.append(number)
    if duplicates:
        raise WorkstreamError(f"Issue #{issue_number} already has another open PR: {duplicates}")


def pull_request_files(pr_number: int) -> list[dict[str, Any]]:
    repository = os.getenv("GITHUB_REPOSITORY")
    token = os.getenv("GITHUB_TOKEN")
    if not repository or not token:
        raise WorkstreamError("changed-file validation requires GitHub PR environment")
    files: list[dict[str, Any]] = []
    page = 1
    while True:
        result = github_json(
            f"https://api.github.com/repos/{repository}/pulls/{pr_number}/files"
            f"?per_page=100&page={page}",
            token,
        )
        if not isinstance(result, list):
            raise WorkstreamError("GitHub PR files response must be a list")
        files.extend(item for item in result if isinstance(item, dict))
        if len(result) < 100:
            return files
        page += 1


def changed_patch_lines(patch: str | None) -> list[str]:
    if not patch:
        raise WorkstreamError("version declaration change is missing a readable patch")
    return [
        line[1:]
        for line in patch.splitlines()
        if (line.startswith("+") or line.startswith("-"))
        and not line.startswith("+++")
        and not line.startswith("---")
    ]


def validate_version_patch(path: str, patch: str | None) -> None:
    lines = changed_patch_lines(patch)
    if path == "VERSION":
        valid = bool(lines) and all(SEMVER_PATTERN.fullmatch(line.strip()) for line in lines)
    elif path in {"platform-api/pyproject.toml", "execution-runtime/pyproject.toml"}:
        valid = bool(lines) and all(
            re.fullmatch(r'version\s*=\s*"\d+\.\d+\.\d+"', line.strip())
            for line in lines
        )
    elif path == "platform-web/.env":
        valid = bool(lines) and all(
            re.fullmatch(r'VITE_GLOB_APP_VERSION\s*=\s*"\d+\.\d+\.\d+"', line.strip())
            for line in lines
        )
    else:
        valid = False
    if not valid:
        raise WorkstreamError(f"{path}: fast mode permits only its product-version line")


def fast_markdown_allowed(path: str) -> bool:
    return (
        path.endswith(".md")
        and path not in FORBIDDEN_FAST_MARKDOWN
        and not path.startswith(FORBIDDEN_FAST_PREFIXES)
    )


def validate_fast_files(files: list[dict[str, Any]]) -> list[str]:
    if not files:
        raise WorkstreamError("fast PR must change at least one file")
    if len(files) > FAST_MAX_FILES:
        raise WorkstreamError(f"fast PR may change at most {FAST_MAX_FILES} files")
    paths: list[str] = []
    changed_versions: set[str] = set()
    for item in files:
        path = str(item.get("filename") or "")
        status = str(item.get("status") or "")
        if not path:
            raise WorkstreamError("fast PR contains a file without a path")
        if status == "renamed":
            raise WorkstreamError(f"{path}: renames require Standard or Critical")
        if path in VERSION_PATHS:
            if status != "modified":
                raise WorkstreamError(f"{path}: version declarations may only be modified")
            validate_version_patch(path, item.get("patch"))
            changed_versions.add(path)
        elif not fast_markdown_allowed(path):
            raise WorkstreamError(f"{path}: outside Fast Markdown/version boundary")
        paths.append(path)
    if changed_versions and changed_versions != VERSION_PATHS:
        raise WorkstreamError(
            f"product version update is incomplete; missing {sorted(VERSION_PATHS - changed_versions)}"
        )
    return paths


def is_critical_path(path: str) -> bool:
    return (
        path in CRITICAL_EXACT_PATHS
        or path.endswith("/AGENTS.md")
        or path.startswith(CRITICAL_PREFIXES)
    )


def validate_standard_files(files: list[dict[str, Any]]) -> list[str]:
    if not files:
        raise WorkstreamError("standard PR must change at least one file")
    paths = [str(item.get("filename") or "") for item in files]
    invalid = sorted(
        path
        for path in paths
        if not path or path in VERSION_PATHS or is_critical_path(path)
    )
    if invalid:
        raise WorkstreamError(
            f"Standard workstream touches Critical or release-governed paths: {invalid}"
        )
    return paths


def main() -> int:
    event = read_event()
    branch = current_branch(event)
    if not branch or branch == "main":
        print("Workstream check skipped for main/no branch context")
        return 0
    if not isinstance(event.get("pull_request"), dict):
        print("Workstream check skipped outside pull-request context")
        return 0

    workstream = requested_workstream(event)
    pr_number = int(event["pull_request"].get("number", 0))
    files = pull_request_files(pr_number)

    if workstream == "fast":
        validate_fast_branch(branch)
        validate_fast_body(event)
        validate_fast_files(files)
    elif workstream == "standard":
        validate_standard_branch(branch)
        validate_standard_files(files)
    else:
        issue = critical_branch_issue(branch)
        packet = find_task_packet(issue)
        validate_task_packet(packet, issue, branch)
        current_pr = pull_request_issue(event, issue)
        validate_issue_and_unique_pr(issue, current_pr)

    print(f"Workstream check passed: {workstream}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except WorkstreamError as exc:
        print(f"Workstream check failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
