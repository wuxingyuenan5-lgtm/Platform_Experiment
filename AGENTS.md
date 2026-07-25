# Project Agent Rules

## Project Identity

This is an internal quantitative research and trading infrastructure platform.

Primary objective:

- Maintain a reliable path from research, strategy execution, risk control to accounting verification.
- Prefer correctness, auditability and small safe changes over rapid feature expansion.

## Architecture Map

```text
admin-risk/          Frontend product application
platform-backend/    Business APIs, strategy, risk, accounting
execution-runtime/   External execution gateway and runtime journal
docs/                Architecture and operational documentation
```

Human orientation starts at `00-人工可读目录/README.md`. Agent orientation starts at `docs/codex/context-map.md`. Canonical major module ownership is recorded in `docs/architecture/OWNERSHIP.md`.

## Safety Rules

- Never commit secrets, passwords, tokens or `.env` contents.
- Never enable real trading by code change alone.
- Do not bypass tests, CI, approval or risk controls.
- Do not modify trading, permission, database or deployment boundaries without explicit task scope.
- Do not perform recursive deletion.

## Development Rules

- Make the smallest complete change.
- Keep code, tests and directly authoritative Markdown synchronized.
- Prefer existing architecture patterns over introducing new frameworks.
- Keep composition roots declarative: wire routers and middleware only; import domain policies explicitly and never monkey-patch modules.
- Keep one authoritative implementation for each domain calculation; compatibility wiring must not replace functions at runtime.
- Keep external HTTP transport in explicit client boundaries; orchestration may coordinate responses and map errors but must not duplicate configured URL/timeout calls.
- Keep API schemas owned by their domain module; compatibility modules may use explicit aliases but must not redefine them.
- Keep operational trading projections (`positions`, `pnl_results`) separate from FinancialFact-based formal accounting projections.
- Assign every Backend and Runtime test exactly one primary layer (`architecture`, `unit`, `integration`, or `live_safety`) and keep classified suites independently executable.
- CI gates must cover complete maintained directories or an explicit no-new-debt mechanism; new files may not bypass validation.
- Update `docs/architecture/OWNERSHIP.md` in the same PR whenever module authority or a compatibility boundary changes.
- Use `rg` for search.
- Ignore `node_modules`, `.venv`, `dist`, generated outputs, archives and external references unless explicitly required.

## One Issue, One Branch, One PR

For non-trivial engineering work:

1. Search existing open Issues and PRs for the same outcome.
2. Reuse or create exactly one GitHub Issue.
3. Create one branch named `<type>/issue-<number>-<slug>`.
4. Use one PR that references the same Issue.
5. Do not start a replacement branch until the previous PR is closed and marked `Superseded by #<new-pr>`.
6. After merge, delete or reset the head branch; never keep two branches carrying the same unique work.

The CI workstream check enforces branch/Issue/PR linkage and rejects duplicate open PRs for one Issue.

## Task Context Rules

Before editing:

1. Read this file.
2. Read `docs/codex/current-state.md`.
3. For cross-session, cross-module, migration or production work, create/update `tasks/issue-<number>-<slug>.md` from `docs/codex/task-template.md`.
4. Read only the target module documentation and paths listed in that task packet.
5. Read `docs/architecture/OWNERSHIP.md` when the task changes ownership, compatibility exports or cross-module dependency direction.
6. Do not load the entire repository unless the task is explicitly architecture-wide.

Default context budget:

- one task packet;
- one module entry document;
- three to eight direct source files;
- their direct tests;
- zero to two additional architecture/contract documents unless justified in the task packet.

Do not repeat repository history in prompts. Use current-state, task packets, commits, Issues and PRs as durable handoff.

## Documentation Rules

- `AGENTS.md`: durable hard rules only.
- `docs/codex/current-state.md`: compact current truth and active workstream.
- `docs/codex/context-map.md`: context-loading map, not an ownership registry.
- `docs/codex/task-template.md`: the single task template.
- `docs/architecture/OWNERSHIP.md`: canonical major module ownership.
- `docs/architecture/`: stable structure and boundaries, not PR diaries.
- `docs/decisions/`: important decisions and rejected alternatives.
- `docs/technical/`: protocols and domain implementation contracts.
- `docs/operations/`: deployment, monitoring, incidents and recovery.
- `docs/engineering/TECHNICAL_DEBT.md`: intentionally deferred work with triggers.
- `tasks/`: one active packet per Issue; progress is replaced, not appended as chat history.
- `outputs/`: disposable artifacts, never a source of truth.

## Product UI

- Production pages show user workflows only.
- Do not add debug panels, implementation explanations or engineering notes to product interfaces.

## Current Default Runtime

```text
TradingMode=simulation
Gateway=fake
Platform Live Write=false
Runtime Live Write=false
```

Live execution requires existing approval, risk and operational gates.
