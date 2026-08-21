# Variable-Global project rules

## Scope and context

Read this file first. Read a module `AGENTS.md`, Context Pack, task card, governance document, or historical record only when the Owner explicitly requests it or the task directly requires its technical or safety semantics. Context Packs are optional discovery aids, never startup requirements or Token gates. Use the configured Python runtime when a script is needed.

## Operating modes

- Mode 1: normal direct work by one Agent on the current worktree.
- Mode 2: multi-Agent work only after the Owner explicitly requests it and defines the boundary.
- Mode 3: Web/GitHub contribution verification only after the Owner provides the exact commit or pull request.

Mode 2/3, task cards, branches, Worktrees, locks, monitors, and structured delivery receipts are never prerequisites for ordinary work.

## Technical and trading safety

- `platform-api` remains a modular monolith unless an approved architecture decision says otherwise. Venue SDKs and order side effects stay in `execution-runtime`; versioned contracts separate it from Platform API.
- Preserve `Decimal` values and timezone-aware timestamps at financial boundaries.
- Live Write is disabled by default. Never create, expose, configure, or infer credentials, account access, external connectivity, deployment, or production state.
- Protect the Kill Switch, idempotency, one-business-intent and duplicate-prevention controls, cumulative-fill limits, reconciliation, and `result_unknown` fail-closed behavior.
- Any real-trading action requires explicit, operation-specific Owner authorization. Local tests and repository validation never confer that authority.
