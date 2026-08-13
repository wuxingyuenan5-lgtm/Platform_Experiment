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


def base_task_card() -> str:
    return """# Task: Sample Governance Task

Task ID: `VG-GOV-TEST-001`
Issue: `none`
Status: active
Risk level: high
Role: implementation
Agent ID: `impl-agent-1`
Implementation owner: `impl-agent-1`
Branch: `codex/sample-governance`
Worktree: `C:\\worktrees\\sample-governance`
Base commit: `0123456789abcdef0123456789abcdef01234567`
Context Pack: `governance`
Recovery from: `none`
Recovered owner status: `none`
Parallel with: `none`
Parallel peer write set: `none`

## Objective

Validate bounded concurrency governance.

## Protected semantics

- Keep single-writer governance intact.

## Scope

- Included paths/outcomes.
- Explicit non-goals.

## Dispatch concurrency decision

- Write set: `AGENTS.md`; `docs/codex/AI_DEVELOPMENT_GOVERNANCE.md`
- Shared workflow, public contract, migration chain or file set: `none`
- Dependencies: `none`
- Independent test: `python -m pytest scripts/tests/test_check_task_card.py -v`
- Rollback boundary: `single governance-only commit`
- Parallel decision: `serial`
- Acceptance task: `not-required`
- Active-agent count after dispatch: `1/2 implementation, 0/2 read-only, 1/4 total`
- Independence evidence: `not-applicable-serial`

## Context

- Current governance candidate only.

## Verification

- `python -m pytest scripts/tests/test_check_task_card.py -v`

## Progress

- Done: none
- Current: none
- Next: none
- Blocked by: none

## Non-goals

- No business source changes.

## Acceptance

- Validator behaves as declared.

## Stop conditions

- Another writer appears.

## Output contract

- `outcome`
- `changed_files`
- `validations`
- `evidence`
- `contract_impact`
- `unproven_facts`
- `residual_risks`
- `next_gate`
"""


class CheckTaskCardTests(unittest.TestCase):
    def make_tmp_path(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_valid_serial_implementation_task_passes(self) -> None:
        module = load_module()
        failures = module.validate(
            write_card(self.make_tmp_path(), base_task_card()), template=False
        )
        self.assertEqual(failures, [])

    def test_valid_parallel_implementation_task_passes(self) -> None:
        module = load_module()
        content = (
            base_task_card()
            .replace("Parallel with: `none`", "Parallel with: `VG-GOV-TEST-002`")
            .replace("Parallel peer write set: `none`", "Parallel peer write set: `scripts/context-for.py`; `scripts/context-packs.json`")
            .replace("Parallel decision: `serial`", "Parallel decision: `parallel-approved`")
            .replace("Active-agent count after dispatch: `1/2 implementation, 0/2 read-only, 1/4 total`", "Active-agent count after dispatch: `2/2 implementation, 0/2 read-only, 2/4 total`")
            .replace("Independence evidence: `not-applicable-serial`", "Independence evidence: `Disjoint write sets, no unfinished dependencies, independent tests and independent rollback.`")
        )
        failures = module.validate(write_card(self.make_tmp_path(), content), template=False)
        self.assertEqual(failures, [])


    def test_parallel_requires_independence_evidence(self) -> None:
        module = load_module()
        content = (
            base_task_card()
            .replace("Parallel with: `none`", "Parallel with: `VG-GOV-TEST-002`")
            .replace("Parallel peer write set: `none`", "Parallel peer write set: `scripts/context-for.py`")
            .replace("Parallel decision: `serial`", "Parallel decision: `parallel-approved`")
            .replace("Active-agent count after dispatch: `1/2 implementation, 0/2 read-only, 1/4 total`", "Active-agent count after dispatch: `2/2 implementation, 0/2 read-only, 2/4 total`")
            .replace("Independence evidence: `not-applicable-serial`", "Independence evidence: `none`")
        )
        failures = module.validate(write_card(self.make_tmp_path(), content), template=False)
        self.assertIn("parallel-approved requires Independence evidence", failures)


    def test_parallel_rejects_overlapping_write_sets(self) -> None:
        module = load_module()
        content = (
            base_task_card()
            .replace("Parallel with: `none`", "Parallel with: `VG-GOV-TEST-002`")
            .replace("Parallel peer write set: `none`", "Parallel peer write set: `docs/codex/AI_DEVELOPMENT_GOVERNANCE.md`; `scripts/context-for.py`")
            .replace("Parallel decision: `serial`", "Parallel decision: `parallel-approved`")
            .replace("Active-agent count after dispatch: `1/2 implementation, 0/2 read-only, 1/4 total`", "Active-agent count after dispatch: `2/2 implementation, 0/2 read-only, 2/4 total`")
            .replace("Independence evidence: `not-applicable-serial`", "Independence evidence: `Declared independent, but peer write set overlaps.`")
        )
        failures = module.validate(write_card(self.make_tmp_path(), content), template=False)
        self.assertIn("parallel-approved write sets must be disjoint", failures)


    def test_parallel_rejects_shared_contract_or_migration_boundary(self) -> None:
        module = load_module()
        content = (
            base_task_card()
            .replace("Parallel with: `none`", "Parallel with: `VG-GOV-TEST-002`")
            .replace("Parallel peer write set: `none`", "Parallel peer write set: `scripts/context-for.py`")
            .replace("Shared workflow, public contract, migration chain or file set: `none`", "Shared workflow, public contract, migration chain or file set: `governance-authority-shared-boundary`")
            .replace("Parallel decision: `serial`", "Parallel decision: `parallel-approved`")
            .replace("Active-agent count after dispatch: `1/2 implementation, 0/2 read-only, 1/4 total`", "Active-agent count after dispatch: `2/2 implementation, 0/2 read-only, 2/4 total`")
            .replace("Independence evidence: `not-applicable-serial`", "Independence evidence: `Paths differ but shared contract exists.`")
        )
        failures = module.validate(write_card(self.make_tmp_path(), content), template=False)
        self.assertIn(
            "parallel-approved tasks cannot share workflow, contract, migration or file-set ownership",
            failures,
        )


    def test_active_agent_total_cannot_exceed_four(self) -> None:
        module = load_module()
        content = base_task_card().replace(
            "Active-agent count after dispatch: `1/2 implementation, 0/2 read-only, 1/4 total`",
            "Active-agent count after dispatch: `2/2 implementation, 3/2 read-only, 5/4 total`",
        )
        failures = module.validate(write_card(self.make_tmp_path(), content), template=False)
        self.assertTrue(any("active-agent counts" in failure for failure in failures))

    def test_implementation_agent_count_cannot_exceed_two(self) -> None:
        module = load_module()
        content = base_task_card().replace(
            "Active-agent count after dispatch: `1/2 implementation, 0/2 read-only, 1/4 total`",
            "Active-agent count after dispatch: `3/2 implementation, 0/2 read-only, 3/4 total`",
        )
        failures = module.validate(write_card(self.make_tmp_path(), content), template=False)
        self.assertTrue(any("active-agent counts" in failure for failure in failures))

    def test_read_only_agent_count_cannot_exceed_two(self) -> None:
        module = load_module()
        content = base_task_card().replace(
            "Active-agent count after dispatch: `1/2 implementation, 0/2 read-only, 1/4 total`",
            "Active-agent count after dispatch: `1/2 implementation, 3/2 read-only, 4/4 total`",
        )
        failures = module.validate(write_card(self.make_tmp_path(), content), template=False)
        self.assertTrue(any("active-agent counts" in failure for failure in failures))

    def test_total_agent_count_must_match_category_counts(self) -> None:
        module = load_module()
        content = base_task_card().replace(
            "Active-agent count after dispatch: `1/2 implementation, 0/2 read-only, 1/4 total`",
            "Active-agent count after dispatch: `1/2 implementation, 1/2 read-only, 1/4 total`",
        )
        failures = module.validate(write_card(self.make_tmp_path(), content), template=False)
        self.assertTrue(any("active-agent counts" in failure for failure in failures))


    def test_read_only_roles_cannot_claim_write_access(self) -> None:
        module = load_module()
        content = (
            base_task_card()
            .replace("Role: implementation", "Role: acceptance")
            .replace("Implementation owner: `impl-agent-1`", "Implementation owner: `none`")
            .replace("Branch: `codex/sample-governance`", "Branch: `none`")
            .replace("Worktree: `C:\\worktrees\\sample-governance`", "Worktree: `none`")
            .replace("Base commit: `0123456789abcdef0123456789abcdef01234567`", "Base commit: `none`")
        )
        failures = module.validate(write_card(self.make_tmp_path(), content), template=False)
        self.assertIn(
            "read-only roles must declare Write set: none (read-only)", failures
        )
        self.assertIn("read-only roles must use Parallel decision: read-only", failures)


    def test_implementation_requires_owner_branch_worktree_and_base_commit(self) -> None:
        module = load_module()
        content = (
            base_task_card()
            .replace("Implementation owner: `impl-agent-1`", "Implementation owner: `none`")
            .replace("Branch: `codex/sample-governance`", "Branch: `none`")
            .replace("Worktree: `C:\\worktrees\\sample-governance`", "Worktree: `none`")
            .replace("Base commit: `0123456789abcdef0123456789abcdef01234567`", "Base commit: `none`")
        )
        failures = module.validate(write_card(self.make_tmp_path(), content), template=False)
        self.assertIn(
            "implementation task requires a concrete Implementation owner", failures
        )
        self.assertIn("implementation task requires a concrete Branch", failures)
        self.assertIn("implementation task requires a concrete Worktree", failures)
        self.assertIn("implementation task requires a concrete Base commit", failures)


    def test_implementation_branch_must_use_codex_prefix(self) -> None:
        module = load_module()
        content = base_task_card().replace(
            "Branch: `codex/sample-governance`",
            "Branch: `feature/sample-governance`",
        )
        failures = module.validate(write_card(self.make_tmp_path(), content), template=False)
        self.assertIn("implementation Branch must start with codex/", failures)


    def test_critical_implementation_requires_acceptance_task(self) -> None:
        module = load_module()
        content = (
            base_task_card()
            .replace("Risk level: high", "Risk level: critical")
            .replace("Acceptance task: `not-required`", "Acceptance task: `none`")
        )
        failures = module.validate(write_card(self.make_tmp_path(), content), template=False)
        self.assertIn(
            "critical implementation must name an independent read-only acceptance task",
            failures,
        )


    def test_recovery_takeover_requires_closed_previous_owner(self) -> None:
        module = load_module()
        content = (
            base_task_card()
            .replace("Recovery from: `none`", "Recovery from: `impl-agent-0`")
            .replace("Recovered owner status: `none`", "Recovered owner status: `blocked`")
        )
        failures = module.validate(write_card(self.make_tmp_path(), content), template=False)
        self.assertIn(
            "recovery takeover requires the previous owner to be recorded as closed",
            failures,
        )


    def test_missing_required_field_fails(self) -> None:
        module = load_module()
        content = base_task_card().replace("Task ID: `VG-GOV-TEST-001`\n", "")
        failures = module.validate(write_card(self.make_tmp_path(), content), template=False)
        self.assertIn("missing required field: Task ID", failures)


    def test_task_template_passes_template_check(self) -> None:
        module = load_module()
        failures = module.validate(TASK_TEMPLATE, template=True)
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
