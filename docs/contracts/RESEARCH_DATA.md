# Research Data Contract

Status: `active contract`.

## Purpose

The research-data capability supports the hedge-fund dashboard with read-only public-market information. It is a Platform API domain and is not part of trade execution, formal accounting or Venue reconciliation.

## Runtime flow

```text
A-share scheduled / authorized manual refresh
  -> public-source adapters -> one collected input set
  -> policy + research_a_share_refresh.py
  -> atomic SQLite snapshot/history publication
  -> read-only research routes -> Vue board

A-share live sector flow / turnover rankings
  -> bounded provider calls + five-minute last-known-good cache
  -> research routes -> visible-page polling
```

Platform-owned research collection does not fan out from the browser to market-data sources. Existing official chart embeds retain their independent display path. `execution-runtime` is not imported or invoked by the research production flow.

## Authoritative modules

| Responsibility | Owner |
|---|---|
| Public response models and data-quality metadata | `platform-api/app/research_data_schemas.py` |
| Deterministic A-share formulas and Shenwan aggregation | `platform-api/app/a_share_research_policy.py` |
| TTL and last-known-good behavior | `platform-api/app/research_cache.py` |
| Free-source adapters and field normalization | `platform-api/app/research_providers.py` |
| Dashboard assembly and live-query partial-failure semantics | `platform-api/app/research_service.py` |
| Daily production and atomic publication | `platform-api/app/research_a_share_refresh.py` and `research_a_share_repository.py` |
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

### Parallel chart and owned-data paths

Owner confirmed on 2026-09-08 that the existing TradingView popup and Market Detail sparklines remain. The popup uses an official embed; the small SVG lines consume the existing `row.spark` mapping from `spark90d`/`spark30d`. Their entry points, interaction and data definitions are outside the strategy refactor. Building an owned database does not establish a future requirement to replace either chart. A production failure in the owned-data path must not prevent opening the existing external chart.

Owned research production follows collection → retained source batch → typed normalization/quality validation → durable observations → versioned calculation → published read projection. These are responsibilities inside the existing research domain, not six services or a new universal database. Page requests read published data; bounded backfills/imports/recalculations belong to existing background job owners, with resources separated from execution work. No new provider, scheduler deployment, full-history ingestion or long/short analysis is established by this design.

| Logical object | Required semantics before extending a dataset | Existing A-share mapping and remaining design gap |
|---|---|---|
| Dataset and entity mapping | Stable dataset/entity IDs, provider code, unit/currency, frequency, session calendar, permitted use and retention | Existing dataset names, pool configuration and versioned Shenwan mappings remain owners. TradingView symbols are display mappings; economic series need not be tradable instruments. |
| Collection run and source batch | Run identity, bounded requested window/cursor, start/end, result and permitted raw-response reference; no credentials | `research_a_share_refresh_runs` records target trade date and run timestamps/status. Full raw-batch retention is not currently implemented; its retention policy and storage remain to be defined. |
| Typed observation/history | Dataset-specific deduplication key, observation time, source, revision identity and nullable fields | `research_a_share_history` uses `(dataset, observed_at, entity_code)` with `source`, `fetched_at`, `payload_json` and `refresh_run_id`. Repeating a day updates that observation; this is not an append-only revision archive. |
| Calculation definition/run | Method version, parameters, input dataset/revision, cutoff, calendar/adjustment rules and missing-data behavior | Existing deterministic A-share policies and Market Detail `methodology_version` remain in place. A universal calculation-run store is not implemented. |
| Published result/projection | Consistent publication, source versus calculated values, quality and input/run references | `research_a_share_dataset_snapshots` owns the latest dataset publication. Current producer transactions publish related history/snapshots together and retain last successful data on failure. |

Keep three times distinct: what period the observation describes, when the source published/revised it, and when Platform obtained it. Source publication time stays missing when unavailable; `fetched_at` cannot prove past public availability. Current A-share persistence has observation and retrieval times but does not prove a complete point-in-time revision archive. Future historical analysis must select data known by its cutoff and identify where this cannot be established.

Raw, adjusted and contract prices, quote/settlement currencies, corporate-action policies and provider revisions are explicit inputs. A future bar key must include provider, entity, period, observation time and adjustment definition; macro data also requires observation period and publication/revision evidence. Borrowing LEAN's explicit adjustment modes or Freqtrade's history-truncation/initialization-length checks means adopting those validation questions, not importing trading signals or claiming that current history already satisfies them.

The first later production extension should use one existing dataset and these existing owners. Acceptance requires idempotent replay, bounded backfill, failed-refresh retention, traceable time/source and coherent publication before expanding markets. One subsequently defined indicator must reproduce from recorded input/method versions and pass cutoff and initialization-history checks. Long/short inputs, denominators, formulas, thresholds, coverage and missing-data rules remain undefined; no default RSI score, position ratio or composite trade signal is implied.

SQLite remains the current serving store. PostgreSQL is a future deployment/concurrent-write decision; Parquet/DuckDB may serve bounded bulk research when justified. This design adds no tables or database migration and never writes research observations into the Runtime journal or financial ledger.

### Delivery modes

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
| A-share dashboard, index history, Shenwan membership, stock-pool, stock snapshots, four-sector crowding history and innovation-drug crowding history; keyed by dataset, observation identity, classification identity or stock code | Platform-owned adapters use complete paginated Eastmoney delayed all-A snapshots for market breadth and turnover, official Eastmoney limit pools for board counts, Tencent adjusted daily K-lines for the tracked pool, official CSI index history for theme indexes, and versioned Shenwan classification. Normalized latest payloads and histories are persisted in SQLite `research_a_share_*` tables with source/fetched/status metadata. A one-time historical bootstrap may import explicitly supplied reference rows tagged `vibe-research-historical-backfill` | `research_a_share_refresh.py` collects and commits coherent snapshots after the China-market close; `/api/v1/research/a-share/*` serves read-only data to Hedge Board. The browser never calls Vibe Research or upstream providers | The dashboard has one fixed strict statistic: individual stock turnover **> 100亿元**, calculated in the daily snapshot. The dashboard GET is a direct persisted read and never re-groups the full market universe. Full index histories remain queryable in SQLite but are not part of the first-screen projection, and market/crowding charts initially read the latest 90 trading days. A rate-limited theme-index source cannot erase the benchmark snapshot; any failed/incomplete module preserves its last meaningful persisted row and marks the refresh run partial/error. External source availability, licensing and long-term scheduler operation remain operational concerns |
| A-share live sector flow and capital rotation; keyed by fetch time and sector code | Eastmoney public board-flow quote feed, normalized at the Platform API boundary | `/api/v1/research/a-share/live-sector-flow` fetches on demand and keeps only a five-minute in-process last-known-good cache; it is not written into the daily SQLite snapshot | Intraday board-flow values are deliberately separate from the post-close research dataset. The client may poll the owned endpoint every five minutes; provider failure returns a clear unavailable result or the last meaningful in-process value, never a synthetic `待分类`/zero row |
| A-share live turnover leaderboard and >100亿元 history; keyed by fetch time/security code and daily observation/security code | Eastmoney public all-A quote feed, normalized into a compact Top50 response at the Platform API boundary. The strict >100亿元 mother table is persisted in `research_a_share_history` under `hot_stock`; an explicitly approved Vibe historical backfill seeds prior daily rows | `/api/v1/research/a-share/live-market-turnover` serves Top10/Top20 UI projections, current >100亿元 detail, and a bounded historical date/industry matrix. The close refresh appends the current day’s strict-threshold rows | A failed Shenwan classification cannot empty the objective turnover board. The browser never fans out to Eastmoney; the client polls only this owned five-minute API. History is a daily production table, not a client recomputation; a missing daily count is shown unavailable rather than as zero. |
| Macro event probability history; keyed by provider event identity and minute observation | Public prediction source, 15-minute process cache and bounded JSON history at `RESEARCH_MACRO_HISTORY_PATH` (default `data/research/macro_probability_history.json`) | `research_service.py` updates it when the macro endpoint is requested; the Macro page consumes the 90-day curve | Entries older than 90 days are removed and duplicate observations within one minute collapse. Request-driven updates are not evidence of a scheduled collector |
| Account research watchlist; keyed by authenticated `user_id` with ordered item payload | Platform SQLite table `user_research_watchlists` | Account watchlist service, also used by the A-share recent-focus GET/POST routes; there is no shared browser fallback | `row_version` rejects concurrent replacement with 409. The UI reloads and asks the user to review rather than overwriting the newer list. Empty lists persist and user changes clear prior in-memory state |

Source selection and rights decisions remain in the [Macro](../hedge-board/specs/MACRO_DATA_SOURCE_MAP.md), [Commodity](../hedge-board/specs/COMMODITY_DATA_SOURCE_MAP.md) and [Crypto](../hedge-board/specs/CRYPTO_DATA_SOURCE_MAP.md) source maps. New persistent history or automated collection is introduced only after its identity, retention, revision and replay behavior are defined; a cache or request-triggered refresh must never be described as that future capability.

## A-share board production and interaction

Research reads require `research.read`, including member accounts. The shared core pool is maintained by roles with `research.write` (CEO, technical lead, or wildcard administrator). Recent focus belongs to the authenticated account and uses `profile.update_self`; CSRF is required for browser writes. Both the common middleware and route dependencies enforce these permissions. Adding/removing a core member is an atomic configuration edit; it leaves private focus and market timestamps intact. There is no GitHub sync action or success-only no-op endpoint.

Opening or refreshing the board rereads persisted data and refreshes the live sections. “更新收盘数据” is a separate privileged action: one producer gathers each required input once, calculates the read models, and commits all snapshots, histories and final run status together. Concurrent production returns `busy`; partial acquisition returns `partial`; a complete failure returns HTTP 503 and retains the last valid publication. GETs also expose a failed latest run as stale after page reload. A failed stock does not freeze healthy stocks; missing index series retain their prior observations with an explicit partial message.

The worker checks weekdays after 15:05 Asia/Shanghai while enabled. Observation dates come from source quotes/history, not the wall clock; a holiday does not create a new market date. This is an in-process worker, not an independently deployed scheduler. A-share close statistics require source quotes at/after 15:00 or an earlier dated close. Same-day high-turnover revisions replace prior qualifiers and record a valid zero-count day. Cancellation/failure remains visible in refresh status.

Market/index charts expose up to 2,000 stored observations, stock detail up to 300, and high-turnover history the last 90 observed dates with a 10-date comparison. “全部” means all returned stored observations. The chart controls change the displayed range and series; gaps stay gaps. Stock clicks open a read-only quote/day-history drawer, without invoking the separate broad one-click stock collection.

Financial metadata keeps source observation and Platform retrieval times distinct. Missing limit-pool counts, period returns and valuation fields remain null. The pool calculates 5/20-session returns from aligned adjusted closes, and YTD only when a prior year-end base exists. If new daily history fails, existing stored history keeps its original dates and retrieval time; the row is partial. Period returns are unavailable when its last close does not align with the quote date. Stale quotes do not enter current rankings or breadth. The market-width line is `(up − down) / (up + down + flat)`, unavailable for an empty denominator. Total all-A turnover comes from the complete quote snapshot, including stocks without an industry mapping.

Tracked HK quotes retain `currency=HKD`; their prices and amounts are displayed in HKD, never silently converted to CNY or summed into the CNY pool turnover summary. The quote DTO's historical `*_yuan` field names carry native currency specified by `currency`; all-A datasets remain CNY. Tencent HK amount fields are already currency units, while mainland quote amounts are in ten-thousands. Unknown HK turnover/valuation fields remain unavailable.

Live sector-flow and turnover responses keep their actual fetch time and show stale/error information on fallback. The UI polls only while visible. The sector table shows the supplied main-fund **net** flow; it does not present positive/negative parts of net flow as gross inflows/outflows. The daily >100亿元 statistic has its own observation date and is not labeled as the live ranking's current count.

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

Industry ownership always uses a versioned Shenwan membership mapping. The adapter reads the official SW2021 stock-classification history and 2014-to-2021 hierarchy workbook, joins the Shenwan index identities, and selects the newest effective record as of the China-market date. It excludes future records and hashes both official workbooks into the classification version. The scoped HTTP client uses the operating system trust store with certificate verification; it does not disable TLS verification or change global SSL settings. Market values can come from free quote sources, but external vendor board names cannot replace Shenwan L1/L2 classification.

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

### Market overview display (Owner confirmed 2026-09-08)

US overview cards are SPY, QQQ, IWM, DJI; theme cards are SOXX, GDX, XLV, XLF in that order. Newly substituted symbols without a quote show an unavailable value rather than the previous symbol’s sample quote. A-share overview and theme card clicks use the existing official TradingView advanced-chart embed with their exact index symbols; external symbol data availability is controlled by TradingView.

The high-turnover history modal defaults to the latest 10 available trading dates, ordered newest first, and offers 30 or all stored dates. Date cards and industry columns share the same date projection and have separate horizontal scrollbars. The live-turnover response supplies all stored hot-stock dates and aligned counts/industry columns; industry totals remain the latest 90 stored trading dates regardless of the selected display range.

US and A-share navigation uses the same rounded toolbar, red selected market tab and numbered pill section navigation as Commodity and Crypto. A-share refresh and close-data update actions retain their existing permissions and behavior.
