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
- Superseded Draft PRs #124, #127, #129, #131 and #133 were closed without merge.

### Phase 1 — Engineering standard and governance

Status: done

- Added `docs/architecture/PRODUCT_PLATFORM_ENGINEERING_STANDARD.md` to this branch.
- Set the standard to `active` for the Platform 0.9.1 baseline.
- Kept the standard aligned with `SYSTEM_MAP.md`, `OWNERSHIP.md` and existing repository checks.

### Phase 2 — Product and account-data implementation

Status: done

- A-share research dashboard and Shenwan workflows.
- One-click stock snapshot and macro expectation modules.
- Account-level watchlist persistence, optimistic concurrency and offline cache fallback.
- Research provider, cache, last-known-good and source-state contracts.

### Phase 3 — Automated acceptance

Status: done

Validated consolidated head `4ef07207997dae09afe268502ee10e53cda4c3f2`:

- Platform CI `30520684957`: passed;
- User System Browser E2E `30520684543`: passed;
- Hedge Board Browser E2E `30520684631`: passed;
- Secret Scan `30520684549`: passed;
- Version Consistency `30520684532`: passed;
- Research Provider Smoke workflow `30520684588`: passed with external result `partial`.

### Phase 4 — Real-environment acceptance

Status: in progress

Completed:

- trading-hours live-provider sample at `2026-07-30 14:47:41 +08:00`;
- provider result: 5 of 8 checks passed and 3 external dependencies failed;
- Tencent/Eastmoney 600519 cross-source quote check passed with absolute difference `0.03`;
- external failures recorded without TLS bypass or false healthy status;
- responsive browser preflight covers 1440, 1024, 768 and 390 widths;
- each viewport captures overview, Shenwan and watchlist evidence;
- the preflight closes responsive navigation overlays, waits for transient errors to clear and rejects page-level horizontal overflow;
- responsive screenshots are uploaded through the Hedge Board Browser E2E artifact.

Pending:

- final workflow validation of the current responsive-evidence head;
- one non-trading-hours provider validation;
- owner review of 1440/1024/768/390 screenshots and actual running page;
- Shenwan mapping spot checks;
- report, announcement and news source-link spot checks.

Automated responsive evidence is a preflight only and does not replace owner visual acceptance. Deterministic research fixtures do not count as live-provider evidence.

### Phase 5 — Platform 0.9.1 Release Candidate

Status: pending Phase 4 owner acceptance

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

- Done: Phases 0–3; unified branch and Draft PR; full deterministic workflow surface; one trading-hours live-provider sample; responsive evidence implementation and initial successful screenshot artifact.
- Current: validate the clean-state responsive screenshot head and complete the scheduled non-trading-hours sample.
- Next: record non-trading evidence, review source links and responsive screenshots, then freeze the Platform 0.9.1 release candidate.
- Blocked by: final visual and link acceptance require the actual running environment and owner review.
