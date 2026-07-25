# Task: EOD Reconciliation Repository

Issue: #77
Status: review
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
- `README.md`
- `AGENTS.md`
- `docs/architecture/OWNERSHIP.md`
- `docs/codex/current-state.md`
- `docs/database/README.md`
- `docs/engineering/TECHNICAL_DEBT.md`
- `scripts/check-repository-structure.py`
- `scripts/check-documentation-consistency.py`
- `CHANGELOG.md`
- this task packet

Temporary patch helper/workflow were permitted only to update large governance files through a bounded path and must be absent from the final diff.

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

- [x] Repository is the sole EOD DDL/direct-SQL/row-mapping owner.
- [x] `eod_reconciliation.py` and `eod_policy.py` contain no direct database access.
- [x] DDL checksum, report identity, review immutability and rollback evidence are exact.
- [x] Existing EOD integration and policy tests pass.
- [ ] Ruff, Pyright, tests, Repository Safety, Runtime, Frontend and Secret Scan pass on the final helper-free head.
- [x] Diff contains no unrelated cleanup.

## Progress

- Done: Repository extraction, orchestration/policy delegation, compatibility aliases, focused regression evidence, progressive typing and authoritative documentation.
- Current: remove the bounded temporary patch helper/workflow and validate the final helper-free PR head.
- Next: mark PR ready and squash merge when all checks are green.
- Blocked by: none.

## Completion

- PR: #78
- Merge commit: pending final squash merge.
- Behavior changed: persistence ownership moved to `eod_reconciliation_repository.py`; no public or business behavior changed.
- Behavior intentionally unchanged: all EOD identity, SQL semantics, report, review, scale-gate, orchestration, route and Live Write semantics.
- Tests/CI: Backend Ruff/Pyright/classified tests and focused EOD suites pass; final Repository Safety, Runtime, Frontend and Secret Scan required after temporary-file removal.
- Follow-up debt: EOD status/review Policy and Service remain separate staged Issues.
