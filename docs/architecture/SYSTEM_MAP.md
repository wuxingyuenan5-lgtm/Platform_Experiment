# System Map

## Deployable topology

```text
User
  ↓
platform-web
  ↓ HTTP / Platform contracts
platform-api
  ├─ identity and authorization
  ├─ strategy, risk and approval
  ├─ execution orchestration
  ├─ research and operational projections
  └─ financial facts, accounting and reconciliation
  ↓ versioned execution commands/events
execution-runtime
  ├─ command journal and idempotency
  ├─ Live Write safety
  ├─ venue adapters
  └─ normalized external results
  ↓
External venues and brokers
```

The repository has exactly three deployable engineering subjects: `platform-web`, `platform-api` and `execution-runtime`. Platform API remains a modular monolith.

## Platform business view

These are product and supporting capabilities inside the three deployable systems, not additional services.

| Area | User entry | Nature and authority boundary |
|---|---|---|
| Home | `/home/index` | Navigation and cross-module presentation. It may summarize other modules but owns no market, position, risk or accounting fact. |
| Hedge Board | `/hedge-board/**`, `/api/v1/research/**` | Read-only research and source navigation. A-share data is collected by Platform-owned adapters in a background refresh, committed to SQLite snapshots/history, and served through read-only API contracts; browser pages never call reference projects or upstream providers. It does not authorize or supply live execution. |
| Financial AI | `/financial-ai/**`, `/api/v1/financial-ai/**` | Analysis over authorized research context. Model output remains a reviewable research draft and cannot become a trading, risk or accounting fact. |
| Strategy | `/strategy/**` and Platform strategy/execution APIs | Strategy definition, instruction and execution orchestration. Platform owns intent and control state; Runtime owns venue side effects and normalized external evidence. |
| Risk | `/risk/**` and Platform risk/approval APIs | Cross-cutting authorization, risk policy and operational safety controls. It constrains execution but does not replace order, fill or accounting authorities. |
| Data and operations | Platform persistence, research refresh, reconciliation and operator interfaces | Supporting capabilities rather than a separate product surface. Each dataset remains with its domain owner; operations may observe and recover state but must not invent business facts. |

## Dependency direction

```text
Frontend → public Platform contracts
Router/application → domain policy and repository ports
Platform API → versioned Runtime contract
Runtime adapters → external SDKs
Immutable financial facts → formal projections
Trading fills → operational projections
```

Forbidden directions:

- frontend to database or venue SDK;
- Platform API to venue SDK;
- Runtime to Platform internal modules;
- pure policy to HTTP, SQL or trade-command implementation;
- operational projection to formal-accounting input;
- composition root to duplicated business rules.

## Data authority

| Data | Authority |
|---|---|
| Served research observations and history | Platform research schemas, `research_a_share_*` SQLite snapshots/history, refresh-run provenance and upstream adapters |
| AI-generated analysis | reviewable research draft with its input context; never an execution or accounting authority |
| Strategy, account and instrument identity | Platform reference/master tables |
| Command acceptance and Platform order state | Platform command persistence |
| External execution result | Runtime journal and normalized venue evidence |
| Monitoring position/PnL | operational projections |
| Auditable economic truth | immutable `financial_facts` |
| Formal position/PnL/NAV | rebuildable formal projections |
| Safety and approval | risk and Live Trading Session modules |

## Key data flows

```text
Research sources/local canonical store
  -> Platform background refresh, normalized snapshots/history, quality metadata and read-only API
     |-> Hedge Board presentation
     `-> optional authorized context for Financial AI
           `-> reviewable analysis draft

User strategy action
  -> Platform authorization, risk and StrategyInstruction
  -> immutable execution plan and batch/command persistence
  -> versioned Runtime command
  -> Runtime journal and venue evidence
     |-> operational projections (monitoring only)
     `-> reconciliation

Authoritative venue evidence / imported statements
  -> immutable financial facts
  -> formal projections
```

Research freshness, model output and operational projections are deliberately separate. Formal projections are rebuilt only from immutable financial facts; operational projections are never accounting inputs. Reusing research data in another module does not transfer authority: the receiving module must authenticate the user and apply its own contract. Only the trading flow may reach `execution-runtime`, and only through the versioned command boundary and existing Live Write gates.

## Strategy implementation choice (2026-09-08)

The approved second-version optimization uses route A: retain the current order kernel and replace bounded shared responsibilities with maintained components. Platform still owns strategy policy, immutable plans and reservations; Runtime remains the sole owner of venue side effects and execution evidence. This is a Windows implementation. Future Linux hosting is a separate deployment decision.

The isolated `nautilus_trader==1.231.0` Windows probe ran its actual live execution engine with a mock execution client. Partial fills `0.2/0.1/0.2`, duplicate trade delivery, order-event replay and a late fill after cancellation behaved as recorded by `execution-runtime/scripts/probe_nautilus_fit.py`. However, its installed Quantity type rejected `0.0000000001` (maximum precision 9), and native USDT Money rounded `0.123456789012345678` to `0.12345679`. This fails the platform's lossless financial boundary and is sufficient to end this candidate trial. No production engine dependency or second OMS is introduced. The probe does **not** establish Funding spot-release, MT5 Ticket mapping or external restart/reconciliation acceptance. Reconsideration requires a candidate that preserves the full contract without a core fork or parallel state authority.

To repeat that decision probe, use a separate Python 3.12 environment with `nautilus_trader==1.231.0` and run `execution-runtime/scripts/probe_nautilus_fit.py`. It starts only an in-process mock client, prints the observed results and `native_precision_passed`, and does not read platform credentials or start a terminal. Do not install this optional probe dependency into the production Runtime environment.

Shared responsibilities now have explicit owners:

| Responsibility | Implementation and limit |
|---|---|
| Bybit connection, standard market/specification parsing and request budget | Account-owned pybit connection plus CCXT `4.5.78`; CCXT has no separate network/write channel. Native private order, account and economic-event extensions remain in Runtime adapters. |
| MT5 connection | Existing fixed-account Worker; Cross market reads use the same Gateway and identity boundary. |
| Platform → Runtime HTTP | One process-owned HTTPX pool; one attempt per write, bounded read retries only where the caller/adapter explicitly owns them. |
| Browser contracts and reads | FastAPI-generated OpenAPI/TypeScript, openapi-fetch over the existing Axios session/CSRF transport, and TanStack Vue Query with session-scoped keys and no mutation retry. |
| Venue identity and management finance | Exact account/instrument/native-order resolution in `venue_identity_repository.py`; retained original aliases and native events, explicit fill provenance, and one management read model. Account monitoring cannot advance command execution or resolve unknown outcomes. See [Live Account Observability](../contracts/LIVE_ACCOUNT_OBSERVABILITY.md) and [Database Guide](../database/README.md). |
| Operational instrumentation | Prometheus client metrics, derived from existing stores and connection calls; no monitoring database, financial ledger or background trading authority. See [Production Operations](../operations/PRODUCTION.md). |

vn.py's active/passive-leg and frozen-close concepts, Hummingbot's duplicate/late-event handling and Freqtrade/LEAN's research reproducibility rules remain references for behavior and acceptance. They do not add strategy plugins, default risk thresholds, new signals or new venue authorization. QuantStats remains downstream of a verified return series; detailed PnL attribution and historical identity reconciliation are not replaced by a statistics library.

The Owner requested reassessment on 2026-09-15 after recurring strategy-management instability and identified the 2026-09-08 V2 strategy/architecture report as historical reference, not an implementation authority. The report itself and subsequent changes must both be evaluated against current requirements, call paths and reproduced failures; divergence from the report alone is not a defect. The Nautilus precision probe supports rejecting the tested candidate configuration, not a conclusion that the custom kernel is more reliable than maintained alternatives. Reassessment must compare the actual Bybit/MT5 order, partial-fill, cancel/fill race and restart/reconciliation contract against version-pinned candidate code. Browser session handling, account read cost and local release serving remain separate responsibilities and cannot be validated by an OMS comparison. No replacement engine has been selected by this reassessment; findings and unresolved scenarios remain in the existing strategy workstream.

Hedge Board keeps the TradingView popup and current market-detail sparklines. The platform-owned production/analysis path runs alongside them; its logical design and current dataset mapping belong solely to [Research Data](../contracts/RESEARCH_DATA.md).

## Convergence rules

- Split a module only when it separates a real policy, persistence or side-effect boundary.
- Do not introduce a service, database, queue, global DI container or event bus for organizational symmetry.
- SQLite remains the current local Platform database.
- Public contracts and persistent semantics change only through an explicit compatibility decision.
- Production topology and venue activation require external evidence and are never inferred from repository content.


## Pretrade strategy observation boundary

Strategy research uses the same three deployable units. Runtime owns native public Bybit capture and fixed-account MT5 Tick access, recoverable spool and versioned read-only batch export. Platform owns archival Parquet, short SQLite manifest/cursor transactions, background experiment workers and authenticated research APIs. Web renders those APIs and can transfer user-owned parameters to existing execution forms. No queue service, microservice, second ledger or execution kernel is added. Research caches/results cannot become execution prices, fills or risk authority. Detailed temporal, statistical and numeric semantics belong only to [Research Data](../contracts/RESEARCH_DATA.md#strategy-pretrade-research-v1); persistence belongs to the [database guide](../database/README.md#strategy-research-schema-version-30).
