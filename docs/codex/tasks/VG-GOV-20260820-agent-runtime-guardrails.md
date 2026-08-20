# Task: Add Project-Scoped Codex Agent Runtime Guardrails
Task ID: `VG-GOV-20260820-agent-runtime-guardrails`
Issue: `#none`
Status: `attention`
Last transition at: `2026-08-20 12:10 Asia/Shanghai`
Owner notice: `sent`
Business status summary: `Needs: trustworthy Token snapshot remains unavailable, so this implementation truthfully stays in attention while the isolated worktree guardrail changes proceed under the current Owner authorization.`
Current leaf task/agent ID: `codex-main`
Risk level: `high`
Role: `implementation`
Agent ID: `codex-main`
Context Pack: `governance`
Token baseline: `unavailable`
Token current: `unavailable`
Token delta: `unavailable`
Control-plane token delta: `unavailable`
Token budget: `2000000`
Token status: `unavailable`

## Objective
Add minimal project-scoped Codex configuration, four narrow agent profiles, startup/tool guardrail hooks, bounded tests, and only the governance text needed to route future tasks without relying on long chat history.

## Implementation fields
- Implementation owner: `codex-main`
- Branch: `codex/vg-agent-runtime-guardrails`
- Worktree: `<workspace-root>\.codex\worktrees\vg-0111-recovery`
- Base commit: `d665eed8f7092af22b1f986827a7064a086d9ce1`

## Protected semantics
- Do not modify 0.11.1 business source, frontend source, runtime services, database code, or external-state behavior.
- Do not touch the protected shared root checkout for any write, checkout, reset, restore, clean, stage, commit, move, or delete action.
- Keep all Live Write, Kill Switch, credentials, external connections, and real-order capabilities unchanged and unauthorized.
- Scope writes to project-level Codex configuration, hooks, related bounded tests, this task card, and minimal governance authority sync only.
- Use one implementation owner only. No parallel implementation and no subagents.
- Hook guardrails may enforce tool and Git safety, but may not claim Codex runtime Token hard limiting.
- Token snapshot fields remain `unavailable` unless a trustworthy external snapshot exists.

## Scope
- Add `.codex/config.toml`.
- Add exactly four project-scoped custom agent files under `.codex/agents/`.
- Add `.codex/hooks.json`, `.codex/hooks/session_start.py`, and `.codex/hooks/pre_tool_use.py`.
- Add bounded tests for config parsing, agent files, hook context generation, and hook blocking behavior.
- Apply only the minimum governance wording changes required in `AGENTS.md` and `docs/codex/AI_DEVELOPMENT_GOVERNANCE.md`.
- Non-goals: new agent platform services, monitoring agents, task databases, Token daemons, business development, frontend changes, database changes, runtime behavior changes, external-state activity.

## Dispatch concurrency decision
- Write set: `.codex/config.toml`; `.codex/agents/`; `.codex/hooks.json`; `.codex/hooks/`; `scripts/tests/`; `AGENTS.md`; `docs/codex/AI_DEVELOPMENT_GOVERNANCE.md`; `docs/codex/tasks/VG-GOV-20260820-agent-runtime-guardrails.md`; `docs/superpowers/plans/`.
- Shared workflow, public contract, migration chain or file set: `repository governance and project-scoped Codex runtime controls`.
- Dependencies: `none`
- Independent test: `python -m unittest scripts.tests.test_codex_runtime_guardrails -v`
- Rollback boundary: `single isolated governance/config branch with one final immutable commit`
- Parallel decision: `serial`

## Context
- `docs/codex/0.11.1-program.md`
- Owner authorization delta in pasted attachment `41aa46ea-4481-4a70-898d-b0b7098bde5b`
- Official OpenAI Codex docs for config, subagents, and hooks

## Verification
- `python -m unittest scripts.tests.test_codex_runtime_guardrails -v`
- `python scripts/context-for.py governance --json`
- `python scripts/check-task-card.py docs/codex/tasks/VG-GOV-20260820-agent-runtime-guardrails.md`
- `python scripts/check-task-card.py --check-template docs/codex/task-template.md`
- `git diff --check`
- `python scripts/check-version-consistency.py`
- `python scripts/check-repository-structure.py`
- `python scripts/check-documentation-consistency.py`

## Progress
- Done: isolated worktree baseline re-verified at `d665eed8f7092af22b1f986827a7064a086d9ce1`; branch `codex/vg-agent-runtime-guardrails` created in the authorized worktree only.
- Current: writing bounded tests first for project-scoped Codex config, agent profiles, and hook guardrails.
- Next: implement `.codex` files, run bounded validation, then commit.
- Blocked by: none
