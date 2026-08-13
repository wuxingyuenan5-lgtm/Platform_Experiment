# Task: Governance Cold-Start Contract and Final Compression
Task ID: `VG-GOV-20260813-COLD-START`
Issue: `none`
Status: `done`
Last transition at: `2026-08-13 23:05 CST`
Owner notice: `required`
Business status summary: `Capability: repository cold-start governance contract and final compression completed. Evidence: new governance-only commit after 50f2165 plus validator, budget and consistency checks. Next gate: owner reviews the closing governance receipt and accepts the remaining Codex runtime notification limitation.`
Current leaf task/agent ID: `codex-temp-impl-20260813-governance`
Risk level: high
Role: implementation
Agent ID: `codex-temp-impl-20260813-governance`
Context Pack: `governance`
Token baseline: `300000`
Token current: `360000`
Token delta: `60000`
Control-plane token delta: `18000`
Token budget: `2000000`
Token status: `green`
## Objective
Move long-term role recovery from chat instructions into repository authority, compress governance text and validator weight, and close the temporary governance implementation line without starting 0.11.1 business development.

## Implementation fields
- Implementation owner: `codex-temp-impl-20260813-governance`
- Branch: `codex/project-ai-governance-bootstrap`
- Worktree: `<workspace-root>`
- Base commit: `50f216574f5a0b695e8e7ff988bee2e1f5b0b5fb`

## Protected semantics
- Do not modify business source, the six protected frontend files or `docs/codex/AI_DEVELOPMENT_STAGE_RETROSPECTIVE.md`.
- Do not amend or rewrite `50f216574f5a0b695e8e7ff988bee2e1f5b0b5fb`.
- Do not enable external connections, credentials, Live Write or 0.11.1 business implementation.

## Scope
- Included: `AGENTS.md`, `docs/codex/AI_DEVELOPMENT_GOVERNANCE.md`, `docs/codex/0.11.1-program.md`, `docs/codex/task-template.md`, this task card, `scripts/check-task-card.py`, `scripts/tests/test_check_task_card.py`
- Non-goals: business development for Platform 0.11.1; unrelated over-budget Pack repair; `.codex/worktrees` history mirror cleanup; new governance roles, polling agents or runtime integrations

## Dispatch concurrency decision
- Write set: `AGENTS.md`; `docs/codex/AI_DEVELOPMENT_GOVERNANCE.md`; `docs/codex/0.11.1-program.md`; `docs/codex/task-template.md`; `docs/codex/tasks/VG-GOV-20260813-cold-start-contract.md`; `scripts/check-task-card.py`; `scripts/tests/test_check_task_card.py`
- Shared workflow, public contract, migration chain or file set: `repository governance authorities and task-card validation`
- Dependencies: `none`
- Independent test: `python -m unittest scripts.tests.test_check_task_card -v`
- Rollback boundary: `single governance-only commit after 50f2165`
- Parallel decision: `serial`

## Context
- `docs/codex/current-state.md`
- `docs/codex/0.11.1-program.md`
- prior governance task cards under `docs/codex/tasks/`

## Verification
- `python -m unittest scripts.tests.test_check_task_card -v`
- `python scripts/check-task-card.py --check-template docs/codex/task-template.md`
- `python scripts/check-task-card.py docs/codex/tasks/VG-GOV-20260813-cold-start-contract.md`
- `git diff --check`
- `python scripts/context-for.py governance --json`
- `python scripts/context-for.py --check-budgets --json`
- `python scripts/check-version-consistency.py`
- `python scripts/check-repository-structure.py`
- `python scripts/check-documentation-consistency.py`
