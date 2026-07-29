# Task: Hedge-board research upgrade

Issue: #125
Status: active
Branch: `feature/hedge-board-research-upgrade-0-9-1`
Base commit: `82142c5ad97485fabfafdd6b2e7a2b0b759971c1`

The delivery branch was created before Issue #125 and retains the previously agreed name.

## Objective

Deliver a complete Platform 0.9.1 hedge-fund research dashboard upgrade with A-share breadth/detail/Shenwan/sentiment/watchlist/one-click stock data and macro event-probability curves through one read-only Platform research boundary.

## Protected semantics

- No change to Platform or Runtime Live Write defaults.
- No change to Venue commands, execution contracts, customer-system authority, formal accounting or reconciliation.
- Frontend never calls third-party market-data sources directly.
- Platform Backend never imports Venue or Broker SDKs.
- Research data never becomes execution-authoritative market data.
- No Wind, Choice or AI data-collection dependency.
- No automatic merge into `main`.

## Scope

Included:

- authenticated `/api/v1/research/**` contracts;
- free-source provider adapters, normalization, independent module failure and last-known-good behavior;
- deterministic A-share formulas and Shenwan L1/L2 aggregation;
- dedicated A-share research page and macro probability panel in the existing UI language;
- tests, layout guard, architecture/technical documentation and validation PR.

Non-goals:

- a complete historical equity data warehouse;
- prediction-market probabilities as platform forecasts or trading signals;
- new execution, accounting, customer or database authority;
- copied React UI or a second copied FastAPI service.

## Context

- `docs/technical/RESEARCH_DATA_PLATFORM.md`
- `platform-backend/app/research_*.py`
- `platform-backend/app/a_share_research_policy.py`
- `admin-risk/src/api/hedgeResearch.ts`
- `admin-risk/src/views/hedgeBoard/aShare/`
- `admin-risk/src/views/hedgeBoard/macro/`

## Verification

```powershell
cd platform-backend
python -m ruff check app tests
python -m pyright
python -m pytest

cd ../admin-risk
npx pnpm@9.15.9 type:check
npx pnpm@9.15.9 test:hedge-board-layout
npx pnpm@9.15.9 build

cd ..
python scripts/check-repository-structure.py
python scripts/check-documentation-consistency.py
python scripts/check-codex-context.py
```

A Draft pull request targeting the validated 0.9.1 handoff branch must run the repository CI, Version Consistency and Secret Scan workflows. It must remain unmerged.

## Progress

- Done: Issue and protected scope; data contracts; policy; cache; provider/service/routes; A-share page modules; macro probability panel; initial unit and layout tests; technical documentation.
- Current: run validation, repair exact lint/type/build/test failures, synchronize architecture ownership and final handoff.
- Next: create Draft validation PR, inspect all checks, apply bounded fixes, mark this packet `review` only after required checks pass.
- Blocked by: none.
