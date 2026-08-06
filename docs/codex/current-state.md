# Current State

This is the sole repository authority for the current stable baseline, candidate target scope and known limits. It is not an authority for volatile Git or GitHub state.

## Delivery

- Stable baseline: Platform `0.10.2`, main promotion commit `e2400cb14c3c0355adf77ccefcf29262c21cade4`.
- No active repository candidate is declared.
- Platform 0.10.2 includes the non-UI governance convergence, browser access and Capability alignment, personal-account and risk-management boundaries, selective frontend product restoration, explicit `live`, `sample`, `unavailable` and `error` product-data states, and visual and browser acceptance completed through PR #156.
- Main promotion does not by itself prove deployment, external production readiness, provider connectivity or Live Write authorization.
- Context Pack, `scripts/context-for.py`, `scripts/context-packs.json`, module `AGENTS.md` files and accepted context budgets remain the maintained AI-context design.

具体活动分支、HEAD和PR状态属于易变Git/GitHub事实，执行时应通过git和GitHub读取，不由长期Markdown充当权威。

## Safety and contracts

- Platform Live Write and Runtime Live Write remain disabled by default.
- Kill Switch, two-person approval, idempotency, Decimal precision and `result_unknown` semantics remain protected.
- Public Execution Risk API paths and request/response schemas remain compatible.
- The Execution Risk module split does not change database schema or persisted data meaning.
- No service, database, queue, event bus or dependency-injection framework was introduced by Platform 0.10.2.
- Controlled live acceptance follows `../operations/LIVE_ACCEPTANCE_RUNBOOK.md`; normal build, validation, merge or deployment validation never authorizes live writes.

## External-state limits

Repository validation does not prove any external production fact. The following remain unverified unless supported by separate operator evidence:

- server processes and filesystem deployment paths;
- public domains, TLS and reverse proxies;
- external database contents or migrations;
- secrets and CI/CD variables;
- broker, venue or data-provider credentials, connectivity and permissions;
- production monitoring, backups and restore readiness.

Deployment configuration must fail clearly when required neutral variables are absent. External production readiness must not be assumed from repository state, CI success or documentation.

## Known limits and next decisions

- Some Dashboard aggregates, the strategy catalog and financial-AI providers remain unconfigured.
- Affected pages use explicitly disclosed, non-actionable `sample` or `unavailable` states instead of presenting fabricated live results.
- External deployment, domains, databases, credentials and provider state are not proven by CI.
- Production expansion in funds, quantity, symbols or automation requires completion of the controlled live-acceptance and end-of-day reconciliation sequence.
- Further optimization should focus on measured AI execution cost, bounded task context, selective frontend-template simplification and removal of proven unused code rather than another unbounded architecture rewrite.
