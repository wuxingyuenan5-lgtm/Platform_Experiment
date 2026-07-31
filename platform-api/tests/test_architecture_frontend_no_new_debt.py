from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "frontend-no-new-debt.py"
SPEC = importlib.util.spec_from_file_location("frontend_no_new_debt", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
frontend_no_new_debt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(frontend_no_new_debt)


def _diagnostic(
    rule_id: str = "prettier/prettier",
    *,
    severity: int = 2,
    line: int = 10,
    end_line: int | None = None,
    message: str = "formatting",
    fatal: bool = False,
):
    return frontend_no_new_debt.EslintDiagnostic(
        rule_id=rule_id,
        severity=severity,
        line=line,
        end_line=end_line or line,
        message=message,
        fatal=fatal,
    )


def test_changed_frontend_source_selection_is_bounded_and_unique() -> None:
    selected = frontend_no_new_debt.select_frontend_files(
        [
            "platform-web/src/views/platform/index.vue",
            "platform-web/src/views/platform/index.vue",
            "platform-web/docs/START-HERE.md",
            "platform-api/app/main.py",
            "platform-web/package.json",
        ]
    )

    assert selected == ["src/views/platform/index.vue"]


def test_exact_renames_are_excluded_but_modified_renames_keep_base_path() -> None:
    legacy_frontend = "admin" + "-risk"
    output = "\n".join(
        [
            f"R100\t{legacy_frontend}/src/views/legacy.vue\t"
            "platform-web/src/views/legacy.vue",
            f"R098\t{legacy_frontend}/src/views/changed.vue\t"
            "platform-web/src/views/changed.vue",
            "M\tplatform-web/src/views/modified.vue",
            "A\tplatform-web/src/views/added.vue",
        ]
    )

    changed = frontend_no_new_debt.parse_changed_files(output)

    assert changed == [
        frontend_no_new_debt.FrontendChange(
            status="R098",
            base_path=f"{legacy_frontend}/src/views/changed.vue",
            current_path="platform-web/src/views/changed.vue",
        ),
        frontend_no_new_debt.FrontendChange(
            status="M",
            base_path="platform-web/src/views/modified.vue",
            current_path="platform-web/src/views/modified.vue",
        ),
        frontend_no_new_debt.FrontendChange(
            status="A",
            base_path=None,
            current_path="platform-web/src/views/added.vue",
        ),
    ]
    assert frontend_no_new_debt.parse_changed_paths(output) == [
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


def test_changed_lines_include_modified_content_and_formatting_boundaries() -> None:
    touched = frontend_no_new_debt.changed_current_lines(
        "alpha\nlegacy\nomega\n",
        "alpha\nmodern\nomega\n",
    )

    assert touched == {1, 2, 3}


def test_existing_debt_may_decrease_away_from_touched_lines() -> None:
    issues = frontend_no_new_debt.compare_diagnostics(
        relative_path="src/views/legacy.vue",
        base=[_diagnostic(line=10), _diagnostic(line=20)],
        current=[_diagnostic(line=20)],
        touched_lines={2, 3},
    )

    assert issues == []


def test_rule_or_severity_counts_may_not_increase() -> None:
    issues = frontend_no_new_debt.compare_diagnostics(
        relative_path="src/views/legacy.vue",
        base=[_diagnostic(line=10)],
        current=[_diagnostic(line=10), _diagnostic(line=20)],
        touched_lines=set(),
    )

    assert any("prettier/prettier: 1 -> 2" in issue for issue in issues)


def test_touched_lines_must_be_clean_even_when_total_debt_is_unchanged() -> None:
    issues = frontend_no_new_debt.compare_diagnostics(
        relative_path="src/views/legacy.vue",
        base=[_diagnostic(line=10)],
        current=[_diagnostic(line=30)],
        touched_lines={29, 30, 31},
    )

    assert any("touched code is not clean" in issue for issue in issues)


def test_new_files_remain_strictly_warning_free() -> None:
    issues = frontend_no_new_debt.compare_diagnostics(
        relative_path="src/views/new.ts",
        base=None,
        current=[
            _diagnostic(
                rule_id="no-console",
                severity=1,
                line=4,
                message="Unexpected console statement.",
            )
        ],
        touched_lines={1, 2, 3, 4},
    )

    assert any("new file must be clean" in issue for issue in issues)


def test_fatal_diagnostics_always_fail_closed() -> None:
    issues = frontend_no_new_debt.compare_diagnostics(
        relative_path="src/views/legacy.vue",
        base=[_diagnostic(fatal=True)],
        current=[_diagnostic(fatal=True)],
        touched_lines=set(),
    )

    assert any("fatal ESLint diagnostic" in issue for issue in issues)
