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

## Bounded task packs

| Task | Read first | Add only when needed | Exclude by default |
|---|---|---|---|
| Narrow frontend style/layout | `admin-risk/AGENTS.md`, target component, direct parent/style owner, relevant layout guard | directly used child component, Playwright spec for visual proof | backend, Runtime, unrelated UI standards, full route tree |
| A-share/Shenwan/research field | target view/composable, `admin-risk/src/api/hedgeResearch.ts`, matching backend schema/service/provider, direct tests | cache policy and source contract when semantics change | trading, Runtime, user administration |
| Add or repair Research Provider | `platform-backend/AGENTS.md`, provider boundary, research service/cache/schema, smoke script and tests | frontend mapper only when the public contract changes | unrelated Providers, trading execution, full frontend |
| Identity/permission/session | frontend access/guard/client, backend auth/authority/policy/service and direct tests | migration and E2E only when persistence or browser flow changes | Research, Runtime adapters, accounting |
| Member holdings/NAV | account view/API client, member-holding route/schema/service/repository, Decimal tests | Financial Fact docs only if formal accounting meaning changes | Runtime, unrelated user administration |
| API contract | producer schema/route, consumer client/type, contract tests | ownership catalog for a boundary move | unrelated services and historical plans |
| Funding or cross-spread display | target strategy component/composable/API client and layout guard | Platform observability schema when displayed semantics change | Venue SDKs and formal accounting internals |
| Trading execution/risk | active Critical task, ownership catalog, Platform orchestration/policy/contract, Runtime adapter/contract and direct safety tests | reconciliation and EOD when outcome semantics change | unrelated research/UI modules |
| Financial Fact/PnL/NAV/accounting | Financial Fact schema/normalization/repository/projection service, reconciliation owner and tests | display mapper only for presentation changes | operational projection as formal calculation input |
| Runtime adapter | `execution-runtime/AGENTS.md`, target adapter/contract/journal and direct tests | Platform contract consumer when payload changes | browser/user/research code |
| Database/migration/backup | `docs/database/README.md`, migration or DDL owner, recovery code and tests | affected service contract | frontend and unrelated domain repositories |
| CI/documentation/context | affected workflow/check script, `docs/engineering/GIT_WORKFLOW.md`, current-state/context map | module commands only for changed scope | product implementation unless a check proves it is required |

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
- GitHub Issue #136 and Draft PR #138 own live HEAD, CI, review and progress evidence.
- `docs/architecture/OWNERSHIP.md` owns code and data authority.
- Domain technical documents own detailed contracts; current-state and context-map link rather than repeat them.
- Historical plans are evidence, not current authority.

Browser ambient state is evidence only. Do not start browser automation for a small code edit unless visual behavior is part of the acceptance requirement or source-level checks cannot prove the result.
