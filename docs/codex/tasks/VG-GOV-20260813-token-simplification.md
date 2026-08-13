# Task: Governance Token and Status Simplification

Task ID: `VG-GOV-20260813-SIMPLIFY-GOVERNANCE`
Issue: `none`
Status: `done`
Last transition at: `2026-08-13 22:10 CST`
Owner notice: `required`
Business status summary: `Capability: governance simplification and minimal status interface completed. Evidence: immutable follow-up commit after 5c6fce0 plus validator, template and governance checks. Next gate: owner review of the new governance-only commit and residual Codex runtime notification limitation.`
Current leaf task/agent ID: `codex-temp-impl-20260813-governance`
Risk level: high
Role: implementation
Agent ID: `codex-temp-impl-20260813-governance`
Context Pack: `governance`
Token indicator budget: `2000000`
Token indicator used: `220000`
Token status: `green`
Control-plane token used: `60000`

## Objective

Reduce governance Token and coordination overhead from commit `5c6fce029d1811600d89633d19af3bd9939a236a` without changing business logic, while adding a minimal status-event interface.

## Implementation fields

- Implementation owner: `codex-temp-impl-20260813-governance`
- Branch: `codex/project-ai-governance-bootstrap`
- Worktree: `<workspace-root>`
- Base commit: `5c6fce029d1811600d89633d19af3bd9939a236a`

## Protected semantics

- Do not change executable trading behavior, permission boundaries, database behavior, external connectivity assumptions or Live Write safety.
- Do not modify the six protected frontend files, `docs/codex/AI_DEVELOPMENT_STAGE_RETROSPECTIVE.md` or business source.
- Do not amend or rewrite commit `5c6fce029d1811600d89633d19af3bd9939a236a`.

## Scope

- Included paths/outcomes:
  - `AGENTS.md`
  - `docs/codex/AI_DEVELOPMENT_GOVERNANCE.md`
  - `docs/codex/task-template.md`
  - `.github/ISSUE_TEMPLATE/engineering-task.yml`
  - `scripts/context-for.py`
  - `scripts/context-packs.json`
  - `scripts/check-task-card.py`
  - `scripts/tests/test_check_task_card.py`
  - `docs/codex/tasks/VG-GOV-20260813-token-simplification.md`
- Explicit non-goals:
  - business source changes
  - new governance roles or runtime agents
  - `.codex/worktrees` history-mirror cleanup
  - over-budget repair for the six pre-existing Context Packs
  - external accounts, credentials, Live Write, push or PR creation

## Dispatch concurrency decision

- Write set: `AGENTS.md`; `docs/codex/AI_DEVELOPMENT_GOVERNANCE.md`; `docs/codex/task-template.md`; `.github/ISSUE_TEMPLATE/engineering-task.yml`; `scripts/context-for.py`; `scripts/context-packs.json`; `scripts/check-task-card.py`; `scripts/tests/test_check_task_card.py`; `docs/codex/tasks/VG-GOV-20260813-token-simplification.md`
- Shared workflow, public contract, migration chain or file set: `repository governance authorities and task-card validation`
- Dependencies: `none`
- Independent test: `python -m unittest scripts.tests.test_check_task_card -v`
- Rollback boundary: `single governance-only commit after 5c6fce0`
- Parallel decision: `serial`

## Context

- Prior bounded-concurrency task card at `docs/codex/tasks/VG-GOV-20260813-bounded-multi-agent.md`
- Validator and tests at `scripts/check-task-card.py` and `scripts/tests/test_check_task_card.py`

## Verification

- `python -m unittest scripts.tests.test_check_task_card -v`
- `python scripts/check-task-card.py --check-template docs/codex/task-template.md`
- `python scripts/check-task-card.py docs/codex/tasks/VG-GOV-20260813-token-simplification.md`
- `git diff --check`
- `python scripts/context-for.py governance --json`
- `python scripts/context-for.py --check-budgets --json`
- `python scripts/check-version-consistency.py`
- `python scripts/check-repository-structure.py`
- `python scripts/check-documentation-consistency.py`

## Progress

- Done: `5c6fce0` governance baseline reviewed and protected-file boundaries confirmed.
- Current: authority, template, validator and test-set simplification in progress.
- Next: implement conditional validation and verify governance Pack budget remains within limits.
- Blocked by: none
