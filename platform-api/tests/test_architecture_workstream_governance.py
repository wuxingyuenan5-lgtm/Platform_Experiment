from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check-workstream.py"
SPEC = importlib.util.spec_from_file_location("check_workstream", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
check_workstream = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_workstream)


def pr_event(workstream: str, extra: str = "") -> dict:
    return {
        "pull_request": {
            "number": 37,
            "body": f"Workstream: {workstream}\n{extra}",
        }
    }


def version_files() -> list[dict[str, str]]:
    return [
        {"filename": "VERSION", "status": "modified", "patch": "@@\n-0.8.0\n+0.9.0"},
        {
            "filename": "platform-api/pyproject.toml",
            "status": "modified",
            "patch": '@@\n-version = "0.8.0"\n+version = "0.9.0"',
        },
        {
            "filename": "execution-runtime/pyproject.toml",
            "status": "modified",
            "patch": '@@\n-version = "0.8.0"\n+version = "0.9.0"',
        },
        {
            "filename": "platform-web/.env",
            "status": "modified",
            "patch": (
                '@@\n-VITE_GLOB_APP_VERSION = "0.8.0"\n'
                '+VITE_GLOB_APP_VERSION = "0.9.0"'
            ),
        },
    ]


def test_workstream_line_must_select_exactly_one_track() -> None:
    assert check_workstream.requested_workstream(pr_event("standard")) == "standard"
    with pytest.raises(check_workstream.WorkstreamError, match="exactly one"):
        check_workstream.requested_workstream(
            {
                "pull_request": {
                    "number": 37,
                    "body": "Workstream: fast\nWorkstream: standard",
                }
            }
        )


def test_track_branch_rules() -> None:
    assert (
        check_workstream.critical_branch_issue("chore/issue-115-lean-project-baseline")
        == 115
    )
    check_workstream.validate_fast_branch("docs/release-0-9-0")
    check_workstream.validate_standard_branch("fix/button-label")

    with pytest.raises(check_workstream.WorkstreamError, match="cannot use"):
        check_workstream.validate_standard_branch("fix/issue-7-button-label")
    with pytest.raises(check_workstream.WorkstreamError, match="critical branch"):
        check_workstream.critical_branch_issue("hardening/project-governance")


def test_critical_task_packet_is_unique_and_matches_branch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    branch = "hardening/issue-36-project-operating-system"
    packet = tmp_path / "issue-36-project-operating-system.md"
    packet.write_text(f"Issue: #36\nBranch: `{branch}`\n", encoding="utf-8")
    monkeypatch.setattr(check_workstream, "TASKS", tmp_path)

    selected = check_workstream.find_task_packet(36)
    check_workstream.validate_task_packet(selected, 36, branch)

    (tmp_path / "issue-36-duplicate.md").write_text(
        f"Issue: #36\nBranch: `{branch}`\n",
        encoding="utf-8",
    )
    with pytest.raises(check_workstream.WorkstreamError, match="exactly one"):
        check_workstream.find_task_packet(36)


def test_critical_pr_links_exact_issue() -> None:
    event = pr_event("critical", "Issue: #36")
    assert check_workstream.pull_request_issue(event, 36) == 37

    event["pull_request"]["body"] = "Workstream: critical\nIssue: #35"
    with pytest.raises(check_workstream.WorkstreamError):
        check_workstream.pull_request_issue(event, 36)


def test_fast_requires_no_behavior_and_no_safety_change() -> None:
    event = pr_event(
        "fast",
        "Behavior change: none\nSafety change: none\n\n## Outcome\nUpdate docs.",
    )
    assert check_workstream.validate_fast_body(event) == 37

    event["pull_request"]["body"] += "\nIssue: #105"
    with pytest.raises(check_workstream.WorkstreamError, match="must not link"):
        check_workstream.validate_fast_body(event)


def test_fast_files_allow_markdown_and_synchronized_versions() -> None:
    files = version_files() + [
        {
            "filename": "docs/releases/0.9.0.md",
            "status": "added",
            "patch": "@@\n+# Platform 0.9.0",
        },
        {
            "filename": "README.md",
            "status": "modified",
            "patch": "@@\n-old\n+new",
        },
    ]
    assert check_workstream.validate_fast_files(files) == [
        item["filename"] for item in files
    ]


def test_fast_rejects_source_and_partial_version_updates() -> None:
    with pytest.raises(check_workstream.WorkstreamError, match="outside Fast"):
        check_workstream.validate_fast_files(
            [
                {
                    "filename": "platform-api/app/main.py",
                    "status": "modified",
                    "patch": "@@\n-old\n+new",
                }
            ]
        )

    with pytest.raises(check_workstream.WorkstreamError, match="incomplete"):
        check_workstream.validate_fast_files(version_files()[:1])


def test_standard_allows_bounded_product_work_but_rejects_critical_paths() -> None:
    assert check_workstream.validate_standard_files(
        [
            {"filename": "platform-web/src/views/example.vue"},
            {"filename": "scripts/dev-platform.ps1"},
        ]
    )

    with pytest.raises(check_workstream.WorkstreamError, match="Critical"):
        check_workstream.validate_standard_files(
            [{"filename": "execution-runtime/app/main.py"}]
        )
    with pytest.raises(check_workstream.WorkstreamError, match="Critical"):
        check_workstream.validate_standard_files(
            [{"filename": ".github/workflows/platform-ci.yml"}]
        )


def test_duplicate_open_critical_pr_is_rejected(monkeypatch) -> None:
    responses = iter(
        [
            {"number": 36, "state": "open", "title": "Critical task"},
            [
                {"number": 37, "body": "Workstream: critical\nIssue: #36"},
                {"number": 38, "body": "Workstream: critical\nIssue: #36"},
            ],
        ]
    )
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setattr(
        check_workstream,
        "github_json",
        lambda _url, _token: next(responses),
    )

    with pytest.raises(check_workstream.WorkstreamError, match="another open PR"):
        check_workstream.validate_issue_and_unique_pr(36, current_pr=37)
