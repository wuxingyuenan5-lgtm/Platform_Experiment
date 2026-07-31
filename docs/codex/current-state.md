# Current Engineering State

Last updated: 2026-07-31

This is the sole repository document for current engineering state. Durable rules live in `AGENTS.md`; ownership lives in `docs/architecture/OWNERSHIP.md`; live branch, Draft PR, HEAD, CI and review state live in GitHub Issue #136.

## Delivery model

- Stable baseline: Platform `0.9.1` at `feature/issue-134-platform-0-9-1-unified-delivery@8114fce45e46e7920f316f49d03db12dc424acf1`.
- Active development: Platform `0.9.2`, tracked by Issue #136 and Draft PR #139.
- Final candidate: `0.10.1` only after all acceptance gates and explicit owner approval.
- `main` remains protected.

## Completed evidence-backed gates

1. Full repository audit, context reduction and 56-page visual baseline;
2. Platform Web and Platform API directory migrations;
3. Research E1–E5.1;
4. Identity I1/I2.1;
5. Portfolio P1–P3;
6. Frontend F1/F2;
7. High-risk H0 responsibility audit;
8. H1 dedicated EOD reconciliation routes;
9. H2 dedicated Venue reconciliation routes.

Frontend hotspot and high-risk structural governance are closed. Trading, Risk, Formal Accounting and Execution Runtime retained their existing owners. Reconciliation routing is separated without moving orchestration, persistence, policy, Financial Fact, Runtime transport, Decimal, idempotency or fail-closed behavior.

## Physical boundaries

```text
platform-web/
    ↓ Browser Session / REST
platform-api/                  modular monolith
    ↓ versioned Runtime contracts
execution-runtime/
    ↓ Venue / Broker / MT5 / Bybit
```

SQLite remains approved for the current Platform stage. Microservices, Kubernetes, Kafka, GraphQL, CQRS, Event Sourcing, micro-frontends and a second global state system remain out of scope.

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

Browser roles remain separate from API-Key roles. Browser Sessions cannot authorize Live Write.

## Permanent boundaries

### Portfolio

- `member_holding_valuation.py` owns pure valuation and NAV state classification.
- `member_holding_decimal.py` is the exact Decimal owner.
- `member_holding_service.py` retains scope, loading, reauthentication, transactions, audit and error translation.
- Public totals require complete same-currency valuation.

### Frontend hotspot

- `components/TradingViewWidget.ts` owns external TradingView lifecycle and cleanup.
- `nativeData/marketSnapshotTables.ts` owns static snapshot types and data.
- Source SHA-256: `20245f2606e15add5e97387c238532697c938677865c9d620178bbc9522b788a`.
- Canonical semantic SHA-256: `580983d83781cb7f0731dd39837d75b16eaf24be18751367432aa605fa0acc92`.
- `hedgeBoard/index.vue` remains page composition, local chart assembly, shared SVG math and style owner.

### EOD Reconciliation

- `eod_reconciliation_routes.py` owns four EOD HTTP endpoints and query aliases.
- `eod_reconciliation.py` retains compatibility aliases, per-call dependency wiring and exact HTTP mapping.
- Service, Policy, Repository, Financial Fact and fail-closed report semantics remain unchanged.

### Venue Reconciliation

- `venue_reconciliation_routes.py` owns five Venue HTTP endpoints, response models and tags.
- `venue_reconciliation.py` retains Repository aliases, Service delegates and exact Runtime/domain error mapping.
- Existing direct consumers continue to use the Facade.
- Service, Policy, Repository, Runtime Client, Financial Fact, DDL and Decimal semantics remain unchanged.

## Current gate: Legacy L0 classification

The next phase is a read-only inventory of `projects/risk-control` and its historical Go/MySQL deployment and data dependencies. It must identify active process references, configuration, database responsibilities, external dependencies and archival status before any structural action is proposed.

Known acceptance work still includes Windows local validation, production HTTPS, real Venue/Broker evidence, backup/restore and formal accounting/reconciliation acceptance.
