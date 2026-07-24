# Current Project State

Last updated: 2026-07-24
Stable branch: `main`
Baseline before Issue #36: `e826c9e4808a0b76c3265bfd5da5b8e65c133b77`

This file is the compact cross-session handoff. It records only current truth, not a PR diary.

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
- `positions` and `pnl_results` are operational projections.
- `financial_facts`, `formal_positions` and `formal_pnl_results` are the formal accounting authority.
- Backend and Runtime tests have exactly one primary taxonomy marker.

## Completed engineering baseline

1. Composition and module-boundary cleanup.
2. Whole-directory lint, dependency and repository-structure gates.
3. Execution-schema ownership extraction.
4. Operational/formal financial projection separation.
5. Executable Backend and Runtime test taxonomy.

## Active work

Issue #36 is the only active workstream for:

1. context and Git workflow governance;
2. schema inventory and non-destructive migration ledger;
3. versioned Platform–Runtime contracts;
4. progressive Python type checking;
5. frontend no-new-debt lint;
6. failure-injection and production-acceptance tests.

Branch: `hardening/issue-36-project-operating-system`.

## Known constraints

- Existing table structures, financial formulas and trading state transitions are protected semantics.
- Operational projections remain supported and must not become formal-accounting inputs.
- Compatibility surfaces require usage evidence and a dedicated migration before removal.
- Live Write cannot be enabled by an engineering refactor or test result.

## Update rule

Replace stale facts when architecture, authority, safety defaults or the active workstream changes. Do not append chat transcripts, long histories or speculative ideas. Detailed progress belongs in `tasks/issue-36-project-operating-system.md`, future task packets, issues and PRs.
