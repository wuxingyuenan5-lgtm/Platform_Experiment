from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "frontend-no-new-debt.py"
SPEC = importlib.util.spec_from_file_location("frontend_no_new_debt", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
frontend_no_new_debt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(frontend_no_new_debt)


def test_changed_frontend_source_selection_is_bounded_and_unique() -> None:
    selected = frontend_no_new_debt.select_frontend_files(
        [
            "platform-web/src/views/platform/index.vue",
            "platform-web/src/views/platform/index.vue",
            "platform-web/docs/START-HERE.md",
            "platform-backend/app/main.py",
            "platform-web/package.json",
        ]
    )

    assert selected == ["src/views/platform/index.vue"]


def test_exact_renames_are_excluded_but_modified_renames_are_linted() -> None:
    legacy_frontend = "admin" + "-risk"
    changed = frontend_no_new_debt.parse_changed_paths(
        "\n".join(
            [
                f"R100\t{legacy_frontend}/src/views/legacy.vue\tplatform-web/src/views/legacy.vue",
                f"R098\t{legacy_frontend}/src/views/changed.vue\tplatform-web/src/views/changed.vue",
                "M\tplatform-web/src/views/modified.vue",
                "A\tplatform-web/src/views/added.vue",
            ]
        )
    )

    assert changed == [
        "platform-web/src/views/changed.vue",
        "platform-web/src/views/modified.vue",
        "platform-web/src/views/added.vue",
    ]


def test_pull_request_base_uses_merge_base_comparison() -> None:
    sha = "a" * 40
    event = {"pull_request": {"base": {"sha": sha}}}
    assert frontend_no_new_debt.event_base_sha(event) == (sha, True)


def test_push_base_uses_direct_comparison() -> None:
    sha = "b" * 40
    event = {"before": sha}
    assert frontend_no_new_debt.event_base_sha(event) == (sha, False)
