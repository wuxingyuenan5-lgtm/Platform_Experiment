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


def test_phase4_performance_baseline_commit_is_evidence() -> None:
    category = MODEL.classify(
        "perf(platform-0.9.3): add repeatable critical path baselines",
        [{"status": "A", "path": "scripts/measure-phase4-critical-paths.py"}],
        100,
        0,
    )
    assert category == "evidence"


def test_formal_frontend_layout_gate_commits_are_governance() -> None:
    for path, subject in (
        (
            "platform-web/scripts/verify-cross-spread-layout.cjs",
            "test(platform-web): retire replica assumptions from layout gate",
        ),
        (
            "platform-web/scripts/verify-hedge-board-layout.cjs",
            "test(platform-web): align hedge board gates with formal owners",
        ),
    ):
        category = MODEL.classify(
            subject,
            [{"status": "M", "path": path}],
            20,
            20,
        )
        assert category == "governance"


def test_phase5_owner_registry_foundations_are_formal_implementation() -> None:
    for path, subject in (
        (
            "config/product-data-owner-matrix.json",
            "feat(platform-0.9.3): add product data owner baseline",
        ),
        (
            "config/product-data-owner-overrides.json",
            "feat(platform-0.9.3): add reviewed product owner overrides",
        ),
        (
            "platform-web/src/api/platform/productDataState.ts",
            "feat(platform-web): add explicit product data state contract",
        ),
        (
            "platform-web/src/components/ProductDataState/ProductDataStatusAlert.vue",
            "feat(platform-web): add product data status presentation",
        ),
        (
            "platform-web/src/components/ProductDataState/ProductNotConfiguredPanel.vue",
            "feat(platform-web): add explicit not configured product state",
        ),
    ):
        category = MODEL.classify(
            subject,
            [{"status": "A", "path": path}],
            100,
            0,
        )
        assert category == "formal-implementation"


def test_arbitrary_feature_commit_remains_unexpected() -> None:
    assert (
        MODEL.classify(
            "feat(platform-web): add new product experience",
            [
                {
                    "status": "A",
                    "path": "platform-web/src/views/product/NewFeature.vue",
                }
            ],
            100,
            0,
        )
        == "unexpected"
    )


def test_unrelated_perf_and_frontend_script_changes_remain_unexpected() -> None:
    assert (
        MODEL.classify(
            "perf(platform-web): tune product rendering",
            [{"status": "M", "path": "platform-web/src/product.ts"}],
            2,
            2,
        )
        == "unexpected"
    )
    assert (
        MODEL.classify(
            "test(platform-web): update helper",
            [{"status": "M", "path": "platform-web/scripts/helper.cjs"}],
            2,
            2,
        )
        == "unexpected"
    )
