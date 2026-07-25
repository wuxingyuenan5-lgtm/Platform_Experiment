from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check-workstream.py"
SPEC = importlib.util.spec_from_file_location("check_workstream", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
check_workstream = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_workstream)


def test_branch_issue_requires_issue_numbered_branch() -> None:
    assert check_workstream.branch_issue("hardening/issue-36-project-operating-system") == 36
    with pytest.raises(check_workstream.WorkstreamError):
        check_workstream.branch_issue("hardening/project-operating-system")


def test_maintenance_branch_is_bounded_and_not_issue_numbered() -> None:
    check_workstream.validate_maintenance_branch("docs/release-0-8-1")
    check_workstream.validate_maintenance_branch("chore/fix-release-links")

    with pytest.raises(check_workstream.WorkstreamError, match="Issue-numbered"):
        check_workstream.validate_maintenance_branch("docs/issue-105-release-metadata")
    with pytest.raises(check_workstream.WorkstreamError, match="docs/<slug> or chore/<slug>"):
        check_workstream.validate_maintenance_branch("feature/release-0-8-1")
    with pytest.raises(check_workstream.WorkstreamError, match="docs/<slug> or chore/<slug>"):
        check_workstream.validate_maintenance_branch("docs/release-0.8.1")


def test_task_packet_must_be_unique_and_match_branch(tmp_path: Path, monkeypatch) -> None:
    task = tmp_path / "issue-36-project-operating-system.md"
    branch = "hardening/issue-36-project-operating-system"
    task.write_text(f"Issue: #36\nBranch: `{branch}`\n", encoding="utf-8")
    monkeypatch.setattr(check_workstream, "TASKS", tmp_path)

    packet = check_workstream.find_task_packet(36)
    check_workstream.validate_task_packet(packet, 36, branch)

    duplicate = tmp_path / "issue-36-duplicate.md"
    duplicate.write_text(f"Issue: #36\nBranch: `{branch}`\n", encoding="utf-8")
    with pytest.raises(check_workstream.WorkstreamError):
        check_workstream.find_task_packet(36)


def test_pull_request_body_must_link_exact_branch_issue() -> None:
    event = {
        "pull_request": {
            "number": 37,
            "body": "Issue: #36\n\n## Objective\nGovern the workstream.",
        }
    }
    assert check_workstream.pull_request_issue(event, 36) == 37

    event["pull_request"]["body"] = "Issue: #35"
    with pytest.raises(check_workstream.WorkstreamError):
        check_workstream.pull_request_issue(event, 36)


def test_maintenance_body_requires_explicit_no_change_declarations() -> None:
    event = {
        "pull_request": {
            "number": 107,
            "body": (
                "Maintenance: true\n"
                "Behavior change: none\n"
                "Safety change: none\n\n"
                "## Objective\nUpdate release documentation."
            ),
        }
    }
    assert check_workstream.validate_maintenance_body(event) == 107

    event["pull_request"]["body"] += "\nIssue: #105"
    with pytest.raises(check_workstream.WorkstreamError, match="must not link"):
        check_workstream.validate_maintenance_body(event)

    event["pull_request"]["body"] = "Maintenance: true\nBehavior change: none"
    with pytest.raises(check_workstream.WorkstreamError, match="Safety change: none"):
        check_workstream.validate_maintenance_body(event)


def version_files() -> list[dict[str, str]]:
    return [
        {
            "filename": "VERSION",
            "status": "modified",
            "patch": "@@\n-0.8.0\n+0.8.1",
        },
        {
            "filename": "platform-backend/pyproject.toml",
            "status": "modified",
            "patch": '@@\n-version = "0.8.0"\n+version = "0.8.1"',
        },
        {
            "filename": "execution-runtime/pyproject.toml",
            "status": "modified",
            "patch": '@@\n-version = "0.8.0"\n+version = "0.8.1"',
        },
        {
            "filename": "admin-risk/.env",
            "status": "modified",
            "patch": "@@\n-VITE_APP_VERSION=0.8.0\n+VITE_APP_VERSION=0.8.1",
        },
    ]


def test_maintenance_files_allow_markdown_and_synchronized_versions() -> None:
    files = version_files() + [
        {
            "filename": "docs/releases/0.8.1.md",
            "status": "added",
            "patch": "@@\n+# Platform 0.8.1",
        },
        {
            "filename": "README.md",
            "status": "modified",
            "patch": "@@\n-old\n+new",
        },
    ]
    assert check_workstream.validate_maintenance_files(files) == [
        item["filename"] for item in files
    ]


def test_maintenance_files_reject_source_and_partial_version_updates() -> None:
    with pytest.raises(check_workstream.WorkstreamError, match="full engineering track"):
        check_workstream.validate_maintenance_files(
            [
                {
                    "filename": "platform-backend/app/main.py",
                    "status": "modified",
                    "patch": "@@\n-old\n+new",
                }
            ]
        )

    with pytest.raises(check_workstream.WorkstreamError, match="missing"):
        check_workstream.validate_maintenance_files(version_files()[:1])

    unsafe_env_patch = version_files()
    unsafe_env_patch[-1] = {
        "filename": "admin-risk/.env",
        "status": "modified",
        "patch": "@@\n-VITE_APP_VERSION=0.8.0\n+VITE_APP_VERSION=0.8.1\n+LIVE_WRITE=true",
    }
    with pytest.raises(check_workstream.WorkstreamError, match="version line"):
        check_workstream.validate_maintenance_files(unsafe_env_patch)


def test_duplicate_open_pull_request_is_rejected(monkeypatch) -> None:
    responses = iter(
        [
            {"number": 36, "state": "open", "title": "Engineering task"},
            [
                {"number": 37, "body": "Issue: #36"},
                {"number": 38, "body": "Issue: #36"},
            ],
        ]
    )
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setattr(check_workstream, "github_json", lambda _url, _token: next(responses))

    with pytest.raises(check_workstream.WorkstreamError, match="another open PR"):
        check_workstream.validate_issue_and_unique_pr(36, current_pr=37)
