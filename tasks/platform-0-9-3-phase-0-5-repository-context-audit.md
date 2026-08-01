# Platform 0.9.3 Phase 0.5 Repository and Context Audit

Workstream: critical  
Branch: `refactor/platform-0-9-3-repository-and-context-optimization`  
Source commit: `cf44c8cca52576acc4e4070a98dcf112ebeec31c`  
Product-code baseline: Platform `0.9.2`

## Scope

This phase audits repository weight, Markdown function, historical content, duplicate content, legacy assets, naming and external dependencies.

No product file, release version, Decimal behavior, Context configuration, visual test, type-check configuration, workflow trigger, route, permission, trading, accounting or Runtime contract is changed.

## Markdown function baseline

The reviewed scope contains 254 Markdown files:

| Classification | Count | Meaning |
|---|---:|---|
| A | 37 | current authority |
| B | 90 | specialist reference |
| C | 12 | production evidence |
| D | 114 | process or historical material |
| E | 1 | dead content |

Key functional findings:

- `docs/codex/current-state.md` remains the sole current-state document, but it still describes the Platform 0.9.2 branch and must be updated only when Phase 1 performs the formal 0.9.3 version transition.
- `docs/architecture/OWNERSHIP.md` has valid repository paths and remains the canonical ownership catalog.
- `docs/architecture/SYSTEM_MAP.md` matches the current Platform Web → Platform API → Execution Runtime topology.
- `docs/operations/RUNBOOK.md` points to the existing `scripts/dev-platform.ps1`; the documented ports 4373, 8000 and 8100 match the launcher.
- `docs/database/README.md` covers SQLite ownership, additive immutable migrations and backup/restore ownership.
- `docs/codex/context-map.md` is executable through `scripts/context-for.py`, but the seven Context Packs keep the frozen Phase 0 Before values.
- `platform-web/docs/README.md`, `platform-web/docs/00-人工可读目录/README.md` and `platform-web/docs/START-HERE.md` contain stale V1/V5/V6, branch, Issue or PR state and must not override root documentation.
- `platform-web/docs/START-HERE.md` is the single E-class document: it points to Issue #24 and PR #25 and duplicates maintained safety facts.

## Process-material baseline

The Phase 0 counts are reconciled as follows:

- Handoff group: 6 files, including the handoff directory index.
- Plan group: 26 files, including root `PLAN.md`.
- Audit group: 8 files.
- Task packets: 47 files in `tasks/`.

Production evidence is excluded from deletion recommendations even when its name contains Legacy, Handoff or Audit.

## Historical and unused-asset findings

| Candidate | Evidence | Recommendation |
|---|---|---|
| `platform-web/apps/test-server` | pnpm workspace and lockfile only; no root script, CI, route or deployment consumer | delete in a lockfile-aware batch |
| `platform-web/src/views/demo/**` | no static route module; included by the broad `views/**/*` dynamic glob; some non-demo files still import demo utilities | replace remaining consumers, then delete as one tested batch |
| `platform-web/mock/**` and mock plugin | `VITE_USE_MOCK=false` in maintained environments; dependencies remain in package and lockfile | delete only with dependency and lockfile update |
| `LegacyAccountDataManager.vue` | no direct import or route reference; still enters the broad views glob | delete after checking external dynamic component names |
| `CrossSpreadMarketLifecyclePanel.vue` | explicitly deprecated and not mounted on product pages | delete after preserving any unique API-wiring test evidence |
| `CrossSpreadLiveObservabilityPanel.vue` | explicitly deprecated and not mounted on product pages | delete after preserving any unique observability test evidence |
| duplicate risk-log page pair | no static route reference; both enter the broad views glob | delete after confirming no external dynamic menu component name |
| `LegacyStrategyCoverage.vue` | actively imported by the risk detail page | retain; rename only after Legacy service responsibility is explicit |
| `CrossVenueExecutionReplica.vue` and `DomesticOverseasExecutionReplica.vue` | actively imported by `SpreadExecutionWorkspace.vue` | retain; naming cleanup requires import, verification and Context updates |
| `user_backup_archive.py` | imported by disaster recovery | retain |
| Runtime V1 contract and V1 readiness | enforced by tests and architecture checks | retain |
| `projects/risk-control`, `deploy/`, `.gitlab-ci.yml` | possible live Go/MySQL/Nginx/GitLab production path | production confirmation required |

## Duplicate-content findings

The 14 exact duplicate-file groups are classified as:

- 3 monorepo package configuration groups: legitimate package-local repetition; retain.
- 4 TinyMCE skin groups: third-party vendor assets; retain.
- 3 VxeTable adapter-wrapper groups: upstream component pattern; retain unless the upstream layer is intentionally replaced.
- 3 Demo account/user component groups: delete with the Demo batch rather than merge.
- 1 risk-log page group: candidate for deletion after route and dynamic-menu verification.

The 56 repeated-code-block groups are classified as:

- intentional Platform/Runtime security and contract parity: retain and enforce with tests;
- E2E seed fixtures and Playwright suite setup: legitimate test repetition, optional shared helper only;
- upstream UI/component wrappers: retain unless ownership changes;
- Demo/template repetition: remove with the Demo batch;
- active product presentation repetition: merge only through bounded shared utilities or composables;
- user reauthentication flow repetition: security-sensitive and not a general cleanup candidate;
- duplicate reference SQL snapshots: consolidate to one canonical reference after updating links.

## Naming findings

- `admin-risk` was the former Vue frontend directory; its current responsibility is `platform-web`.
- `platform-backend` was the former FastAPI modular-monolith directory; its current responsibility is `platform-api`.
- Historical task packets, release notes and migration checks may legitimately retain those old names.
- `私募` is a legitimate business term and must not be mechanically replaced.
- `私募交易风控平台` is an old narrow product label in Legacy project documentation; the current product identity is broader.
- `rta-office`, `risk-web`, `runner20`, `/www/wwwroot/risk-web.rta-office.com/`, `/api/auth`, `/api/data`, MySQL `risk_control` and related environment variables are external migration dependencies, not ordinary template strings.

## External migration freeze

The following remain frozen pending production evidence:

- `platform-web/.gitlab-ci.yml`;
- GitLab Runner tag `runner20`;
- domain and deployment path `risk-web.rta-office.com`;
- `deploy/` Nginx and systemd assets;
- `projects/risk-control/` Go services;
- MySQL database `risk_control` and user `risk_app`;
- `/api/auth`, `/api/data` and `/api/data/ws` routes;
- production `VITE_GLOB_API_URL*` and `DB_DSN` values.

## Recommended cleanup order

1. Documentation entrypoints and dead process material: establish 0.9.3 authority, merge unique facts, then remove stale indexes and superseded Drafts.
2. Unreferenced frontend/template assets: test-server, Demo/Mock and deprecated panels, with lockfile, route, build and E2E evidence.
3. Naming and external migration: rename active internal symbols separately; migrate external domain, Runner, database and routes only after production confirmation.

## Phase 1 candidate scope

Phase 1 should remain bounded to:

- formal Platform 0.9.3 version-file transition;
- current-state, root documentation and active task/PR naming alignment;
- minimum CI trigger support for the active 0.9.3 PR;
- no Context reduction, visual comparison rewrite, type-check expansion, Decimal change or business-loop implementation unless separately authorized.

## CI trigger finding

The active PR base `refactor/issue-136-platform-0-9-2-system-optimization` is not included in the current `pull_request.branches` list of the nine workflows. Therefore no existing workflow naturally auto-triggers for the new 0.9.3 PR.

Workflows with `workflow_dispatch` can be run manually:

- Platform 0.9.2 Baseline Audit;
- Platform Visual Baseline;
- User System Browser E2E;
- Hedge Board Browser E2E;
- Research Provider Smoke.

Platform CI, Directory Invariants, Secret Scan and Version Consistency have no manual dispatch entry at this baseline.

The minimum Phase 1 CI change should add the active base branch to required PR workflows without changing job semantics or Path Filters, then explicitly run the full matrix once before Phase 1 acceptance.
