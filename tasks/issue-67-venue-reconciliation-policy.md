# Issue #67 — Extract Venue Reconciliation difference policy

Issue: #67
Status: active
Branch: `refactor/issue-67-venue-reconciliation-policy`
Base commit: `f8161116885a9263f0e0094b4826add6568b7136`

## Objective

Make one pure module the authoritative owner of Venue Reconciliation status mapping and Order/Position/Balance difference decisions while preserving exact persisted outputs.

## Background

`app.venue_reconciliation` previously combined Runtime/SQLite orchestration with pure mappings and comparison rules. Moving only the decision policy creates an independently testable boundary without changing persistence or external effects.

## Non-goals

- No DDL, Repository, Runtime Client, Service or route extraction.
- No SQL, transaction, Runtime call, FinancialFact import, audit or API change.
- No tolerance, rounding or business-rule redesign.
- No Schema, Migration, Seed, credential, production or Live Write change.

## Allowed scope

- New pure Difference Policy owner.
- Thin orchestration wrappers that retrieve local state and persist returned drafts.
- Golden and architecture tests.
- Ownership, Pyright, Current State, technical debt and Changelog synchronization.

## Expected changed files

- `platform-backend/app/venue_reconciliation_policy.py`
- `platform-backend/app/venue_reconciliation.py`
- `platform-backend/tests/test_venue_reconciliation_policy.py`
- `platform-backend/tests/test_architecture_venue_reconciliation_policy.py`
- `platform-backend/pyproject.toml`
- `docs/architecture/OWNERSHIP.md`
- `docs/architecture/README.md`
- `scripts/check-documentation-consistency.py`
- `docs/engineering/TECHNICAL_DEBT.md`
- `docs/codex/current-state.md`
- `CHANGELOG.md`
- `tasks/issue-67-venue-reconciliation-policy.md`

Conditional:

- Modify an existing focused reconciliation test only if direct wrapper-equivalence evidence cannot be expressed in the new test files.

## Protected semantics

- External-order status mappings and unknown-status fallback.
- Difference order, keys, types, entity types and references.
- Local/external JSON value shapes and Decimal formatting.
- Formal-position-first, operational-position fallback behavior.
- Balance comparison precedence: missing, currency, then equity.
- Every SQL statement, transaction, audit, Runtime call and API response.
- Database Schema and both Live Write defaults.

## Required verification

- Pure Golden drafts for all decision branches.
- Existing wrapper/API integration tests.
- Sole-owner and dependency-purity architecture checks.
- Ruff and progressive Pyright.
- Repository Safety, full Backend/Runtime/Frontend CI and independent Secret Scan.

## Stop conditions

- Any Difference key/value or decision order changes.
- Extraction requires moving SQL, persistence or Runtime access.
- A tolerance or reconciliation-rule redesign is needed.
- Work expands into another Venue Reconciliation stage.

## Implementation plan

1. Define immutable `DifferenceDraft` and pure mapping/decision functions.
2. Keep database retrieval and `create_difference` calls in the existing module.
3. Convert drafts to persisted differences without changing field values or order.
4. Add complete Golden and architecture evidence.
5. Register Ownership/Pyright and run full CI.

## Risk and rollback

Risk: medium-low.

- Failure modes: draft value drift, changed precedence or missed difference persistence.
- Detection: exact dataclass Goldens and existing reconciliation/EOD integration suites.
- Rollback: revert the final squash commit.

## Progress

- Done: pure policy, status mappings, Order/Position/Balance drafts, thin persistence wrappers, Golden and architecture tests.
- Current: standard full CI and final Diff review.
- Next: freeze evidence, mark ready, squash merge and close Issue.
- Blocked by: nothing.

## Completion

- PR: #68
- Merge commit:
- Behavior changed: decision ownership only.
- Behavior intentionally unchanged: every persisted difference and external behavior.
- Tests/CI: pending standard final-head runs.
- Follow-up debt: Venue Reconciliation Repository extraction remains the next stage.
