# Task: FinancialFact persistence repository extraction

Issue: #42
Status: ready for merge
Branch: `refactor/issue-42-financial-fact-repository`
Base commit: `052cb1ddb678197eee2f81ef81542c0f8f063304`

## Objective

Extract all direct SQLite access for immutable FinancialFact and formal-accounting projections into `app/financial_fact_repository.py` while preserving current SQL semantics and transaction boundaries.

## Non-goals

- No normalization-policy extraction.
- No projection-service extraction.
- No formula, rounding, hashing, FX, multiplier, average-cost or PnL change.
- No table, index, seed, migration or database-technology change.
- No route, API field or compatibility removal.
- No Live Write or real-account activity.

## Allowed scope

- `platform-backend/app/financial_facts.py`.
- New `platform-backend/app/financial_fact_repository.py`.
- Direct FinancialFact/formal-accounting and architecture tests.
- `platform-backend/pyproject.toml`.
- `scripts/check-repository-structure.py` when needed to enforce ownership.
- `docs/codex/current-state.md`, `docs/architecture/README.md`, `docs/database/README.md`, `docs/engineering/TECHNICAL_DEBT.md`, `CHANGELOG.md`, and this task packet.

## Protected semantics

- Fact identity and payload-conflict behavior.
- Fact insert and audit event remain one transaction.
- Formal Position and PnL upsert remain one transaction.
- Rebuild pair discovery, clear ordering and audit evidence remain equivalent.
- NAV snapshot and audit event remain one transaction.
- Query ordering and API response shapes remain unchanged.
- Existing SQL is moved without business-semantic rewriting.

## Minimal context packet

1. `AGENTS.md`.
2. `docs/codex/current-state.md`.
3. `docs/engineering/TECHNICAL_DEBT.md` TD-002.
4. `platform-backend/app/financial_facts.py`.
5. `platform-backend/app/financial_fact_schemas.py`.
6. `platform-backend/tests/test_financial_facts.py`.
7. `platform-backend/tests/test_architecture_financial_fact_schemas.py`.
8. `platform-backend/pyproject.toml`.
9. `scripts/check-repository-structure.py`.

Do not modify unrelated Runtime, frontend or trading modules unless a proven regression requires it.

## Acceptance criteria

- [x] One Issue, one task packet, one branch and one PR.
- [x] Repository module owns all FinancialFact/formal-accounting direct SQL access.
- [x] `financial_facts.py` contains no `connection()` call or SQL statement.
- [x] Schema compatibility exports and service function imports remain unchanged.
- [x] Existing accounting golden tests pass unchanged.
- [x] Transaction-boundary tests cover fact+audit, Position+PnL, rebuild-clear and NAV+audit atomicity.
- [x] Repository ownership is machine-checked.
- [x] Repository module is included in progressive Pyright.
- [x] Backend dependency, Ruff, Pyright and all classified tests pass.
- [x] Runtime regression gates pass.
- [x] Secret Scan passes.
- [x] Documentation matches the final implementation.
- [ ] Final frontend regression build and squash merge; evidence is recorded in PR #43.

## Verification commands

```text
python scripts/check-workstream.py
python scripts/check-repository-structure.py
cd platform-backend && python -m pip check
cd platform-backend && python -m ruff check app tests
cd platform-backend && python -m pyright
cd platform-backend && python -m pytest -m architecture
cd platform-backend && python -m pytest -m unit
cd platform-backend && python -m pytest -m integration
cd platform-backend && python -m pytest -m live_safety
```

Full Platform CI and independent Secret Scan are required before merge.

## Risk and rollback

Risk: medium because auditable SQL moves structurally.

Detection: repository ownership checks, transaction tests, unchanged financial golden suite and full cross-component CI.

Rollback: revert the final squash commit. No migration or external state is introduced.

## Progress

- Done: extracted SQL/row mapping/transaction units, preserved compatibility aliases, added forced-rollback tests, Pyright and machine ownership checks, and synchronized documentation.
- Current: final Platform CI and PR review evidence.
- Next: squash merge after every required job is green.
- Blocked by: none.

## Completion

- PR: #43.
- Merge commit: pending squash merge.
- Behavior changed: none; persistence ownership only.
- Tests/CI: Backend and Runtime gates plus Repository Safety and Secret Scan passed during implementation; final head evidence is recorded in PR #43.
- Follow-up: normalization-policy and projection-service extraction require separate Issues and PRs.
