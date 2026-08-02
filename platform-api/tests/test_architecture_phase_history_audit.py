from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "audit-phase-history.py"
SPEC = importlib.util.spec_from_file_location("audit_phase_history", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
audit_phase_history = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit_phase_history)


def run(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()


def commit(repo: Path, message: str) -> str:
    run(repo, "add", "-A")
    run(repo, "commit", "-m", message)
    return run(repo, "rev-parse", "HEAD")


def governance_commit(repo: Path, index: int) -> str:
    target = repo / "docs" / f"history-{index:02d}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"history {index}\n", encoding="utf-8")
    return commit(repo, f"governance(platform-0.9.3): audit step {index:02d}")


def initialize_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    run(repo, "init")
    run(repo, "config", "user.name", "Audit Test")
    run(repo, "config", "user.email", "audit@example.com")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    base = commit(repo, "base")
    monkeypatch.chdir(repo)
    return repo, base


def test_history_audit_accepts_linear_temporary_add_remove(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, base = initialize_repo(tmp_path, monkeypatch)
    temp = repo / "scripts/phase3-materialize/payload.part00"
    temp.parent.mkdir(parents=True)
    temp.write_text("payload\n", encoding="utf-8")
    commit(repo, "chore(platform-0.9.3): add materialization payload")
    temp.unlink()
    head = commit(repo, "chore(platform-0.9.3): remove materialization payload")

    result = audit_phase_history.audit(base, head, required_ancestor=None)

    assert result["audited_commit_count"] == 2
    assert result["merge_commit_count"] == 0
    assert result["unexpected_commits"] == []
    assert result["temporary_paths_absent_from_final_tree"] is True
    assert [item["category"] for item in result["commits"]] == [
        "temporary-add",
        "temporary-remove",
    ]


def test_history_audit_stops_on_unclassified_product_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, base = initialize_repo(tmp_path, monkeypatch)
    product = repo / "platform-web/src/product.ts"
    product.parent.mkdir(parents=True)
    product.write_text("export const changed = true;\n", encoding="utf-8")
    head = commit(repo, "change product behavior")

    with pytest.raises(audit_phase_history.AuditError, match="unexpected commits"):
        audit_phase_history.audit(base, head, required_ancestor=None)


def test_real_head_merge_commit_still_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, base = initialize_repo(tmp_path, monkeypatch)
    primary = run(repo, "branch", "--show-current")
    governance_commit(repo, 1)
    run(repo, "checkout", "-b", "side", base)
    governance_commit(repo, 2)
    run(repo, "checkout", primary)
    run(repo, "merge", "--no-ff", "side", "-m", "merge side")
    head = run(repo, "rev-parse", "HEAD")

    with pytest.raises(audit_phase_history.AuditError, match="non-linear or merge commit"):
        audit_phase_history.audit(base, head, required_ancestor=None)


def test_original_phase_head_must_be_34_commit_ancestor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, base = initialize_repo(tmp_path, monkeypatch)
    original = base
    for index in range(1, 35):
        original = governance_commit(repo, index)
    head = governance_commit(repo, 35)

    result = audit_phase_history.audit(base, head, required_ancestor=original)
    assert result["original_commit_count"] == 34
    assert result["audited_commit_count"] == 35

    primary = run(repo, "branch", "--show-current")
    run(repo, "checkout", "-b", "unrelated", base)
    unrelated = governance_commit(repo, 99)
    with pytest.raises(audit_phase_history.AuditError, match="not an ancestor"):
        audit_phase_history.audit(base, unrelated, required_ancestor=original)
    run(repo, "checkout", primary)


def test_base_must_be_merge_base_and_head_has_zero_behind(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, root = initialize_repo(tmp_path, monkeypatch)
    base = governance_commit(repo, 1)
    primary = run(repo, "branch", "--show-current")
    run(repo, "checkout", "-b", "side", root)
    side_head = governance_commit(repo, 2)

    with pytest.raises(audit_phase_history.AuditError, match="base is not the merge base"):
        audit_phase_history.audit(base, side_head, required_ancestor=None)
    run(repo, "checkout", primary)


def test_workflow_selects_actual_pr_head_not_temporary_merge_sha() -> None:
    workflow = (ROOT / ".github/workflows/platform-ci.yml").read_text(encoding="utf-8")
    section = workflow.split("- name: Audit stacked Phase history", 1)[1].split(
        "- name: Check repository structure",
        1,
    )[0]

    assert "EVENT_NAME: ${{ github.event_name }}" in section
    assert "PR_HEAD_SHA: ${{ github.event.pull_request.head.sha }}" in section
    assert 'if [ "$EVENT_NAME" = "pull_request" ]; then' in section
    assert 'AUDIT_HEAD="$PR_HEAD_SHA"' in section
    assert 'AUDIT_HEAD="$GITHUB_SHA"' in section
    assert '--head "$AUDIT_HEAD"' in section
    assert '--head "$GITHUB_SHA"' not in section
    assert "github.event.pull_request.head.sha || github.sha" not in section
