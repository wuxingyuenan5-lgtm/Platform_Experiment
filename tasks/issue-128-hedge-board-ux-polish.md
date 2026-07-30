# Task: Hedge-board UX polish round 2

Issue: #128
Status: active
Branch: `feature/issue-128-hedge-board-ux-polish`
Base commit: `af8ad664f30fce9a711d0d275eb00729093ac759`
Validated HEAD: `5d125f7ab55a9e71af7a1599dc076dc734ff9eef`

## Objective

Perform a second-round product acceptance and interaction polish pass on the completed, unmerged hedge-fund research dashboard without changing execution, accounting, customer-system or permission semantics.

## Protected semantics

- No change to Platform or Runtime Live Write defaults.
- No change to Venue commands, execution contracts, formal accounting, reconciliation or customer-system authority.
- Frontend never calls third-party research sources directly.
- Research data never becomes execution-authoritative market data.
- No automatic merge into `main` or the previous Issue #125 branch.

## Scope

Included:

- preserve a deliberately empty A-share watchlist across reloads;
- normalize common A-share code input formats;
- validate duplicate and malformed watchlist entries;
- keep watchlist ordering within the current group;
- improve user feedback and accessibility for watchlist actions;
- clarify research source time, platform fetch time and data-state presentation;
- prevent stale dashboard or stock requests from overwriting newer results;
- provide explicit threshold apply, copy and CSV-export feedback;
- use China-market calendar dates for exported filenames;
- expose Shenwan sort direction, current result order, result counts and empty-filter recovery;
- add bounded regression checks and run the existing Critical validation surface.

Non-goals:

- new research providers or additional market coverage;
- changes to execution, risk, accounting, customer-system or authorization code;
- merging either Issue #125 or Issue #128 into `main`;
- redesigning the full hedge-board visual language.

## Context

- `tasks/issue-125-hedge-board-research-upgrade.md`
- `admin-risk/src/views/hedgeBoard/aShare/useAShareResearch.ts`
- `admin-risk/src/views/hedgeBoard/aShare/components/AShareWatchlistSection.vue`
- `admin-risk/src/views/hedgeBoard/aShare/components/ShenwanIndustrySection.vue`
- `admin-risk/src/views/hedgeBoard/research/components/ResearchSourceState.vue`
- Draft PR #129

## Verification

```powershell
cd admin-risk
npx pnpm@9.15.9 test:hedge-board-layout
npx pnpm@9.15.9 type:check
npx pnpm@9.15.9 build

cd ..
python scripts/check-repository-structure.py
python scripts/check-documentation-consistency.py
python scripts/check-codex-context.py
```

The Draft pull request targeting `main` must run Platform CI, User System Browser E2E, Version Consistency and Secret Scan and remain unmerged.

## Validated runs

- Platform CI `30502015128`: passed.
- User System Browser E2E `30502015115`: passed.
- Secret Scan `30502015108`: passed.
- Version Consistency `30502015165`: passed.

## Progress

- Done: Issue #128; isolated child branch; empty-watchlist persistence; stock-code normalization; group-bounded ordering; add-form feedback; source-state clarification; stale-request protection; threshold feedback; Shanghai-date CSV export; Shenwan sorting and empty states; regression guards; full automated validation.
- Current: code and automated regression work are complete; retain `active` until owner-side visual and business-use acceptance is recorded.
- Next: owner reviews the running page and records any visual or workflow observations; no merge occurs without explicit instruction.
- Blocked by: none.
