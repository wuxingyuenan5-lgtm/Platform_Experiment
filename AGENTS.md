# Project Agent Rules

## Start Here

- `docs/codex/current-state.md` is the sole repository document for current version, branch, phase and known limits.
- `docs/codex/context-map.md` routes a task to the smallest sufficient reading pack.
- `docs/architecture/OWNERSHIP.md` is the canonical business-rule, code and data ownership catalog.
- `docs/contracts/README.md` indexes current domain contracts; load only the contract required by the task.
- After these root rules, read the nearest module `AGENTS.md`, then only directly affected source files and tests.
- `docs/codex/CURRENT_CONTEXT.md` is a compatibility pointer, not an authority.
- GitHub PR #141 owns volatile HEAD, CI and review evidence for the active Platform 0.9.3 workstream.

## Protected Invariants

- Keep Browser Session authority separate from API-Key and Live Write authority.
- Preserve CSRF and Origin validation, role scope, last-CEO protection and member-data isolation.
- Preserve Decimal money, Financial Fact, PnL, NAV, formal accounting, reconciliation and immutable migration semantics.
- Preserve Kill Switch, two-person approval, Live Write disabled by default, idempotency, Market/FOK/PostOnly/TP-SL, Result Unknown, EOD and Last Known Good behavior.
- Do not disable TLS, security checks, type checks or critical tests to make a change pass.
- Keep Platform API and Platform Execution Runtime as separate safety boundaries.
- Do not modify or merge `main` without explicit owner approval.

## Scope Control

- For a narrow UI fix, read the target component, its direct owner and necessary styles; do not scan the repository.
- For a business-domain change, start from the owning route/service/schema or composable/API client and its direct tests.
- For Trading, Execution, Risk, Accounting, authentication, migrations, Runtime contracts or Live behavior, use the Critical workstream and the active task packet.
- Plan, Handoff, Audit, Superseded, release-history, generated, lock and unrelated module material is excluded by default.
- Do not create a new abstraction, interface, factory or permanent document unless it removes a demonstrated second responsibility or repeated fact.

## Product UI Boundary

- Preserve the existing navigation, layout, information hierarchy, workflows, typography, spacing, colors and responsive behavior unless an explicit product change is approved.
- Do not add engineering explanations, validation panels or debug state to product pages.
- Reuse maintained product components and the existing visual language.

## Default Checks

Use the smallest check set that proves the change, then expand for cross-domain or safety-sensitive work.

```powershell
python scripts/check-version-consistency.py
python scripts/check-codex-context.py
python scripts/check-repository-structure.py
python scripts/check-documentation-consistency.py
```

Module commands are owned by the nearest module `AGENTS.md`. The frontend package-manager authority is recorded in `docs/codex/current-state.md`.

## File Safety

- Do not batch-delete files or directories.
- Delete only reviewed paths after proving they are unused and recording rollback evidence.
- Keep directory renames separate from behavioral refactors.
- Preserve third-party licenses, attribution, compatibility fixtures and historical records.
