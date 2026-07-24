# Codex Context Map

Purpose: finish normal tasks without repeatedly loading the whole repository.

## Mandatory startup order

1. `AGENTS.md` — durable safety and engineering rules.
2. `docs/codex/current-state.md` — current architecture, safety defaults and active workstream.
3. The active `tasks/issue-<number>-<slug>.md` packet for multi-file, cross-session or high-risk work.
4. One target-module entry document.
5. Three to eight directly relevant source files and their direct tests.

Read `docs/architecture/OWNERSHIP.md` when a task changes module authority, compatibility exports, cross-module dependencies or architecture enforcement. Do not load the full repository, historical Changelog or every planning document by default.

## Human versus Agent entrypoints

- Human/business orientation: `00-人工可读目录/README.md`.
- Agent/current engineering orientation: this file plus `docs/codex/current-state.md`.
- Canonical module ownership: `docs/architecture/OWNERSHIP.md`.
- One task handoff: the matching file under `tasks/`.

Do not create another `START-HERE`, context map, ownership catalog or task template unless the existing canonical document is replaced in the same PR.

## Module context selection

| Task | Primary context | Usually exclude |
|---|---|---|
| Frontend UI | `admin-risk/docs/START-HERE.md`, target `src/views`, its API client and hooks | Backend/Runtime full source |
| Platform API | target `platform-backend/app` module, API/technical doc, direct tests | frontend template and venue adapters |
| Execution/Gateway | target `execution-runtime/app` module, Runtime tests, live-adapter doc | Platform UI and formal-accounting internals |
| Risk/Live | risk/auth/live-session modules, operations and `live_safety` tests | unrelated strategy pages |
| Accounting | `docs/technical/FINANCIAL_FACTS.md`, the relevant Schema/Normalization/Repository/Projection/API owner from `docs/architecture/OWNERSHIP.md`, and direct tests | operational UI details |
| Database | `docs/database/`, the relevant Connection/Bootstrap/Seed/Migration owner from `docs/architecture/OWNERSHIP.md`, and direct tests | frontend and external SDKs |
| Cross-service contract | `docs/contracts/`, producer schema, consumer schema and compatibility tests | unrelated domains |
| Architecture-wide | `docs/architecture/SYSTEM_MAP.md`, `docs/architecture/OWNERSHIP.md` and boundary tests | archives and generated outputs |

## High-value entrypoints

- Platform composition root: `platform-backend/app/main.py`.
- Venue SDKs and external side effects: `execution-runtime/` only.
- Code architecture checks: `scripts/check-repository-structure.py`.
- Documentation ownership checks: `scripts/check-documentation-consistency.py`.
- Complete major ownership map: `docs/architecture/OWNERSHIP.md`.

Do not reproduce the ownership table here. The catalog is the single durable source for module authority; this file only decides what context to load.

## Default context budget

A normal task should use:

- one task packet at most;
- one module entry document;
- three to eight direct source files;
- direct tests;
- zero to two architecture/contract documents.

If more context is needed, record the added paths and reason in the task packet before expanding. Never repeatedly rescan already summarized material.

## Documentation priority

1. `AGENTS.md`.
2. `docs/codex/current-state.md`.
3. Active task packet.
4. Target module documentation.
5. `docs/architecture/OWNERSHIP.md` when ownership is relevant.
6. Architecture decisions and technical contracts.
7. README.
8. Historical Changelog, archived plans and closed PRs only when tracing history.

## Do not load automatically

- `node_modules`, `.venv`, `dist`, generated outputs;
- `outputs/`;
- external reference projects;
- `archive/` and old DRAFT documents;
- closed PR discussions and historical implementation plans;
- unrelated modules merely because the repository is large.

## Change discipline

Update only affected code, direct tests and directly authoritative documentation. Avoid copying the same rule into multiple documents. Stable rules belong in `AGENTS.md`; ownership belongs in `docs/architecture/OWNERSHIP.md`; current facts belong in `current-state.md`; implementation progress belongs in the task packet and PR.
