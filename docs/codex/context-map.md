# Codex Context Map

Purpose: reduce unnecessary repository-wide context loading.

## General Rule

Do not ask AI agents to understand the whole repository for normal tasks.
Load only the module required by the task.

## Module Boundaries

| Task | Primary Context |
|---|---|
| Frontend UI | `admin-risk/` + frontend docs |
| Backend API | `platform-backend/` + API docs |
| Execution | `execution-runtime/` + execution docs |
| Risk/Live | risk, auth, operations docs |
| Accounting | FinancialFact and PnL docs |
| Architecture | full architecture docs only |

## Documentation Priority

1. AGENTS.md
2. Module documentation
3. Architecture decisions
4. README
5. Historical changelog

Historical records explain why. They are not default coding context.

## Do Not Load Automatically

- node_modules
- .venv
- dist
- outputs
- external reference projects
- old implementation discussions

## Change Discipline

Every engineering change should update only:

- affected code
- related tests
- directly related documentation

Avoid copying the same rule into multiple documents.