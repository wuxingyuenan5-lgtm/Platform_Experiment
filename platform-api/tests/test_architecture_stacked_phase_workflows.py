from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = (
    "platform-ci.yml",
    "platform-directory-invariants.yml",
    "version-consistency.yml",
    "secret-scan.yml",
    "platform-0-9-2-audit.yml",
    "platform-visual-baseline.yml",
    "user-system-e2e.yml",
    "hedge-board-e2e.yml",
    "research-provider-smoke.yml",
)
CREDENTIAL_WORKFLOWS = (
    "platform-visual-baseline.yml",
    "user-system-e2e.yml",
    "hedge-board-e2e.yml",
)
CONTROLLED_PATTERN = "refactor/platform-0-9-3-*"
OLD_EXACT_BRANCHES = (
    "refactor/platform-0-9-3-repository-and-context-optimization",
    "refactor/platform-0-9-3-codebase-and-build-simplification",
)


def workflow_text(name: str) -> str:
    return (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")


def test_controlled_phase_pattern_matches_only_intended_branch_family() -> None:
    assert fnmatch.fnmatchcase(
        "refactor/platform-0-9-3-repository-and-context-optimization",
        CONTROLLED_PATTERN,
    )
    assert fnmatch.fnmatchcase(
        "refactor/platform-0-9-3-codebase-and-build-simplification",
        CONTROLLED_PATTERN,
    )
    assert fnmatch.fnmatchcase(
        "refactor/platform-0-9-3-future-phase-slug",
        CONTROLLED_PATTERN,
    )
    assert not fnmatch.fnmatchcase("internal/phase3-object-publish", CONTROLLED_PATTERN)
    assert not fnmatch.fnmatchcase(
        "refactor/issue-136-platform-0-9-2-system-optimization",
        CONTROLLED_PATTERN,
    )
    assert not fnmatch.fnmatchcase("refactor/unrelated-cleanup", CONTROLLED_PATTERN)
    assert not fnmatch.fnmatchcase("refactor/platform-0-9-4-future-phase", CONTROLLED_PATTERN)


@pytest.mark.parametrize("name", WORKFLOWS)
def test_all_nine_workflows_use_controlled_phase_pattern(name: str) -> None:
    text = workflow_text(name)
    assert CONTROLLED_PATTERN in text
    assert "refactor/**" not in text
    assert "      - '**'" not in text
    assert '      - "**"' not in text
    for branch in OLD_EXACT_BRANCHES:
        assert branch not in text


@pytest.mark.parametrize("name", CREDENTIAL_WORKFLOWS)
def test_generated_e2e_passwords_are_masked_before_export(name: str) -> None:
    text = workflow_text(name)
    generated_credentials = text.split("- name: Generate isolated", 1)[1].split(
        "\n      - name:",
        1,
    )[0]

    assert 'password = f"Cc9!{secrets.token_urlsafe(24)}"' in generated_credentials
    assert 'print(f"::add-mask::{password}")' in generated_credentials
    assert "GITHUB_ENV" in generated_credentials
    assert generated_credentials.index("::add-mask::") < generated_credentials.index(
        "GITHUB_ENV"
    )


def test_platform_ci_uses_event_driven_stacked_history_and_debt_bases() -> None:
    platform_ci = workflow_text("platform-ci.yml")
    history = platform_ci.split("- name: Audit stacked Phase history", 1)[1].split(
        "- name: Check repository structure",
        1,
    )[0]
    debt = platform_ci.split("- name: Enforce frontend no-new-debt gate", 1)[1].split(
        "- name: Type check strategy frontend",
        1,
    )[0]

    assert '--event "$GITHUB_EVENT_PATH"' in history
    assert '--repository "$GITHUB_REPOSITORY"' in history
    assert 'AUDIT_REF="$GITHUB_HEAD_REF"' in history
    assert 'AUDIT_REF="${GITHUB_REF#refs/heads/}"' in history
    assert "not-applicable" in history
    assert "python ../scripts/frontend-no-new-debt.py" in debt
    assert "--base" not in debt
    assert "--direct" not in debt
    assert "GITHUB_REF_NAME" not in debt

    for forbidden in (
        "PHASE3_BASE_SHA",
        "PHASE3_ORIGINAL_HEAD",
        "CANDIDATE_BASE_SHA",
        "STACKED_HEAD_SHA",
        "STACKED_PR_NUMBER",
    ):
        assert forbidden not in platform_ci


def test_baseline_and_visual_conditions_use_generic_phase_family() -> None:
    audit = workflow_text("platform-0-9-2-audit.yml")
    visual = workflow_text("platform-visual-baseline.yml")

    assert "startsWith(github.ref_name, 'refactor/platform-0-9-3-')" in audit
    assert "!startsWith(github.ref_name, 'refactor/platform-0-9-3-')" in visual


def test_required_legacy_delivery_branches_remain_where_they_are_operationally_used() -> None:
    platform_ci = workflow_text("platform-ci.yml")
    baseline = workflow_text("platform-0-9-2-audit.yml")

    assert "      - main" in platform_ci
    assert "      - feature/issue-134-platform-0-9-1-unified-delivery" in platform_ci
    assert "      - refactor/issue-136-platform-0-9-2-system-optimization" in baseline
    assert "      - feature/issue-134-platform-0-9-1-unified-delivery" in baseline


def test_formal_route_sources_are_unchanged_from_r1_start() -> None:
    git_dir = ROOT / ".git"
    if not git_dir.exists():
        pytest.skip(
            "source snapshot has no Git metadata; CI checkout provides the authoritative check"
        )
    subprocess.run(
        [
            "git",
            "diff",
            "--exit-code",
            "735542b69c38b552fd3bb3109819b177e424b0fb",
            "--",
            "platform-web/src/router/routes/modules",
        ],
        cwd=ROOT,
        check=True,
    )
