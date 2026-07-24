# Issue #65 — Extract Venue Reconciliation public schemas

Issue: #65
Status: active
Branch: `refactor/issue-65-venue-reconciliation-schemas`
Base commit: `2a410aff8110502a54b862d7a6aa6d959c8efdf5`

## Objective

Move Venue Reconciliation public request/response DTOs and status Literal types into one dedicated authoritative module while preserving exact API and import compatibility.

## Background

`app.venue_reconciliation` currently owns public Pydantic models together with DDL, SQL, Runtime queries, FinancialFact import, comparison policy, audit, persistence and routes. Schema ownership is the safest first decomposition stage.

## Non-goals

- No SQL, DDL, Runtime HTTP, comparison, difference persistence, audit or route logic change.
- No API path, field, alias, default, validation, error, identity or transaction change.
- No Schema, Migration, Seed, credential, production or Live Write change.
- No Difference Policy, Repository, Runtime Client or Service extraction in this Issue.

## Allowed scope

- New Venue Reconciliation schema owner.
- Compatibility imports/re-exports from the existing module.
- Exact schema/OpenAPI and architecture evidence.
- Ownership, Pyright, Current State, technical debt and Changelog synchronization.

## Expected changed files

- `platform-backend/app/venue_reconciliation_schemas.py`
- `platform-backend/app/venue_reconciliation.py`
- `platform-backend/tests/test_venue_reconciliation_schemas.py`
- `platform-backend/tests/test_architecture_venue_reconciliation_schemas.py`
- `platform-backend/pyproject.toml`
- `docs/architecture/OWNERSHIP.md`
- `docs/architecture/README.md`
- `scripts/check-documentation-consistency.py`
- `docs/engineering/TECHNICAL_DEBT.md`
- `docs/codex/current-state.md`
- `CHANGELOG.md`
- `tasks/issue-65-venue-reconciliation-schemas.md`

Conditional:

- Update an existing API/schema snapshot test only if the new owner must be registered in that existing test rather than a focused new test.

## Protected semantics

- Every model class name and public Literal type.
- Field names, aliases, required/default values, constraints and JSON serialization.
- Existing imports from `app.venue_reconciliation`.
- Route paths, response models, HTTP errors and OpenAPI contract.
- Reconciliation SQL, identities, statuses, transactions and external calls.
- Database Schema and both Live Write defaults.

## Required verification

- Exact class/type identity through old and new import paths.
- Exact model JSON Schema and relevant OpenAPI fragments.
- Sole-definition and dependency architecture checks.
- Existing Venue Reconciliation, EOD and live-safety suites.
- Ruff and progressive Pyright.
- Repository Safety, full Backend/Runtime/Frontend CI and independent Secret Scan.

## Stop conditions

- Any JSON Schema or OpenAPI fragment changes.
- Existing import identity cannot be preserved.
- Extraction requires modifying SQL, routes, comparison logic or Runtime calls.
- Work expands into another reconciliation decomposition stage.

## Implementation plan

1. Inventory all public Venue Reconciliation models and Literal types.
2. Move definitions without changing source text or order.
3. Import/re-export exact objects from the legacy module.
4. Add schema, OpenAPI, identity and sole-owner evidence.
5. Register Ownership and Pyright, then run full CI.

## Risk and rollback

Risk: low-medium.

- Failure modes: schema drift, broken import identity or circular dependency.
- Detection: exact JSON Schema/OpenAPI snapshots, identity tests and existing API suites.
- Rollback: revert the final squash commit.

## Progress

- Done: Issue and branch created.
- Current: model inventory and extraction design.
- Next: implementation, direct verification and full CI.
- Blocked by: nothing.

## Completion

- PR:
- Merge commit:
- Behavior changed: schema ownership only.
- Behavior intentionally unchanged: every public contract and all reconciliation behavior.
- Tests/CI:
- Follow-up debt: Difference Policy extraction is the next independent Venue Reconciliation stage.
