from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "check-task-card.py"
TASK_TEMPLATE = REPO_ROOT / "docs" / "codex" / "task-template.md"


def load_module():
    spec = importlib.util.spec_from_file_location("check_task_card", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_card(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "task-card.md"
    path.write_text(content, encoding="utf-8")
    return path


def base_short_record() -> str:
    return """# Task: Read-only Investigation

Task ID: `VG-GOV-TEST-READ-001`
Issue: `none`
Status: `active`
Last transition at: `2026-08-13 21:00 CST`
Owner notice: `none`
Business status summary: `Read-only investigation is active and gathering bounded governance evidence.`
Current leaf task/agent ID: `investigator-1`
Risk level: medium
Role: investigation
Agent ID: `investigator-1`
Context Pack: `governance`
Token indicator budget: `2000000`
Token indicator used: `200000`
Token status: `green`
Control-plane token used: `40000`

## Objective

Confirm that short read-only task records do not require implementation placeholders.

## Protected semantics

- Read-only only.

## Scope

- Included paths/outcomes.
- Explicit non-goals.

## Context

- Governance sources only.

## Verification

- `python scripts/check-task-card.py <task-card>`

## Progress

- Done: none
- Current: evidence review
- Next: close
- Blocked by: none
"""


def base_implementation_task() -> str:
    return """# Task: Governance Simplification

Task ID: `VG-GOV-TEST-IMPL-001`
Issue: `none`
Status: `active`
Last transition at: `2026-08-13 21:00 CST`
Owner notice: `none`
Business status summary: `Implementation is active on governance simplification.`
Current leaf task/agent ID: `impl-agent-1`
Risk level: high
Role: implementation
Agent ID: `impl-agent-1`
Context Pack: `governance`
Token indicator budget: `2000000`
Token indicator used: `400000`
Token status: `green`
Control-plane token used: `90000`

## Objective

Reduce governance overhead without changing business logic.

## Implementation fields

- Implementation owner: `impl-agent-1`
- Branch: `codex/sample-governance`
- Worktree: `C:\\worktrees\\sample-governance`
- Base commit: `0123456789abcdef0123456789abcdef01234567`

## Protected semantics

- Keep business behavior unchanged.

## Scope

- Included paths/outcomes.
- Explicit non-goals.

## Dispatch concurrency decision

- Write set: `AGENTS.md`; `docs/codex/AI_DEVELOPMENT_GOVERNANCE.md`
- Shared workflow, public contract, migration chain or file set: `none`
- Dependencies: `none`
- Independent test: `python -m unittest scripts.tests.test_check_task_card -v`
- Rollback boundary: `single governance-only commit`
- Parallel decision: `serial`

## Context

- Governance sources only.

## Verification

- `python -m unittest scripts.tests.test_check_task_card -v`

## Progress

- Done: none
- Current: implementation
- Next: verify
- Blocked by: none
"""


class CheckTaskCardTests(unittest.TestCase):
    def make_tmp_path(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def validate_content(self, content: str) -> list[str]:
        module = load_module()
        return module.validate(write_card(self.make_tmp_path(), content), template=False)

    def test_valid_serial_implementation_task_passes(self) -> None:
        self.assertEqual(self.validate_content(base_implementation_task()), [])

    def test_short_read_only_record_passes_without_implementation_fields(self) -> None:
        self.assertEqual(self.validate_content(base_short_record()), [])

    def test_parallel_requires_disjoint_write_sets_and_evidence(self) -> None:
        content = (
            base_implementation_task()
            .replace("Token indicator used: `400000`", "Token indicator used: `500000`")
            .replace("Parallel decision: `serial`", "Parallel decision: `parallel-approved`")
            .replace(
                "## Context",
                "- Parallel with: `VG-GOV-TEST-IMPL-002`\n"
                "- Parallel peer write set: `docs/codex/AI_DEVELOPMENT_GOVERNANCE.md`\n"
                "- Independence evidence: `none`\n"
                "- Active-agent count after dispatch: `2/2 implementation, 0/2 read-only, 2/4 total`\n\n## Context",
            )
        )
        failures = self.validate_content(content)
        self.assertIn("parallel-approved requires Independence evidence", failures)
        self.assertIn("parallel-approved write sets must be disjoint", failures)

    def test_parallel_cannot_start_after_sixty_percent_token_use(self) -> None:
        content = (
            base_implementation_task()
            .replace("Token indicator used: `400000`", "Token indicator used: `1300000`")
            .replace("Token status: `green`", "Token status: `amber`")
            .replace("Owner notice: `none`", "Owner notice: `required`")
            .replace("Parallel decision: `serial`", "Parallel decision: `parallel-approved`")
            .replace(
                "## Context",
                "- Parallel with: `VG-GOV-TEST-IMPL-002`\n"
                "- Parallel peer write set: `scripts/context-for.py`\n"
                "- Independence evidence: `Disjoint writes, independent tests and rollback.`\n"
                "- Active-agent count after dispatch: `2/2 implementation, 0/2 read-only, 2/4 total`\n\n## Context",
            )
        )
        failures = self.validate_content(content)
        self.assertIn(
            "Token indicator use at or above 60 percent cannot add a parallel implementation agent",
            failures,
        )

    def test_critical_implementation_requires_acceptance_task(self) -> None:
        content = base_implementation_task().replace("Risk level: high", "Risk level: critical")
        failures = self.validate_content(content)
        self.assertIn(
            "critical implementation must name an independent read-only acceptance task",
            failures,
        )

    def test_recovery_requires_closed_previous_owner(self) -> None:
        content = base_implementation_task().replace(
            "## Context",
            "- Recovery from: `impl-agent-0`\n"
            "- Recovered owner status: `blocked`\n\n## Context",
        )
        failures = self.validate_content(content)
        self.assertIn(
            "recovery takeover requires the previous owner to be recorded as closed",
            failures,
        )

    def test_token_eighty_percent_requires_owner_notice(self) -> None:
        content = (
            base_implementation_task()
            .replace("Token indicator used: `400000`", "Token indicator used: `1700000`")
            .replace("Token status: `green`", "Token status: `amber`")
        )
        failures = self.validate_content(content)
        self.assertIn(
            "Token indicator use at or above 80 percent requires Owner notice",
            failures,
        )

    def test_token_hundred_percent_requires_attention(self) -> None:
        content = (
            base_implementation_task()
            .replace("Token indicator used: `400000`", "Token indicator used: `2000000`")
            .replace("Token status: `green`", "Token status: `red`")
            .replace("Owner notice: `none`", "Owner notice: `required`")
        )
        failures = self.validate_content(content)
        self.assertIn(
            "Token indicator use at or above 100 percent requires Status: attention",
            failures,
        )

    def test_attention_and_done_require_status_event_content(self) -> None:
        attention_failures = self.validate_content(
            base_implementation_task().replace("Status: `active`", "Status: `attention`")
        )
        self.assertIn(
            "attention Business status summary must state who needs to do what next using Needs:",
            attention_failures,
        )

        done_failures = self.validate_content(
            base_implementation_task()
            .replace("Status: `active`", "Status: `done`")
            .replace(
                "Business status summary: `Implementation is active on governance simplification.`",
                "Business status summary: `Completed.`",
            )
        )
        self.assertIn(
            "done Business status summary must include Capability:, Evidence: and Next gate:",
            done_failures,
        )

    def test_control_plane_share_cannot_exceed_thirty_percent(self) -> None:
        content = base_implementation_task().replace(
            "Control-plane token used: `90000`",
            "Control-plane token used: `150000`",
        )
        failures = self.validate_content(content)
        self.assertIn(
            "Control-plane token used cannot exceed 30 percent of Token indicator used",
            failures,
        )

    def test_task_template_passes_template_check(self) -> None:
        module = load_module()
        self.assertEqual(module.validate(TASK_TEMPLATE, template=True), [])


if __name__ == "__main__":
    unittest.main()
