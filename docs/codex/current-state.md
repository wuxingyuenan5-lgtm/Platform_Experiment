# Current State

This is the sole repository authority for current version, branch, review scope and known limits.

## Delivery

- Stable baseline: Platform `0.10.0`, release commit `cf6030d53b3e9a759263455569503b6c7242174e`.
- Current remediation target: Platform `0.10.1`.
- Active branch: `refactor/platform-0-10-1-non-ui-convergence`.
- Active review: Draft PR `<DRAFT_PR>`.
- The Platform 0.9.3 phase chain is complete. PRs #141 and #148–#153 are closed historical work and are not active execution state.
- Frontend product restoration is explicitly deferred and is outside this pull request.
- Context Pack, `scripts/context-for.py`, `scripts/context-packs.json`, module `AGENTS.md` files and the current context budgets are frozen at their accepted design.

## Current scope

Platform 0.10.1 non-UI convergence is limited to:

- active-document and current-state correction;
- removal of obsolete project/service naming and historical process material;
- `execution_risk` model, pure-policy, persistence and router/application separation;
- permanent repository, security and CI governance convergence.

It does not restore product pages, alter frontend product structure, change visual baselines or redesign UI data-state behavior.

## Safety and contracts

- Platform Live Write and Runtime Live Write remain disabled by default.
- Kill Switch, two-person approval, idempotency, Decimal precision and Result Unknown semantics remain protected.
- Public execution-risk API paths and request/response schemas remain compatible.
- No database schema or data meaning is changed by the module split.
- No service, database, queue, event bus or dependency-injection framework is added.

## External-state limits

Repository validation does not prove any external production fact. The following remain unverified unless supported by separate operator evidence:

- server processes and filesystem deployment paths;
- public domains, TLS and reverse proxies;
- external database contents or migrations;
- secrets and CI/CD variables;
- broker or venue credentials, connectivity and permissions;
- production monitoring, backups and restore readiness.

Deployment configuration must fail clearly when required neutral variables are absent. Their presence outside the repository must not be assumed.

## Next decision

Merge, release, tag creation, production deployment, Live Write activation and frontend restoration require separate owner decisions.
