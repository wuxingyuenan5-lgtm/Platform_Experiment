# Issue #63 — Unify platform order submission orchestration

Issue: #63
Status: active
Branch: `refactor/issue-63-order-submission-orchestration`
Base commit: `216225ecc3a2b1b2bc0e1737b0c69a5f78adc470`

## Objective

Use one implementation for local Order creation, Safety enforcement, Runtime submission, unknown-result handling, Event application and response mapping while preserving both existing public entry points.

## Background

`app.trading.submit_order` and `app.trade_command_execution.submit_trade_command_order` independently implemented nearly the same submission workflow. The duplicate paths could drift on Order fields, Safety arguments, Runtime error handling and Event validation.

## Non-goals

- No API route removal or deprecation-policy change.
- No Order/Fill Schema, Migration, Seed or transaction change.
- No Runtime V1 contract change.
- No Event application, operational Position/PnL or reconciliation redesign.
- No broader `trading.py` split.
- No credential, production or Live Write change.

## Allowed scope

- Submission orchestration ownership in `trade_command_execution.py`.
- Compatibility delegation from `trading.submit_order`.
- Behavioral/payload and architecture tests.
- Ownership, architecture, Current State, Changelog and task evidence.

## Expected changed files

- `platform-backend/app/trade_command_execution.py`
- `platform-backend/app/trading.py`
- `platform-backend/tests/test_order_submission_orchestration.py`
- `platform-backend/tests/test_architecture_order_submission.py`
- `docs/architecture/OWNERSHIP.md`
- `docs/architecture/README.md`
- `scripts/check-documentation-consistency.py`
- `docs/codex/current-state.md`
- `CHANGELOG.md`
- `tasks/issue-63-order-submission-orchestration.md`

Conditional:

- Modify an existing direct test only when its patch target or expectation is intentionally part of the preserved compatibility surface.

## Protected semantics

- Deprecated `/trading/orders` route and response.
- Legacy Runtime payload keys and absence of Strategy/V1-only fields.
- TradeCommand V1 contract fields, Strategy identity and `reduceOnly`.
- Limit-order validation and all Safety checks.
- Local Order IDs, command IDs, persisted fields and initial status.
- `result_unknown` on Runtime transport/strict-contract uncertainty.
- Event validation/application, operational projections and reconciliation.
- Database Schema and both Live Write defaults.

## Required verification

- Legacy payload and filled-flow equivalence.
- TradeCommand V1 payload and typed Event validation.
- Timeout/invalid-contract `result_unknown` behavior.
- Existing trading, recovery, TradeCommand, Runtime contract and live-safety suites.
- Architecture sole-owner checks.
- Ruff, progressive Pyright, full Platform CI and independent Secret Scan.

## Stop conditions

- Legacy payload must change to complete the refactor.
- Runtime V1 contract or Event semantics must change.
- Order/Fill persistence or transaction boundaries must change.
- Work expands into Event projection, reconciliation or route removal.
- Live Safety becomes less strict.

## Implementation plan

1. Generalize the existing typed submission module with explicit legacy/V1 modes.
2. Replace legacy implementation with a compatibility delegate.
3. Add payload, error-semantic and sole-owner evidence.
4. Synchronize architecture ownership and engineering state.
5. Run full CI and inspect the final Diff.

## Risk and rollback

Risk: medium.

- Failure modes: payload drift, changed Safety arguments, changed unknown-result handling or duplicated Order writes.
- Detection: exact payload tests, failure-path tests, architecture checks and existing trading/live-safety suites.
- Rollback: revert the final squash commit.

## Progress

- Done: compatibility audit, single-owner implementation, legacy/V1 payload preservation and architecture tests.
- Current: standard full CI and final Diff review.
- Next: freeze evidence, mark ready, squash merge and close Issue.
- Blocked by: nothing.

## Completion

- PR: #64
- Merge commit:
- Behavior changed: internal ownership only; duplicate orchestration becomes one implementation.
- Behavior intentionally unchanged: both public paths, payload modes, Safety, persistence, Runtime and Event behavior.
- Tests/CI: pending standard final-head runs.
- Follow-up debt: broader Venue Reconciliation decomposition remains next after this workstream.
