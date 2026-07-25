# Task: EOD Reconciliation Public Schemas

Issue: #75
Status: review
Branch: `refactor/issue-75-eod-reconciliation-schemas`
Base commit: `13189a9262fefe654e708b1f706a27948f69d64f`

## Objective

Make one dedicated module the sole owner of EOD Reconciliation public status types and Pydantic request/response schemas while preserving exact API, validation and compatibility behavior.

## Non-goals

- No DDL, SQL, row mapping, report orchestration, review policy or route change.
- No EOD status/scale-gate logic change.
- No FinancialFact, Venue Reconciliation, Runtime or Live Write change.

## Expected changed files

- `platform-backend/app/eod_reconciliation_schemas.py`
- `platform-backend/app/eod_reconciliation.py`
- direct EOD schema and architecture tests
- `platform-backend/pyproject.toml`
- `docs/architecture/OWNERSHIP.md`
- `docs/codex/current-state.md`
- `docs/engineering/TECHNICAL_DEBT.md`
- `scripts/check-documentation-consistency.py`
- `CHANGELOG.md`
- this task packet

## Protected semantics

- Exact class/type names and object identity through `app.eod_reconciliation`.
- Exact field aliases, required fields, validators and validation messages.
- Exact EOD OpenAPI request/response schemas.
- Existing routes, DDL/SQL, orchestration, review decisions and scale-gate logic.
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

- Stop if any field, alias, validation or OpenAPI fragment must change.
- Stop if moving schemas requires changes to SQL, report logic, routes or EOD policy.
- Stop if any trading, accounting or Live Write semantic must change.

## Acceptance criteria

- [x] EOD public schemas/types have one authoritative owner.
- [x] Compatibility imports are identical Python objects.
- [x] JSON Schema/OpenAPI and validation behavior remain exact.
- [x] Existing EOD integration tests pass.
- [x] Ruff, Pyright, tests, Repository Safety, Runtime, Frontend and Secret Scan pass on the implementation head.
- [ ] All checks pass on the final documentation head.
- [x] Diff contains no unrelated cleanup.

## Progress

- Done: schema owner, compatibility imports, exact schema/validation evidence, architecture enforcement, progressive typing and existing EOD regressions are complete.
- Current: final PR-head Platform CI and Secret Scan.
- Next: mark PR ready and squash merge when every final-head check is green.
- Blocked by: none.

## Completion

- PR: #76
- Merge commit: recorded by the final squash merge of PR #76.
- Behavior changed: EOD public schema/type ownership moved to `eod_reconciliation_schemas.py`.
- Behavior intentionally unchanged: all EOD public, persistence, orchestration, review, scale-gate and Live Write semantics.
- Tests/CI: exact schema/validation tests plus full Backend/Runtime/Frontend/Repository Safety and Secret Scan required on final head.
- Follow-up debt: EOD Repository/Policy/Service remain separate staged Issues.
