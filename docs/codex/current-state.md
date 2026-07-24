# Current Project State

Last updated: 2026-07-24
Stable branch: `main`
Latest completed engineering scope: Issue #53 / PR #54
Active engineering scope: Issue #55 / PR #56

This file is the compact cross-session handoff. It records current truth, not a PR diary. Read the actual open Issues and PRs before assuming that work is active.

## Current architecture

- `admin-risk/`: Vue product frontend.
- `platform-backend/`: modular-monolith business, risk, execution orchestration and accounting API.
- `execution-runtime/`: isolated venue/Gateway process and runtime journal.
- SQLite remains the approved persistence technology for the current stage.
- Canonical major module ownership is recorded in `docs/architecture/OWNERSHIP.md`.

## Safety defaults

```text
TradingMode=simulation
Gateway=fake
Platform Live Write=false
Runtime Live Write=false
```

Real-account acceptance remains controlled-host, small-capital and minimum-size.

## Current invariants

- Platform Backend does not import venue SDKs; external execution remains inside `execution-runtime/`.
- `platform-backend/app/main.py` is a composition root only.
- Operational `positions` and `pnl_results` remain separate from FinancialFact-based formal accounting.
- Formal accounting is reconstructed from immutable facts and does not read operational projections as inputs.
- Platform–Runtime Command/Event traffic uses explicit V1.0 contracts and snapshots.
- Database changes use an ordered migration ledger with immutable checksums.
- Backend and Runtime tests have exactly one primary taxonomy marker.
- Ownership or compatibility-boundary changes must update `docs/architecture/OWNERSHIP.md` in the same PR.

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
18. Core database Bootstrap/Schema ownership extraction with exact checksum.
19. Fixed database Seed ownership extraction with exhaustive all-value snapshot and repeated-startup equivalence.

## Active work

Issue #55 / PR #56 establishes one canonical architecture ownership catalog and a blocking documentation-consistency check. It corrects stale Agent context without changing runtime behavior, SQL, formulas, trading or Live Write.

Before starting another code change:

1. verify current `main`, open Issues and open PRs;
2. reuse an Issue only when the outcome exactly matches;
3. create one matching task packet, Issue-numbered branch and open PR;
4. preserve the ownership boundaries recorded in `docs/architecture/OWNERSHIP.md`.

Separate non-code follow-ups remain:

- Issue #38: repository administrator verifies GitHub protection and merge settings.
- Issue #39: controlled real-environment operational acceptance; it is not an engineering refactor and does not run in CI.

## Known constraints

- Existing table structures, Seed identifiers, financial formulas and trading state transitions are protected semantics.
- Operational projections remain supported and must not become formal-accounting inputs.
- Compatibility surfaces require usage evidence and a dedicated migration before removal.
- Inherited frontend lint debt remains outside untouched modules; new and changed files cannot add debt.
- Pyright coverage is progressive rather than whole-repository strict.
- Live Write cannot be enabled by an engineering refactor or test result.
- GitHub repository-level branch protection/ruleset configuration must be verified by an administrator because it is not mutable through the available connector.

## Update rule

Replace stale facts when architecture, authority, safety defaults or a genuine active workstream changes. Do not append chat transcripts, long histories or speculative ideas. Detailed progress belongs in the matching task packet, Issue and PR.
