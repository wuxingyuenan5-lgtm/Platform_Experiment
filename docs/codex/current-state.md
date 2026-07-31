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
5. Gate D2 — Platform API directory migration.

The current physical service boundaries are now:

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

The next phase is low-risk modularization. The approved order is Research, Identity, then Portfolio. Trading, Risk, formal Accounting, Reconciliation and Execution Runtime remain later, conservative gates.

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

## Next gate: Research modularization

Start with evidence and boundaries, not a broad rewrite:

1. inventory the current Research frontend and Platform API dependency graph;
2. separate page composition from reusable research view components;
3. split Provider acquisition, normalization, cache/state and service orchestration without changing response contracts;
4. preserve `ready`/`partial`/`stale`/`no_data`/`error` semantics and Last Known Good behavior;
5. keep A-share/Shenwan, macro and hedge-fund research routes and visuals unchanged;
6. require Platform CI, Provider Smoke, both browser E2E suites and the 56-page visual baseline after each structural step.
