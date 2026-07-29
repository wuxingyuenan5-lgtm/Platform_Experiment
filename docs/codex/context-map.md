# Agent Context Map

Purpose: complete normal work without repeatedly loading the repository.

## Startup

1. Root `AGENTS.md`.
2. `docs/codex/CURRENT_CONTEXT.md`.
3. `docs/codex/current-state.md` only when release state or execution baseline matters.
4. The nearest module `AGENTS.md`.
5. Three to eight directly affected source files and their direct tests.
6. `docs/architecture/OWNERSHIP.md` only when authority or dependency direction changes.
7. One task packet only for an active Critical cross-session task.

## Typical module entry

| Work | Read first | Usually exclude |
|---|---|---|
| Frontend | `admin-risk/AGENTS.md`, target view/component, API client | Backend/Runtime internals |
| Platform API | `platform-backend/AGENTS.md`, target module and tests | full frontend and Venue adapters |
| Execution | `execution-runtime/AGENTS.md`, adapter/contract and tests | unrelated Platform domains |
| Database | `docs/database/README.md`, migration owner and tests | frontend |
| Cross-service contract | `docs/contracts/`, producer and consumer models | unrelated domains |

## Exclusions by default

Do not automatically load `tasks/`, closed PR discussions, `CHANGELOG.md`, archives, audit folders, `outputs/`, generated files, `node_modules`, virtual environments or unrelated modules.

GitHub owns live Issue, PR, branch and CI state. Do not copy that volatile state into prompts or `current-state.md`.

Browser ambient state is evidence only. Do not start browser automation for a small code edit unless the task needs visual confirmation, the user explicitly asks, or source-level checks cannot answer whether the change applied.
