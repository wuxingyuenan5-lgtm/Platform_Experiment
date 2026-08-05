# Current State

This is the sole repository authority for the current stable baseline, candidate target scope and known limits. It is not an authority for volatile Git or GitHub state.

## Delivery

- Stable baseline: Platform `0.10.0`, release commit `cf6030d53b3e9a759263455569503b6c7242174e`.
- Current candidate target: Platform `0.10.1`.
- Platform 0.10.1 non-UI convergence covers active-document correction, durable live-acceptance operations, historical naming/process cleanup, Execution Risk responsibility separation, type safety and long-term repository governance.
- Frontend product restoration has not been executed and remains outside the current non-UI scope.
- Context Pack, `scripts/context-for.py`, `scripts/context-packs.json`, module `AGENTS.md` files and accepted context budgets remain frozen at their maintained design.

具体活动分支、HEAD和PR状态属于易变Git/GitHub事实，执行时应通过git和GitHub读取，不由长期Markdown充当权威。

## Safety and contracts

- Platform Live Write and Runtime Live Write remain disabled by default.
- Kill Switch, two-person approval, idempotency, Decimal precision and `result_unknown` semantics remain protected.
- Public Execution Risk API paths and request/response schemas remain compatible.
- The Execution Risk module split does not change database schema or persisted data meaning.
- No service, database, queue, event bus or dependency-injection framework is introduced by this convergence scope.
- Controlled live acceptance follows `../operations/LIVE_ACCEPTANCE_RUNBOOK.md`; normal build or deployment validation never authorizes live writes.

## External-state limits

Repository validation does not prove any external production fact. The following remain unverified unless supported by separate operator evidence:

- server processes and filesystem deployment paths;
- public domains, TLS and reverse proxies;
- external database contents or migrations;
- secrets and CI/CD variables;
- broker or venue credentials, connectivity and permissions;
- production monitoring, backups and restore readiness.

Deployment configuration must fail clearly when required neutral variables are absent. External production readiness must not be assumed from repository state, CI success or documentation.

## Known limits and next decisions

- Frontend product restoration, UI data-state remediation and visual changes require a separate owner decision.
- Merge, release, tag creation, production deployment and Live Write activation require separate owner decisions.
- Production expansion in funds, quantity, symbols or automation requires completion of the controlled live-acceptance and end-of-day reconciliation sequence.
