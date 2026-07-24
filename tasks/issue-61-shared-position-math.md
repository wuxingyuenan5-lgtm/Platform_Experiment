# Issue #61 — Extract shared position calculation policy

Issue: #61
Status: done
Branch: `refactor/issue-61-shared-position-math`
Base commit: `a762692096f3960106cf492c7f3142479f815779`

## Objective

Make one pure function the authoritative per-fill position quantity, average price and realized PnL calculation for both operational and formal projections.

## Background

`app.trading` and `app.financial_projection_service` contained equivalent copies of `calculate_position_update`. Maintaining two accounting formulas created a future drift risk even though their results were identical.

## Non-goals

- No formula, rounding, multiplier, FX or persistence change.
- No broader `trading.py`, order submission or FinancialFact refactor.
- No API, Schema, Migration, Seed, Runtime contract, credential or Live Write change.

## Allowed scope

- New pure Position Math owner.
- Operational/formal compatibility imports.
- Golden and architecture tests.
- Ownership, Pyright, current-state, technical debt and Changelog synchronization.

## Expected changed files

- `platform-backend/app/position_math.py`
- `platform-backend/app/trading.py`
- `platform-backend/app/financial_projection_service.py`
- `platform-backend/tests/test_position_calculation.py`
- `platform-backend/tests/test_architecture_position_math.py`
- `platform-backend/tests/test_architecture_financial_projection_service.py`
- `platform-backend/pyproject.toml`
- `docs/architecture/OWNERSHIP.md`
- `docs/architecture/README.md`
- `scripts/check-documentation-consistency.py`
- `docs/engineering/TECHNICAL_DEBT.md`
- `docs/codex/current-state.md`
- `CHANGELOG.md`
- `tasks/issue-61-shared-position-math.md`

Conditional:

- Update another architecture checker only if it currently hard-codes the old formula owners.

## Protected semantics

- Exact function inputs and return tuple.
- Long, short, increase, partial close, full close and flip results.
- Existing import paths from `app.trading`, `app.financial_projection_service` and `app.financial_facts`.
- Multiplier, FX, formal/operational persistence and transaction behavior.
- Database Schema and both Live Write defaults.

## Required verification

- Position Math golden cases and compatibility identity tests.
- Existing trading and formal projection/accounting suites.
- Architecture ownership and sole-definition checks.
- Ruff and progressive Pyright.
- Repository Safety, full Backend/Runtime/Frontend CI and independent Secret Scan.

## Stop conditions

- Any golden result changes.
- Extraction requires changing persistence, transaction or Runtime boundaries.
- Compatibility import identity cannot be preserved without a public API change.
- Work expands into order submission or broader trading decomposition.

## Implementation plan

1. Create the pure calculation owner with the existing formula unchanged.
2. Replace both implementations with imports and preserve compatibility aliases.
3. Add behavior, identity and sole-definition evidence.
4. Register Ownership and Pyright boundaries.
5. Run full CI and review the final Diff.

## Risk and rollback

Risk: medium-low.

- Failure mode: one projection path uses a changed function or compatibility import breaks.
- Detection: exact golden suites, identity tests and existing accounting/trading regression suites.
- Rollback: revert the final squash commit.

## Progress

- Done: implementation, ten Golden cases, compatibility identity, sole-definition/purity checks, Ownership, Pyright and complete pre-freeze CI.
- Current: final frozen-head verification and squash merge.
- Next: close Issue and begin order-submission unification as a separate workstream.
- Blocked by: nothing.

## Completion

- PR: #62
- Merge commit: recorded by the final squash merge on PR #62.
- Behavior changed: ownership only; two copies become one pure implementation.
- Behavior intentionally unchanged: every calculation result and all external/persistence behavior.
- Tests/CI: Platform CI `30110735275` success; Secret Scan `30110735238` success. Final frozen-head runs must also pass before merge.
- Follow-up debt: order submission unification remains the next independent workstream.
