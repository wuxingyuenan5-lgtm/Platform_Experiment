# Engineering Baseline

This is the repository authority for the stable engineering baseline, candidate technical scope and externally unverified limits. Current priorities, blockers and next actions belong in `PROJECT.md`; volatile Git or GitHub state must be read from Git and GitHub.

## Delivery

- Stable baseline: Platform `0.11.4`.
- Current candidate target: Platform `0.11.4`.
- Platform 0.11.0 is the owner-accepted local engineering baseline. It includes the restored product surfaces from 0.10.3 plus the single-root repository layout, Windows local lifecycle governance, path-stable local data configuration and clean dependency bootstrapping.
- Platform 0.11.4 is the current engineering version. It carries forward independent acceptance, browser-access regression hardening and Capability alignment; it does not reopen accepted product restoration, business behavior or controlled-live core direction. Local branch and commit state must be verified separately.
- The candidate also includes the owner-accepted Hedge Board V1 work now present on main: Macro, Commodity and Crypto research surfaces, local research-data reads, explicit Native/External Link unavailable-state handling and browser acceptance. News/calendar/wealth is no longer a standalone primary module: macro calendar belongs to Hedge Board Macro, wealth information to Hedge Board Crypto, news digest to Financial AI Analysis, and legacy routes only preserve navigation compatibility.
- The Platform 0.11.4 candidate scope includes owner-confirmed Financial AI Analysis with four formal child pages: AI daily review, stock analysis, news radar and AI connection. Candidate inclusion does not by itself prove a Provider, subscription account or public upstream is available.
- Its included scope is two local, CEO-operated strategy closures: the existing Bybit `XAUTUSDT` and MT5 `XAUUSD+` cross-venue gold spread, and same-account Bybit funding carry using a CEO-specified perpetual-short plus spot-long pair. Both reuse one bounded two-leg execution, idempotency, ledger, reconciliation and recovery foundation. Funding carry supports CEO-specified symbols and quantities, multiple held pairs, perpetual-first bounded PostOnly execution for open and close, and at least one verified funding settlement. The owner additionally authorized three named Bybit read-only strategy-account migrations: bottom-fishing, short-term trader A and short-term trader B. They expose account facts only and cannot submit, amend or cancel orders. The candidate excludes automatic symbol selection, automatic sizing or rebalancing, reverse carry, cross-venue funding carry, unattended new-trade decisions, external client funds, multi-person fund operation, production deployment and home-abroad spread.
- Candidate acceptance covers shared account, instruction, ledger, permission and reconciliation foundations; connection and performance evidence; Cross and Funding execution and settlement; strategy-management presentation; and independent acceptance. Current continuation uses the single active strategy workstream linked by `PROJECT.md`; task cards and staged approval are not prerequisites for ordinary development or normal CEO trading. New external connectivity and each real-trading action still require the applicable Owner authorization.
- Candidate validation does not mean the candidate is released, deployed or production-ready.
- Platform 0.11.0 acceptance does not prove external deployment or production readiness.
- Main promotion does not by itself prove deployment, external production readiness, provider connectivity or Live Write authorization.
- `AGENTS.md` is the normal project entrypoint. Governance documents, Context Packs, task cards, and module instructions are read only when explicitly requested or directly required by the affected surface. Context estimates are guidance, not execution gates.
- Concrete active branch, HEAD and PR state are volatile Git/GitHub facts. Read them from Git and GitHub at execution time instead of treating long-lived Markdown as authority.

## Safety and contracts

- Platform Live Write and Runtime Live Write remain disabled by default. Previously configured Cross TP/SL and accepted Funding instructions can continue in the backend independently of the browser; this is not authority for autonomous new-trade decisions. Process outages and restart behavior are owned by the execution contracts.
- Kill Switch, idempotency, Decimal precision and `result_unknown` semantics remain protected. The Owner changed to normal CEO trading on 2026-09-09; current authority and operating rules are owned by `contracts/AUTHORIZATION.md` and `operations/LIVE_ACCEPTANCE_RUNBOOK.md`. Legacy acceptance sessions and temporary windows are not normal trading prerequisites; default-disabled gates and operation-specific real-trading authorization remain.
- One CEO instruction may create at most one execution batch. Bounded amend or cancel-repost activity remains inside that batch and may never increase cumulative external fill beyond the instruction quantity. Duplicate submission, concurrent execution, restart, disconnect, identity mismatch or `result_unknown` must fail closed and cannot create a new business intent.
- Normal CEO execution no longer applies temporary acceptance quantity/notional, daily-volume or position-group caps. Native quantity specifications, available balance/margin, immutable instruction quantities, cumulative-fill ceilings, bounded chase, resource serialization, Kill Switch, reconciliation and unknown-result protection remain enforced. This implemented rule does not itself authorize a real order or activation of Live Write.
- Funding partial fills use incremental hedging: each newly proven perpetual cumulative-fill increment permits only its CEO-specified proportional spot increment while the bounded perpetual remainder remains active. Duplicate events cannot duplicate spot fills; expiry or the approved chase boundary cancels the remainder, and unknown cancellation or execution state stops further side effects. Initial local-test PostOnly settings are owner-approved at a 15-second total chase TTL, one-second evaluation cadence, at most five amend or cancel-repost mutations, and at least one tick of price change before mutation. They are configuration rather than exchange facts or permanent production defaults; any pre-live change requires evidence and owner approval.
- Public Execution Risk API paths and request/response schemas remain compatible.
- Cross-venue spread execution continues to use the restored new-version safety implementation.
- The Execution Risk module split does not change database schema or persisted data meaning.
- No service, database, queue, event bus or dependency-injection framework was introduced by the 0.11.0 release.
- Controlled live acceptance follows `operations/LIVE_ACCEPTANCE_RUNBOOK.md`; normal build, validation, merge or deployment validation never authorizes live writes.

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
- Windows local lifecycle uses only Platform Web (4373), Platform API (8000) and Execution Runtime (8100). Startup records only successfully healthy services; status derives runtime state from listeners and health checks; stop acts only on matching managed records.
- External data sources, broker connectivity, production hosts, databases, credentials and real production connections remain unproven without separate operator evidence.
- External deployment, domains, databases, credentials and provider state are not proven by CI.
- Repository checks cannot establish external connectivity, a real account state or completion of controlled live trading; those facts require separate operator evidence.
- Production expansion in funds, quantity, symbols or automation requires completion of the controlled live-acceptance and end-of-day reconciliation sequence.
- Near-term priorities, blockers and next actions are maintained only in `PROJECT.md`; this baseline does not duplicate them.
