# Current Project State

Last updated: 2026-07-24
Stable branch: `main`
Latest engineering program: Issue #36 / PR #37

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

## Active work

No engineering workstream is active by default.

Before starting work:

1. search open Issues and PRs;
2. reuse an existing Issue when the outcome is already tracked;
3. create one task packet and one Issue-numbered branch;
4. update this section only when a workstream becomes genuinely active.

Real-account operational acceptance remains a separate manual activity and is not implied by the engineering baseline.

## Known constraints

- Existing table structures, financial formulas and trading state transitions are protected semantics.
- Operational projections remain supported and must not become formal-accounting inputs.
- Compatibility surfaces require usage evidence and a dedicated migration before removal.
- `app/database.py` and `app/financial_facts.py` remain intentionally concentrated pending dedicated equivalence-safe decomposition.
- Inherited frontend lint debt remains outside untouched modules; new and changed files cannot add debt.
- Pyright coverage is progressive rather than whole-repository strict.
- Live Write cannot be enabled by an engineering refactor or test result.
- GitHub repository-level branch protection/ruleset configuration must be verified by an administrator because it is not mutable through the available connector.

## Update rule

Replace stale facts when architecture, authority, safety defaults or a genuine active workstream changes. Do not append chat transcripts, long histories or speculative ideas. Detailed progress belongs in the matching `tasks/issue-*.md`, Issue and PR.
