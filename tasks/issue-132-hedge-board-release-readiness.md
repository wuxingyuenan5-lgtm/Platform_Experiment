# Task: Hedge-board release readiness

Issue: #132  
Status: active  
Branch: `feature/issue-132-hedge-board-release-readiness`  
Base commit: `ed095a16f686593b5115191052f3459357c067cd`

## Objective

Complete the remaining Platform 0.9.1 hedge-board release-readiness work without changing execution, accounting, customer-system authority or permission semantics.

## Protected semantics

- No change to Platform or Runtime Live Write defaults.
- No change to Venue commands, execution contracts, formal accounting or reconciliation.
- Frontend never calls third-party research sources directly.
- Research data never becomes execution-authoritative market data.
- No automatic merge into `main` or previous delivery branches.

## Scope

Included:

- account-level A-share watchlist persistence with local cache fallback;
- optimistic concurrency and account isolation;
- dedicated hedge-board Playwright browser acceptance;
- live Platform research-source probe and manual acceptance runbook;
- Platform 0.9.1 release-candidate handoff and final validation evidence.

Non-goals:

- new market coverage or new research providers;
- redesigning the full hedge-board visual language;
- changing trade, risk, accounting, customer authority or Runtime behavior;
- treating deterministic E2E research fixtures as live-provider evidence;
- merging to `main` without explicit owner approval.

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

cd ..
python scripts/check-repository-structure.py
python scripts/check-documentation-consistency.py
python scripts/check-codex-context.py
```

A Draft pull request targeting `main` must run Platform CI, User System Browser E2E, Hedge Board Browser E2E, Version Consistency and Secret Scan and remain unmerged.

## Progress

- Done: Issue #132; isolated stacked branch; migration and backend account-watchlist contracts; optimistic concurrency; frontend local-cache/account synchronization; synchronization status UI; backend tests; structural regression guard; dedicated E2E seed/config/spec/workflow; live-source probe; manual acceptance runbook.
- Current: run the full automated validation surface and repair exact findings.
- Next: record validated HEAD and workflow runs, prepare the Platform 0.9.1 release-candidate handoff, and leave live-provider/visual acceptance explicitly pending until executed in the real environment.
- Blocked by: none.
