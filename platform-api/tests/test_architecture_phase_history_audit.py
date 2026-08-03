from __future__ import annotations

import importlib.util
import json
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


def formal_commit(repo: Path, index: int, *, prefix: str = "refactor") -> str:
    target = repo / "platform-api" / "app" / f"owner_{index}.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"OWNER = {index}\n", encoding="utf-8")
    return commit(repo, f"{prefix}(platform-0.9.3): establish owner {index}")


def event(base: str, head: str, *, phase: int = 4, number: int = 149) -> dict:
    return {
        "pull_request": {
            "number": number,
            "body": (
                "Workstream: critical\n"
                f"Stacked phase: {phase}\n"
                f"Accepted base SHA: {base}\n"
            ),
            "base": {"sha": base},
            "head": {"sha": head},
        }
    }


def test_phase_3_and_phase_4_use_their_own_accepted_base(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, phase_3_base = initialize_repo(tmp_path, monkeypatch)
    phase_3_head = formal_commit(repo, 1)
    phase_3 = audit_phase_history.metadata_from_event(
        event(phase_3_base, phase_3_head, phase=3, number=148)
    )
    result_3 = audit_phase_history.audit(
        phase_3["accepted_base_sha"],
        phase_3["head_sha"],
        pr_base=phase_3["pr_base_sha"],
        phase_number=phase_3["stacked_phase"],
    )

    phase_4_base = phase_3_head
    phase_4_head = formal_commit(repo, 2)
    phase_4 = audit_phase_history.metadata_from_event(
        event(phase_4_base, phase_4_head, phase=4, number=149)
    )
    result_4 = audit_phase_history.audit(
        phase_4["accepted_base_sha"],
        phase_4["head_sha"],
        pr_base=phase_4["pr_base_sha"],
        phase_number=phase_4["stacked_phase"],
    )

    assert result_3["stacked_phase"] == 3
    assert result_3["audited_commit_count"] == 1
    assert result_4["stacked_phase"] == 4
    assert result_4["audited_commit_count"] == 1


def test_phase_and_pr_number_changes_need_no_workflow_change() -> None:
    base = "a" * 40
    head = "b" * 40
    for phase, number in ((3, 148), (4, 149), (17, 812)):
        metadata = audit_phase_history.metadata_from_event(
            event(base, head, phase=phase, number=number)
        )
        assert metadata["stacked_phase"] == phase
        assert metadata["pr_number"] == number


def test_legal_refactor_is_not_unexpected() -> None:
    category = audit_phase_history.classify(
        "refactor(platform-0.9.3): establish trading owner",
        [{"status": "A", "path": "platform-api/app/trading_owner.py"}],
        30,
        0,
    )
    assert category == "formal-implementation"


def test_real_unknown_change_remains_unexpected() -> None:
    category = audit_phase_history.classify(
        "change product behavior",
        [{"status": "A", "path": "platform-web/src/product.ts"}],
        1,
        0,
    )
    assert category == "unexpected"


def test_architecture_baseline_and_evidence_are_distinct() -> None:
    baseline = audit_phase_history.classify(
        "test(platform-0.9.3): add deterministic architecture baseline tool",
        [{"status": "A", "path": "scripts/analyze-architecture.py"}],
        100,
        0,
    )
    evidence = audit_phase_history.classify(
        "test(platform-0.9.3): verify deterministic architecture evidence",
        [
            {
                "status": "A",
                "path": "platform-api/tests/test_architecture_metrics_tool.py",
            }
        ],
        40,
        0,
    )
    assert baseline == "architecture-baseline"
    assert evidence == "evidence"


def test_base_declaration_mismatch_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, base = initialize_repo(tmp_path, monkeypatch)
    head = formal_commit(repo, 1)
    with pytest.raises(audit_phase_history.AuditError, match="does not match"):
        audit_phase_history.audit(
            base,
            head,
            pr_base="0" * 40,
            phase_number=4,
        )


def test_non_linear_history_and_merge_commit_fail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, base = initialize_repo(tmp_path, monkeypatch)
    primary = run(repo, "branch", "--show-current")
    formal_commit(repo, 1)
    run(repo, "checkout", "-b", "side", base)
    formal_commit(repo, 2)
    run(repo, "checkout", primary)
    run(repo, "merge", "--no-ff", "side", "-m", "merge side")
    head = run(repo, "rev-parse", "HEAD")

    with pytest.raises(audit_phase_history.AuditError, match="merge commit"):
        audit_phase_history.audit(base, head, pr_base=base, phase_number=4)


def test_behind_nonzero_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, root = initialize_repo(tmp_path, monkeypatch)
    base = formal_commit(repo, 1)
    primary = run(repo, "branch", "--show-current")
    run(repo, "checkout", "-b", "side", root)
    side_head = formal_commit(repo, 2)

    with pytest.raises(audit_phase_history.AuditError, match="behind accepted base"):
        audit_phase_history.audit(base, side_head, pr_base=base, phase_number=4)
    run(repo, "checkout", primary)


def test_temporary_facility_must_exit_final_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, base = initialize_repo(tmp_path, monkeypatch)
    temp = repo / "scripts/phase4-materialize/payload.part00"
    temp.parent.mkdir(parents=True)
    temp.write_text("payload\n", encoding="utf-8")
    head = commit(repo, "chore(platform-0.9.3): add materialization payload")

    with pytest.raises(audit_phase_history.AuditError, match="facilities remain"):
        audit_phase_history.audit(base, head, pr_base=base, phase_number=4)


def test_pr_temporary_merge_sha_is_not_selected() -> None:
    workflow = (ROOT / ".github/workflows/platform-ci.yml").read_text(encoding="utf-8")
    section = workflow.split("- name: Audit stacked Phase history", 1)[1].split(
        "- name: Check repository structure",
        1,
    )[0]

    assert 'GITHUB_EVENT_PATH' in section
    assert '--event "$GITHUB_EVENT_PATH"' in section
    assert "github.event.pull_request.head.sha" not in section
    assert 'AUDIT_HEAD="$GITHUB_SHA"' not in section


def test_explicit_cli_metadata_remains_available(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, base = initialize_repo(tmp_path, monkeypatch)
    head = formal_commit(repo, 1)
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event(base, head)), encoding="utf-8")

    metadata = audit_phase_history.metadata_from_event(
        json.loads(event_path.read_text(encoding="utf-8"))
    )
    assert metadata["accepted_base_sha"] == base
    assert metadata["pr_base_sha"] == base
    assert metadata["head_sha"] == head
