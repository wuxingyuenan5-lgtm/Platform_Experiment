# Current Engineering State

Last updated: 2026-08-01

This is the sole repository document for current engineering state. Durable rules live in `AGENTS.md`; ownership lives in `docs/architecture/OWNERSHIP.md`; live branch, Draft PR, HEAD, CI and review state live in GitHub Issue #136.

## Delivery model

- Stable baseline: Platform `0.9.1` at `feature/issue-134-platform-0-9-1-unified-delivery@8114fce45e46e7920f316f49d03db12dc424acf1`.
- Active development version: Platform `0.9.2`, tracked by Issue #136 and Draft PR #139.
- Final candidate: `0.10.1` only after all acceptance gates and explicit owner approval.
- Frontend package-manager authority: `pnpm@9.15.9`.
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
9. H2 dedicated Venue reconciliation routes;
10. Phase J / J0 repository classification, credential-document cleanup, strengthened Secret Scan, minimal read-only evidence collector, MySQL aggregate inventory and operator handoff.

Frontend hotspot and high-risk structural governance are closed. Trading, Risk, Formal Accounting and Execution Runtime retained their existing owners. Reconciliation routing is separated without moving orchestration, persistence, policy, Financial Fact, Runtime transport, Decimal, idempotency or fail-closed behavior.

J0 repository classification is complete. The external server, GitLab Runner and MySQL evidence required for J1 cannot be obtained through the current GitHub connection and is deferred by owner instruction. It remains a release acceptance item but no longer blocks GitHub-only optimization.

The current engineering gate is **Phase J / J2 GitHub repository hygiene and reduction**.

## Target physical boundaries

```text
platform-web/
    ↓ Browser Session / REST
platform-api/                  modular monolith
    ↓ versioned Runtime contracts
execution-runtime/
    ↓ Venue / Broker / MT5 / Bybit
```

The authoritative local entry is `scripts/dev-platform.ps1`, which starts Platform Web on 4373, Platform API on 8000 and Execution Runtime on 8100.

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

## Legacy production classification

The repository contains more than one historical production path.

### Native Nginx / Go / MySQL path

```text
platform-web production build
    ↓ /api/auth and /api/data
Nginx
    ├─ Go Auth Service :8080
    └─ Go Data Service :8082
          ↓
        MySQL risk_control
```

Critical facts:

- `platform-web/.env.production` still directs production API traffic to `/api/auth`, `/api/data` and `/api/data/ws`;
- the old Auth Service owns an independent MySQL user schema and JWT security model;
- the old Data Service owns a MySQL schema, Bybit client and optional NAV scheduler;
- deployment documentation describes a fixed server, backup, upgrade and rollback path;
- historical project documents contained reusable credentials and weak-password examples, so related server-side credentials must be treated as compromised and rotated;
- this stack cannot be treated as Demo, deleted, renamed or automatically switched without external evidence and owner approval.

The authoritative plan is `docs/architecture/PLATFORM_LEGACY_DEPLOYMENT_AUDIT.md`. The operator procedure is `docs/operations/LEGACY_PRODUCTION_EVIDENCE_HANDOFF.md`.

### Legacy GitLab frontend deployment path

`platform-web/.gitlab-ci.yml` defines test and production jobs using a dedicated `runner20`, fixed Node/npm/pnpm versions and direct copies to `/www/wwwroot/risk-web.rta-office.com/`. GitHub cannot establish whether the GitLab project, Runner or target site remains active.

The authoritative audit is `docs/architecture/PLATFORM_LEGACY_GITLAB_DEPLOYMENT_AUDIT.md`. This file is frozen as Legacy production evidence and is excluded from ordinary repository cleanup.

## Current gate: J2 GitHub repository hygiene

GitHub-only cleanup already applied in this phase:

- removed local homepage inspection screenshot and stale source-tree snapshot;
- added ignore rules for recurring local inspection artifacts;
- removed the upstream Vben `CNAME` and unused Gitpod configuration;
- removed the complete inert `platform-web/.github` subtree, including upstream workflows, Issue templates, PR template and contribution documents;
- added permanent architecture tests preventing those artifacts and nested GitHub metadata from returning;
- replaced machine-specific workspace size/path notes with durable repository hygiene rules;
- classified and froze `.gitlab-ci.yml` rather than deleting a possible production deployment path.

The governing document is `docs/operations/WORKSPACE_HYGIENE.md`.

J2 may continue only with high-confidence, reference-checked deletions. Any candidate that affects package locks, active routes, production configuration, runtime state, historical accounting evidence or Legacy production assets must stop for a dedicated plan.

## Deferred external acceptance

The following work remains required for release acceptance but is skipped during GitHub-only optimization:

1. server repository path, branch, HEAD and working-tree state;
2. systemd state and listening ports;
3. loaded Nginx routes, domain and TLS status;
4. environment-file existence, permissions, key names and hashes without values;
5. MySQL schema metadata, aggregate row counts, recent writes and sensitive-column occupancy without business rows;
6. current `/api/auth`, `/api/data` and WebSocket consumers;
7. GitLab project, `runner20`, `risk-web.rta-office.com` and deployment history;
8. backups, restore evidence and rollback path;
9. rotation status for MySQL, JWT, account-encryption, exchange and historical administrator credentials.

Until that evidence is reviewed, do not delete or rename `projects/risk-control`, alter `deploy/`, delete `.gitlab-ci.yml`, switch `.env.production`, import MySQL automatically, stop legacy services or declare the old stack retired.

## Remaining acceptance work

### GitHub-only work

- continue J2 high-confidence repository reduction;
- review remaining upstream scaffold metadata and unused source candidates without changing lockfiles or product contracts;
- maintain the full quality matrix and 56-page visual baseline for each accepted slice.

### Deferred external work

- external legacy server, GitLab Runner and MySQL evidence;
- J1 decision: continue Legacy Production, controlled migration or evidence-backed retirement;
- Windows real local validation;
- production HTTPS/TLS;
- real Venue/Broker evidence;
- database migration and backup/restore rehearsal;
- formal accounting, EOD and reconciliation acceptance;
- final rollback rehearsal and owner approval.
