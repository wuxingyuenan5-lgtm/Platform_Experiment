# Issue #59 — Preserve Decimal precision in venue fill reconciliation

Issue: #59
Status: done
Branch: `fix/issue-59-decimal-venue-fill-reconciliation`
Base commit: `9f93c83eb662c889b3109d27df52e0588250df3d`

## Objective

Remove SQLite binary floating-point aggregation from venue fill quantity reconciliation while preserving exact existing reconciliation behavior.

## Background

`venue_reconciliation.compare_order` aggregated stored text quantities with `SUM(CAST(quantity AS REAL))`. SQLite REAL uses binary floating point and can manufacture a mismatch for exact decimal quantities.

## Non-goals

- No Venue Reconciliation module split.
- No Schema, Migration, Seed or persisted-value change.
- No change to fill ingestion, status mapping, FinancialFact identity, accounting formulas or Runtime contracts.

## Allowed scope

- Venue fill quantity comparison.
- Direct venue reconciliation tests.
- Current-state, Changelog and this task packet.

## Expected changed files

- `platform-backend/app/venue_reconciliation.py`
- `platform-backend/tests/test_venue_reconciliation_decimal.py`
- `docs/codex/current-state.md`
- `CHANGELOG.md`
- `tasks/issue-59-decimal-venue-fill-reconciliation.md`

## Protected semantics

- Reconciliation endpoint and response fields.
- Difference keys, types and status transitions.
- Order/fill persistence and operational/formal accounting.
- Database Schema and all Live Write defaults.

## Required verification

- Direct venue reconciliation regression tests.
- Platform Backend Ruff and classified tests.
- Repository Safety, Runtime, Frontend and independent Secret Scan.

## Stop conditions

- A fix requires changing stored quantity format or database Schema.
- Existing difference identity or Runtime contracts would change.
- Work expands into the broader reconciliation split.

## Implementation plan

1. Read stored fill quantity rows without numeric coercion.
2. Sum with Python `Decimal`.
3. Add fractional/high-precision regression coverage.
4. Run full CI and review the final Diff.

## Risk and rollback

Risk: low.

- Failure mode: reconciliation comparison changes unexpectedly.
- Detection: existing and new venue reconciliation tests.
- Rollback: revert the final squash commit.

## Progress

- Done: exact Decimal implementation, focused regression test, documentation and full pre-freeze CI.
- Current: final frozen-head verification and squash merge.
- Next: close Issue and begin the next independent optimization.
- Blocked by: nothing.

## Completion

- PR: #60
- Merge commit: recorded by the final squash merge on PR #60.
- Behavior changed: exact Decimal aggregation replaces SQLite REAL aggregation.
- Behavior intentionally unchanged: all APIs, identities, statuses, persistence and accounting.
- Tests/CI: Platform CI `30109481940` success; Secret Scan `30109482006` success. Final frozen-head runs must also pass before merge.
- Follow-up debt: broader Venue Reconciliation decomposition remains separate.
