# Task: Close Repository Governance To A Single Local Mainline
Task ID: `VG-GOV-20260820-single-mainline`
Issue: `#none`
Status: `attention`
Last transition at: `2026-08-20 18:00 Asia/Shanghai`
Owner notice: `sent`
Business status summary: `Needs: trustworthy Token snapshots are unavailable, so repository rules require attention. Capability: governance now defaults to Local single-writer work on codex/platform-main. Evidence: immutable safety tag and governance commit in the candidate worktree. Next gate: synchronize the dirty shared root only after an owner-approved no-loss procedure.`
Current leaf task/agent ID: `none`
Risk level: `high`
Role: `implementation`
Agent ID: `codex-main`
Context Pack: `governance`
Token baseline: `unavailable`
Token current: `unavailable`
Token delta: `unavailable`
Control-plane token delta: `unavailable`
Token budget: `8000`
Token status: `unavailable`

## Objective
Make the repository's durable delivery contract single-mainline, single-writer and Local-first without changing business behavior or touching the dirty shared root.

## Implementation fields
- Implementation owner: `codex-main`
- Mode: `Local`
- Branch/worktree exception: `high-risk recovery isolation; closed after commit`
- Branch: `codex/platform-main`
- Worktree: `<workspace-root>/.codex/worktrees/vg-0111-recovery`
- Base commit: `0e0079da344ab8e4aebbd763667075efdd4c53a8`

## Protected semantics
- Preserve all shared-root staged, tracked and untracked user changes.
- Do not modify business source, external state, credentials, deployment or Live Write behavior.
- Hooks remain optional and cannot be a runtime prerequisite.

## Scope
- Included: governance authorities, task template, Context Pack concurrency declarations, Local-first Codex defaults and immutable close evidence.
- Explicit non-goals: shared-root synchronization, bulk deletion, branch/worktree checkout or restore, business implementation and external operations.

## Dispatch concurrency decision
- Write set: `AGENTS.md; .codex/config.toml; .codex/agents/platform-worker.toml; docs/codex/AI_DEVELOPMENT_GOVERNANCE.md; docs/codex/0.11.1-program.md; docs/codex/current-state.md; docs/codex/task-template.md; docs/codex/tasks/VG-GOV-20260820-single-mainline.md; scripts/context-packs.json`
- Shared workflow, public contract, migration chain or file set: `repository governance authority`
- Dependencies: `none`
- Independent test: `governance Pack checks and repository consistency checks`
- Rollback boundary: `immutable safety tag at 0e0079da344ab8e4aebbd763667075efdd4c53a8`
- Parallel decision: `serial`
- Acceptance task: `none; owner-requested single-agent closure`
- Active-agent count after dispatch: `1/1 implementation, 0/1 read-only, 1/2 total`

## Context
- `docs/codex/AI_DEVELOPMENT_GOVERNANCE.md`
- `docs/codex/0.11.1-program.md`
- Shared-root safety inventory supplied by owner: `84 staged, 90 tracked worktree, 9536 untracked; candidate mismatch confirmed`

## Verification
- `python scripts/context-for.py governance --json`
- `python scripts/context-for.py --check-budgets --json`
- Governance Pack checks and repository consistency checks
- `git diff --check`

## Progress
- Done: candidate worktree confirmed clean at `0e0079d`; shared root was not modified.
- Done: Local single-mainline rules, one-writer concurrency, optional hooks and exception-only worktrees written into repository authorities.
- Done: `codex/platform-main` and immutable safety tag created; duplicate temporary refs closed after reachability verification.
- Blocked by: shared-root synchronization is not proven safe and remains the sole next gate.
