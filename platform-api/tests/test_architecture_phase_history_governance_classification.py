from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL_PATH = ROOT / "scripts/stacked_phase_history_model.py"
SPEC = importlib.util.spec_from_file_location("stacked_phase_history_model", MODEL_PATH)
assert SPEC is not None and SPEC.loader is not None
MODEL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODEL)


def test_mixed_governance_test_commit_is_classified_as_governance() -> None:
    category = MODEL.classify(
        "test(platform-0.9.3): restore bounded context and SQL governance",
        [
            {"status": "M", "path": "scripts/context-for.py"},
            {
                "status": "A",
                "path": "platform-api/tests/test_architecture_context_budgets.py",
            },
            {
                "status": "A",
                "path": "docs/architecture/non-repository-sql-allowlist.json",
            },
        ],
        200,
        10,
    )
    assert category == "governance"
