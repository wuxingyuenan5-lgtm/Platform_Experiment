# Project Agent Rules

## Start Here

- `docs/codex/current-state.md` is the sole repository document for current engineering state.
- `docs/codex/context-map.md` routes a task to a bounded reading pack; use it when the target domain is not already obvious.
- `docs/architecture/OWNERSHIP.md` is the canonical code, data and boundary ownership catalog.
- After the root rules, read the nearest module `AGENTS.md`, then only the directly affected source files and tests.
- `docs/codex/CURRENT_CONTEXT.md` is a compatibility pointer, not an authority.
- GitHub Issue #136 and Draft PR #138 own live branch, HEAD, CI and review status. Do not copy live progress into new permanent documents.

## Protected Invariants

- Keep Browser Session authority separate from API-Key and Live Write authority.
- Preserve CSRF and Origin validation, role scope, last-CEO protection and member-data isolation.
- Preserve Decimal money, Financial Fact, PnL, NAV, formal accounting, reconciliation and immutable migration semantics.
- Preserve Kill Switch, two-person approval, Live Write disabled by default, idempotency, Market/FOK/PostOnly/TP-SL, Result Unknown, EOD and Last Known Good behavior.
- Do not disable TLS, security checks, type checks or critical tests to make a change pass.
- Keep Platform API and Execution Runtime as separate safety boundaries.
- Do not modify or merge `main` without explicit owner approval.

## Scope Control

- For a narrow UI fix, read the target component, its direct owner and necessary styles; do not scan the repository.
- For a business-domain change, start from the domain route/service/schema or composable/API client and its direct tests.
- For trading execution, risk, accounting, authentication, migrations, Runtime contracts or Live behavior, use the Critical workstream and the active task packet.
- Historical plans, closed task packets, changelogs, generated files, lock files and unrelated modules are excluded by default.
- Do not create a new abstraction, interface, factory or permanent document unless it removes a demonstrated second responsibility or repeated fact.

## Product UI Boundary

- Preserve the existing navigation, layout, information hierarchy, main workflows, typography, spacing, colors and responsive behavior unless an explicit defect or product change is approved.
- Do not add engineering explanations, validation panels or debug state to product pages.
- Reuse the user-designed product components and existing visual language.

## Default Checks

Use the smallest check set that proves the change, then expand for cross-domain or safety-sensitive work.

```powershell
python scripts/check-version-consistency.py
python scripts/check-codex-context.py
python scripts/check-repository-structure.py
python scripts/check-documentation-consistency.py
```

Module commands are owned by the nearest module `AGENTS.md`. Frontend package-manager authority is `admin-risk/package.json#packageManager` until the directory-renaming phase is completed.

## File Safety

- Do not batch-delete files or directories.
- Delete only reviewed, explicit paths after proving they are unused and recording rollback evidence.
- Keep directory renames separate from behavioral refactors.
- Preserve third-party licenses, attribution and legitimate fixtures or historical records.
