# Variable-Global project rules

## Scope and context

Read this file first. Read a module `AGENTS.md`, Context Pack, task card, governance document, or historical record only when the Owner explicitly requests it or the task directly requires its technical or safety semantics. Context Packs are optional discovery aids, never startup requirements or Token gates. Use the configured Python runtime when a script is needed.

## Operating modes

- Mode 1: normal direct work by one Agent on the current worktree.
- Mode 2: multi-Agent work only after the Owner explicitly requests it and defines the boundary.
- Mode 3: Web/GitHub contribution verification only after the Owner provides the exact commit or pull request.

Mode 2/3, task cards, branches, Worktrees, locks, monitors, and structured delivery receipts are never prerequisites for ordinary work.

## Execution behavior

- For an execution request, complete reversible local work within scope by default. Make ordinary technical choices from the current code, contracts, and tests; do not stop at a plan, status update, first error, or partial implementation.
- Ask the Owner only when ambiguity would materially change the user experience, an external fact cannot be inferred safely, concurrent changes cannot be merged safely, or the work requires credentials, external writes, real trading, or an irreversible action.
- Implement only the requested product result. Do not add product states, parallel flows, compatibility layers, configuration switches, authorization mechanisms, or future architecture without evidence that the current requirement needs them.
- Select validation by impact and risk: keep narrow changes focused, and expand regression coverage for shared contracts, cross-module behavior, permissions, persistence, and trading safety.
- The Owner's latest explicit request determines current intent. If it conflicts with an active contract or safety rule, surface the conflict and update the owning authority when approved; never bypass it silently.

When work fails, reproduce and locate the root cause from the error, logs, and existing call path, then make the smallest complete fix in the layer that owns the problem. Do not mask failure with a parallel path, duplicate state, silent fallback, temporary switch, swallowed error, or open-ended compatibility layer, and do not bypass contracts, consistency, or safety boundaries. Limit systemic changes to the reproduced cause, avoid unrelated redesign, remove only failed experimental code introduced by the current task, and continue through directly relevant verification.

## Documentation maintenance

Before finishing any non-trivial task, perform a documentation-impact check:

- AI may update the status, blocker, verified result and next technical action of an existing workstream in `docs/PROJECT.md` without a separate Owner prompt when repository or external evidence supports the change.
- AI may add newly discovered ideas, gaps and uncertainties to the discovery inbox in `docs/PROJECT.md`. Every such entry must remain explicitly unconfirmed.
- Do not promote a discovery, suggestion or inferred requirement into `docs/product/` until the Owner explicitly says `确认进入范围`. Implementation activity, code presence or test coverage does not substitute for that product-scope confirmation.
- Product priority, milestone choice, risk tolerance, external connectivity and real-trading authorization remain Owner decisions. AI may recommend changes but must not infer approval from an active task.
- Update the owning durable document when behavior, a contract, an architectural boundary, an operating procedure, or a safety rule changes.
- Do not create a new task card, status report, handoff, plan, audit, or parallel architecture document unless the Owner explicitly asks for one or the work needs a durable ADR.
- Do not update documentation for a refactor, test-only change, or implementation detail when the documented behavior and project status did not change.
- In the final response, state which project or authority document changed, or state `Docs: no update needed`.

Task plans, agent coordination, investigation logs and intermediate evidence are temporary working context. At task close, merge only durable verified facts into the owning document and discard the process narrative. Real-trading or externally auditable evidence is the exception: retain it in the approved audit or operator evidence location, not in active project documentation.

### Active stage workstreams

Use an active stage file only when the Owner defines a stage, or when one independently verifiable outcome spans multiple tasks or sessions. Ordinary bounded work needs no task document.

- Keep one file for one active stage under `docs/workstreams/`. Do not create separate Markdown for its phases, subtasks, handoffs, receipts, test runs or repairs.
- Multiple stages may be active when they can be progressed, paused and accepted independently. Closely coupled features that share one acceptance outcome or repeatedly change the same core contract should remain work lines in one stage rather than duplicate state across files.
- A stage file is a concise continuation snapshot, not a product or architecture authority. It should contain enough current scope, result, acceptance, blocker or decision, next action and authority links for another task to continue, but it has no mandatory template, status vocabulary or receipt format.
- Before continuing a stage, read `AGENTS.md`, `docs/PROJECT.md`, the relevant stage file and only its directly relevant durable authorities. Chat provides the Owner's latest intent and reasoning but must not be the only handoff source. When a new explicit Owner request conflicts with the stage file, point out the change and update the file; do not silently choose either version.
- When continuing a stage or changing a shared contract, notice other active stages listed in `docs/PROJECT.md`. Read another stage file only when the intended change touches its current code, data or contract boundary. Shared facts must have one durable owner and must not be maintained independently in two stage files.
- AI may update evidence-backed progress, verified results, technical blockers, acceptance and next technical action. AI must not change confirmed product scope, priority, risk tolerance or authorization. New product needs remain explicitly unconfirmed until the Owner says `确认进入范围`.
- Task replies should briefly communicate the actual result, important verification, real blocker and documentation impact. Do not use a rigid receipt schema or depend on a long chat receipt for continuation.
- At stage close, merge durable facts into their owning documents, update `docs/PROJECT.md`, and delete the single stage file. Git retains history; do not archive completed stage files. A blocked stage remains active, while cancellation or milestone changes require an Owner decision.

## Technical and trading safety

- `platform-api` remains a modular monolith unless an approved architecture decision says otherwise. Venue SDKs and order side effects stay in `execution-runtime`; versioned contracts separate it from Platform API.
- Preserve `Decimal` values and timezone-aware timestamps at financial boundaries.
- Live Write is disabled by default. Never create, expose, configure, or infer credentials, account access, external connectivity, deployment, or production state.
- Protect the Kill Switch, idempotency, one-business-intent and duplicate-prevention controls, cumulative-fill limits, reconciliation, and `result_unknown` fail-closed behavior.
- Any real-trading action requires explicit, operation-specific Owner authorization. Local tests and repository validation never confer that authority.
