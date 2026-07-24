# Task: FinancialFact golden equivalence and schema extraction

Issue: #40
Status: complete; awaiting squash merge
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
6. `platform-backend/tests/test_architecture_financial_fact_schemas.py`.
7. `platform-backend/pyproject.toml`.
8. `scripts/check-repository-structure.py`.

Do not scan unrelated frontend, Runtime or historical planning documents unless a failing regression directly requires them.

## Acceptance criteria

- [x] One Issue, one task packet, one branch and one PR.
- [x] Public financial schema classes have one authoritative owner.
- [x] Existing `app.financial_facts` imports remain identity-compatible.
- [x] Existing golden equivalence covers hashing conflicts, FX completeness, multiplier, average cost, component PnL, rebuild and NAV behavior.
- [x] No SQL or formula diff is present.
- [x] Extracted schemas are included in progressive Pyright.
- [x] Architecture ownership and JSON Schema tests prevent schema duplication or field drift.
- [x] Backend dependency, Ruff, Pyright and all classified tests pass.
- [x] Runtime and frontend regression gates pass.
- [x] Secret Scan passes.
- [x] Documentation matches the final implementation.

## Verification

Platform CI `30080685698`:

- repository-safety: success;
- platform-backend dependency/Ruff/Pyright/architecture/unit/integration/live-safety: success;
- execution-runtime dependency/Ruff/Pyright/unit/integration/live-safety: success;
- frontend maintained lint/no-new-debt/type check/production build: success.

Independent Secret Scan `30080685661`: success.

The first validation exposed only import ordering. The second exposed UTC `+00:00` versus canonical `Z` in the new test expectation. Both were corrected without changing runtime models or weakening gates.

## Risk and rollback

Risk: medium because auditable financial interfaces are structurally moved.

Detection: schema identity tests, JSON Schema snapshots, existing golden accounting equivalence, full classified suites and cross-component regression CI.

Rollback: revert the final squash commit. No persistent schema, external state or Live Write setting is changed.

## Completion

- PR: #41.
- Merge commit: pending squash merge; GitHub is the authority after merge.
- Behavior changed: public DTO ownership only.
- Behavior intentionally unchanged: SQL, persistence, normalization, hashing, FX, average cost, PnL formulas, formal rebuild, API fields, database schema and Live Write.
- Tests/CI: Platform CI `30080685698` and Secret Scan `30080685661` passed.
- Follow-up: repository, normalization and projection-service extraction require separate Issues and PRs.
