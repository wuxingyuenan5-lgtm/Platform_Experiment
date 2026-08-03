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
Platform API → venue SDK
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
## Architecture convergence rules

- The repository remains three deployable engineering subjects: Platform Web, modular-monolith Platform API and isolated Platform Execution Runtime. Do not split services without measured ownership, scaling or failure-isolation evidence.
- SQLite remains the current local Platform database; schema authority is additive migrations plus documented DDL owners, not ad-hoc table creation.
- External projects and libraries are adopted by capability behind Platform contracts. Runtime code must not import an external product's domain model as Platform authority.
- Source facts are immutable or append-only where required; caches, read models, operational positions and reports are derived and rebuildable.
- Production topology, Legacy services and real Venue activation are evidence-gated and are not inferred from repository files alone.
