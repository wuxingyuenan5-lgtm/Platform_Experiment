# Current Project State

Last updated: 2026-07-26  
Stable branch: `main`  
Product release: `0.9.0`

This file records stable operating truth. GitHub is authoritative for open Issues, PRs, branches and CI.

## Architecture

- `admin-risk/`: Vue product frontend.
- `platform-backend/`: business, risk, execution orchestration and accounting API.
- `execution-runtime/`: isolated Venue/Gateway process and Runtime Journal.
- SQLite remains approved for the current stage.
- Major ownership: `docs/architecture/OWNERSHIP.md`.
- Synthetic execution: `docs/technical/CROSS_SPREAD_SYNTHETIC_EXECUTION.md`.
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

Code completion, version changes and CI do not relax these values.

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

- Product release `0.9.0` includes Market, FOK, TP/SL execution selection and disabled-by-default PostOnly Chase.
- One Windows command starts Runtime, Backend and Frontend:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-platform.ps1
```

- The script reads the pnpm version from `admin-risk/package.json`, installs only when needed, starts three service windows and checks their HTTP readiness.

## Engineering workflow

- Fast: Markdown and synchronized version maintenance.
- Standard: bounded single-module work without Critical paths; no mandatory Issue or task packet.
- Critical: execution, Runtime, risk, auth, credentials, database/migration, contracts, CI governance, Live behavior, cross-service or cross-session work.
- Pull requests run only affected application jobs; `main` runs the full matrix.
- Secret Scan runs once in its dedicated workflow.

See `docs/engineering/GIT_WORKFLOW.md`.

## Deferred product decision

Quote age, cross-Venue time skew, Bid/Ask width, MT5 deviation, unhedged duration, realized-spread deviation and fee decomposition remain Markdown-only candidates for later post-trade analysis. No frontend placement has been chosen.

## Operational acceptance

Issue #39 remains the real Windows-host acceptance workstream. It must prove credentials, permissions, symbol specifications, private-stream behavior, MT5 Terminal stability, controlled minimum-size execution, recovery and clean reconciliation. CI is not that evidence.

## Known constraints

- PostOnly currently derives its hard Bybit bound from the pre-submit MT5 reference quote and does not dynamically reprice from MT5 during Chase.
- One successful Open maps to one MT5 Position Ticket; ambiguity fails closed.
- Real liquidity, Broker behavior and Venue fields require operational evidence.
