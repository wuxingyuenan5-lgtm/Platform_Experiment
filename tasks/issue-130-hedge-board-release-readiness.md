# Task: Hedge-board release readiness

Issue: #130
Status: active
Branch: `feature/issue-130-hedge-board-release-readiness`
Base commit: `ed095a16f686593b5115191052f3459357c067cd`

## Objective

Complete the remaining code-side release-readiness work for the unmerged Platform 0.9.1 hedge-fund dashboard without changing execution, accounting, customer-system or permission semantics.

## Scope

- account-scoped A-share watchlist persistence with optimistic concurrency and local fallback;
- dedicated hedge-board Playwright E2E coverage;
- optional live free-provider smoke validation that does not make external uptime a mandatory CI dependency;
- final visual, data-quality and business-use acceptance checklist;
- Draft validation PR only; no merge into `main`.

## Protected semantics

- Frontend calls only Platform APIs.
- Research data remains non-authoritative for execution.
- No Live Write, Venue command, formal accounting or customer authority changes.
- No automatic merge into `main` or previous delivery branches.

## Verification

- backend Ruff, Pyright and tests;
- hedge-board layout guard and frontend type check/build;
- dedicated hedge-board Playwright suite;
- Platform CI, User System Browser E2E, Secret Scan and Version Consistency.

## Progress

- Current: implement account watchlist persistence and release-readiness validation surfaces.
- Next: run all checks, update the Draft PR handoff and leave the branch unmerged.
- Blocked by: owner-side visual acceptance requires an actual running deployment or local environment.
