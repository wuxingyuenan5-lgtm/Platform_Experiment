# Task: FinancialFact normalization policy extraction

Issue: #44
Status: active
Branch: `refactor/issue-44-financial-fact-normalization`
Base commit: `c892f2db16d6b22d94976966e472142e184037b0`

## Objective

Extract FinancialFact normalization and normalized-content hashing into `app/financial_fact_normalization.py` while preserving every current normalized value, error status, content hash and accounting result.

## Non-goals

- No projection-service extraction.
- No repository SQL, DDL, row mapping or transaction change.
- No formula, rounding, average-cost or PnL change.
- No table, index, seed, migration or database-technology change.
- No route, API field or public schema change.
- No trading, credential, risk-control, Live Write or real-account activity.

## Allowed scope

- `platform-backend/app/financial_facts.py`.
- New `platform-backend/app/financial_fact_normalization.py`.
- Direct normalization, architecture and API-equivalence tests.
- `platform-backend/pyproject.toml`.
- `scripts/check-repository-structure.py` when needed to enforce ownership.
- `docs/codex/current-state.md`, `docs/architecture/README.md`, `docs/engineering/TECHNICAL_DEBT.md`, `CHANGELOG.md`, and this task packet.

## Protected semantics

- Strategy, account-binding and instrument validation status codes/messages.
- Currency uppercasing and trade settlement-currency enforcement.
- Catalog-derived quantity unit and contract multiplier.
- Same-currency FX rate `1` and converted amount equality.
- Cross-currency missing FX quality state and null converted amount.
- Decimal and UTC timestamp text canonicalization.
- Sorted payload JSON.
- Normalized dictionary keys and values.
- SHA-256 content hash and idempotency/conflict behavior.
- Existing FinancialFact, formal Position/PnL and NAV outputs.

## Minimal context packet

1. `AGENTS.md`.
2. `docs/codex/current-state.md`.
3. `docs/engineering/TECHNICAL_DEBT.md` TD-002.
4. `platform-backend/app/financial_facts.py`.
5. `platform-backend/app/financial_fact_schemas.py`.
6. `platform-backend/app/financial_fact_repository.py`.
7. `platform-backend/tests/test_financial_facts.py`.
8. `platform-backend/tests/test_architecture_financial_fact_repository.py`.
9. `platform-backend/pyproject.toml`.
10. `scripts/check-repository-structure.py`.

Do not modify unrelated Runtime, frontend, SQL or trading modules unless a proven regression requires it.

## Acceptance criteria

- [ ] One Issue, one task packet, one branch and one PR.
- [ ] `financial_fact_normalization.py` owns canonicalization, FX/quality policy and normalized-content hashing.
- [ ] `financial_facts.py` contains no normalization implementation or direct SHA-256 construction.
- [ ] `app.financial_facts.normalize_fact` remains callable with the same behavior.
- [ ] Exact normalized-output and content-hash golden tests pass.
- [ ] API validation and persisted-value equivalence tests pass.
- [ ] Existing accounting and repository transaction tests pass unchanged.
- [ ] Normalization ownership is machine-checked.
- [ ] Policy module is included in progressive Pyright.
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

Risk: medium because normalized content defines immutable fact identity.

Detection: exact normalized dictionary/hash snapshots, API equivalence, unchanged accounting golden suite and full cross-component CI.

Rollback: revert the final squash commit. No migration or external state is introduced.

## Progress

- Done: verified `main@c892f2db...`, no open PRs, created Issue #44 and its unique branch.
- Current: define pure normalization context and exact golden vectors.
- Next: extract policy and hash, preserve service compatibility wrapper, then enforce ownership.
- Blocked by: none.

## Completion

- PR: pending.
- Merge commit: pending.
- Behavior changed: none intended; normalization ownership only.
- Tests/CI: pending.
- Follow-up: formal projection-service extraction requires a separate Issue and PR.
