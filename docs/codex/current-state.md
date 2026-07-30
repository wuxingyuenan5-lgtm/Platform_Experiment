# Current Engineering State

Last updated: 2026-07-31

This is the sole repository document for current engineering state. Durable rules live in `AGENTS.md`; ownership lives in `docs/architecture/OWNERSHIP.md`; live HEAD, CI and review state live in GitHub Issue #136 and Draft PR #138.

## Version and delivery line

- Stable product baseline: Platform `0.9.1`.
- Frozen baseline branch: `feature/issue-134-platform-0-9-1-unified-delivery`.
- Frozen baseline commit: `8114fce45e46e7920f316f49d03db12dc424acf1`.
- Active development version: Platform `0.9.2`.
- Active delivery branch: `refactor/issue-136-platform-0.9.2-system-optimization`.
- Master Issue: `#136`.
- Draft PR: `#138`, based on the frozen 0.9.1 branch.
- Final accepted candidate: Platform `0.10.1` only after all optimization and acceptance gates pass.
- `main` remains protected and must not be modified or merged without explicit owner approval.

## Current phase

Phase A evidence-based audit is complete. The authoritative plan is:

`docs/architecture/PLATFORM_0_9_2_SYSTEM_OPTIMIZATION_MASTER_PLAN.md`

Phase B is active:

1. make the full existing CI matrix cover the non-`main` 0.9.2 Draft PR;
2. reduce current-state documents to one authority;
3. establish bounded domain reading packs and default exclusions;
4. measure context cost again before structural code changes.

No broad product-code refactor, directory rename, database migration or trading/accounting semantic change has been approved merely by entering Phase B.

## Architecture retained by audit

```text
Platform Web
    ↓ Browser Session / REST
Platform API (modular monolith)
    ↓ controlled Runtime contracts
Execution Runtime
    ↓ Venue / Broker / MT5 / Bybit
```

Current physical paths remain unchanged until the isolated naming phase:

- `admin-risk/`: Vue product frontend.
- `platform-backend/`: business, identity, portfolio, research, trading, risk, accounting and operations API.
- `execution-runtime/`: Venue/Broker adapters, external side effects and Runtime Journal.

SQLite remains approved for the current stage. Do not introduce microservices, Kubernetes, Kafka, GraphQL, CQRS, Event Sourcing, micro-frontends or a second global state system.

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

Browser business roles remain separate from API-Key roles. Browser Sessions cannot authorize Live Write. Code cleanup, version changes and CI changes do not relax these defaults.

## Preserved product baseline

The 0.9.1 baseline includes the browser user system, four business roles, user administration, member holdings/NAV, A-share and Shenwan research, hedge-fund research, funding and cross-spread workflows, Runtime adapters, formal Financial Fact/accounting boundaries, reconciliation and local three-process startup.

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

## Known constraints and unresolved decisions

- Windows real local acceptance, full-platform four-width visual evidence, production HTTPS, real Venue/Broker behavior and final Provider evidence remain acceptance work, not assumed completion.
- `projects/risk-control` may contain legacy Go/MySQL production dependencies. It must not be deleted or renamed until server, user-data and migration evidence is resolved.
- Repository name `Platform_Experiment` and final product brand require owner approval; do not rename them automatically.
- PostOnly currently uses the pre-submit MT5 reference quote as its hard Bybit bound and does not dynamically reprice from MT5 during Chase.
- One successful Open maps to one MT5 Position Ticket; ambiguity fails closed.

## Next gate

Before low-risk domain modularization begins:

- all existing CI, browser E2E, Secret Scan, Version Consistency and Provider Smoke workflows must cover Draft PR #138;
- the current-state/context checks must reject duplicate or stale authorities;
- the 0.9.2 version declarations must be synchronized;
- core page visual baselines must be frozen without changing the UI.
