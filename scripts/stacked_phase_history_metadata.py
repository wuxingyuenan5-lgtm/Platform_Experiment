"""Resolve generic stacked-phase metadata from GitHub events and PR bodies."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from stacked_phase_history_model import AuditError

STACKED_PHASE_PATTERN = re.compile(r"(?mi)^Stacked phase:\s*(?P<phase>[1-9]\d*)\s*$")
ACCEPTED_BASE_SHA_PATTERN = re.compile(
    r"(?mi)^Accepted base SHA:\s*(?P<sha>[0-9a-f]{40})\s*$"
)


def _single_match(pattern: re.Pattern[str], body: str, label: str) -> str:
    matches = list(pattern.finditer(body))
    if len(matches) != 1:
        raise AuditError(f"PR body must contain exactly one {label} line")
    values = matches[0].groupdict()
    return values.get("sha") or values.get("phase") or ""


def parse_stacked_metadata(body: str) -> tuple[str, int]:
    accepted_base = _single_match(
        ACCEPTED_BASE_SHA_PATTERN,
        body,
        "'Accepted base SHA: <40-hex-sha>'",
    )
    phase = int(
        _single_match(
            STACKED_PHASE_PATTERN,
            body,
            "'Stacked phase: <number>'",
        )
    )
    return accepted_base, phase


def github_json(url: str, token: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "platform-stacked-phase-audit",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise AuditError(f"GitHub API failed with {exc.code}: {details}") from exc
    except urllib.error.URLError as exc:
        raise AuditError(f"GitHub API unavailable: {exc.reason}") from exc


def _pull_request_from_push(
    event: dict[str, Any],
    repository: str,
    token: str,
) -> dict[str, Any]:
    branch = str(event.get("ref") or "").removeprefix("refs/heads/")
    owner = repository.split("/", 1)[0]
    query = urllib.parse.urlencode(
        {"state": "open", "head": f"{owner}:{branch}", "per_page": 100}
    )
    pulls = github_json(f"https://api.github.com/repos/{repository}/pulls?{query}", token)
    candidates = [
        pull
        for pull in pulls
        if isinstance(pull, dict)
        and isinstance(pull.get("head"), dict)
        and pull["head"].get("ref") == branch
    ] if isinstance(pulls, list) else []
    if len(candidates) != 1:
        numbers = [pull.get("number") for pull in candidates]
        raise AuditError(
            "stacked phase push must resolve exactly one open PR for "
            f"{branch}; found {numbers}"
        )
    return candidates[0]


def metadata_from_event(
    event: dict[str, Any],
    *,
    repository: str | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    pull = event.get("pull_request")
    if not isinstance(pull, dict):
        if not repository or not token:
            raise AuditError(
                "push history audit requires GITHUB_REPOSITORY and GITHUB_TOKEN"
            )
        pull = _pull_request_from_push(event, repository, token)

    accepted_base, phase = parse_stacked_metadata(str(pull.get("body") or ""))
    base_data = pull.get("base")
    head_data = pull.get("head")
    pr_base = base_data.get("sha") if isinstance(base_data, dict) else None
    head = head_data.get("sha") if isinstance(head_data, dict) else None
    if not isinstance(pr_base, str) or re.fullmatch(r"[0-9a-f]{40}", pr_base) is None:
        raise AuditError("pull request is missing a valid base SHA")
    if not isinstance(head, str) or re.fullmatch(r"[0-9a-f]{40}", head) is None:
        raise AuditError("pull request is missing a valid head SHA")
    return {
        "accepted_base_sha": accepted_base,
        "pr_base_sha": pr_base,
        "head_sha": head,
        "stacked_phase": phase,
        "pr_number": pull.get("number"),
    }
