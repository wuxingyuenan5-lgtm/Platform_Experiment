# Task: Venue Reconciliation Runtime Client

Issue: #71
Status: review
Branch: `refactor/issue-71-venue-reconciliation-runtime-client`
Base commit: `79367060c023e3f14af649ea9538b53cadaf4873`

## Objective

Make one small module the sole owner of Venue Reconciliation Runtime HTTP configuration and GET transport while preserving all public and reconciliation behavior.

## Non-goals

- No Service or route-facade extraction.
- No endpoint, payload, timeout, retry, database, accounting, Difference or order-state change.
- No credential, production or Live Write change.

## Allowed scope

- Venue Reconciliation Runtime transport and direct integration tests.
- Architecture/type ownership registration.
- Directly affected architecture, current-state, technical-debt and changelog documentation.

## Expected changed files

- `platform-backend/app/venue_reconciliation_runtime_client.py`
- `platform-backend/app/venue_reconciliation.py`
- `platform-backend/tests/test_venue_reconciliation_runtime_client.py`
- `platform-backend/tests/test_architecture_venue_reconciliation_runtime_client.py`
- `platform-backend/tests/test_venue_reconciliation.py`
- `platform-backend/pyproject.toml`
- `docs/architecture/OWNERSHIP.md`
- `docs/codex/current-state.md`
- `docs/engineering/TECHNICAL_DEBT.md`
- `scripts/check-documentation-consistency.py`
- `CHANGELOG.md`
- this task packet

Conditional only if a repository safety check requires it:

- `scripts/check-repository-structure.py`

## Protected semantics

- Runtime paths, query parameters, base URL and timeout values.
- Network failures map to Platform HTTP 503 with detail `Execution Runtime query failed`.
- Runtime 404 and other response-status handling.
- Order recovery, FinancialFact identity/import, Difference identity and precedence.
- Database Schema, transactions, position/PnL formulas and order state transitions.
- Platform and Runtime Live Write remain disabled by default.

## Context packet

Read only:

1. `AGENTS.md`;
2. `docs/codex/current-state.md`;
3. `docs/architecture/OWNERSHIP.md`;
4. `platform-backend/app/venue_reconciliation.py`;
5. `platform-backend/app/venue_reconciliation_repository.py`;
6. `platform-backend/tests/test_venue_reconciliation.py`;
7. direct architecture tests;
8. `platform-backend/pyproject.toml`.

## Required verification

```text
cd platform-backend
python -m ruff check app tests
python -m pyright
python -m pytest
cd ..
python scripts/check-repository-structure.py
python scripts/check-documentation-consistency.py
```

Final delivery also requires full Platform CI and independent Secret Scan on the final PR head.

## Stop conditions

- Stop if endpoint/payload/retry semantics must change.
- Stop if a Service or route extraction becomes necessary.
- Stop if any financial, trading, persistence or Live Write semantic must change.
- Stop if the change exceeds Expected changed files without direct CI or architecture evidence.

## Acceptance criteria

- [x] Runtime transport has one authoritative owner.
- [x] Compatibility delegate and external behavior are preserved.
- [x] Focused unit, architecture and existing integration tests pass.
- [x] Ruff, Pyright, repository and documentation checks pass.
- [ ] Full Platform CI and Secret Scan pass on the final documentation head.
- [x] Diff contains no unrelated cleanup.

## Risk and rollback

Risk: low-to-medium

- Failure modes: wrong URL/params/timeout, incorrect network-error mapping, stale monkeypatch target.
- Detection: focused transport tests, integration tests and full CI.
- Rollback: revert the final squash commit.

## Progress

- Done: Runtime Client, compatibility delegate, integration/architecture tests, progressive typing and authoritative documentation are complete.
- Current: final PR-head Platform CI and Secret Scan.
- Next: mark PR ready and squash merge when all checks are green.
- Blocked by: none.

## Completion

- PR: #72
- Merge commit: recorded by the final squash merge of PR #72.
- Behavior changed: Runtime GET transport ownership moved to `venue_reconciliation_runtime_client.py`.
- Behavior intentionally unchanged: every Runtime query, response-status path, reconciliation identity, API, transaction, order state and Live Write default.
- Tests/CI: focused Runtime Client tests plus Backend/Runtime/Frontend/Repository Safety and Secret Scan required on final head.
- Follow-up debt: Reconciliation Service and route facade remain separate future Issues.
