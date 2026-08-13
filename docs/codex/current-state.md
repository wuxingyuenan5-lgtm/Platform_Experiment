# Current State

This is the sole repository authority for the current stable baseline, candidate target scope and known limits. It is not an authority for volatile Git or GitHub state.

## Delivery

- Stable baseline: Platform `0.11.0`.
- Current candidate target: Platform `0.11.1`.
- Platform 0.11.0 is the owner-accepted local engineering baseline. It includes the restored product surfaces from 0.10.3 plus the single-root repository layout, Windows local lifecycle governance, path-stable local data configuration and clean dependency bootstrapping.
- Platform 0.11.1 is the local, founder-supervised controlled-live-acceptance candidate. The project owner authorized governance updates and business implementation for the scope recorded below. Real credentials, external account or venue connections, and every Live Write step remain separately unauthorized until their explicit owner gates.
- The Platform 0.11.1 candidate scope includes controlled-live governance and readiness without reopening the accepted product restoration. Browser-access regression hardening and Capability alignment remain later acceptance concerns; they do not authorize this stage to modify frontend UI, business behavior or the candidate's controlled-live core direction.
- Its included scope is two local, CEO-operated strategy closures: the existing Bybit `XAUTUSDT` and MT5 `XAUUSD+` cross-venue gold spread, and same-account Bybit funding carry using a CEO-specified perpetual-short plus spot-long pair. Both reuse one bounded two-leg execution, idempotency, ledger, reconciliation and recovery foundation. Funding carry supports CEO-specified symbols and quantities, multiple held pairs, perpetual-first bounded PostOnly execution for open and close, and at least one verified funding settlement. It excludes automatic symbol selection, automatic sizing or rebalancing, reverse carry, cross-venue funding carry, unattended trading, external client funds, multi-person fund operation, production deployment, home-abroad spread, bottom-fishing and short-term trader strategies.
- It is managed as one version task with acceptance gates rather than separate management phases. The gates cover governance and technical design; shared account, instruction, ledger, permission and reconciliation foundations; connection and performance evidence; cross-venue spread controlled-live acceptance; funding collection and controlled-live acceptance; verified strategy-management and market presentation; and final independent acceptance. Each external connection and controlled-live execution step requires separate owner authorization.
- Candidate validation does not mean the candidate is released, deployed or production-ready.
- Platform 0.11.0 acceptance does not prove external deployment or production readiness.
- Main promotion does not by itself prove deployment, external production readiness, provider connectivity or Live Write authorization.
- `docs/codex/AI_DEVELOPMENT_GOVERNANCE.md`, Context Packs, `scripts/context-for.py`, `scripts/context-packs.json`, module `AGENTS.md` files and accepted context budgets remain the maintained AI-development governance design.
- Concrete active branch, HEAD and PR state are volatile Git/GitHub facts. Read them from Git and GitHub at execution time instead of treating long-lived Markdown as authority.

## Safety and contracts

- Platform Live Write and Runtime Live Write remain disabled by default.
- Kill Switch, idempotency, Decimal precision and `result_unknown` semantics remain protected. The 0.11.1 narrow single-responsible-person exception is governed by `../operations/LIVE_ACCEPTANCE_RUNBOOK.md`; it requires a new time-limited Live Write window for every authorized step and does not alter the default-disabled gates.
- One CEO instruction may create at most one execution batch. Bounded amend or cancel-repost activity remains inside that batch and may never increase cumulative external fill beyond the instruction quantity. Duplicate submission, concurrent execution, restart, disconnect, identity mismatch or `result_unknown` must fail closed and cannot create a new business intent.
- The owner does not require a new funding-carry amount cap merely because the strategy supports multiple symbols. Existing runbook absolute limits remain in force until the technical lead supplies a conflict-safe proposal and the owner separately approves any contract change; this unresolved contract question cannot be interpreted as Live Write authority.
- Public Execution Risk API paths and request/response schemas remain compatible.
- Cross-venue spread execution continues to use the restored new-version safety implementation.
- The Execution Risk module split does not change database schema or persisted data meaning.
- No service, database, queue, event bus or dependency-injection framework was introduced by the 0.11.0 release.
- Controlled live acceptance follows `../operations/LIVE_ACCEPTANCE_RUNBOOK.md`; normal build, validation, merge or deployment validation never authorizes live writes.

## External-state limits

Repository validation does not prove any external production fact. The following remain unverified unless supported by separate operator evidence:

- server processes and filesystem deployment paths;
- public domains, TLS and reverse proxies;
- external database contents or migrations;
- secrets and CI/CD variables;
- broker, venue or data-provider credentials, connectivity and permissions;
- test-account status, external orders, fills, deals, positions, balances and live-trading state;
- production monitoring, backups and restore readiness.

Deployment configuration must fail clearly when required neutral variables are absent. External production readiness must not be assumed from repository state, CI success or documentation.

## Known limits and next decisions

- The restored product pages use the new architecture to carry the accepted legacy product content, layout hierarchy and primary interactions. Fonts and small spacing follow the newer frontend conventions.
- Product-data metadata remains internal. Ordinary product UI uses concise business state language and does not expose Provider, Owner, source, `actionable`, static-design or architecture explanations.
- Risk detail is available as a formal page. The global risk message strip and notification center currently have no available backend message source, so they display empty business states and must later be restored only through Capability or explicit service configuration rather than unconditional polling.
- Windows local multi-service start/stop lifecycle governance is deferred to the next development stage and is not part of this release gate.
- External data sources, broker connectivity, production hosts, databases, credentials and real production connections remain unproven without separate operator evidence.
- External deployment, domains, databases, credentials and provider state are not proven by CI.
- Repository checks cannot establish external connectivity, a real account state or completion of controlled live trading; those facts require separate operator evidence.
- Production expansion in funds, quantity, symbols or automation requires completion of the controlled live-acceptance and end-of-day reconciliation sequence.
- Further optimization should focus on measured AI execution cost, bounded task context, selective frontend-template simplification and removal of proven unused code rather than another unbounded architecture rewrite.
- `docs/codex/0.11.1-program.md` is the bounded control entry for the active 0.11.1 version task. It contains decisions, active work, blockers, authorization gates and evidence links only; it is not a substitute for owning contracts or immutable PR evidence.
