# Current Engineering State

Last updated: 2026-07-31

This is the sole repository document for current engineering state. Durable rules live in `AGENTS.md`; ownership lives in `docs/architecture/OWNERSHIP.md`; live branch, Draft PR, HEAD, CI and review state live in GitHub Issue #136.

## Version and delivery model

- Stable product baseline: Platform `0.9.1`.
- Frozen baseline branch: `feature/issue-134-platform-0-9-1-unified-delivery`.
- Frozen baseline commit: `8114fce45e46e7920f316f49d03db12dc424acf1`.
- Active development version: Platform `0.9.2`.
- Master engineering tracker: GitHub Issue `#136`.
- Final accepted candidate: Platform `0.10.1` only after all optimization and acceptance gates pass.
- `main` remains protected and must not be modified or merged without explicit owner approval.

The active branch, Draft PR, current HEAD and workflow run IDs are intentionally not copied here. Resolve them from Issue #136 so repository documents do not drift.

## Current phase

The following gates are complete and evidence-backed:

1. Phase A — full repository audit;
2. Phase B — current-state and AI context reduction;
3. Phase C — 56-page four-width visual baseline and responsive guard;
4. Gate D1 — Platform Web directory migration;
5. Gate D2 — Platform API directory migration;
6. Research E1–E5.1 — Provider, state and bounded frontend/local-state modularization;
7. Identity I1 — administrator response Presenter;
8. Identity I2.1 — Browser Session response Presenter;
9. Portfolio P1 — pure member-holding valuation owner and permanent boundary.

Portfolio P1 passed the complete quality matrix on the evidence HEAD recorded in Issue #136 and Draft PR #139. The next gate is a read-only review of Fund catalog and NAV mutation response construction. No additional Portfolio backend module may be introduced unless that review proves a distinct stateless responsibility and measurable maintenance benefit.

The current physical service boundaries are:

```text
platform-web/
    ↓ Browser Session / REST
platform-api/                  modular monolith
    ↓ controlled Runtime contracts
execution-runtime/
    ↓ Venue / Broker / MT5 / Bybit
```

Directory migration evidence and invariants are defined in:

`docs/architecture/PLATFORM_DIRECTORY_MIGRATION_PLAN.md`

The approved low-risk modularization order remains Research, Identity, then Portfolio. Trading, Risk, formal Accounting, Reconciliation and Execution Runtime remain later, conservative gates.

## Architecture retained by audit

SQLite remains approved for the current stage. Do not introduce microservices, Kubernetes, Kafka, GraphQL, CQRS, Event Sourcing, micro-frontends or a second global state system.

Platform API remains a modular monolith. Python imports remain under package `app`; changing the top-level service directory did not change API paths, ports, database paths, migration semantics or Runtime contracts.

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

Browser business roles remain separate from API-Key roles. Browser Sessions cannot authorize Live Write. Code cleanup, directory changes, version changes and CI changes do not relax these defaults.

## Preserved product baseline

The preserved baseline includes the browser user system, four business roles, user administration, member holdings/NAV, A-share and Shenwan research, hedge-fund research, funding and cross-spread workflows, Runtime adapters, formal Financial Fact/accounting boundaries, reconciliation and local three-process startup.

Detailed authority is not repeated here:

- architecture and code ownership: `docs/architecture/OWNERSHIP.md`;
- database and migration authority: `docs/database/README.md`;
- synthetic execution: `docs/technical/CROSS_SPREAD_SYNTHETIC_EXECUTION.md`;
- engineering workflow: `docs/engineering/GIT_WORKFLOW.md`;
- task routing: `docs/codex/context-map.md`.

## Local run

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-platform.ps1
```

- Frontend: `http://127.0.0.1:4373/index.html`
- Platform API: `http://127.0.0.1:8000/health`
- Execution Runtime: `http://127.0.0.1:8100/health`
- Frontend package manager: `pnpm@9.15.9`

## Permanent directory invariants

The following command must remain green:

```bash
python scripts/audit-directory-migration.py \
  --mode post-rename \
  --target all \
  --fail-on-unclassified
```

Active CI, scripts, service trees and current documentation must not reintroduce legacy top-level paths. Historical evidence and explicitly classified external dependencies may retain the path facts that were true when recorded.

## Known constraints and unresolved decisions

- Windows real local acceptance, production HTTPS, real Venue/Broker behavior and final real-Provider evidence remain acceptance work, not assumed completion.
- `projects/risk-control` may contain legacy Go/MySQL production dependencies. It must not be deleted or renamed until server, user-data and migration evidence is resolved.
- Repository name `Platform_Experiment` and final product brand require owner approval; do not rename them automatically.
- PostOnly currently uses the pre-submit MT5 reference quote as its hard Bybit bound and does not dynamically reprice from MT5 during Chase.
- One successful Open maps to one MT5 Position Ticket; ambiguity fails closed.

## Portfolio boundary

Member-holding optimization remains deliberately narrow:

1. `member_holding_valuation.py` owns persistence-independent validation, NAV state classification, UTC normalization and exact response construction from already loaded structural inputs;
2. `member_holding_decimal.py` remains the only exact Decimal calculation owner;
3. `member_holding_service.py` retains scope, Fund/NAV loading, recent reauthentication, transactions, audit and error translation;
4. Repository, Routes, Schemas, Financial Fact, Position Math and Formal Projection contracts remain unchanged;
5. only read-only evidence may justify a Fund catalog Presenter or NAV mutation response Presenter;
6. absent a clear stateless cut, Portfolio backend modularization stops rather than mechanically splitting financial code.
