# Project Agent Rules

## Baseline

- Current product version: `0.9.1`.
- Current uploaded main baseline: `a4e22021c71cf5cd703cb0bc35676ff5adbfec36`.
- Current integration branch: `feature/issue-117-platform-0-9-1`; do not merge it into `main` without explicit user approval.
- Frontend port: `4373`.
- Platform Backend port: `8000`.
- Execution Runtime port: `8100`.
- Use `npx pnpm@9.15.9 ...` for frontend commands.
- Canonical ownership: `docs/architecture/OWNERSHIP.md`.

## Scope Control

- For UI point fixes, read only the target component, direct parent component, and necessary styles.
- For trading execution changes, read the execution component, lifecycle API, exit plan API, and related types.
- For position, account, and observability changes, read the position table component, observability API, and snapshot types.
- For user-system changes, preserve Browser Session, CSRF/Origin, business-role scope, member data isolation and API-Key/Live Write separation.
- Do not scan the whole repository for narrow UI edits.

## Product UI Rules

- Do not add explanatory product copy such as `设计保留`, `真实执行请使用下方`, `保护口径`, `验收面板`, or similar engineering notes.
- Do not add standalone execution, lifecycle, observability, or validation panels unless explicitly requested.
- Reuse the user-designed product components. Trading actions belong in `价差执行指令`; account and observability state belongs in `价差持仓总览`.
- `CrossSpreadMarketLifecyclePanel.vue` and `CrossSpreadLiveObservabilityPanel.vue` are deprecated references and must not be mounted on product pages.

## Required Checks

- Strategy frontend type check: `npx pnpm@9.15.9 type:check`
- User-system frontend check: `npx pnpm@9.15.9 test:user-system`
- Homepage layout guard: `npx pnpm@9.15.9 test:homepage-layout`
- Cross-spread structure guard: `npx pnpm@9.15.9 test:cross-spread-layout`
- Version consistency: `python scripts/check-version-consistency.py`
- Codex context: `python scripts/check-codex-context.py`

## File Safety

- Do not batch-delete files or directories.
- Delete only one explicit file path at a time, and only when the user clearly requests deletion.
- Prefer ASCII selectors, function names, class names, and script structure for patches because terminal Chinese output can be mojibake.
