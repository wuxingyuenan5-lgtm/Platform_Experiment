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

## Convergence rules

- Split a module only when it separates a real policy, persistence or side-effect boundary.
- Do not introduce a service, database, queue, global DI container or event bus for organizational symmetry.
- SQLite remains the current local Platform database.
- Public contracts and persistent semantics change only through an explicit compatibility decision.
- Production topology and venue activation require external evidence and are never inferred from repository content.
