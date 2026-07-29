# Project Agent Rules

## Baseline

- Current product version: `0.9.0`.
- Current main baseline: `71603bcc6807284ef3a6da26ad3f43c541bc99c2`.
- Frontend port: `4373`.
- Use `npx pnpm@9.15.9 ...` for frontend commands.

## Scope Control

- For UI point fixes, read only the target component, direct parent component, and necessary styles.
- For trading execution changes, read the execution component, lifecycle API, exit plan API, and related types.
- For position, account, and observability changes, read the position table component, observability API, and snapshot types.
- Do not scan the whole repository for narrow UI edits.

## Product UI Rules

- Do not add explanatory product copy such as `设计保留`, `真实执行请使用下方`, `保护口径`, `验收面板`, or similar engineering notes.
- Do not add standalone execution, lifecycle, observability, or validation panels unless explicitly requested.
- Reuse the user-designed product components. Trading actions belong in `价差执行指令`; account and observability state belongs in `价差持仓总览`.
- `CrossSpreadMarketLifecyclePanel.vue` and `CrossSpreadLiveObservabilityPanel.vue` are deprecated references and must not be mounted on product pages.

## Required Checks

- Strategy frontend type check: `npx pnpm@9.15.9 type:check`
- Homepage layout guard: `npx pnpm@9.15.9 test:homepage-layout`
- Cross-spread structure guard: `npx pnpm@9.15.9 test:cross-spread-layout`

## File Safety

- Do not batch-delete files or directories.
- Delete only one explicit file path at a time, and only when the user clearly requests deletion.
- Prefer ASCII selectors, function names, class names, and script structure for patches because terminal Chinese output can be mojibake.
