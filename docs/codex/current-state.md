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

## Completed evidence-backed gates

1. Phase A — full repository audit;
2. Phase B — current-state and AI context reduction;
3. Phase C — 56-page four-width visual baseline and responsive guard;
4. Gate D1 — Platform Web directory migration;
5. Gate D2 — Platform API directory migration;
6. Research E1–E5.1 — Provider, state and bounded frontend/local-state modularization;
7. Identity I1 — administrator response Presenter;
8. Identity I2.1 — Browser Session response Presenter;
9. Portfolio P1–P3 — valuation owner, backend stop decision and complete public valuation semantics;
10. Frontend F1 — independent TradingView external-widget lifecycle owner;
11. Frontend F2 — static market snapshot data owner with source and canonical semantic Hash guards;
12. High-risk H0 — Trading/Risk/Accounting/Reconciliation/Runtime responsibility audit;
13. High-risk H1 — dedicated EOD reconciliation route owner.

Frontend hotspot governance is closed. Trading, Risk, Formal Accounting and Execution Runtime retained their existing owners after read-only audit. EOD routing is now separated without moving any report orchestration, persistence, policy, accounting, idempotency or fail-closed behavior.

The current gate is H2: read-only review of the Venue Reconciliation route boundary. Venue has a much wider compatibility surface than EOD, so no implementation is authorized until all cross-domain consumers and exact HTTP contracts are frozen.

## Current physical boundaries

```text
platform-web/
    ↓ Browser Session / REST
platform-api/                  modular monolith
    ↓ controlled Runtime contracts
execution-runtime/
    ↓ Venue / Broker / MT5 / Bybit
```

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

Browser business roles remain separate from API-Key roles. Browser Sessions cannot authorize Live Write. Code cleanup, route extraction, directory changes and CI changes do not relax these defaults.

## Preserved product baseline

The preserved baseline includes the browser user system, four business roles, user administration, member holdings/NAV, A-share and Shenwan research, hedge-fund research, funding and cross-spread workflows, Runtime adapters, formal Financial Fact/accounting boundaries, reconciliation and local three-process startup.

Detailed authority remains in:

- architecture and code ownership: `docs/architecture/OWNERSHIP.md`;
- high-risk audit and active gate: `docs/architecture/PLATFORM_HIGH_RISK_DOMAIN_AUDIT.md`;
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

- Windows real local acceptance, production HTTPS, real Venue/Broker behavior and final real-Provider evidence remain acceptance work, not assumed completion.
- `projects/risk-control` may contain legacy Go/MySQL production dependencies. It must not be deleted or renamed until server, user-data and migration evidence is resolved.
- Repository name `Platform_Experiment` and final product brand require owner approval; do not rename them automatically.
- PostOnly currently uses the pre-submit MT5 reference quote as its hard Bybit bound and does not dynamically reprice from MT5 during Chase.
- One successful Open maps to one MT5 Position Ticket; ambiguity fails closed.

## Permanent Portfolio boundary

1. `member_holding_valuation.py` owns persistence-independent validation, NAV state classification, UTC normalization and exact response construction from loaded structural inputs;
2. `member_holding_decimal.py` remains the only exact Decimal calculation owner;
3. `member_holding_service.py` retains scope, Fund/NAV loading, recent reauthentication, transactions, audit and error translation;
4. member and administrator views share `decimalDisplay.ts`;
5. account market value and cumulative return require complete same-currency valuation;
6. Repository, Routes, Schemas, Financial Fact, Position Math and Formal Projection contracts remain unchanged.

## Permanent frontend hotspot boundary

1. `components/TradingViewWidget.ts` owns external TradingView lifecycle, bounded layout repair, fallback and cleanup;
2. `nativeData/marketSnapshotTables.ts` owns the local static snapshot types and dataset;
3. snapshot source SHA-256: `20245f2606e15add5e97387c238532697c938677865c9d620178bbc9522b788a`;
4. canonical semantic SHA-256: `580983d83781cb7f0731dd39837d75b16eaf24be18751367432aa605fa0acc92`;
5. `hedgeBoard/index.vue` remains the page composition, local chart assembly, shared SVG math and style owner;
6. no further Hedge Board extraction is approved without new product requirements or demonstrated duplicate implementation.

## Permanent EOD Reconciliation boundary

1. `eod_reconciliation_routes.py` owns exactly four EOD HTTP endpoints, response models, tags and query aliases;
2. `eod_reconciliation.py` retains stable compatibility aliases, per-call dependency wiring and exact service-error-to-HTTP translation;
3. `eod_reconciliation_service.py` retains report creation/read/list/review sequencing and partial-failure capture;
4. Policy, Repository, Schemas, Financial Fact, Venue Reconciliation and database semantics remain unchanged;
5. existing Monkeypatch ports, idempotency, immutable review, `failed + blocked` reporting and Scale Gate fail-closed behavior remain frozen.

## Next gate: H2 Venue route read-only review

Before any Venue route extraction, inventory:

1. exact endpoint paths, methods, response models, Query aliases and error mappings;
2. every compatibility export and direct cross-domain consumer;
3. whether routes can call the facade at runtime without changing Monkeypatch behavior;
4. Service, Policy, Repository, Runtime Client and Financial Fact Golden coverage;
5. whether extraction reduces mixed responsibility enough to justify the wider compatibility surface.

If the cut requires changing service orchestration, error mapping, Runtime transport, Financial Fact import or compatibility delegates, retain the current Venue facade and record a stop decision.
