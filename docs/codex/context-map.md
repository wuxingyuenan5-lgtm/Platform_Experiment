# Agent Context Map

Purpose: route a task to the smallest sufficient evidence set without scanning the repository or loading historical material.

## Default startup

1. Read root `AGENTS.md`.
2. Read `docs/codex/current-state.md`.
3. Read the nearest module `AGENTS.md`.
4. Read three to eight directly affected source files and their direct tests.
5. Read `docs/architecture/OWNERSHIP.md` only when authority, dependency direction or persistence ownership changes.
6. Read one active task packet only for a Critical cross-session task.

`docs/codex/CURRENT_CONTEXT.md` is a compatibility pointer and is not part of default context.

## Executable task packs

Use the repository tool to print a bounded file list, live line/Token estimate, optional files, exclusions and checks:

```powershell
python scripts/context-for.py --list
python scripts/context-for.py research-field
python scripts/context-for.py identity-permission --json
```

The tool does not concatenate source, build a prompt, create a vector database or replace engineering judgment. Optional files are excluded until the requested semantics require them.

## Bounded task packs

| Task | Tool key | Read first | Add only when needed | Exclude by default |
|---|---|---|---|---|
| Narrow frontend style/layout | `hedge-style` | `platform-web/AGENTS.md`, target component, direct parent/style owner, relevant layout guard | directly used child component, Playwright spec for visual proof | backend, Runtime, unrelated UI standards, full route tree |
| A-share/Shenwan/research field | `research-field` | target view/composable, `platform-web/src/api/hedgeResearch.ts`, matching backend schema/service and direct tests | Provider/cache only when source semantics change | trading, Runtime, user administration |
| Add or repair Research Provider | `research-provider` | `platform-backend/AGENTS.md`, provider boundary, research service/cache/schema, smoke script and tests | frontend mapper only when the public contract changes | unrelated Providers, trading execution, full frontend |
| Identity/permission/session | `identity-permission` | frontend access/guard, backend auth/authority/permissions and direct tests | migration and E2E only when persistence or browser flow changes | Research, Runtime adapters, accounting |
| Member holdings/NAV | `member-contract` | account API client, member-holding route/schema/service and direct tests | repository and formal accounting docs only when persistence or meaning changes | Runtime, unrelated user administration |
| API contract | task-specific | producer schema/route, consumer client/type, contract tests | ownership catalog for a boundary move | unrelated services and historical plans |
| Funding or cross-spread display | `trading-display` | target strategy component/API client, Platform display schema and direct tests | Runtime contract only when displayed execution semantics change | Venue SDKs and formal accounting internals |
| Trading execution/risk | task-specific Critical pack | active Critical task, ownership catalog, Platform orchestration/policy/contract, Runtime adapter/contract and direct safety tests | reconciliation and EOD when outcome semantics change | unrelated research/UI modules |
| Financial Fact/PnL/NAV/accounting | task-specific Critical pack | Financial Fact schema/normalization/repository/projection service, reconciliation owner and tests | display mapper only for presentation changes | operational projection as formal calculation input |
| Runtime adapter | task-specific | `execution-runtime/AGENTS.md`, target adapter/contract/journal and direct tests | Platform contract consumer when payload changes | browser/user/research code |
| Database/migration/backup | task-specific Critical pack | `docs/database/README.md`, migration or DDL owner, recovery code and tests | affected service contract | frontend and unrelated domain repositories |
| User-system browser E2E | `user-e2e` | E2E spec/config/access guard, seed script and module rules | backend browser-flow tests when failure crosses the HTTP boundary | unrelated product pages and Runtime |
| CI/documentation/context | task-specific | affected workflow/check script, `docs/engineering/GIT_WORKFLOW.md`, current-state/context map | module commands only for changed scope | product implementation unless a check proves it is required |

## Default exclusions

Do not automatically load:

- `tasks/` except the one active Critical packet;
- closed PR discussions, historical handoffs, release archives, DRAFT plans and changelogs;
- lock files unless dependency resolution is the task;
- `node_modules`, virtual environments, build output, coverage, Playwright output and generated inventories;
- `src/views/demo`, Mock data and template examples for product work unless the task explicitly concerns them;
- large static catalogs such as `marketTools.ts` unless the requested item is inside that catalog;
- `projects/risk-control` unless the task concerns legacy deployment, MySQL data or migration;
- unrelated services merely because a keyword appears there.

## Authority rules

- `docs/codex/current-state.md` owns compact current engineering truth.
- GitHub Issue #136 owns the live branch, Draft PR, HEAD, CI, review and progress evidence.
- `docs/architecture/OWNERSHIP.md` owns code and data authority.
- Domain technical documents own detailed contracts; current-state and context-map link rather than repeat them.
- Historical plans are evidence, not current authority.

Browser ambient state is evidence only. Do not start browser automation for a small code edit unless visual behavior is part of the acceptance requirement or source-level checks cannot prove the result.
