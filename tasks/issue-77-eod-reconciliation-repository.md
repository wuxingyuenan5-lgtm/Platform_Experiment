# Task: EOD Reconciliation Repository

Issue: #77
Status: active
Branch: `refactor/issue-77-eod-reconciliation-repository`
Base commit: `1b12d048a2de3c01a9e74a02ff2fc11fd6eb1ae5`

## Objective

Make one repository module the sole owner of EOD Reconciliation DDL, direct SQL, row mapping and persistence transactions while preserving report, review, scale-gate and API behavior.

## Non-goals

- No report status/scale-gate formula or review-decision change.
- No partial-failure string, cross-module orchestration or route change.
- No table/index/migration, FinancialFact, Venue Reconciliation, Runtime or Live Write change.

## Expected changed files

- `platform-backend/app/eod_reconciliation_repository.py`
- `platform-backend/app/eod_reconciliation.py`
- `platform-backend/app/eod_policy.py`
- direct EOD repository/architecture tests
- existing EOD integration/policy tests only when compatibility assertions require synchronization
- `platform-backend/pyproject.toml`
- `docs/architecture/OWNERSHIP.md`
- `docs/codex/current-state.md`
- `docs/engineering/TECHNICAL_DEBT.md`
- `scripts/check-documentation-consistency.py`
- `CHANGELOG.md`
- this task packet

## Protected semantics

- Exact EOD DDL bytes, tables, indexes and startup behavior.
- Exact report natural/idempotency identity and conflict behavior.
- Exact query predicates, parameter order and result ordering.
- Exact report row mapping and SLA calculation.
- Exact review idempotency, immutability, approval gate and transaction atomicity.
- Exact order-window and outstanding-Difference scale-gate behavior.
- Existing report orchestration, partial-failure strings, routes and both Live Write defaults.

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

- Stop if preserving review atomicity requires changing review-decision semantics.
- Stop if any report/scale-gate formula, route, migration or Live Write behavior must change.
- Stop if SQL extraction requires broad changes outside EOD Repository, Policy and direct callers.

## Acceptance criteria

- [ ] Repository is the sole EOD DDL/direct-SQL/row-mapping owner.
- [ ] `eod_reconciliation.py` and `eod_policy.py` contain no direct database access.
- [ ] DDL checksum, report identity, review immutability and rollback evidence are exact.
- [ ] Existing EOD integration and policy tests pass.
- [ ] Ruff, Pyright, tests, Repository Safety, Runtime, Frontend and Secret Scan pass.
- [ ] Diff contains no unrelated cleanup.

## Progress

- Done: baseline, Issue, branch and protected persistence semantics verified.
- Current: extract Repository and preserve compatibility delegates.
- Next: final-head CI, review and squash merge.
- Blocked by: none.

## Completion

- PR:
- Merge commit:
- Behavior changed: none intended.
- Behavior intentionally unchanged: all EOD identity, SQL, report, review, scale-gate, orchestration, route and Live Write semantics.
- Tests/CI:
- Follow-up debt: EOD status/review Policy and Service remain separate staged Issues.
