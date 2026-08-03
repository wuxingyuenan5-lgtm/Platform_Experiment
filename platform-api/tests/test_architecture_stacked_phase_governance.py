from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "check-workstream.py"
SPEC = importlib.util.spec_from_file_location("check_workstream_stacked", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check)

BASE = "refactor/platform-0-9-3-repository-and-context-optimization"
HEAD = "refactor/platform-0-9-3-codebase-and-build-simplification"
BASE_SHA = "cd825fe6bd9ecdf42082069b2785844eda2efac8"


def event(*, number: int = 148, workstream: str = "critical", head: str = HEAD, base: str = BASE,
          base_sha: str = BASE_SHA, declared_sha: str | None = BASE_SHA, draft: bool = True,
          phase: int | None = 3, extra: str = "") -> dict:
    lines = [f"Workstream: {workstream}"]
    if phase is not None:
        lines.append(f"Stacked phase: {phase}")
    if declared_sha is not None:
        lines.append(f"Accepted base SHA: {declared_sha}")
    if extra:
        lines.append(extra)
    return {
        "pull_request": {
            "number": number,
            "draft": draft,
            "body": "\n".join(lines),
            "head": {"ref": head, "sha": "1" * 40},
            "base": {"ref": base, "sha": base_sha},
        }
    }


def test_valid_stacked_phase_is_pr_number_independent() -> None:
    for number in (148, 149, 812):
        current = event(number=number)
        assert check.requested_workstream(current) == "critical"
        check.validate_stacked_platform_critical(current)


def test_same_version_future_phase_is_valid() -> None:
    check.validate_stacked_platform_critical(event(
        head="refactor/platform-0-9-3-future-phase-slug",
        base=HEAD,
        phase=4,
    ))


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"base": "main"}, "stacked Platform phase branch"),
        ({"declared_sha": "0" * 40}, "does not match"),
        ({"declared_sha": None}, "Accepted base SHA"),
        ({"draft": False}, "remain Draft"),
        ({"workstream": "standard"}, "must use Workstream: critical"),
        ({"base": "refactor/platform-0-9-2-repository-optimization"}, "versions must match"),
    ],
)
def test_invalid_stacked_phase_metadata_fails(kwargs: dict, message: str) -> None:
    current = event(**kwargs)
    with pytest.raises(check.WorkstreamError, match=message):
        if kwargs.get("workstream") == "standard":
            check.validate_stacked_workstream_selection(
                current["pull_request"]["head"]["ref"],
                "standard",
            )
        else:
            check.validate_stacked_platform_critical(current)


def test_duplicate_workstream_fails() -> None:
    with pytest.raises(check.WorkstreamError, match="exactly one"):
        check.requested_workstream(event(extra="Workstream: critical"))


def test_issue_critical_and_missing_packet_behavior(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    branch = "hardening/issue-36-project-operating-system"
    packet = tmp_path / "issue-36-project-operating-system.md"
    packet.write_text(f"Issue: #36\nBranch: `{branch}`\n", encoding="utf-8")
    monkeypatch.setattr(check, "TASKS", tmp_path)
    selected = check.find_task_packet(36)
    check.validate_task_packet(selected, 36, branch)
    selected.unlink()
    with pytest.raises(check.WorkstreamError, match="exactly one task packet"):
        check.find_task_packet(36)


def test_fast_and_standard_rules_remain_unchanged() -> None:
    check.validate_fast_branch("docs/release-0-9-3")
    check.validate_standard_branch("fix/button-label")
    with pytest.raises(check.WorkstreamError):
        check.validate_fast_branch("fix/issue-7-button-label")
    with pytest.raises(check.WorkstreamError):
        check.validate_standard_branch("fix/issue-7-button-label")


def test_platform_ci_has_no_pr_specific_parser() -> None:
    workflow = (ROOT / ".github/workflows/platform-ci.yml").read_text(encoding="utf-8")
    section = workflow.split("- name: Validate PR workstream", 1)[1].split(
        "- name: Audit stacked Phase history",
        1,
    )[0]
    assert "python scripts/check-workstream.py" in section
    assert "STAC" + "KED_PR_NUMBER" not in workflow
    assert "bounded Phase 3 PR #148" not in workflow
    assert "python - <<'PY'" not in section
