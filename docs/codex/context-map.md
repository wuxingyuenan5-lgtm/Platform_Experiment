# Agent Context Map

Use the smallest sufficient evidence set. Historical process material, phase receipts and chat history are not active context.

## On-demand context

Read `AGENTS.md` first. Read this map, Context Packs, task cards, governance documents, module instructions, contracts, and historical records only when the Owner explicitly asks or the affected technical surface requires them.

## Context Pack commands

```bash
python scripts/context-for.py --list
python scripts/context-for.py research-field
python scripts/context-for.py identity-permission --json
python scripts/context-for.py --check-budgets --json
```

Context Packs are optional reading aids. Their estimates are informational and never a Token gate.

## Task routing

| Task | Read first | Add only when necessary |
|---|---|---|
| Frontend layout or style | target view/component, direct layout test, `platform-web/AGENTS.md` | visual spec and direct child |
| Restored product acceptance | accepted product page, direct E2E or screenshot script, owning product criteria | old snapshot only as read-only historical reference |
| Research field/provider | schema, provider/service/cache and direct tests | frontend mapper for public-contract changes |
| Identity and permission | auth, authority, permission registry and tests | persistence and browser E2E |
| Member holdings/NAV | schemas, service, valuation and tests | repository and contract |
| Trading/execution risk | models, pure policy, repository, router/orchestration and safety tests | Runtime contract and reconciliation |
| Financial facts/accounting | accounting contract, normalization, repository and projection tests | display mapper only for presentation |
| Runtime adapter | Runtime contract, journal, adapter and tests | Platform consumer for payload changes |
| Database/migration | database authority, migration module and affected tests | one domain contract |
| CI/documentation | affected workflow/check and current authorities | module commands for changed scope |

## Default exclusions

Do not load generated output, dependencies, virtual environments, historical plans, handoffs, evidence ledgers, phase receipts, closed review discussions, release-status snapshots, unrelated services, demo pages or visual assets unless the task directly requires them.

Browser state and external environments are evidence only. Do not infer product or production status from them.
