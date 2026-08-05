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
| Strategy, account and instrument identity | Platform reference/master tables |
| Command acceptance and Platform order state | Platform command persistence |
| External execution result | Runtime journal and normalized venue evidence |
| Monitoring position/PnL | operational projections |
| Auditable economic truth | immutable `financial_facts` |
| Formal position/PnL/NAV | rebuildable formal projections |
| Safety and approval | risk and Live Trading Session modules |

## Convergence rules

- Split a module only when it separates a real policy, persistence or side-effect boundary.
- Do not introduce a service, database, queue, global DI container or event bus for organizational symmetry.
- SQLite remains the current local Platform database.
- Public contracts and persistent semantics change only through an explicit compatibility decision.
- Production topology and venue activation require external evidence and are never inferred from repository content.
