# Task: Venue Reconciliation Service

Issue: #73
Status: review
Branch: `refactor/issue-73-venue-reconciliation-service`
Base commit: `7f8224a7b88f58caaeb08e3b4f48d5da5153e267`

## Objective

Make one framework-independent Service the sole owner of Venue Reconciliation use-case sequencing while preserving public APIs, EOD callers and all protected semantics.

## Non-goals

- No route-module extraction.
- No Runtime endpoint/payload/timeout/retry change.
- No SQL, DDL, transaction, FinancialFact, Difference, order-state, EOD or Live Write behavior change.
- No compatibility function removal.

## Expected changed files

- `platform-backend/app/venue_reconciliation_service.py`
- `platform-backend/app/venue_reconciliation.py`
- direct Venue Reconciliation architecture and Service tests
- `platform-backend/pyproject.toml`
- `docs/architecture/OWNERSHIP.md`
- `docs/codex/current-state.md`
- `docs/engineering/TECHNICAL_DEBT.md`
- `scripts/check-documentation-consistency.py`
- `CHANGELOG.md`
- `AGENTS.md`
- `README.md`
- this task packet

Conditional only when existing compatibility assertions require synchronization:

- direct EOD or Venue Reconciliation integration tests.

## Protected semantics

- Exact public routes, schemas, status codes and detail strings.
- Existing EOD imports and partial-error capture behavior.
- Runtime paths, parameters, timeout and response handling.
- FinancialFact identity/import and Difference identity/precedence.
- Database Schema, SQL, transactions and order state transitions.
- Platform and Runtime Live Write remain disabled by default.

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

- Stop if a public status/detail or EOD error representation must change.
- Stop if route extraction becomes necessary.
- Stop if any trading, accounting, persistence or Live Write semantic must change.
- Stop if the change expands beyond direct Service/facade ownership evidence.

## Acceptance criteria

- [x] Service is the sole use-case sequencing owner.
- [x] Service has no FastAPI, APIRouter, configured HTTP or direct SQL dependency.
- [x] Facade owns exact domain-error-to-HTTP mapping, compatibility delegates and routes.
- [x] Existing APIs and EOD callers pass unchanged.
- [x] Ruff, Pyright, Backend tests, Repository Safety and Runtime tests pass on the implementation head.
- [ ] Frontend and Secret Scan pass on the final documentation head.
- [x] Diff contains no unrelated cleanup.

## Progress

- Done: Service/facade extraction, domain errors, compatibility mappings, architecture enforcement, progressive typing and Backend/EOD regressions are complete.
- Current: final PR-head Platform CI and Secret Scan.
- Next: mark PR ready and squash merge when every final-head check is green.
- Blocked by: none.

## Completion

- PR: #74
- Merge commit: recorded by the final squash merge of PR #74.
- Behavior changed: Venue Reconciliation use-case ownership moved from the FastAPI facade to `venue_reconciliation_service.py`.
- Behavior intentionally unchanged: all public, EOD, Runtime, FinancialFact, Difference, persistence, order-state and Live Write semantics.
- Tests/CI: focused Service/domain-error tests plus full Backend/Runtime/Frontend/Repository Safety and Secret Scan required on final head.
- Follow-up debt: dedicated route-module extraction is optional and requires separate usage/value evidence; it is not required for the current maintenance boundary.
