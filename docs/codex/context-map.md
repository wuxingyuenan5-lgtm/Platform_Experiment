# Agent Context Map

Purpose: route a task to the smallest sufficient evidence set without loading historical material.

## Default startup

1. Read root `AGENTS.md`.
2. Read `docs/codex/current-state.md`.
3. Read the nearest module `AGENTS.md`.
4. Read directly affected source files and direct tests.
5. Read `docs/architecture/OWNERSHIP.md` only for authority or persistence changes.
6. Read one A2 contract from `docs/contracts/README.md` only when domain semantics change.
7. Read one active Critical task packet only for a Critical cross-session task.

## Executable task packs

```powershell
python scripts/context-for.py --list
python scripts/context-for.py research-field
python scripts/context-for.py identity-permission --json
```

The tool prints bounded file lists and estimates. It does not concatenate source or replace engineering judgment.

## Bounded task packs

| Task | Tool key | Read first | Add only when needed | Exclude by default |
|---|---|---|---|---|
| Narrow frontend style/layout | `hedge-style` | target component, direct parent/style owner and layout guard | direct child and visual spec | backend, Runtime and unrelated UI |
| A-share/Shenwan/research field | `research-field` | view/composable, API client, schema/service and tests | Provider/cache for source semantics | Trading, Runtime and user administration |
| Research Provider | `research-provider` | provider boundary, service/cache/schema, smoke and tests | frontend mapper for public-contract change | unrelated Providers and Execution |
| Identity/permission/session | `identity-permission` | access guard, auth/authority/permissions and tests | migration/E2E for persistence or browser flow | Research and Runtime adapters |
| Member holdings/NAV | `member-contract` | client, route/schema/service and tests | repository and contract for meaning changes | Runtime and unrelated administration |
| API contract | task-specific | producer, consumer and contract tests | ownership catalog for a boundary move | unrelated services and history |
| Funding or cross-spread display | `trading-display` | component/client, display schema and tests | Runtime contract only for execution semantics | Venue SDK internals |
| Trading execution/risk | task-specific Critical pack | active task, owner, contract, policy and safety tests | reconciliation/EOD for outcome semantics | unrelated Research/UI |
| Financial Fact/PnL/NAV/accounting | task-specific Critical pack | accounting contract, schema/repository/projection and tests | display mapper only for presentation | operational projection as formal input |
| Runtime adapter | task-specific | Runtime module rules, adapter/contract/journal and tests | Platform consumer for payload change | browser/user/research |
| Database/migration/backup | task-specific Critical pack | database authority, migration/recovery owner and tests | affected domain contract | frontend and unrelated repositories |
| User-system browser E2E | `user-e2e` | E2E/config/access guard, seed and module rules | backend flow tests across HTTP | unrelated pages and Runtime |
| CI/documentation/context | task-specific | affected workflow/check, current-state and context map | module commands for changed scope | product implementation unless proven necessary |

## Default exclusions

Do not automatically load:

- `tasks/` except one active Critical packet;
- Plan, Handoff, Audit, Superseded, DRAFT, release-history and archive material;
- closed PR discussions and historical progress records;
- lock files unless dependency resolution is the task;
- `node_modules`, virtual environments, build, coverage, Playwright and generated output;
- `src/views/demo`, Mock data and template examples unless explicitly targeted;
- `projects/risk-control` unless Legacy deployment or migration is the task;
- unrelated services and large static catalogs.

## Authority rules

- `docs/codex/current-state.md` owns current delivery state.
- `docs/architecture/SYSTEM_MAP.md` owns service and data-flow boundaries.
- `docs/architecture/OWNERSHIP.md` owns business-rule, code and data authority.
- `docs/operations/RUNBOOK.md` owns operating commands.
- `docs/contracts/README.md` routes detailed domain contracts.
- GitHub PR #141 owns volatile HEAD, CI and review evidence.
- Historical plans are evidence, not current authority.

Browser ambient state is evidence only. Do not start browser automation unless visual behavior is part of acceptance or source-level checks cannot prove the result.

## Context budgets

Each existing task pack has separate Required and Optional token budgets in the existing `scripts/context-for.py` pack tool. `docs/codex/context-budgets.json` publishes the same pack names and numeric limits as a machine-readable manifest, and an architecture test rejects drift; file paths remain owned only by the existing pack definitions.

```powershell
python scripts/context-for.py identity-permission --json
python scripts/context-for.py identity-permission --with-optional --json
python scripts/context-for.py --check-budgets --json
```

Budget rules:

- Required paths must exist and must remain within the Required budget.
- Optional paths must exist, remain unloaded by default and stay within the Optional budget.
- A new pack without an explicit budget fails the gate.
- The default startup set is root `AGENTS.md`, `docs/codex/current-state.md` and one nearest module `AGENTS.md`; every module variant must remain below 4,000 estimated tokens.
- Historical Plan, Handoff, Audit, Task, Draft, Superseded and Archive material must not enter a default pack.
- Budgets are small growth guards, not permission to remove security, trading, accounting, reconciliation or recovery rules.
