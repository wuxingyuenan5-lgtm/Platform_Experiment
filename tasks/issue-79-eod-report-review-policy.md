# Task: EOD Report and Review Policy

Issue: #79
Status: active
Branch: `refactor/issue-79-eod-report-review-policy`
Base commit: `ed4a73e94160bac5d8f56fd2762a5716fef1bc8b`

## Objective

Make one pure module the sole owner of EOD report status, scale-gate and immutable-review decisions while preserving exact report, transaction and API behavior.

## Non-goals

- No EOD Service or route-facade extraction.
- No SQL, DDL, query, transaction, identity, partial-failure string or API change.
- No order-window, cross-domain orchestration, FinancialFact, Venue Reconciliation, Runtime or Live Write change.

## Expected changed files

- `platform-backend/app/eod_reconciliation_policy.py`
- `platform-backend/app/eod_reconciliation.py`
- `platform-backend/app/eod_reconciliation_repository.py`
- `platform-backend/app/eod_policy.py`
- direct EOD Policy unit/architecture tests
- existing EOD repository/integration tests only for compatibility evidence
- `platform-backend/pyproject.toml`
- `docs/architecture/OWNERSHIP.md`
- `docs/codex/current-state.md`
- `docs/engineering/TECHNICAL_DEBT.md`
- `scripts/check-documentation-consistency.py`
- `CHANGELOG.md`
- this task packet

A bounded temporary patch helper/workflow may update large existing files but must be absent from the final diff.

## Protected semantics

- Exact initial report status and scale-gate precedence.
- Exact historical open/accepted Difference gate behavior.
- Exact review replay, conflict and approval-eligibility behavior.
- Exact repository read/decision/write atomicity and rollback.
- Exact exception identities and FastAPI status/detail mapping.
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

Final delivery requires full Platform CI and independent Secret Scan on the final PR head.

## Stop conditions

- Stop if policy extraction would move a database read/write outside the repository transaction.
- Stop if any status, scale-gate, review, API, migration or Live Write behavior must change.
- Stop if the task requires Service or route extraction.

## Acceptance criteria

- [ ] One pure Policy owns report/status/scale-gate/review decisions.
- [ ] Repository review remains atomic with exact replay/conflict/approval behavior.
- [ ] Orchestration and operational gate coordinator delegate without duplicate decisions.
- [ ] Exhaustive policy Goldens and architecture purity checks pass.
- [ ] Existing EOD integration/repository tests pass.
- [ ] Ruff, Pyright, Repository Safety, Runtime, Frontend and Secret Scan pass.
- [ ] Diff contains no unrelated cleanup or temporary helper/workflow.

## Progress

- Done: main, Issue, branch and exact decision boundaries verified.
- Current: implement pure Policy and compatibility delegation.
- Next: focused tests, final-head CI, review and squash merge.
- Blocked by: none.

## Completion

- PR:
- Merge commit:
- Behavior changed: none intended.
- Behavior intentionally unchanged: all EOD report, gate, review, transaction, API and Live Write semantics.
- Tests/CI:
- Follow-up debt: EOD Service and route facade remain separate staged Issues.
