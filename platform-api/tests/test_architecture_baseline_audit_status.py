from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/platform-0-9-2-audit.yml"


def test_baseline_audit_uses_formal_jobs_without_synthetic_commit_status() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")

    assert "Candidate workflow evidence" in source
    assert "Formal workflow jobs and run conclusions are the only CI authority" in source
    assert "statuses: write" not in source
    assert 'f"/repos/{repository}/statuses/{sha}"' not in source
    assert '"state": state' not in source
    assert 'context = "phase-1a/"' not in source
