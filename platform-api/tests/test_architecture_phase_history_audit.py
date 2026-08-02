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
