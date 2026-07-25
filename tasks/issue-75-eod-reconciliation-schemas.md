# Task: EOD Reconciliation Public Schemas

Issue: #75
Status: active
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

- [ ] EOD public schemas/types have one authoritative owner.
- [ ] Compatibility imports are identical Python objects.
- [ ] JSON Schema/OpenAPI and validation behavior remain exact.
- [ ] Existing EOD integration tests pass.
- [ ] Ruff, Pyright, tests, Repository Safety, Runtime, Frontend and Secret Scan pass.
- [ ] Diff contains no unrelated cleanup.

## Progress

- Done: baseline, Issue, branch and protected schema surface verified.
- Current: extract schemas and add equivalence evidence.
- Next: final-head CI, review and squash merge.
- Blocked by: none.

## Completion

- PR:
- Merge commit:
- Behavior changed: none intended.
- Behavior intentionally unchanged: all EOD public, persistence, orchestration, review, scale-gate and Live Write semantics.
- Tests/CI:
- Follow-up debt: EOD Repository/Policy/Service remain separate staged Issues.
