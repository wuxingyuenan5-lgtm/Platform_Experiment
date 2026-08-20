# Platform Agent Rules

This repository is the engineering source for Variable-Global.

## Startup and context routing

For every task, read `AGENTS.md`, `docs/codex/current-state.md`, run `python scripts/context-for.py <pack>`, then read the Pack required files and the current Issue or task card before work. Use the project/environment-configured Python interpreter. If `python` is not on `PATH`, use the platform-provided configured dependency runtime; in Codex desktop, load workspace dependencies first and use the returned Python absolute path. Do not install another interpreter or bypass the Pack. If no configured interpreter can be resolved, stop and escalate. Read optional files only when a concrete question requires them; do not use broad repository scans for orientation. Read the nearest module `AGENTS.md` before entering that module.

`docs/codex/AI_DEVELOPMENT_GOVERNANCE.md` owns the permanent role model, task protocol, authority hierarchy, task closure and Context Pack maintenance rules. `scripts/context-packs.json` and `scripts/context-for.py` route stable task types to bounded context and checks.

Long-term governance roles must read their role contract in `docs/codex/AI_DEVELOPMENT_GOVERNANCE.md` and the current version control file before work. Project-scoped `.codex/config.toml`, `.codex/agents/` and `.codex/hooks.json` are optional local conveniences only; hooks are disabled by default and must never be a prerequisite for project operation. They do not replace repository authority. Chat startup cannot override repository role boundaries, and new authorization or working agreements must be written into a task card or version control file before they carry forward.

## Safety boundaries

- Deployable subjects are `platform-web`, `platform-api` and `execution-runtime`; Platform API remains a modular monolith unless an approved architecture decision says otherwise.
- Venue SDKs and order side effects belong to `execution-runtime`; Platform API uses versioned contracts. Preserve Decimal values and timezone-aware timestamps at financial boundaries.
- Live Write is disabled by default. Kill Switch, idempotency and Result Unknown semantics are protected. The narrow 0.11.1 local founder-owned-test-account exception remains governed only by current state, acceptance criteria and the live-acceptance runbook; it never expands to client funds, multi-person operation, unattended trading, long-lived Live Write, production deployment, or funds/symbols/concurrency expansion.
- Do not infer external connectivity, account state, deployment or production facts from repository files or CI.

## Default delivery shape

- The durable default is Local execution on `codex/platform-main`, with one implementation writer and serial work.
- Do not create a task branch or linked worktree for ordinary work. Use a worktree only for explicitly approved high-risk recovery or separately proven parallel writes; close it after the task.
- Read-only review does not create a branch or worktree. No second implementation agent is created by default or to consume capacity.

## Bounded multi-agent concurrency

The project-wide default is one active implementation writer in Local mode. This is the normal operating limit, not a target to expand. Each workflow, contract, migration chain or shared file set has one implementation owner. Record the write set and dependencies before work. A linked worktree or task branch requires explicit high-risk recovery approval or evidence of an independently necessary parallel write; otherwise remain on `codex/platform-main` and work serially.

Critical work uses one implementer plus acceptance. Findings return to owner. Close failed owners before takeover. Investigators are read-only. Do not create a standing reporting or monitoring agent; wake parent roles only on real task-card state transitions or explicit Owner gates.

Close with only `outcome`, `changed_files`, `validations`, `evidence`, `contract_impact`, `unproven_facts`, `residual_risks` and `next_gate`. Do not return full source, complete diffs or long logs by default.

## Validation

Run the Pack checks plus `git diff --check`, `python scripts/context-for.py --check-budgets --json`, `python scripts/check-version-consistency.py`, `python scripts/check-repository-structure.py`, and `python scripts/check-documentation-consistency.py` when applicable.
