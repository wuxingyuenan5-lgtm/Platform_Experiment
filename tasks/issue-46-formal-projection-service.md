# Task: Formal projection service extraction

Issue: #46
Status: ready for merge
Branch: `refactor/issue-46-formal-projection-service`
Base commit: `0e1e0f2599346aa80e0e663ce0c397e8c58c1e23`

## Objective

Extract formal Position/PnL/NAV calculations and rebuild orchestration into `app/financial_projection_service.py` while preserving all formulas, error contracts, repository transactions and API results.

## Non-goals

- No FinancialFact normalization or content-hash change.
- No repository SQL, DDL, row mapping or transaction change.
- No table, index, seed, migration or database-technology change.
- No route, API field or public schema change.
- No operational projection or trading-flow change.
- No credential, risk-control, Live Write or real-account activity.

## Allowed scope

- `platform-backend/app/financial_facts.py`.
- New `platform-backend/app/financial_projection_service.py`.
- Direct projection calculation, architecture and API-equivalence tests.
- `platform-backend/pyproject.toml`.
- `docs/codex/current-state.md`, `docs/architecture/README.md`, `docs/engineering/TECHNICAL_DEBT.md`, `CHANGELOG.md`, and this task packet.

## Protected semantics

- Average-cost and realized-PnL behavior for position increase, partial/full close and reversal.
- Contract multiplier and FX conversion of realized trading PnL.
- Funding, Swap, Fee and FX component aggregation.
- Incomplete-quality propagation and final total PnL.
- Latest fact timestamp used as projection update time.
- Rebuild pair/fact counts and audit payload.
- NAV account coverage, missing-account ordering, equity, quality and capital-base division.
- Existing 404/422 status codes and messages.
- Existing FinancialFact idempotency, normalization, repository transactions and API responses.

## Acceptance criteria

- [x] One Issue, one task packet, one branch and one PR.
- [x] `financial_projection_service.py` owns all formal projection calculations and orchestration.
- [x] `financial_facts.py` contains no projection formula implementation.
- [x] Existing projection compatibility functions remain callable.
- [x] Exact calculation and orchestration golden tests pass.
- [x] Existing accounting, normalization and repository rollback suites pass unchanged.
- [x] Projection ownership is machine-checked.
- [x] Projection service is included in progressive Pyright.
- [x] Backend dependency, Ruff, Pyright and all classified tests pass on implementation heads.
- [x] Runtime regression gates pass on implementation heads.
- [x] Secret Scan passes on implementation heads.
- [x] Documentation matches the final implementation.
- [ ] Final frozen-head frontend regression and complete Platform CI; evidence is recorded in PR #47 before merge.

## Risk and rollback

Risk: medium because formal accounting formulas move structurally.

Detection: pure calculation goldens, API/accounting equivalence, repository rollback tests and full cross-component CI.

Rollback: revert the final squash commit. No migration or external state is introduced.

## Progress

- Done: extracted Projection Service, preserved API compatibility, added formula/orchestration goldens, architecture ownership checks and progressive Pyright, and synchronized documentation.
- Current: final frozen-head Platform CI and independent Secret Scan.
- Next: update PR evidence and squash merge after every required job is green.
- Blocked by: none.

## Completion

- PR: #47.
- Merge commit: pending squash merge.
- Behavior changed: none; formal projection ownership only.
- Tests/CI: Backend and Runtime gates, Repository Safety and Secret Scan passed during implementation; final frozen-head evidence will be recorded in PR #47.
- Follow-up: database module decomposition remains separate work.
