# Platform Agent Rules

This repository is the engineering source for Variable-Global.

## Startup and context routing

For every task, read `AGENTS.md`, `docs/codex/current-state.md`, run `python scripts/context-for.py <pack>`, then read the Pack required files and the current Issue or task card before work. Read optional files only when a concrete question requires them; do not use broad repository scans for orientation. Read the nearest module `AGENTS.md` before entering that module.

`docs/codex/AI_DEVELOPMENT_GOVERNANCE.md` owns the permanent role model, task protocol, authority hierarchy, task closure and Context Pack maintenance rules. `scripts/context-packs.json` and `scripts/context-for.py` route stable task types to bounded context and checks.

## Safety boundaries

- Deployable subjects are `platform-web`, `platform-api` and `execution-runtime`; Platform API remains a modular monolith unless an approved architecture decision says otherwise.
- Venue SDKs and order side effects belong to `execution-runtime`; Platform API uses versioned contracts. Preserve Decimal values and timezone-aware timestamps at financial boundaries.
- Live Write is disabled by default. Kill Switch, idempotency and Result Unknown semantics are protected. The narrow 0.11.1 local founder-owned-test-account exception remains governed only by current state, acceptance criteria and the live-acceptance runbook; it never expands to client funds, multi-person operation, unattended trading, long-lived Live Write, production deployment, or funds/symbols/concurrency expansion.
- Do not infer external connectivity, account state, deployment or production facts from repository files or CI.

## Single implementation owner

Every workflow has at most one implementation agent with file-modification authority. Investigation, review and acceptance agents default to read-only. Work on a branch and pull request; preserve public contracts unless explicitly authorized.

## Validation

Run the Pack checks plus `git diff --check`, `python scripts/context-for.py --check-budgets --json`, `python scripts/check-version-consistency.py`, `python scripts/check-repository-structure.py`, and `python scripts/check-documentation-consistency.py` when applicable.
