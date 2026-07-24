# Current Project State

Last updated: 2026-07-24
Stable branch: `main`
Latest completed engineering scope: Issue #50 / PR #51

This file is the compact cross-session handoff. It records current truth, not a PR diary. Read the actual open Issues and PRs before assuming that work is active.

## Current architecture

- `admin-risk/`: Vue product frontend.
- `platform-backend/`: modular-monolith business, risk, execution orchestration and accounting API.
- `execution-runtime/`: isolated venue/Gateway process and runtime journal.
- SQLite remains the approved persistence technology for the current stage.

## Safety defaults

```text
TradingMode=simulation
Gateway=fake
Platform Live Write=false
Runtime Live Write=false
```

Real-account acceptance remains controlled-host, small-capital and minimum-size.

## Authoritative boundaries

- Platform Backend must not import venue SDKs.
- `app/main.py` is a composition root only.
- Execution API DTOs are owned by `platform-backend/app/execution_schemas.py`.
- Public FinancialFact/formal-accounting DTOs are owned by `platform-backend/app/financial_fact_schemas.py`.
- FinancialFact canonicalization, FX/data-quality policy and normalized-content hashing are owned by `platform-backend/app/financial_fact_normalization.py`.
- FinancialFact/formal-accounting SQL, row mapping and transaction units are owned by `platform-backend/app/financial_fact_repository.py`.
- Formal Position/PnL/NAV calculations and rebuild orchestration are owned by `platform-backend/app/financial_projection_service.py`.
- `platform-backend/app/financial_facts.py` owns catalog resolution, FinancialFact recording, HTTP error mapping and API routes.
- Shared SQLite path and transaction-managed connections are owned by `platform-backend/app/database_connection.py`.
- Core Platform Schema and legacy compatibility DDL are owned by `platform-backend/app/database_bootstrap.py` and pinned by an exact SHA-256 snapshot.
- `platform-backend/app/database.py` is the compatibility facade and startup orchestrator; fixed reference Seeds remain there pending the final extraction.
- Platform–Runtime Command/Event traffic uses explicit V1.0 contracts and snapshots.
- `positions` and `pnl_results` are operational projections.
- `financial_facts`, `formal_positions` and `formal_pnl_results` are the formal accounting authority.
- Database changes use an ordered migration ledger with immutable checksums.
- Backend and Runtime tests have exactly one primary taxonomy marker.

## Completed engineering baseline

1. Composition and module-boundary cleanup.
2. Whole-directory lint, dependency and repository-structure gates.
3. Execution-schema ownership extraction.
4. Operational/formal financial projection separation.
5. Executable Backend and Runtime test taxonomy.
6. Canonical human/Agent context system and bounded task packets.
7. One-Issue/one-branch/one-PR machine governance.
8. DDL ownership inventory and non-destructive schema migration ledger.
9. Versioned Platform–Runtime V1 contracts and compatibility snapshots.
10. Progressive Pyright gates for critical Backend/Runtime boundaries.
11. Frontend changed-file no-new-debt lint enforcement.
12. Failure-injection tests and controlled production-acceptance matrix.
13. FinancialFact public-schema ownership extraction.
14. FinancialFact persistence ownership extraction with transaction rollback evidence.
15. FinancialFact normalization and immutable-content hash ownership extraction.
16. Formal Position/PnL/NAV projection-service extraction.
17. SQLite connection/path transaction boundary extraction.
18. Core database Bootstrap/Schema ownership extraction with exact checksum and fresh/existing/repeated initialization evidence.

## Active work

No engineering code workstream is active by default after PR #51 merges.

The final authorized structural code step is fixed reference Seed extraction:

1. search open Issues and PRs;
2. create one concrete Issue, task packet and Issue-numbered branch;
3. preserve every Seed ID/value and startup order;
4. require exhaustive Seed snapshot plus fresh/existing/repeated initialization equivalence.

Separate non-code follow-ups remain:

- Issue #38: repository administrator verifies GitHub protection and merge settings.
- Issue #39: controlled real-environment operational acceptance; it is not an engineering refactor and does not run in CI.

## Known constraints

- Existing table structures, Seed identifiers, financial formulas and trading state transitions are protected semantics.
- Operational projections remain supported and must not become formal-accounting inputs.
- Compatibility surfaces require usage evidence and a dedicated migration before removal.
- `app/database.py` still owns initializer orchestration and fixed reference Seeds; connection and core Bootstrap ownership are isolated.
- The FinancialFact domain is separated into API/schema, normalization, persistence and projection owners.
- Inherited frontend lint debt remains outside untouched modules; new and changed files cannot add debt.
- Pyright coverage is progressive rather than whole-repository strict.
- Live Write cannot be enabled by an engineering refactor or test result.
- GitHub repository-level branch protection/ruleset configuration must be verified by an administrator because it is not mutable through the available connector.

## Update rule

Replace stale facts when architecture, authority, safety defaults or a genuine active workstream changes. Do not append chat transcripts, long histories or speculative ideas. Detailed progress belongs in the matching task packet, Issue and PR.
