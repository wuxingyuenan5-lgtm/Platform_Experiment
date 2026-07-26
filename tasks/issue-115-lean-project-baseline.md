# Task: Lean project baseline for local run

Issue: #115
Status: review
Branch: `chore/issue-115-lean-project-baseline`
Base commit: `c7d399885a1585e47495bca1fc9f1061315741c4`

## Objective

Prepare a lean `0.9.0` local-run baseline by simplifying governance, CI, Agent context, documentation and startup tooling without changing trading behavior.

## Protected semantics

- Market, FOK, PostOnly and TP/SL execution behavior remains unchanged.
- No database business-schema or execution-contract change.
- Live Write, Exit Monitor, 1 oz and single-lifecycle defaults remain unchanged.
- Frontend product layout and navigation remain unchanged.

## Scope

- Fast / Standard / Critical workstreams.
- path-scoped PR CI and dedicated Secret Scan.
- compact global and module Agent context.
- active-only Technical Debt.
- Windows local startup, health checks and pnpm alignment.
- synchronized `0.9.0` declarations and release notes.

## Verification

- workstream, CI-scope and version-tooling architecture tests;
- version consistency;
- final full Platform CI, Version Consistency and Secret Scan;
- no trading/runtime behavior diff.

## Progress

- Done: implementation prepared as one repository tree.
- Current: PR and full CI verification.
- Next: squash merge and controlled local run.
- Blocked by: none.
