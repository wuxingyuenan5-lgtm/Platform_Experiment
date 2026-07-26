# Project Agent Rules

## Purpose

Internal quantitative research and trading infrastructure. Prefer safe, complete changes over speculative architecture work.

## Service boundaries

```text
admin-risk/          Vue product frontend
platform-backend/    Business, risk, orchestration and accounting API
execution-runtime/   Venue/Broker SDKs, external side effects and Runtime Journal
```

Canonical major ownership is recorded in `docs/architecture/OWNERSHIP.md`.

## Permanent safety rules

- Never commit credentials, tokens, passwords or real `.env` values.
- Never enable real trading, Live Write or automatic exit monitoring through an unrelated change.
- Platform Backend must not import Venue SDKs.
- ACK is not Fill; unknown external results must not be blindly retried.
- Database, execution contract, trading, risk, permission and reconciliation semantics require explicit Critical scope.
- Do not bypass CI, safety checks or approval controls.
- Do not perform recursive deletion.

## Workstream choice

Choose the smallest valid track:

- **Fast** — Markdown and synchronized release-version maintenance; no behavior change.
- **Standard** — bounded single-module product work without Critical paths; no Issue or task packet required.
- **Critical** — trading/execution, Runtime, risk, auth, credentials, database/migration, contracts, CI governance, Live behavior, cross-service or cross-session work; one Issue, one task packet and one Issue-numbered branch.

Rules and branch formats: `docs/engineering/GIT_WORKFLOW.md`.

## Context loading

Read only:

1. this file;
2. `docs/codex/current-state.md`;
3. the nearest module `AGENTS.md`;
4. directly affected source files and tests;
5. a task packet only for an active Critical cross-session task.

Do not load closed PR history, all task packets, the full Technical Debt register or the entire repository by default. The compact map is `docs/codex/context-map.md`.

## Change discipline

- Make the smallest complete change.
- Prefer existing patterns; do not add a framework for one feature.
- Do not split modules merely to match a theoretical layer pattern.
- Refactor only after a real maintenance, reuse, testability or safety problem appears.
- Update only directly authoritative documentation.
- Form the complete patch and run local checks before pushing; normal PRs should use roughly one to three logical commits, not one commit per file.
- Product pages show user workflows, not debug or engineering notes.

## Default runtime safety

```text
TradingMode=simulation
Gateway=fake
Platform Live Write=false
Runtime Live Write=false
Cross-spread Exit Monitor=false
Bybit PostOnly Chase=false
```

Local startup: `powershell -ExecutionPolicy Bypass -File .\scripts\dev-platform.ps1`.
