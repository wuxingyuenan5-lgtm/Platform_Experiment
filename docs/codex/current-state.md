# Current Engineering State

Last updated: 2026-08-01

This is the sole repository document for current engineering state. Durable rules live in `AGENTS.md`; ownership lives in `docs/architecture/OWNERSHIP.md`; the active branch, Draft PR, HEAD, CI and review state live in GitHub PR #141.

## Delivery model

- Current target version: Platform `0.9.3`.
- Active branch: `refactor/platform-0-9-3-repository-and-context-optimization`.
- Active review: Draft PR #141, which must remain unmerged until explicit owner acceptance.
- Platform 0.9.2 code baseline: `cf44c8cca52576acc4e4070a98dcf112ebeec31c`.
- Content-level merge snapshot: `17f65059c91548f40dd786eb222420ad8e5fead8`; its file diff from the designated baseline is zero.
- Frontend package-manager authority: `pnpm@9.15.9`.
- `main` remains protected and is not modified directly.

## Current phase

- Phase 0 baseline reconstruction and evidence freeze is complete in closed, unmerged PR #140.
- Phase 0 final evidence commit: `7e8275dd4742db0b9e6ea191b37762313e2864b1`.
- Phase 0.5 repository, documentation, historical-content and naming audit is complete at `b6bcf437c6dd7fa4533b06dad73e8f704eb21578`.
- Current work is Platform 0.9.3 Phase 1A: version facts, current entry points, executable documentation paths and candidate-branch CI validation.
- Phase 1B and later cleanup phases have not started.
- Cross-venue spread and funding-fee arbitrage business closure belong to the later Phase 8 scope and are not part of Phase 1A.

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

Production Live Write remains closed. Browser Sessions cannot authorize Live Write, and no version or documentation change may weaken fail-closed trading, permission, accounting or Runtime boundaries.

## Current authority

- Repository and AI rules: `AGENTS.md`.
- Current state: `docs/codex/current-state.md`.
- Minimal task context: `docs/codex/context-map.md`.
- System topology: `docs/architecture/SYSTEM_MAP.md`.
- Module ownership: `docs/architecture/OWNERSHIP.md`.
- Local operation and troubleshooting: `docs/operations/RUNBOOK.md`.
- Database migration and recovery: `docs/database/README.md`.
- Git and release governance: `docs/engineering/GIT_WORKFLOW.md`.
- Legacy production migration gate: `docs/architecture/PLATFORM_LEGACY_DEPLOYMENT_AUDIT.md`.
- Legacy GitLab deployment evidence: `docs/architecture/PLATFORM_LEGACY_GITLAB_DEPLOYMENT_AUDIT.md`.

`docs/codex/CURRENT_CONTEXT.md` remains a compatibility pointer and is not a current-state authority.

## Deferred acceptance

The following remain outside GitHub-only acceptance and must not be inferred from green CI:

1. Windows real local validation;
2. external server, Nginx, systemd and TLS state;
3. GitLab Runner and deployment history;
4. MySQL schema, backup, restore and rollback evidence;
5. real Provider availability and market-value correctness;
6. real Venue/Broker and Live Write evidence;
7. formal accounting, EOD and reconciliation acceptance.

Until those items are reviewed, do not delete or rename `projects/risk-control`, alter `deploy/`, delete `platform-web/.gitlab-ci.yml`, migrate external domains or databases, or declare the Legacy production path retired.
