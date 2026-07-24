# Task: FinancialFact golden equivalence and schema extraction

Issue: #40
Status: active
Branch: `refactor/issue-40-financial-fact-schemas`
Base commit: `07a2a843b590277acd2b0d50c6e4ac9bc584f9c9`

## Objective

Create an executable equivalence boundary for formal accounting and extract only the public FinancialFact/formal-accounting Pydantic models from `app/financial_facts.py` into one authoritative schema module.

## Non-goals

- No SQL, repository, normalization or projection implementation movement.
- No formula, rounding, hashing, FX, average-cost or rebuild behavior change.
- No database schema or migration change.
- No API field rename or compatibility removal.
- No Live Write or real-account activity.

## Allowed scope

- `platform-backend/app/financial_facts.py`.
- New `platform-backend/app/financial_fact_schemas.py`.
- Direct FinancialFact/formal-accounting tests.
- Architecture/ownership tests and repository-structure checks.
- `platform-backend/pyproject.toml` progressive Pyright include list.
- `docs/codex/current-state.md`, architecture and technical-debt documentation.
- `CHANGELOG.md` and this task packet.

## Protected semantics

- Client and external idempotency identities.
- Normalized content hash.
- Currency, quantity unit and contract multiplier snapshots.
- Average-cost, realized and unrealized PnL formulas.
- Trading, Funding, Swap, Fee, FX and Total attribution.
- Formal Position, PnL and NAV rebuild results.
- Existing public API field names, aliases and response shapes.

## Minimal context packet

1. `AGENTS.md`.
2. `docs/codex/current-state.md`.
3. `docs/engineering/TECHNICAL_DEBT.md` TD-002.
4. `platform-backend/app/financial_facts.py`.
5. `platform-backend/tests/test_financial_facts.py`.
6. Direct formal-accounting and schema-ownership tests discovered during implementation.
7. `platform-backend/pyproject.toml`.
8. `scripts/check-repository-structure.py`.

Do not scan unrelated frontend, Runtime or historical planning documents unless a failing regression directly requires them.

## Acceptance criteria

- [ ] One Issue, one task packet, one branch and one PR.
- [ ] Public financial schema classes have one authoritative owner.
- [ ] Existing `app.financial_facts` imports remain identity-compatible.
- [ ] Golden equivalence covers protected hashing, FX, multiplier, average-cost, component-PnL and rebuild behavior already implemented.
- [ ] No SQL or formula diff is present.
- [ ] Extracted schemas are included in progressive Pyright.
- [ ] Repository structure/ownership checks prevent schema duplication.
- [ ] Backend dependency, Ruff, Pyright and all classified tests pass.
- [ ] Runtime and frontend regression gates pass.
- [ ] Secret Scan passes.
- [ ] Documentation matches the final implementation.

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

Risk: medium because auditable financial interfaces are structurally moved.

Detection: schema identity tests, golden accounting equivalence, full classified suites and cross-component regression CI.

Rollback: revert the final squash commit. No persistent schema, external state or Live Write setting is changed.

## Progress

- Done: verified `main@07a2a843...`, no open PRs, created Issue #40 and the unique Issue-numbered branch.
- Current: inventory public models and existing golden coverage.
- Next: add missing equivalence tests, extract schemas, preserve compatibility aliases, run CI.
- Blocked by: none.

## Completion

- PR: pending.
- Merge commit: pending.
- Behavior changed: none intended; schema ownership only.
- Tests/CI: pending.
- Follow-up: repository, normalization and projection-service extraction require separate Issues and PRs.
