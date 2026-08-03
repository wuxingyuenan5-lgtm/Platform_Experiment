# System Map

## Runtime topology

```text
User
  │
  ▼
platform-web (Vue frontend)
  │ HTTP / Platform API contracts
  ▼
platform-api (modular monolith)
  ├─ identity / authorization
  ├─ strategy / risk / approvals
  ├─ execution orchestration
  ├─ operational projections
  ├─ immutable financial facts
  └─ formal accounting / EOD / operations
  │ versioned execution commands and events
  ▼
execution-runtime
  ├─ command journal and idempotency
  ├─ live-write safety
  ├─ venue adapters
  └─ normalized external results
  │
  ▼
External venues and brokers
```

## Dependency direction

```text
Frontend → Platform contracts
Platform orchestration → Platform domain policies
Platform → versioned Runtime contract
Runtime adapters → external SDKs
Financial facts → formal projections
Trading fills → operational projections
```

Forbidden directions:

```text
Platform Backend → venue SDK
Frontend → database or venue SDK
Runtime → Platform internal modules
Trading projections → formal accounting tables
Formal accounting → operational projection inputs
Composition root → domain implementation
```

## Data authority

| Data | Authority | Derived views |
|---|---|---|
| Strategy and account binding | Platform reference/master tables | API responses |
| Execution command state | Platform command plus Runtime journal | order/batch status views |
| External execution result | Runtime normalized event and immutable references | operational order state |
| Near-real-time trading position/PnL | operational projections | UI monitoring |
| Auditable economic truth | immutable `financial_facts` | formal position, PnL and NAV |
| Safety and approval state | Platform risk/live-session modules | readiness and operations views |

## Change classification

- Local: one module, no public contract or schema change.
- Boundary: producer/consumer contract, authorization, data ownership or execution semantics.
- Migration: persistent schema or authority transition.
- Production: deployment, live-write, credentials, monitoring or recovery.

Boundary, migration and production changes require a dedicated task packet and explicit protected semantics.
