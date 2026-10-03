# Database Schema and Migration Guide

SQLite remains the approved local Platform database. This document owns persistence rules; domain meaning belongs to the relevant contract.

## Authority classes

| Class | Examples |
|---|---|
| Reference/master | legal entity, fund, strategy, venue, account, instrument |
| Identity/access | users, sessions and recovery tickets |
| Command/execution | trade commands, orders, batches and Runtime evidence |
| Operational projection | monitoring positions, PnL and exit plans |
| Immutable financial fact | `financial_facts` |
| Formal projection | formal positions, PnL and NAV |
| Risk/approval | Kill Switch, execution risk and Live Trading Session |
| Reconciliation/operations | differences, reports, alerts and recovery evidence |

A table has one owner and one authority class.

## Shared infrastructure

- `app/database_connection.py` — configured path and transaction-managed connection;
- `app/database_bootstrap.py` — core bootstrap schema;
- `app/database_seeds.py` — fixed reference data;
- `app/database.py` — single application/CLI/test initializer: bootstrap and reference seed, then all Platform and user-product migrations in numeric order;
- `app/schema_migrations.py` — ordered, additive, checksum-protected migrations.

## Domain persistence owners

| Owner | Responsibility |
|---|---|
| `app/execution_risk_repository.py` | Kill Switch, risk policy, batch-risk snapshots and risk actions |
| `app/financial_fact_repository.py` | immutable financial facts and formal projections |
| `app/venue_reconciliation_repository.py` | venue reconciliation |
| `app/eod_reconciliation_repository.py` | EOD reports and reviews |
| `app/live_trading_sessions.py` | two-person Live session state |
| `app/cross_spread_exit_repository.py` | exit plans and lifecycle persistence |
| `app/strategies/funding_exit_repository.py` | Funding per-opening exit configuration, revision, one-shot claim, original close link and audit |
| dedicated identity repositories | users, sessions, notes and holdings |
| `app/research_a_share_repository.py` | collected A-share snapshots/history and shared core-pool configuration; personal focus remains in `user_research_watchlists` |
| `app/research_market_layout_repository.py` | account-scoped market-table groups, row identities and ordering; no quote or return facts |
| `app/live_venue_snapshot_sync.py` | atomic account monitoring frames, risk, synchronization status and append-only native venue events |
| `app/venue_identity_repository.py` | exact native order identity and legacy alias resolution shared by monitoring, management and Funding account checks; no new ledger |
| `app/strategy_financial_readmodel.py` | read-only management PnL derived from canonical fills and native events; no formal accounting writes |
| Runtime journal/store owners | Runtime command, event and venue snapshots |

Router and pure-policy modules must not contain direct SQL. Services with a dedicated repository use that owner. Existing colocated transactional and read-model owners are explicitly bounded in `docs/architecture/non-repository-sql-allowlist.json`; this registry does not override stricter domain rules. The architecture check examines executable string constants recursively, excluding comments and docstrings. Venue reconciliation writes, including accepted-absence resolution and native-fill persistence, belong to `venue_reconciliation_repository.py`.

Strategy instruction planning reads native specifications before reserving the SQLite
writer. The short publication transaction rechecks the idempotency fingerprint and
Funding close capacity and original account/instrument identities, then commits the frozen plan, batch and legs together. A
concurrent identical request returns the winning persisted plan; it cannot publish a
second batch. This changes transaction duration, not schema or financial facts.

## Migration rules

1. Never edit an applied migration.
2. Add one monotonic version with a stable name and checksum.
3. Prefer additive DDL.
4. Test fresh, existing-row, repeated-startup and checksum-drift behavior.
5. Record ownership, compatibility and rollback/forward-fix behavior.
6. Do not insert real users, credentials, holdings or secrets.
7. Do not transfer authority between operational and formal data implicitly.

Execution-risk module refactors change ownership only unless an explicit migration changes DDL or persisted semantics.

## Market layouts version 38

Migration 38 adds `user_research_market_layouts`, keyed by authenticated
`(user_id, market_id)`, with a users foreign key, JSON identities, optimistic
`row_version` and UTC update time. It changes no existing market or trading
rows. Concurrent stale replacements return 409; empty layouts persist and JSON
null means defaults. Existing applications can ignore the additive table;
rollback does not require dropping it. Forward fixes use a new migration.

Four market-detail latest snapshots reuse `research_a_share_dataset_snapshots`
under `market_detail_us`, `market_detail_global`, `market_detail_gold` and
`market_detail_crypto`. Dataset quality is persisted separately from retrieval
and source dates; failed updates keep the previous observations. They do not
duplicate the strategy raw-price archive or claim historical tick retention.

## Management history read indexes version 35

Migration 35 adds a covering index for non-null account-risk history and an
instance-scoped time index for market-spread snapshots. These accelerate the
existing management projection queries without changing rows, decimal strings,
timestamp precision, timezone, valuation windows or financial classification.
They add disk space and index-maintenance work to writes; they do not compact
the database or authorize data deletion. Existing applications can read the
upgraded schema unchanged. Apply through the normal migration owner during an
approved local service update; do not edit previously applied migrations.

## Data audit persistence version 36

Migration 36 registers `data_audit_runs` and `data_audit_calendar` with the ordered
initializer. The audit and calendar modules own their contents, not their DDL.
Fresh databases no longer depend on starting the audit router to create them;
existing reports, calendar provenance and prior migration checksums are retained.
Repeated initialization is idempotent. This additive change remains readable by
the previous application; rollback does not require deleting reports or tables.

Root `data/` is ignored local output when a relative database configuration is
resolved from the repository root. It is not a fourth service or the normal
managed business database location. Preserve unexpected files for ownership
inspection; never merge or delete them as part of a structure check.

## A-share schema version 21

Version 20 remains immutable. Version 21 rebuilds the three research tables under their status checks and refresh-run foreign keys, repairing databases originally created by the retired repository DDL guard. Valid rows are copied unchanged; invalid statuses or orphan references abort and roll back the migration rather than being discarded. Migration DDL and its ledger entry share a savepoint.

`research_a_share_pool_config` is a singleton configuration row with ordered codes, version and update time. It imports the existing core-pool membership once. Market snapshots retain their own source and observation times; membership edits do not manufacture fresh prices. Personal focus uses authenticated `user_id` and optimistic `row_version` in the existing watchlist owner. The legacy global focus snapshot is retained but is not distributed to every account.

Initialize explicitly before application/CLI use. Research GETs never create or alter tables. Forward repair is tested on fresh and legacy schemas; running databases are not reset as part of validation.

## Strategy account schema version 22

Version 22 moves account synchronization/risk DDL into the ordered initializer, adds scope and raw risk payloads, and introduces `account_venue_snapshots` plus `venue_account_events`. The first retains each account's last successful frame and declared history coverage. The second retains native fill, fee, funding, swap and realized-settlement evidence across venue windows, keyed by `(account_id, source, event_type, external_id)`. An existing identity with conflicting financial content aborts the whole refresh. These are monitoring/source facts and do not silently become formal NAV or accounting facts.

Orders gain a venue payload without replacing their command identity; synchronization uses constrained updates rather than deleting and reinserting an order. `balance_snapshots.available_balance` becomes nullable while preserving prior rows and indexes. Unknown cash availability cannot satisfy admission. Existing financial fact table definitions are frozen in this migration for fresh databases.

Schema initialization precedes services and reads; management GETs perform no DDL. A successful frame, current positions, native events and last-success time commit together. Validation or persistence failure retains the previous frame and marks the attempt failed. Backward, foreign-account or malformed snapshots cannot clear positions. Old account-risk scope is `unspecified`, so old points cannot silently join a newly defined USD/UTA curve. Validation includes a read-only copy of the existing version-21 business database: upgrade to 22 and repeated initialization preserve execution-row counts and strategy bindings, with SQLite integrity check passing. Applying 22 to the original database is a separate deployment operation.

## Operational fill provenance version 23

Version 23 only adds `fills.origin`, `fills.source` and `fills.external_fill_id`. Existing rows default to `origin=legacy` with unknown source/native ID; their identifiers, quantities, prices and timestamps are unchanged. New execution confirmations use `runtime_confirmation`; native imports and monitor projections use `venue_execution`. Both represent increments within their own source stream. Runtime V1 wire fields and the execution ceiling remain unchanged.

Legacy aliases are resolved from existing order/account/instrument/native-order evidence, without renaming rows or creating a parallel alias ledger. Monitoring synthetic order IDs include account and instrument; monitoring fill IDs include account, source and native fill identity. A replay can reuse an old fill ID only with matching evidence. Command confirmations may have a different confirmation time from the native execution time: the immutable native event owns native replay validation, and monitoring does not rewrite the command confirmation.

An isolated copy of the existing version-22 backup passed upgrade to 23, two initializations and `integrity_check`. All original fields of 313 orders, 429 fills, 60 commands, 14 bindings, six positions and 222 native events were preserved. Four stored account frames replayed twice without inserting duplicate orders, fills or native events.

The Owner-authorized local maintenance on 2026-09-08 subsequently backed up both stores and upgraded the business database from 22 to 23. Backup and business integrity checks passed. Existing identities, bindings and external positions were retained; all original command, fill, instruction and batch fields matched the backup. Runtime commands, events and order routes were unchanged. Four configured accounts resumed successful read-only synchronization with both live-write gates disabled. Evidence is retained in `platform-api/data/backups/strategy-maintenance-20260908T115443Z/`, outside Git. This establishes this local installation's migration and read-only compatibility; it does not establish complete historical provenance, financial coverage or real-trading acceptance. Future upgrades use authorized maintenance; rollback uses the pre-upgrade backup or a forward repair, never relabeling or deleting historical financial facts.

## Capital monitoring schema versions 24–25

Version 24 adds `account_capital_movements` (native evidence, scope and nullable classified amount), `account_capital_coverage` (successful bounded reads), `account_capital_sync` (independent attempt/error state), and `account_valuation_rates` (timestamped USD rates). Version 25 records valuation source provenance. Amounts/rates remain decimal strings and timestamps UTC; unknown classification is null. Additive migrations preserve existing account, execution and accounting rows. Bybit UTA/Funding and MT5 history backfill starts at the earliest local equity observation. These tables support monitoring only; calculation semantics belong to `../contracts/LIVE_ACCOUNT_OBSERVABILITY.md`.


## Strategy research schema version 30

Migration 30 is additive under the existing initializer and checksum ledger. `strategy_research_repository.py` owns `research_strategy_parts`, `research_strategy_capture`, `research_strategy_experiments` and `research_strategy_drafts`. They are research metadata, not financial facts, commands or a second trading ledger. Runtime never opens the Platform database.

Raw high-frequency observations and derived events live in lossless decimal-text Parquet shards. Runtime has a checksummed append-only spool with a single-process lease; Platform has a separate publisher lease. Compression, fsync, footer/checksum checks and atomic rename occur before a short transaction atomically publishes the shard and matching derivation state/cursor. Rename-before-commit leaves a recoverable orphan; replay verifies identical content. Cursor conflicts fail. Corrupt/incomplete spool tails are retained as gap evidence and recovery proceeds in a new segment. No automatic retention deletion is implemented; storage budget exhaustion pauses capture visibly.

SQLite journal mode and synchronous settings are not weakened. The ingest guard requires FULL or stronger; WAL additionally requires an upstream WAL-reset-fixed SQLite release (3.51.3+, the 3.50.7 branch or the 3.44.6 branch). Check the actually loaded library, not the sqlite CLI version. Existing DELETE/FULL installations need no WAL migration.

Online backup first snapshots SQLite, then copies exactly its sealed shard and experiment-artifact references with checksums. `scripts/strategy_research_ops.py verify-backup` checks integrity and manifest consistency in an isolated read-only restore. It does not copy an active spool as if it were sealed, or roll back a live trading database. Large result payloads remain in Parquet; SQLite keeps task status/summary/reference. Cancellation is checked during bounded computation; interrupted running tasks return to queued on restart. Rollback is disabling the two research lifecycle flags while preserving additive tables/files; original business database restoration requires controlled maintenance.


## Strategy research serving projection version 31

Migration 31 adds `research_strategy_projection` and its single replay cursor under the existing migration owner. `strategy_research_projection.py` owns this rebuildable query layer: minute trade-price closes, minute funding indications, settled rates, public borrow observations, latest catalog values, and one-second spread buckets. Raw ticks/events remain in the original Parquet authority. Prices remain decimal text. No trading ledger or Runtime database access is introduced.

The existing Platform research lifecycle incrementally verifies sealed shards and upserts bounded batches of 500 derived rows, then commits the processed-part cursor and trailing spread-event state. A crash before cursor commit replays idempotent upserts. Trailing spread seconds are recomputed with the next shard, including the immediate predecessor, so split-shard durations match whole-sequence derivation. Projection progress is exposed separately; a rebuilding projection must not be described as complete coverage. HTTP reads do no projection writes, migrations, venue calls or Parquet scans for standard minute-history/one-second/chart-board requests. Explicit event-level replay and experiments retain the immutable Parquet path. Online SQLite backup includes the projection and cursor; existing DELETE/FULL durability is preserved.

## Funding exit configuration migration 39

Migration 39 adds `funding_exit_plans`, keyed by the original opening in `strategy_runs`. Decimal thresholds remain TEXT; revision compare-and-swap serializes configuration and trigger claims. A unique close key, frozen trigger quantity/quote timestamps, original account and linked close instruction preserve one business intent through restart. Configuration, trigger and close-link audit events share their owning transactions. No existing trading facts change and no plan is seeded or enabled by migration. Rollback retains this additive table or restores the authorized pre-upgrade backup; it must not erase a triggered identity. The linked instruction and existing orders/fills remain execution authority.

## Execution read performance migration 40

Migration 40 adds only the `(subject_id, event_type)` audit index used to verify batch flattening; it does not change evidence rows, journal mode, durability or transaction isolation. Native fee/financial reads load accepted timestamp corrections once per read operation and retain exact original-receipt, account, source and event identity checks. Fee lookups limit order and instrument-alias loading to the relevant accounts while retaining every competing command owner within each account. No cross-request cache is used: new receipts and correction decisions remain visible on the next read. Raw venue receipts, Decimal amounts and missingness retain their authority.

Funding 交易对目录读取先物化合格现货映射，再按标准化标的匹配永续，避免对两类完整目录做重复扫描。查询仍按场所、active 映射、complete 规格和原现货/永续类型筛选；仅优化查询，不改变目录、精度或迁移版本。

## Account observation lookup migration 41

Migration 41 adds lookup indexes for account/case-insensitive currency/current balance, account/actual observed instant/current risk scope, and account/scope/latest capital coverage. Timestamp expression indexes use the same `julianday` comparison as their existing queries, preserving offset-aware selection. No balances, capital-flow evidence, Decimal values, journal settings or scope rules change. Account performance reads restrict coverage to windows intersecting the requested points and parse each daily candidate timestamp once; missing days and unclassified flows remain unavailable.
