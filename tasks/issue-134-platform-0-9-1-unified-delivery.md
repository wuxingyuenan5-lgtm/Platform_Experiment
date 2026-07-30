# Task: Platform 0.9.1 unified delivery

Issue: #134
Status: active
Branch: `feature/issue-134-platform-0-9-1-unified-delivery`
Base commit: `f4294eb9c781a2eb4c7150b9859f73176e8dde08`

## Objective

Consolidate the Platform engineering standard, hedge-board research implementation, account-level watchlist, automated acceptance and release-readiness work into one branch and one Draft pull request, then execute the remaining release plan in explicit phases.

## Protected semantics

- Do not merge or mutate `main` without explicit owner approval.
- Do not change execution, Live Write, risk, accounting, reconciliation, customer-authority or permission semantics.
- The frontend must not call third-party research sources directly.
- Research data must not become authoritative execution, risk or accounting input.
- Deterministic fixtures must not be represented as live-provider evidence.

## Scope

Included:

- platform product-engineering standard;
- Platform 0.9.1 customer-system baseline already contained in the validated stack;
- A-share dashboard, Shenwan aggregation, short-term sentiment, stock snapshot and macro expectation modules;
- account-level research watchlist with local cache fallback;
- research provider/cache/status contracts;
- Platform CI, User System Browser E2E and Hedge Board Browser E2E;
- live-provider and responsive manual-acceptance runbooks;
- final Platform 0.9.1 release-candidate handoff.

Non-goals:

- new markets, paid data providers or a market-data warehouse;
- React migration, microservices, Kafka, Kubernetes, GraphQL or a second FastAPI service;
- execution, Venue adapter, formal accounting or Live Write changes;
- automatic merge into `main`.

## Phased execution

### Phase 0 — Branch consolidation and baseline freeze

Status: done

- Unified branch created from validated head `f4294eb9c781a2eb4c7150b9859f73176e8dde08`.
- Issue #134 owns all further work.
- Former documentation, feature and release-readiness branches are historical references only.

### Phase 1 — Engineering standard and governance

Status: active

- Add `docs/architecture/PRODUCT_PLATFORM_ENGINEERING_STANDARD.md` to this branch.
- Keep the standard aligned with `SYSTEM_MAP.md`, `OWNERSHIP.md` and existing repository checks.

### Phase 2 — Product and account-data implementation

Status: done

- A-share research dashboard and Shenwan workflows.
- One-click stock snapshot and macro expectation modules.
- Account-level watchlist persistence, optimistic concurrency and offline cache fallback.
- Research provider, cache, last-known-good and source-state contracts.

### Phase 3 — Automated acceptance

Status: done on base head; must be rerun after consolidation commits

Required workflows:

- Platform CI;
- User System Browser E2E;
- Hedge Board Browser E2E;
- Secret Scan;
- Version Consistency.

### Phase 4 — Real-environment acceptance

Status: pending external environment

- one A-share trading-hours live-provider validation;
- one non-trading-hours validation;
- market value, Shenwan mapping and source-link spot checks;
- visual acceptance at 1440px, 1024px, 768px and 390px.

### Phase 5 — Platform 0.9.1 Release Candidate

Status: pending Phase 3 rerun and Phase 4 owner acceptance

- freeze one candidate commit;
- update release notes and acceptance evidence;
- retain Draft status until explicit owner approval;
- merge only after explicit approval.

## Verification

```powershell
cd platform-backend
python -m ruff check app tests scripts
python -m pyright
python -m pytest

cd ../admin-risk
npx pnpm@9.15.9 test:hedge-board-layout
npx pnpm@9.15.9 type:check
npx pnpm@9.15.9 build
npx pnpm@9.15.9 test:e2e:hedge-board
npx pnpm@9.15.9 test:e2e:user-system

cd ..
python scripts/check-repository-structure.py
python scripts/check-documentation-consistency.py
python scripts/check-codex-context.py
```

A Draft pull request targeting `main` must run all repository workflows and remain unmerged.

## Progress

- Done: Issue #134; unified branch; validated product/research/account-watchlist base; Phase 0 branch consolidation.
- Current: Phase 1 standard integration and consolidated Draft PR creation.
- Next: rerun Phase 3 workflows on the consolidated head; then record Phase 4 as owner-side acceptance evidence.
- Blocked by: Phase 4 requires access to the actual running environment and live external providers.
