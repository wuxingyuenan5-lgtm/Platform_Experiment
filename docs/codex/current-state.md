# Current Project State

Last updated: 2026-07-29  
Uploaded stable branch: `main` at `a4e22021c71cf5cd703cb0bc35676ff5adbfec36`  
Active integration branch: `feature/issue-117-platform-0.9.1`  
Product release: `0.9.1`

This file records current operating truth. The 0.9.1 integration branch is intentionally not merged into `main`.

## Architecture

- `admin-risk/`: Vue product frontend.
- `platform-backend/`: business, risk, browser user system, orchestration and accounting API.
- `execution-runtime/`: isolated Venue/Gateway process and Runtime Journal.
- SQLite remains approved for the current stage.
- Major ownership: `docs/architecture/OWNERSHIP.md`.
- Synthetic execution: `docs/technical/CROSS_SPREAD_SYNTHETIC_EXECUTION.md`.
- User-system handoff: `docs/operations/USER_SYSTEM_LOCAL_INTEGRATION_HANDOFF.md`.
- Operational acceptance: `docs/operations/V6-小资金实盘验收手册.md`.

## Safety defaults

```text
TradingMode=simulation
Gateway=fake
Platform Live Write=false
Runtime Live Write=false
Cross-spread Exit Monitor=false
Cross-spread acceptance max quantity=1 oz
Cross-spread non-closed lifecycle max=1
Cross-spread FOK hedge reserve=0 unless explicitly configured
Bybit PostOnly Chase=false
```

Code completion, version changes, browser roles and CI do not relax these values. API-Key roles and browser business roles remain separate.

## 0.9.1 integration

The branch preserves all changes in the latest uploaded `main`, including hedge-fund dashboard, funding execution, cross-spread product restructuring, Runtime adapters and local startup improvements.

It additionally integrates:

- browser registration, login, logout and password reset;
- Argon2id passwords, opaque server-side Sessions and CSRF/Origin validation;
- CEO, technical lead, employee and member roles;
- user administration, target-scoped data masking and operational notes;
- member holdings, NAV and asset views using Decimal strings;
- eight reusable local/test accounts;
- user, Session, holding, NAV and avatar backup/restore boundaries;
- browser E2E and user-system access guards.

Browser CEO authority cannot replace API-Key or LiveTradingSession authorization for real trading.

## Execution baseline

- Four synthetic actions remain separate from `MARKET`/`LIMIT` and trigger reason.
- Market uses confirmed Bybit Fill before MT5 hedge submission.
- FOK requires exact terminal full fill; zero, partial, mismatch and unknown outcomes remain distinct.
- PostOnly Chase is bounded by price limit, TTL, mutation count, cooldown and private-event evidence.
- PostOnly exact cumulative full fill is required before the existing MT5 path is released.
- Manual close, TP and SL reuse one Close Action with persisted Market/FOK/PostOnly selection.
- Bybit Close remains reduce-only with matching Position Index.
- MT5 Close remains bound to the intended Position Ticket.
- Unknown external results never authorize blind retry.

## Product and local-run baseline

One Windows command starts Runtime, Backend and Frontend:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-platform.ps1
```

The script reads pnpm from `admin-risk/package.json`, installs only when needed, starts three service windows and checks frontend `4373`, backend `8000`, and runtime `8100` readiness.

## Engineering workflow

- Fast: Markdown and synchronized version maintenance.
- Standard: bounded single-module work without Critical paths; no mandatory Issue or task packet.
- Critical: execution, Runtime, risk, auth, credentials, database/migration, contracts, CI governance, Live behavior, cross-service or cross-session work.
- Pull requests run only affected application jobs; `main` runs the full matrix.
- Secret Scan runs once in its dedicated workflow.

See `docs/engineering/GIT_WORKFLOW.md`.

## Production-only follow-up

Before production cutover:

- validate HTTPS same-origin proxy and Secure Cookie behavior;
- decide whether legacy Go/MySQL contains real users requiring migration;
- confirm initial production member-holding source;
- execute controlled-host Backup, Restore Drill, read-only restored startup and rollback rehearsal;
- complete real Windows/Venue/Broker acceptance under Issue #39.

## Known constraints

- PostOnly currently derives its hard Bybit bound from the pre-submit MT5 reference quote and does not dynamically reprice from MT5 during Chase.
- One successful Open maps to one MT5 Position Ticket; ambiguity fails closed.
- Real liquidity, Broker behavior, HTTPS proxy behavior and production data paths require operational evidence.
