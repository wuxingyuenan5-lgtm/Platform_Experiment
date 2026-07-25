# Task: EOD Reconciliation Service

Issue: #81
Status: active
Branch: `refactor/issue-81-eod-reconciliation-service`
Base commit: `accb6ed010d27dfb467507c3a1e798f0071a5412`

## Objective

Make one framework-independent Service the sole owner of EOD report creation/read/list/review use-case sequencing while preserving exact API, partial-failure, persistence and Live Write behavior.

## Non-goals

- No dedicated EOD route-module extraction.
- No SQL, DDL, query, transaction, identity, Policy decision, partial-failure string or route change.
- No FinancialFact, Venue Reconciliation, Runtime, credential, production or Live Write change.

## Expected changed files

- `platform-backend/app/eod_reconciliation_service.py`
- `platform-backend/app/eod_reconciliation.py`
- direct EOD Service/facade architecture and behavior tests
- existing EOD integration tests only for compatibility evidence
- `platform-backend/pyproject.toml`
- `docs/architecture/OWNERSHIP.md`
- `docs/codex/current-state.md`
- `docs/engineering/TECHNICAL_DEBT.md`
- `scripts/check-documentation-consistency.py`
- `CHANGELOG.md`
- this task packet

A bounded temporary patch helper/workflow may update large existing files but must be absent from the final diff.

## Protected semantics

- Exact report natural/idempotency identity and hash.
- Exact order/account/economic-event/formal-rebuild/NAV sequencing.
- Exact partial-failure capture strings and precedence.
- Exact report completion, audit and outstanding-Difference gate order.
- Exact review transaction, audit and compatibility exception behavior.
- Exact 403/404/409/422 status and detail mapping.
- Existing facade monkeypatch targets and both Live Write defaults.

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

- Stop if existing `app.eod_reconciliation.*` monkeypatch targets cannot remain effective.
- Stop if any partial-failure, HTTP, Policy, persistence or Live Write behavior must change.
- Stop if the task requires route extraction or cross-domain owner changes.

## Acceptance criteria

- [ ] Service is the sole EOD use-case sequencing owner and imports no FastAPI/APIRouter/Query/get_settings.
- [ ] Facade retains compatibility delegates, per-call dependency wiring and exact HTTP mapping.
- [ ] Existing monkeypatch targets control Service dependencies.
- [ ] Existing EOD integration/repository/policy tests pass.
- [ ] Service/facade architecture and exact failure-mapping tests pass.
- [ ] Ruff, Pyright, Repository Safety, Runtime, Frontend and Secret Scan pass.
- [ ] Diff contains no unrelated cleanup or temporary helper/workflow.

## Progress

- Done: main, Issue, branch, existing monkeypatch targets and protected sequencing verified.
- Current: implement Service and thin facade delegation.
- Next: focused tests, final-head CI, review and squash merge.
- Blocked by: none.

## Completion

- PR:
- Merge commit:
- Behavior changed: none intended.
- Behavior intentionally unchanged: all EOD sequencing, errors, transactions, APIs and Live Write semantics.
- Tests/CI:
- Follow-up debt: dedicated EOD route module remains separate staged work.
