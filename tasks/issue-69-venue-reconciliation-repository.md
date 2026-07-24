# Issue #69 — Extract Venue Reconciliation persistence repository

Issue: #69
Status: active
Branch: `refactor/issue-69-venue-reconciliation-repository`
Base commit: `c353db56edea96f529e897fd7d87ba11dc33a359`

## Objective

Make one repository the sole owner of Venue Reconciliation DDL, direct SQL, row mapping and protected persistence transactions.

## Background

After Schema and Difference Policy extraction, `app.venue_reconciliation` still combines external orchestration with all reconciliation persistence. Moving persistence next keeps the remaining service boundary explicit and testable.

## Non-goals

- No DDL text, table/index, Schema, Migration or Seed change.
- No Runtime Client, Service or route extraction.
- No reconciliation rule, Difference identity, API, FinancialFact or order-state behavior change.
- No credential, production or Live Write change.

## Allowed scope

- New repository Owner.
- Thin orchestration wrappers and compatibility aliases.
- DDL checksum, idempotency, rollback and architecture tests.
- Ownership, Pyright, Current State, technical debt and Changelog synchronization.

## Expected changed files

- `platform-backend/app/venue_reconciliation_repository.py`
- `platform-backend/app/venue_reconciliation.py`
- `platform-backend/tests/test_venue_reconciliation_repository.py`
- `platform-backend/tests/test_architecture_venue_reconciliation_repository.py`
- `platform-backend/pyproject.toml`
- `docs/architecture/OWNERSHIP.md`
- `docs/architecture/README.md`
- `scripts/check-documentation-consistency.py`
- `docs/engineering/TECHNICAL_DEBT.md`
- `docs/codex/current-state.md`
- `CHANGELOG.md`
- `tasks/issue-69-venue-reconciliation-repository.md`

Conditional:

- Update an existing focused test only if compatibility identity or rollback evidence cannot be isolated in the new tests.

## Protected semantics

- Exact DDL bytes and all table/index definitions.
- Every SQL query, predicate, ordering and selected field.
- Run/Difference IDs, idempotency and row mapping.
- Transaction commit/rollback boundaries.
- HTTP errors and orchestration order.
- Runtime, FinancialFact, Difference Policy and API behavior.
- Both Live Write defaults.

## Required verification

- Exact pre-extraction DDL SHA-256.
- Compatibility identity for `ensure_schema`, `audit`, `run_from_row`, `difference_from_row`.
- Difference idempotency and forced rollback.
- Run-completion forced rollback.
- Existing Venue Reconciliation/EOD/live-safety suites.
- Sole-SQL-owner architecture checks, Ruff and progressive Pyright.
- Full Platform CI and independent Secret Scan.

## Stop conditions

- Any DDL or SQL behavior must change.
- Error mapping or orchestration order must move into the repository.
- Extraction requires Runtime, FinancialFact, Policy or route changes.
- Work expands into another decomposition stage.

## Implementation plan

1. Move DDL, SQL, row mapping and persistence transactions unchanged.
2. Keep HTTP exceptions and external orchestration in the legacy module.
3. Preserve compatibility aliases.
4. Add checksum, idempotency, rollback and architecture evidence.
5. Register Ownership/Pyright and run full CI.

## Risk and rollback

Risk: medium.

- Failure modes: transaction drift, changed query ordering, broken compatibility or row mapping.
- Detection: exact checksum, forced rollback, identity and existing integration suites.
- Rollback: revert the final squash commit.

## Progress

- Done: persistence inventory, Issue/branch/PR and repository API design.
- Current: DDL/SQL/row-mapping extraction and transaction tests.
- Next: full CI, final review and merge.
- Blocked by: nothing.

## Completion

- PR: #70
- Merge commit:
- Behavior changed: persistence ownership only.
- Behavior intentionally unchanged: every SQL result, API and external effect.
- Tests/CI:
- Follow-up debt: Runtime Client extraction remains next.
