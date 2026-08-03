# Data Model

The local Platform API currently stores state in SQLite at `platform-api/data/platform.db`. Connection, bootstrap, seeds and additive migrations have separate owners documented in `docs/architecture/OWNERSHIP.md` and `docs/database/README.md`.

## Data authority layers

| Layer | Examples | Rule |
|---|---|---|
| Reference/master | Strategy, Account, Instrument, ContractSpecification, bindings | Platform-owned current state with audited mutations |
| Command/journal | TradeCommand, ExecutionBatch, Runtime Command/Event | Idempotent lifecycle evidence; unknown results remain unknown |
| Immutable fact | FinancialFact, external Fill/Deal/Funding/Fee/Balance snapshots | Append-only identity plus content-hash conflict detection |
| Operational projection | near-real-time Position/PnL and UI status | Low-latency monitoring; never formal accounting input |
| Formal projection | formal Position, PnL, NAV and EOD reports | Rebuildable only from immutable facts |
| Read model/cache | dashboards, summaries, provider cache | Derived, freshness-labelled and replaceable |

## Numerical and temporal rules

- Money, price, quantity, multiplier and FX cross API boundaries as exact decimal strings with explicit currency/unit.
- Every external or financial record carries source time, ingestion time and data-quality state; missing is not zero.
- Stablecoin and fiat currencies are not automatically equivalent.
- Corrections append facts, differences or audited adjustments; they do not rewrite accepted history.

SQL reference snapshots under `references/database/` are evidence, not an alternate schema owner.
