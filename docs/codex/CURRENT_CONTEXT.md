# Codex Current Context

Last updated: 2026-07-29

## Stable Facts

- Product version: `0.9.1`
- Uploaded main baseline: `a4e22021c71cf5cd703cb0bc35676ff5adbfec36`
- Active integration branch: `release/0.9.1-user-system`
- The integration branch is not merged into `main`; do not merge without explicit user approval.
- GitHub repository: `wuxingyuenan5-lgtm/Platform_Experiment`
- Frontend: `http://127.0.0.1:4373/index.html`
- Platform Backend: `http://127.0.0.1:8000/health`
- Execution Runtime: `http://127.0.0.1:8100/health`
- Frontend package manager: `pnpm@9.15.9`

## Integrated Product Boundary

`0.9.1` preserves the latest uploaded platform, hedge-fund dashboard, cross-spread, funding and Runtime changes, and adds the browser user system:

- HttpOnly Cookie Sessions and memory-only CSRF;
- CEO, technical lead, employee and member roles;
- user administration, approval, operational notes and Session control;
- member holdings, NAV and asset views;
- eight reusable local/test accounts;
- user-domain backup and restore coverage.

Browser business roles remain separate from API-Key roles. Browser Sessions cannot authorize existing Live Write routes.

## Default Local Run

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-platform.ps1
```

This starts the frontend, Platform Backend and Execution Runtime. Keep these as the only normal local entrypoints unless a task explicitly requires otherwise.

## Default Checks

Run checks by task weight. Do not run the full frontend guard set for every small UI tweak.

Light UI tweak:

- Read only the target component and direct style owner.
- Change the smallest relevant CSS/template surface.
- Use targeted search and browser computed-style inspection only when visual confirmation is useful.
- Do not update md standards or guard scripts unless the user explicitly asks to make the rule durable.

Standard UI rule:

- Use when the request says `同类型同步`, `以后都按这个标准`, `更新md`, or fixes a repeated mistake.
- Update the formal standard document, usually `admin-risk/docs/design/platform-ui-guidelines.md`.
- Add or update a small guard only when the issue has already recurred or the rule is cheap to assert.

Architecture or high-risk change:

- Run relevant type checks, structure guards and context checks.
- Update architecture or ownership docs only when boundaries change.
- For auth, permissions, migrations or Session changes, run the full user-system backend and browser matrix.

Command index:

```powershell
npx.cmd pnpm@9.15.9 type:check
npx.cmd pnpm@9.15.9 test:user-system
npx.cmd pnpm@9.15.9 test:homepage-layout
npx.cmd pnpm@9.15.9 test:cross-spread-layout
npx.cmd pnpm@9.15.9 test:funding-order-layout
npx.cmd pnpm@9.15.9 test:hedge-board-layout
python scripts/check-version-consistency.py
python scripts/check-codex-context.py
```

## Context Rules

- For narrow UI edits, read only the target component, direct parent, directly used child components and necessary styles.
- Do not scan the whole repository for small UI changes.
- Do not load changelogs, archives, generated structure files, `node_modules`, virtual environments, outputs or unrelated modules by default.
- Historical documents are not active product authority.
- Product pages must not contain engineering explanation copy such as `设计保留`, `真实执行请使用下方`, `保护口径`, or `验收面板`.
- UI typography and component visual rules are governed by `admin-risk/docs/design/platform-ui-guidelines.md`; do not store design standards only in this context file.

## Active Frontend Hotspots

- Homepage: `admin-risk/src/views/dashboard/index.vue`
- Cross-spread page: `admin-risk/src/views/strategy/spread-carry/components/CrossVenueExecutionReplica.vue`
- Funding execution page: `admin-risk/src/views/strategy/funding-carry/components/FundingOrderPanel.vue`
- Hedge board page: `admin-risk/src/views/hedgeBoard/index.vue`
- User management: `admin-risk/src/views/users/`
- Member account: `admin-risk/src/views/account/`
- Cross-spread guard: `admin-risk/scripts/verify-cross-spread-layout.cjs`
- Funding order guard: `admin-risk/scripts/verify-funding-order-layout.cjs`
- Hedge board guard: `admin-risk/scripts/verify-hedge-board-layout.cjs`
- Homepage guard: `admin-risk/scripts/verify-homepage-layout.cjs`
- User-system guard: `admin-risk/scripts/test-user-system-access.cjs`
- Lightweight optimization plan: `docs/architecture/LIGHTWEIGHT_OPTIMIZATION_PLAN.md`

## Architecture Boundary

- `admin-risk/`: Vue product frontend
- `platform-backend/`: business, risk, user, orchestration and accounting API
- `execution-runtime/`: isolated Venue/Broker adapters and external side effects

Keep the three-service boundary. Current optimization work should reduce frontend/document noise, not merge services or introduce a new framework.
