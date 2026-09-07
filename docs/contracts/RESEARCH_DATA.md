# Research Data Contract

Status: `active contract`.

## Purpose

The research-data capability supports the hedge-fund dashboard with read-only public-market information. It is a Platform API domain and is not part of trade execution, formal accounting or Venue reconciliation.

## Runtime flow

```text
Vue research pages
  -> /api/v1/research/**
  -> research_routes.py
  -> research_service.py
  -> research_providers.py
  -> free public market-data sources
```

The frontend never calls external market-data sources directly. `execution-runtime` is not imported or invoked by this flow.

## Authoritative modules

| Responsibility | Owner |
|---|---|
| Public response models and data-quality metadata | `platform-api/app/research_data_schemas.py` |
| Deterministic A-share formulas and Shenwan aggregation | `platform-api/app/a_share_research_policy.py` |
| TTL and last-known-good behavior | `platform-api/app/research_cache.py` |
| Free-source adapters and field normalization | `platform-api/app/research_providers.py` |
| Concurrent orchestration and partial-failure semantics | `platform-api/app/research_service.py` |
| Authenticated HTTP routes | `platform-api/app/research_routes.py` |
| Frontend API contract | `platform-web/src/api/hedgeResearch.ts` |
| A-share page orchestration | `platform-web/src/views/hedgeBoard/aShare/index.vue` |
| Macro event-probability presentation | `platform-web/src/views/hedgeBoard/macro/MacroExpectationPanel.vue` |

## Data-quality contract

Every module returns:

- actual upstream source;
- source timestamp when supplied upstream;
- Platform fetch timestamp;
- `loading`, `ready`, `partial`, `no_data`, `stale` or `error` status;
- stale marker and bounded error metadata.

An empty or invalid pull cannot overwrite the last meaningful value. If a refresh fails and a prior meaningful value exists, the API returns the prior value as `stale` and labels it explicitly.

## Canonical research series

A reusable research series has a stable identity and carries the metadata needed to interpret it across dashboard consumers:

- identity, label and methodology version;
- observation timestamp and Platform retrieval timestamp, both with timezone semantics;
- value, unit, currency and frequency;
- upstream source identity and source URL;
- freshness, quality flags, status and rights scope.

Derived values retain their input identities, alignment rule and methodology version. Calendar-aware market data, low-frequency macro observations and continuous crypto markets must not share an assumed session calendar. Missing history, a pending release or an unavailable field remains unavailable; it is never converted to zero or a synthetic trend.

## Delivery and source boundary

Research content uses one of four delivery modes:

- **Native** when a source is rights-clear, stable enough to maintain and supports the required history and semantics.
- **External link** when the original provider is the proper research experience, redistribution is restricted, or local reproduction has poor maintenance value.
- **Official embed** only when the provider explicitly supports embedding and it preserves the product boundary.
- **Not configured** when none of the above is suitable.

Free browser access is not evidence of redistribution rights. Third-party login sessions, private browser templates, restricted APIs and undocumented web endpoints must not become a long-term service dependency. The frontend does not directly fan out to market-data providers.

## Persistence and recovery

Research persistence is dataset-specific: only the explicit stores listed below are durable. In-process last-known-good caches provide bounded recovery within one process but are not persistent snapshots. The application repository consumes the serving representation and does not treat source-control history, a local binary database, a workflow run or a machine-specific path as a product contract.

Refresh failure, schema drift or validation failure must preserve the last meaningful observation where available, expose its staleness, and retain a bounded error state. A successful empty response does not erase a meaningful prior value without an explicit source-level rule.

### Current implementation map

The A-share read model now has a persistent snapshot/history path and lifecycle refresh worker. Other research domains continue to use their existing dataset-specific persistence and process caches; this is not a claim of a universal warehouse or production scheduler deployment.

| Dataset and identity | Current source and storage | Update owner and consumers | Time, failure and repeat semantics |
|---|---|---|---|
| Macro, Commodity and Crypto dashboard series; keyed by domain, series/row identity and observation time | Operator-produced canonical JSON under `HEDGE_BOARD_DATA_ROOT/public/v1/`; served by the corresponding research provider adapters | No in-repository producer or scheduler is established; an operator-managed upstream process owns file updates, while Platform API reads them for Hedge Board and authorized analysis inputs | Payload timestamps and quality fields remain authoritative. The API does not schedule refreshes; missing, invalid or empty files produce an explicit unavailable state rather than synthetic values |
| A-share dashboard, index history, Shenwan membership, stock-pool, stock snapshots, four-sector crowding history and innovation-drug crowding history; keyed by dataset, observation identity, classification identity or stock code | Platform-owned adapters use complete paginated Eastmoney delayed all-A snapshots for market breadth and turnover, official Eastmoney limit pools for board counts, Tencent adjusted daily K-lines for the tracked pool, Eastmoney index history for theme indexes, and versioned Shenwan classification. Normalized latest payloads and histories are persisted in SQLite `research_a_share_*` tables with source/fetched/status metadata. A one-time historical bootstrap may import explicitly supplied reference rows tagged `vibe-research-historical-backfill` | `research_a_share_refresh.py` collects and commits coherent snapshots after the China-market close; `/api/v1/research/a-share/*` serves read-only data to Hedge Board. The browser never calls Vibe Research or upstream providers | The dashboard has one fixed strict statistic: individual stock turnover **> 100亿元**, calculated in the daily snapshot. The dashboard GET is a direct persisted read and never re-groups the full market universe. Full index histories remain queryable in SQLite but are not part of the first-screen projection, and market/crowding charts initially read the latest 90 trading days. A rate-limited theme-index source cannot erase the benchmark snapshot; any failed/incomplete module preserves its last meaningful persisted row and marks the refresh run partial/error. External source availability, licensing and long-term scheduler operation remain operational concerns |
| A-share live sector flow and capital rotation; keyed by fetch time and sector code | Eastmoney public board-flow quote feed, normalized at the Platform API boundary | `/api/v1/research/a-share/live-sector-flow` fetches on demand and keeps only a five-minute in-process last-known-good cache; it is not written into the daily SQLite snapshot | Intraday board-flow values are deliberately separate from the post-close research dataset. The client may poll the owned endpoint every five minutes; provider failure returns a clear unavailable result or the last meaningful in-process value, never a synthetic `待分类`/zero row |
| A-share live turnover leaderboard and >100亿元 history; keyed by fetch time/security code and daily observation/security code | Eastmoney public all-A quote feed, normalized into a compact Top50 response at the Platform API boundary. The strict >100亿元 mother table is persisted in `research_a_share_history` under `hot_stock`; an explicitly approved Vibe historical backfill seeds prior daily rows | `/api/v1/research/a-share/live-market-turnover` serves Top10/Top20 UI projections, current >100亿元 detail, and a bounded historical date/industry matrix. The close refresh appends the current day’s strict-threshold rows | A failed Shenwan classification cannot empty the objective turnover board. The browser never fans out to Eastmoney; the client polls only this owned five-minute API. History is a daily production table, not a client recomputation; a missing daily count is shown unavailable rather than as zero. |
| Macro event probability history; keyed by provider event identity and minute observation | Public prediction source, 15-minute process cache and bounded JSON history at `RESEARCH_MACRO_HISTORY_PATH` (default `data/research/macro_probability_history.json`) | `research_service.py` updates it when the macro endpoint is requested; the Macro page consumes the 90-day curve | Entries older than 90 days are removed and duplicate observations within one minute collapse. Request-driven updates are not evidence of a scheduled collector |
| Account research watchlist; keyed by authenticated `user_id` with ordered item payload | Platform SQLite table `user_research_watchlists` | Explicit account GET/PUT through the watchlist service; the A-share page keeps a browser offline copy for recovery | `row_version` rejects concurrent replacement. An empty list is a valid persisted value; browser fallback is not the account authority |

Source selection and rights decisions remain in the [Macro](../hedge-board/specs/MACRO_DATA_SOURCE_MAP.md), [Commodity](../hedge-board/specs/COMMODITY_DATA_SOURCE_MAP.md) and [Crypto](../hedge-board/specs/CRYPTO_DATA_SOURCE_MAP.md) source maps. New persistent history or automated collection is introduced only after its identity, retention, revision and replay behavior are defined; a cache or request-triggered refresh must never be described as that future capability.

## A-share definitions

### 20-session volatility

Use the newest 21 strictly positive closing prices, calculate 20 log returns, take the sample standard deviation and annualize by `sqrt(252)`. The result is a percentage. Missing observations return unavailable; suspended sessions are not inserted as zero returns.

### Market breadth

- fewer than 600 advancing stocks: `冰点`;
- advance/decline ratio below 0.7: `偏弱`;
- below 1.2: `中性`;
- below 2.5: `偏强`;
- otherwise: `普涨`.

Speculation state uses the upstream `真实涨停` count: 100+ `亢奋`, 60+ `活跃`, 30+ `普通`, otherwise `冰点`.

### Short-term sentiment

- attempts = limit-up pool count + broken-board pool count;
- seal rate = limit-up count / attempts;
- break rate = broken-board count / attempts;
- promotion rate = today two-board-and-above count / yesterday limit-up count;
- zero denominators are unavailable rather than fabricated as zero.

### Shenwan classification

Industry ownership always uses a versioned Shenwan membership mapping. Market values can come from free quote sources, but external vendor board names cannot replace Shenwan L1/L2 classification.

The default L2 table shows only rank, L2, parent L1, return, turnover, total-market turnover share and net inflow when available. Constituent count and threshold counts are not columns in this default table.

The high-turnover work statistic is separate. It uses the single strict rule `stock turnover > 100亿元`; a value exactly equal to 100亿元 is excluded. Stock-pool theme baskets are platform-owned research-list configuration. The initial eight baskets were migrated from the approved historical pool definition and are returned with the stock-pool read model; they filter the displayed pool only and never alter market facts.

## One-click stock data

A stock query is fixed code orchestration, not an AI workflow. The Platform API reads quote/valuation, consensus, financials, valuation percentiles, reports, announcements, raw stock news, margin, holders, fund flow, dividends, block trades, dragon-tiger data, lockups, investor Q&A and Shenwan classification in parallel.

Each module fails independently. A report-source failure cannot remove the quote or financial modules. A-share chart history is retained in the persistent read model; the platform still does not claim a full tick-level stock warehouse or guaranteed upstream completeness.

## Macro probabilities

The macro panel displays selected monetary-policy, macroeconomic, geopolitical and election event probabilities from a public prediction-market source. The backend stores a bounded 90-day probability history for curve display and calculates one-day and seven-day probability-point changes when enough observations exist.

These probabilities are research observations, not forecasts owned by the platform and not trade signals.

## Safety boundary

Research market data must never be used as the authoritative quote, position, order, fill, risk or accounting input for live execution. Any future reuse in execution requires a separate contract, Issue, review and acceptance process.
