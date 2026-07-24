"""Validate one-Issue/one-branch/one-PR workstream discipline.

The check is intentionally dependency-free so it can run locally and in GitHub Actions.
On pull requests it also queries the GitHub API and rejects another open PR that
references the same Issue.
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
BRANCH_PATTERN = re.compile(
    r"^(?:feature|fix|refactor|hardening|docs|chore)/issue-(?P<issue>\d+)-"
    r"(?P<slug>[a-z0-9][a-z0-9-]*)$"
)
ISSUE_LINE_PATTERN = re.compile(r"(?mi)^Issue:\s*#(?P<issue>\d+)\s*$")
PR_ISSUE_PATTERN = re.compile(
    r"(?mi)^(?:Issue|Closes|Fixes|Resolves):?\s*#(?P<issue>\d+)\s*$"
)


class WorkstreamError(RuntimeError):
    """A repository workstream rule was violated."""


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


def branch_issue(branch: str) -> int:
    match = BRANCH_PATTERN.fullmatch(branch)
    if match is None:
        raise WorkstreamError(
            "branch must use <type>/issue-<number>-<slug>; "
            f"received {branch!r}"
        )
    return int(match.group("issue"))


def find_task_packet(issue_number: int) -> Path:
    matches = sorted(TASKS.glob(f"issue-{issue_number}-*.md"))
    if len(matches) != 1:
        relative = [str(path.relative_to(ROOT)) for path in matches]
        raise WorkstreamError(
            f"Issue #{issue_number} must have exactly one task packet; found {relative}"
        )
    return matches[0]


def validate_task_packet(path: Path, issue_number: int, branch: str) -> None:
    content = path.read_text(encoding="utf-8")
    issue_match = ISSUE_LINE_PATTERN.search(content)
    if issue_match is None or int(issue_match.group("issue")) != issue_number:
        raise WorkstreamError(
            f"{path.relative_to(ROOT)} must declare exactly 'Issue: #{issue_number}'"
        )
    expected_branch = f"Branch: `{branch}`"
    if expected_branch not in content:
        raise WorkstreamError(
            f"{path.relative_to(ROOT)} must declare {expected_branch!r}"
        )


def pull_request_issue(event: dict[str, Any], expected_issue: int) -> int | None:
    pull_request = event.get("pull_request")
    if not isinstance(pull_request, dict):
        return None
    body = pull_request.get("body") or ""
    matches = {int(match.group("issue")) for match in PR_ISSUE_PATTERN.finditer(body)}
    if matches != {expected_issue}:
        raise WorkstreamError(
            "pull request body must contain one standalone linkage line such as "
            f"'Issue: #{expected_issue}'; found {sorted(matches)}"
        )
    return int(pull_request.get("number", 0)) or None


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


def main() -> int:
    event = read_event()
    branch = current_branch(event)
    if not branch or branch == "main":
        print("Workstream check skipped for main/no branch context")
        return 0

    try:
        issue_number = branch_issue(branch)
        packet = find_task_packet(issue_number)
        validate_task_packet(packet, issue_number, branch)
        current_pr = pull_request_issue(event, issue_number)
        validate_issue_and_unique_pr(issue_number, current_pr)
    except WorkstreamError as exc:
        print(f"Workstream check failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"Workstream check passed: Issue #{issue_number}, branch {branch}, "
        f"packet {packet.relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
