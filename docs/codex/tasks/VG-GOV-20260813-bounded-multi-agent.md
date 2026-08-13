# Task: Bounded Multi-Agent Governance Retrofit

Task ID: `VG-GOV-20260813-BOUNDED-CONCURRENCY`
Issue: `none`
Status: active
Risk level: high
Role: implementation
Agent ID: `codex-temp-impl-20260813-governance`
Implementation owner: `codex-temp-impl-20260813-governance`
Branch: `codex/project-ai-governance-bootstrap`
Worktree: `<workspace-root>`
Base commit: `0ff599c62c660fe3e87a91845ab345e2c989b3dd`
Context Pack: `governance`
Recovery from: `previous-sidebar-governance-candidate (identity unavailable; owner instructed single current writer takeover)`
Recovered owner status: `closed`
Parallel with: `none`
Parallel peer write set: `none`

## Objective

Re-audit and finish the uncommitted bounded multi-agent governance candidate so repository authorities, task cards, Context Packs and the task-card validator enforce single-writer-per-workflow and bounded parallelism without claiming Codex runtime hard limits.

## Protected semantics

- Do not change executable trading behavior, Live Write boundaries, external connectivity assumptions or production claims.
- Do not modify protected frontend files or `docs/codex/AI_DEVELOPMENT_STAGE_RETROSPECTIVE.md`.
- Do not represent task-card declarations as a runtime-enforced Codex agent counter.

## Scope

- Included paths and outcomes:
  - `AGENTS.md`
  - `docs/codex/AI_DEVELOPMENT_GOVERNANCE.md`
  - `docs/codex/task-template.md`
  - `.github/ISSUE_TEMPLATE/engineering-task.yml`
  - `scripts/context-for.py`
  - `scripts/context-packs.json`
  - `scripts/check-task-card.py`
  - `scripts/tests/test_check_task_card.py`
  - this task card
- Explicit non-goals:
  - business source changes
  - Codex global config changes
  - runtime multi-agent enforcement outside repository declarations and checks
  - deployment, credentials, external accounts, Live Write, push or PR creation

## Dispatch concurrency decision

- Write set: `AGENTS.md`; `docs/codex/AI_DEVELOPMENT_GOVERNANCE.md`; `docs/codex/task-template.md`; `.github/ISSUE_TEMPLATE/engineering-task.yml`; `scripts/context-for.py`; `scripts/context-packs.json`; `scripts/check-task-card.py`; `scripts/tests/test_check_task_card.py`; `this task card`
- Shared workflow, public contract, migration chain or file set: `repository governance authorities and task-card validation`
- Dependencies: `none; candidate already exists in working tree and must be re-audited before commit`
- Independent test: `project-configured Python -m unittest scripts.tests.test_check_task_card -v`
- Rollback boundary: `single governance-only commit on current branch; revert that commit if needed`
- Parallel decision: `serial`
- Acceptance task: `not-required`
- Active-agent count after dispatch: `1/2 implementation, 0/2 read-only, 1/4 total`
- Independence evidence: `not-applicable-serial`

## Context

- Candidate provenance is an uncommitted prior sidebar-generated governance draft, not a validated result from this agent.
- This agent is responsible for re-audit, validator completion and immutable commit formation.
- If another active writer is discovered on the same governance candidate, work stops rather than merging concurrent edits.

## Verification

- project-configured Python -m unittest scripts.tests.test_check_task_card -v
- project-configured Python scripts/check-task-card.py --check-template docs/codex/task-template.md
- project-configured Python scripts/check-task-card.py <this-task-card>
- `git diff --check`
- project-configured Python scripts/context-for.py governance --json
- project-configured Python scripts/context-for.py --check-budgets --json
- project-configured Python scripts/check-version-consistency.py
- project-configured Python scripts/check-repository-structure.py
- project-configured Python scripts/check-documentation-consistency.py

## Progress

- Done: root authorities, current state, governance pack, retrospective, branch status and current governance diff reviewed.
- Current: task card established; validator gaps and authority/template inconsistencies are being converted into tests and implementation.
- Next: add failing validator tests, tighten `check-task-card.py`, then align authorities and templates to the validated contract.
- Blocked by: none

## Non-goals

- Rewriting unrelated Context Packs
- Modifying protected frontend work
- Claiming runtime enforcement of the fifth agent limit

## Acceptance

- Task card validates and accurately records takeover context.
- Validator covers bounded-concurrency relationship failures named in the task brief.
- Governance authorities, template and issue intake are consistent with the validator and with single-writer-per-workflow semantics.
- `governance` Pack remains within budget and budget-check output distinguishes pre-existing over-budget packs from this work.
- Only allowed governance files are staged and committed.

## Stop conditions

- Another writer is found modifying the same governance candidate.
- Existing candidate changes cannot be distinguished from unrelated user work.
- Required change escapes the allowed write set.
- Any step would require deleting, resetting, stashing or overwriting existing files.
- Validation would require claiming Codex runtime hard concurrency enforcement.
- `governance` Pack goes over budget and cannot be repaired within the allowed files.

## Output contract

- `outcome`
- `changed_files`
- `validations`
- `evidence`
- `contract_impact`
- `unproven_facts`
- `residual_risks`
- `next_gate`
