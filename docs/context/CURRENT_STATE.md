# Current Project State

Last updated: 2026-07-24
Baseline branch: `main`
Baseline commit before this governance phase: `e826c9e4808a0b76c3265bfd5da5b8e65c133b77`

## System status

- Architecture: modular monolith Platform Backend plus separate Execution Runtime and Vue frontend.
- Default trading mode: simulation.
- Platform Live Write: disabled by default.
- Runtime Live Write: disabled by default.
- Operational projections: `positions`, `pnl_results`.
- Formal accounting authority: `financial_facts`, `formal_positions`, `formal_pnl_results`.
- Backend venue SDK imports: forbidden.
- Main branch changes: branch → tests → PR → squash merge.

## Completed engineering baseline

1. Composition-root and module-boundary cleanup.
2. Whole-directory lint, dependency and repository-structure gates.
3. Execution API schema ownership extraction.
4. Operational versus formal financial projection separation.
5. Executable test taxonomy for Backend and Runtime.

## Current workstream

The next hardening sequence is:

1. Project context and documentation operating system.
2. Database schema inventory and migration discipline.
3. Versioned Platform–Runtime contracts.
4. Progressive Python type checking.
5. Frontend no-new-debt lint coverage.
6. Failure-injection and production-acceptance tests.

## Known constraints

- SQLite remains the current database; no database replacement is approved.
- Existing table schemas and trading semantics must not be changed without explicit migration and business review.
- Operational projections remain supported; they are not formal accounting inputs.
- Real-account acceptance must remain controlled-host, small-capital and minimum-size.
- Compatibility exports and legacy surfaces may only be removed with usage evidence and a dedicated migration plan.

## Update rule

Update this file only when one of these changes:

- current stable architecture;
- active workstream;
- production/default safety state;
- authoritative data ownership;
- a material constraint affecting future tasks.

Do not append PR diaries, detailed implementation logs or speculative ideas here. Those belong in PRs, task files or `TECHNICAL_DEBT.md`.
