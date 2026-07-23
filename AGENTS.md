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

## Safety Rules

- Never commit secrets, passwords, tokens or `.env` contents.
- Never enable real trading by code change alone.
- Do not bypass tests, CI, approval or risk controls.
- Do not modify trading, permission, database or deployment boundaries without explicit task scope.
- Do not perform recursive deletion.

## Development Rules

- Make the smallest complete change.
- Keep code, tests and relevant Markdown documentation synchronized.
- Prefer existing architecture patterns over introducing new frameworks.
- Keep composition roots declarative: wire routers and middleware only; import domain policies explicitly and never monkey-patch modules.
- Keep one authoritative implementation for each domain calculation; compatibility wiring must not replace functions at runtime.
- Keep API schemas owned by their domain module; cross-domain compatibility modules may use explicit public aliases to re-export but must not redefine them.
- CI quality gates must cover complete maintained directories; do not use file allowlists that let new code bypass lint or dependency validation.
- Use `rg` for search.
- Ignore `node_modules`, `.venv`, `dist`, generated outputs and external references unless explicitly required.

## Task Context Rules

Before editing:

1. Read this file.
2. Read only the target module documentation.
3. Do not load the entire repository unless architecture work requires it.

Module context:

- Frontend tasks → `admin-risk/` + frontend docs.
- Backend tasks → `platform-backend/` + backend docs.
- Runtime tasks → `execution-runtime/` + execution docs.
- Operations tasks → `docs/operations/`.

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
