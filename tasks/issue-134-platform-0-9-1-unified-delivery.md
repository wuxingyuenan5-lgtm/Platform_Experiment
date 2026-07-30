# Task: Platform 0.9.1 unified delivery

Issue: #134
Status: active
Branch: `feature/issue-134-platform-0-9-1-unified-delivery`
Base commit: `f4294eb9c781a2eb4c7150b9859f73176e8dde08`
Validated functional baseline: `00574a8f10a3fc3723ae78c97aacbff075ff803b`

## Objective

Consolidate the Platform engineering standard, hedge-board research implementation, account-level watchlist, automated acceptance and release-readiness work into one branch and one Draft pull request, then execute the remaining release plan in explicit phases.

## Protected semantics

- Do not merge or mutate `main` without explicit owner approval.
- Do not change execution, Live Write, risk, accounting, reconciliation, customer-authority or permission semantics.
- The frontend must not call third-party research sources directly.
- Research data must not become authoritative execution, risk or accounting input.
- Deterministic fixtures must not be represented as live-provider evidence.
- Local acceptance must use a detached worktree and must not modify tracked files.

## Scope

Included:

- platform product-engineering standard;
- Platform 0.9.1 customer-system baseline already contained in the validated stack;
- A-share dashboard, Shenwan aggregation, short-term sentiment, stock snapshot and macro expectation modules;
- account-level research watchlist with local cache fallback;
- research provider/cache/status contracts;
- Platform CI, User System Browser E2E and Hedge Board Browser E2E;
- live-provider and responsive manual-acceptance runbooks;
- local acceptance handoff and evidence template;
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
- Kept the standard aligned with repository ownership and architecture checks.

### Phase 2 — Product and account-data implementation

Status: done

- A-share research dashboard and Shenwan workflows.
- One-click stock snapshot and macro expectation modules.
- Account-level watchlist persistence, optimistic concurrency and offline cache fallback.
- Research provider, cache, last-known-good and source-state contracts.

### Phase 3 — Automated acceptance

Status: done for functional baseline

Validated functional baseline `00574a8f10a3fc3723ae78c97aacbff075ff803b`:

- Platform CI `30524228159`: passed;
- User System Browser E2E `30524228014`: passed;
- Hedge Board Browser E2E `30524228011`: passed;
- Secret Scan `30524228235`: passed;
- Version Consistency `30524228121`: passed;
- Research Provider Smoke `30524228015`: workflow passed, external result recorded as `partial`.

Documentation-only handoff commits after this baseline must pass the applicable PR workflow surface before becoming the current validated head.

### Phase 4 — Real-environment acceptance

Status: local handoff ready; owner-side execution pending

Completed:

- trading-hours live-provider sample at `2026-07-30 14:47:41 +08:00`;
- trading-hours result: 5 of 8 checks passed, Tencent/Eastmoney 600519 difference `0.03`;
- non-trading-hours live-provider sample at `2026-07-30 15:42:05 +08:00`;
- non-trading-hours result: 5 of 8 checks passed, Tencent/Eastmoney 600519 both `1361.76`, difference `0.00`;
- both sessions reported the same three external failures: full-market spot remote disconnect, unavailable index history and unverifiable official Shenwan TLS chain;
- external failures recorded without TLS bypass or false healthy status;
- responsive browser preflight covers 1440, 1024, 768 and 390 widths;
- each viewport captures overview, Shenwan and watchlist evidence;
- account-level watchlist browser persistence E2E;
- complete local acceptance handoff:

```text
docs/operations/PLATFORM_0_9_1_LOCAL_ACCEPTANCE_HANDOFF.md
```

The local handoff requires:

- an independent detached worktree;
- no tracked-file modifications, commits, pushes or merges;
- `VG_LIVE_TRADING_ENABLED=false`;
- logs, screenshots and result files outside the repository;
- actual Platform page checks for source time, fetched time, state and Last Known Good;
- Shenwan and report/announcement/news original-link spot checks;
- owner visual review at four responsive widths.

Pending:

- applicable workflow validation of the documentation handoff head;
- actual running Platform review for source timestamp, fetched timestamp, `stale` and Last Known Good display;
- owner review of 1440/1024/768/390 screenshots and actual running page;
- Shenwan mapping spot checks;
- report, announcement and news source-link spot checks.

Provider smoke proves upstream availability only at the sampled time. It does not prove the running Platform's stale/LKG display. Automated responsive evidence is a preflight only and does not replace owner visual acceptance. Deterministic research fixtures do not count as live-provider evidence.

### Phase 5 — Platform 0.9.1 Release Candidate

Status: pending Phase 4 owner acceptance

- freeze one candidate commit;
- update release notes and acceptance evidence;
- retain Draft status until explicit owner approval;
- merge only after explicit approval.

## Verification

```bash
python3.12 scripts/check-documentation-consistency.py
python3.12 scripts/check-repository-structure.py
python3.12 scripts/check-version-consistency.py
python3.12 scripts/check-codex-context.py
python3.12 scripts/scan-secrets.py

cd platform-backend
python -m ruff check app tests scripts
python -m pyright
python -m pytest

cd ../admin-risk
pnpm test:user-system
pnpm test:hedge-board-layout
pnpm exec vue-tsc -p tsconfig.user-system.json --noEmit --skipLibCheck
pnpm type:check
pnpm build
pnpm test:e2e:hedge-board
pnpm test:e2e:user-system
```

A Draft pull request targeting `main` must remain open and unmerged until explicit owner approval.

## Progress

- Done: Phases 0–3; unified branch and Draft PR; full automated workflow surface on the functional baseline; trading and non-trading provider samples; responsive evidence; local acceptance handoff.
- Current: validate the documentation handoff head and execute local owner acceptance from a detached worktree.
- Next single action: run `docs/operations/PLATFORM_0_9_1_LOCAL_ACCEPTANCE_HANDOFF.md`, return the evidence directory and owner conclusion, then decide whether Phase 5 can freeze.
- Blocked by: actual local page review, original-link spot checks and owner acceptance cannot be claimed from CI or deterministic fixtures.