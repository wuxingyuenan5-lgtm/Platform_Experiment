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

Overseas research (FedWatch / BTC spot ETF flow / Deribit IV)
  -> daily after 06:00 Asia/Shanghai or authorized manual refresh
  -> public-source adapters -> per-dataset SQLite history
  -> read-only research routes -> dashboard consumers

TradingView Seasonal Chart (Crypto / Commodity toolbox jump buttons)
  -> board renders a lightweight external-link card
  -> user opens TradingView's Seasonal Chart for `BTCUSD` / `XAUUSD` in a new tab
  -> TradingView owns the chart data and interaction; no local chart is mounted

BTC / gold intraday cumulative movement (owned research dataset)
  -> strategy-owned Bybit high-resolution closed trade archive -> backend UTC session calculation and sampling
  -> derived SQLite history (`cumulative_volatility`), without a second raw-price store
  -> read-only range/precision route -> intraday cumulative-movement cards
```

Platform-owned research collection does not fan out from the browser to market-data sources. Seasonal Chart is an explicit external-link entry: the board does not mount a provider component or call a TradingView REST endpoint; the destination page owns data loading and does not require a Platform API key. `execution-runtime` is not imported or invoked by the research production flow.

Research-board navigation displays the next page without a whole-page CSS transition. Local chart cards mount when they approach the viewport, retaining the configured card height until then; section navigation also triggers this visibility check. Mounted charts remain mounted while scrolling, and cached-page reactivation retains their state. Existing explicit expansion controls remain authoritative. This scheduling changes browser work only: source precision, history windows, missing-data semantics and server-side session verification are unchanged.

## Authoritative modules

| Responsibility | Owner |
|---|---|
| Public response models and data-quality metadata | `platform-api/app/research_data_schemas.py` |
| Deterministic A-share formulas and Shenwan aggregation | `platform-api/app/a_share_research_policy.py` |
| TTL and last-known-good behavior | `platform-api/app/research_cache.py` |
| Free-source adapters and field normalization | `platform-api/app/research_providers.py` |
| Dashboard assembly and live-query partial-failure semantics | `platform-api/app/research_service.py` |
| Daily production and atomic publication | `platform-api/app/research_a_share_refresh.py` and `research_a_share_repository.py` |
| Overseas public-source adapters (FedWatch / Farside UK + Reader fallback / Deribit) | `platform-api/app/research_provider_overseas.py` |
| Overseas refresh scheduling and failure retention | `platform-api/app/research_overseas_refresh.py` and `research_overseas_repository.py` |
| Authenticated HTTP routes | `platform-api/app/research_routes.py` |
| Frontend API contract | `platform-web/src/api/hedgeResearch.ts` |
| A-share page orchestration | `platform-web/src/views/hedgeBoard/aShare/index.vue` |
| Macro event-probability presentation | `platform-web/src/views/hedgeBoard/macro/MacroExpectationPanel.vue` |
| Overseas public-source adapters and refresh | `platform-api/app/research_provider_overseas.py` and `research_overseas_refresh.py` |
| Overseas history storage and read routes | `platform-api/app/research_overseas_repository.py` and `research_routes.py` |
| BTC/gold intraday collection, calculation and persistence | `platform-api/app/research_cumulative_volatility.py` and `research_overseas_refresh.py` |

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

The overseas routes currently expose FedWatch probabilities, BTC spot ETF flows, BTC ATM IV term structure/snapshots, Deribit DVOL history and persisted BTC/gold intraday cumulative movement. They are read-only and public-source backed; each dataset has an independent refresh status and failure boundary. A failed refresh must retain the last valid dataset, and missing settlement/IV/flow/candle values remain null or unavailable. Intraday movement reads the strategy-owned Bybit high-resolution closed trade archive for BTCUSDT/XAUTUSDT, then the backend splits UTC Asia (23:00–07:00), Europe (07:00–15:00) and Americas (15:00–23:00) sessions, accumulates signed close-to-close percentage points, samples only the board's 15m/1h/4h levels, and emits a daily price overlay using the first valid Americas close as the baseline. The gold source is XAUTUSDT; no KuCoin/PAXG fallback or duplicate raw-price store is used. Crypto and Commodity toolboxes expose Seasonal Chart as external TradingView jump buttons, while the board keeps one platform-owned intraday cumulative-movement card per asset. These entry points must not be merged or duplicated.

## Delivery and source boundary

### Parallel chart and owned-data paths

Owner confirmed on 2026-09-08 that the existing TradingView popup and Market Detail sparklines remain. The popup uses an official embed; the small SVG lines consume the existing `row.spark` mapping from `spark90d`/`spark30d`. Their entry points, interaction and data definitions are outside the strategy refactor. Building an owned database does not establish a future requirement to replace either chart. A production failure in the owned-data path must not prevent opening the existing external chart.

Owned research production follows collection → retained source batch → typed normalization/quality validation → durable observations → versioned calculation → published read projection. These are responsibilities inside the existing research domain, not six services or a new universal database. Page requests read published data; bounded backfills/imports/recalculations belong to existing background job owners, with resources separated from execution work. No new provider, scheduler deployment, full-history ingestion or long/short analysis is established by this design.

The strategy archive consumer, serving projection and overseas derived-data refresh share one API-owned SQLite write lock. Archive publication and projection computation execute in one spawned child process; the API holds that same lock through the child result and drains an in-flight job on cancellation. A broken process is recreated and work resumes from the durable cursor; no new queue or execution authority is introduced. Collection/fetch work may remain concurrent, but publication is serialized so a close refresh or cumulative-volatility write cannot stall the archive cursor. The managed local service launcher enables Runtime research capture and the strategy worker/projection flags together; a disabled worker is an explicit non-production mode, not a valid Hedge Board serving configuration.

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
| Macro, Commodity and Crypto dashboard series; keyed by domain, series/row identity and observation time | Operator-produced canonical JSON under `HEDGE_BOARD_DATA_ROOT/public/v1/`; served by the corresponding research provider adapters | The sibling `platform-data` repository owns collection, raw responses, canonical series, dashboard publication and the DuckDB mirror. Its existing `HedgeBoard-LocalData-Refresh` Windows task invokes `scripts/refresh_local.ps1` at the configured 00:15/06:15/12:15/18:15 local times. Platform API only reads the artifacts; no second request-time collector is created | Payload timestamps and quality fields remain authoritative. The API does not schedule refreshes; missing, invalid or empty files produce an explicit unavailable state rather than synthetic values |
| BTC/gold intraday cumulative movement and price overlay; keyed by asset, UTC session, sampling interval and candle timestamp | Strategy research's shared Bybit high-resolution closed trade archive (`BTCUSDT:linear:trade`, `XAUTUSDT:linear:trade`) is the only raw-price store. `research_cumulative_volatility.py` reads that projection, samples it into the board's 15-minute/1h/4h output levels, performs UTC session bucketing and cumulative movement, and uses the first valid Americas-session close per UTC day as the price baseline. It persists only the small derived `cumulative_volatility` read model in SQLite `research_a_share_history` | The strategy research collector owns high-resolution Bybit capture; the Hedge Board producer owns the derived projection and its five-minute overseas-worker refresh. `/api/v1/research/cumulative-volatility` is a read-only serving route. The frontend only renders backend-derived cumulative and price fields; it does not fetch providers or calculate sessions, baselines or returns. Seasonal buttons open TradingView externally | The producer stores calculated 15-minute/1h/4h points with `price`, `priceBaseline` and `priceChangePct`, upserts by `(dataset, observed_at, entity_code)`, and retains prior rows on failure. Reads support 1–365 days, defaulting to the latest one-year window; the UI also offers a custom date range over the returned history and dual-handle dragging. Each session's first returned cumulative sample is rebased to **0**, and explicit no-data/stale metadata is returned. The three session curves and the Americas-session price overlay can each be toggled independently from the legend; hiding the price overlay also hides its right-side price scale. Raw BTC/XAUT candles are not duplicated by the Hedge Board; shared archive freshness and strategy collector uptime remain operational concerns. |
| A-share dashboard, index history, Shenwan membership, stock-pool, stock snapshots, four-sector crowding history and innovation-drug crowding history; keyed by dataset, observation identity, classification identity or stock code | Platform-owned adapters use complete paginated Eastmoney delayed all-A snapshots for market breadth and turnover, official Eastmoney limit pools for board counts, Tencent adjusted daily K-lines for the tracked pool, official CSI index history for theme indexes, and versioned Shenwan classification. The four crowding industries use direct Eastmoney board quotes (`BK0448`, `BK0735`, `BK0459`, `BK1036`), not a sum of classified constituents. Normalized latest payloads and histories are persisted in SQLite `research_a_share_*` tables with source/fetched/status metadata. A one-time historical bootstrap may import explicitly supplied reference rows tagged `vibe-research-historical-backfill` | `research_a_share_refresh.py` collects and commits coherent snapshots after the China-market close; `/api/v1/research/a-share/*` serves read-only data to Hedge Board. The browser never calls Vibe Research or upstream providers | The dashboard has one fixed strict statistic: individual stock turnover **> 100亿元**, calculated in the daily snapshot. The dashboard GET is a direct persisted read and never re-groups the full market universe. Full index histories remain queryable in SQLite but are not part of the first-screen projection, and market/crowding charts initially read the latest 90 trading days. Crowd `turnoverPct` fields are percentage points (3.27 means 3.27%); an absent quote stays null and the crowding module is `ready` only when all four same-date sector amount/share/turnover values and the innovation-drug amount/share/turnover are present. A rate-limited theme-index source cannot erase the benchmark snapshot; any failed/incomplete module preserves its last meaningful persisted row and marks the refresh run partial/error. External source availability, licensing and long-term scheduler operation remain operational concerns |
| A-share live sector flow and capital rotation; keyed by fetch time and sector code | Eastmoney public board-flow quote feed, normalized at the Platform API boundary | `/api/v1/research/a-share/live-sector-flow` fetches on demand and keeps only a five-minute in-process last-known-good cache; it is not written into the daily SQLite snapshot | Intraday board-flow values are deliberately separate from the post-close research dataset. The client may poll the owned endpoint every five minutes; provider failure returns a clear unavailable result or the last meaningful in-process value, never a synthetic `待分类`/zero row |
| A-share live turnover leaderboard and >100亿元 history; keyed by fetch time/security code and daily observation/security code | Eastmoney public all-A quote feed, normalized into a compact Top50 response at the Platform API boundary. The strict >100亿元 mother table is persisted in `research_a_share_history` under `hot_stock`; an explicitly approved Vibe historical backfill seeds prior daily rows | `/api/v1/research/a-share/live-market-turnover` serves Top10/Top20 UI projections, current >100亿元 detail, and a bounded historical date/industry matrix. The close refresh appends the current day’s strict-threshold rows | A failed Shenwan classification cannot empty the objective turnover board. The browser never fans out to Eastmoney; the client polls only this owned five-minute API. History is a daily production table, not a client recomputation; a missing daily count is shown unavailable rather than as zero. |
| Macro event probability history; keyed by provider event identity and observation timestamp | Curated public Polymarket markets, plus a bounded Fed-event slug list when the volume-ranked feed has no live monetary-policy contract; filtered in `research_macro_expectations_refresh.py` and atomically published to `HEDGE_BOARD_DATA_ROOT/public/v1/macro/expectations.json` | The overseas worker refreshes this small feed on its five-minute loop; `MacroResearchProvider` and the Macro page only read the local artifact. Fed monetary-policy contracts are backfilled from the Polymarket CLOB Yes-leg price-history endpoint and retained for 30 days at five-minute fidelity. The Fed path is rendered in the Rates section with 1D/7D/30D/All range tabs; the event-probability panel excludes monetary-policy cards to avoid duplicate presentation. Event `label` is the Chinese display title and `originalLabel` preserves the provider title for audit; the artifact carries a stable Polymarket markets source URL and each event carries its own event URL | Only binary Yes/No markets with macro taxonomy, sufficient liquidity/volume and a bounded expiry window are admitted. Category matching is word-boundary based so terms such as `fed` do not match unrelated words such as `Federation`, and election terms take precedence over country keywords. Monetary policy is retained as an explicit category even when temporarily empty. Upstream failure preserves the last valid artifact; no-data/stale status is explicit and no probability is synthesized |
| Account research watchlist; keyed by authenticated `user_id` with ordered item payload | Platform SQLite table `user_research_watchlists` | Account watchlist service, also used by the A-share recent-focus GET/POST routes; there is no shared browser fallback | `row_version` rejects concurrent replacement with 409. The UI reloads and asks the user to review rather than overwriting the newer list. Empty lists persist and user changes clear prior in-memory state |

Source selection and rights decisions remain in the [Macro](../hedge-board/specs/MACRO_DATA_SOURCE_MAP.md), [Commodity](../hedge-board/specs/COMMODITY_DATA_SOURCE_MAP.md) and [Crypto](../hedge-board/specs/CRYPTO_DATA_SOURCE_MAP.md) source maps. New persistent history or automated collection is introduced only after its identity, retention, revision and replay behavior are defined; a cache or request-triggered refresh must never be described as that future capability.

## Overseas public research data

### Market-detail snapshots and account layouts

`GET /api/v1/research/market-detail/{market_id}` accepts `macro`, `gold`, `crypto`,
`us` and `global`. Macro continues to read the platform-data artifact. The other
four markets read persisted `market_detail_<market_id>` payloads in
`research_a_share_dataset_snapshots`; GET never starts Yahoo requests or writes
prices. `research_market_detail_refresh.py` owns their production using the
existing Yahoo chart transport, the page's fixed symbol universe, at most six
concurrent requests, and a 15-minute refresh window. Its worker is managed by
the overseas lifespan and the existing `research_refresh_enabled` setting,
independently of the ETF/IV and cumulative-movement loops.

These are latest research snapshots, not a tick archive or execution quotes.
Source daily dates use the upstream exchange timezone; Decimal values, source
observation dates and retrieval times remain distinct. Returns are close-price
returns, excluding distributions. Missing year/quarter baselines and incomplete
52-week coverage remain null. Moving-average directions require the full
10/20/50/200-observation window. Table signal headings identify these daily
moving averages and the 20/50 average comparison; they are not 1H/4H candle
signals. Continuous commodity futures are identified as
futures, not spot substitutes. The API retains a failed symbol's last row as
`stale`, retains all prior rows on total failure, and marks snapshots older than
one hour stale. No successful retry may relabel an old observation as today's
price. Data audit checks both persisted quality and last successful retrieval. Each
market snapshot is checked once under market-specific rules, not again under
the A-share snapshot rules; fresh partial coverage is a warning, and stale or
failed collection remains an error.

US/global overview, details and rotation read this same snapshot. Unconnected
breadth, DSPX/COR1M and wealth-campaign fields have no authoritative feed; they
remain unavailable. External research-link cards remain external links. No
sample prices, yield offers, zero fills or generated sparklines substitute for
missing source data. File-dashboard read failures mark retained cache values
and their series stale without changing the last source date.

`GET`/`PUT /api/v1/me/research-market-layout/{market_id}` persist only ordered
groups and row identities in `user_research_market_layouts`, owned by
`research_market_layout_repository.py`. The authenticated account owns the key;
read/write use `profile.read_self`/`profile.update_self`. PUT requires
`expectedVersion`; conflicts return 409. `groups: null` restores defaults;
`groups: []` is a saved empty list. Market values are forbidden in the payload.
After a page reload, research writes restore missing in-memory CSRF through
the existing authenticated `/auth/me` flow before sending a mutation; failed
authentication prevents the write. No authorization or CSRF checks are bypassed.
An unknown custom symbol is retained as an identity with unavailable values,
never used to construct an arbitrary upstream URL. Older unscoped browser
layout keys are left intact but are not silently imported into an account.

Deribit daily idempotency requires both term and snapshot datasets to be fresh;
one successful write cannot suppress a retry of the other failed dataset.

The overseas capability covers six read-only public datasets: CME FedWatch (30-Day Fed Funds
Futures implied probabilities), Farside UK BTC/ETH spot-ETF daily flows, Deribit BTC options ATM
implied volatility (both a legacy term structure and a 1M/3M/6M/1Y daily snapshot), and the
shared Bybit strategy research archive used by the derived BTC/gold intraday cumulative-movement
read model. These are
research observations. They are not platform forecasts, not trade signals, and never an
execution, position, risk or accounting input.

### Sources and identifiers

| Dataset | Entity identity | Upstream source name recorded on every row | Observation date |
|---|---|---|---|
| `macro_fedwatch` | FOMC meeting date; one `__meta__` row carries EFFR, current target, hourly UTC `observedAt`, settlement source and ZQ pricing | `CME FedWatch (30-Day Fed Funds Futures)`; Yahoo delayed ZQ quotes are a transport fallback when CME blocks the deployment IP | UTC hour bucket of the fetch; the worker refreshes at most once per hour and retains prior hourly snapshots |
| `crypto_etf_flow` | BTC ETF ticker; one `__meta__` row carries the ticker column order and unit `US$m` | `Farside UK BTC Spot ETF Flows (US$m)`; direct page with same-page Reader transport fallback | Upstream flow date (the source-provided history is rewritten within a bounded 10-year window); read projection also emits backend-derived `totalFlow`, `cumulativeFlow` and an optional Bybit strategy-archive reference close for the chart's independent price axis |
| `crypto_eth_etf_flow` | ETH ETF ticker; one `__meta__` row carries the ticker column order and unit `US$m` | `Farside UK ETH Spot ETF Flows (US$m)`; direct page with same-page Reader transport fallback | Upstream flow date (the source-provided history is rewritten within a bounded 10-year window); read projection also emits backend-derived `totalFlow`, `cumulativeFlow` and an optional Bybit strategy-archive reference close for the chart's independent price axis |
| `crypto_iv_term` | Expiry code; payload carries `daysToExpiry`, standardized `tenor` and `iv` | `Deribit BTC Options ATM IV` | Platform China-calendar date of the fetch |
| `crypto_iv_snapshot` | Tenor name (`1M`/`3M`/`6M`/`1Y`); one `__meta__` row carries index price, DVOL and `observedAt` | `Deribit BTC Options ATM IV` | Platform China-calendar date of the fetch |
| `cumulative_volatility` | Asset/session/interval derived point (`btc:asia:15m`, etc.); payload carries UTC timestamp, session date, cumulative value, source close and Americas baseline fields | `Strategy research shared Bybit archive -> Hedge Board backend derived projection` | Candle timestamp in UTC |

These datasets are stored in the existing generic time-series container
`research_a_share_history`, keyed by `(dataset, observed_at, entity_code)`. The table name is
historical — its structure is a dataset-agnostic series container, and the dataset name is what
separates data domains. No overseas-specific table exists and none is required.

### Refresh scheduling

The overseas worker uses the same in-process `lifespan` + periodic-poll shape as the A-share
worker. It is a bounded in-process task, not an independently deployed scheduler, and it is
enabled only while `research_refresh_enabled` is set.

- The worker refreshes at most once per dataset per China-calendar day, and only at or after
  **06:00 Asia/Shanghai** (after the US close). Before that window `refresh_overseas` returns
  `not_due` and performs no network call.
- Idempotency is evaluated per dataset from the latest `fetched_at`; an already-refreshed dataset
  returns `up_to_date` and is skipped.
- A corrupt or unparseable `fetched_at` does not block future refreshes; it is treated as
  not-yet-refreshed.
- Sources are collected concurrently with exception isolation: one failed source does not prevent
  the others from writing. A run returns `ready`, `up_to_date`, `not_due`, `busy` or `error`.
- `POST /api/v1/research/overseas/refresh` triggers an authorized manual refresh (`research.write`)
  and bypasses the time window via `force`.

Intraday cumulative movement is refreshed on a five-minute worker cadence without the
daily-after-close gate used by the low-frequency overseas datasets. It requests a bounded
365-day window (subject to the shared archive's actual coverage), stores the 15-minute base
series and derived 1-hour/4-hour samples, and isolates
BTC and gold failures. A successful BTC pull must not erase an older gold series (or vice versa);
the read route exposes the last observation and a 45-minute stale threshold.
Each UTC-session-relative sampling bucket retains one final/latest close. Publication
replaces provisional observations in the same bucket and writes the replacement in one
transaction; historical legacy revisions are reduced to the latest observation per bucket
on read. Incremental calculation starts on a session boundary to preserve the previous
session's cumulative seed and avoid dropping a return at an arbitrary refresh timestamp.

The cumulative-movement GET accepts optional timezone-aware `start` and `end` timestamps,
inclusive and bounded by the retained 365-day read window. The backend filters first and
rebases each session's first available point to zero without rewriting stored history.
Reversed or timezone-naive windows return 422. `asOf` and `availableFrom`/`availableTo`
describe persisted coverage, so selecting older history does not mark the source stale.
Presets, custom dates and debounced slider changes all use this read path. The browser
retains the full timeline for navigation, only plots backend-returned values and resolves
hover values by the same session-day/sample slot used to draw the lines.

Historical A-share and cumulative-movement charts use the same dual-handle time-range interaction:
the preset buttons only move the selected window, while either handle can be dragged to choose a
bounded start/end date. The chart itself renders only the selected window and keeps missing points
as gaps; intraday session lines share a per-session-day sample axis so UTC session boundaries do
not create artificial breaks. It does not create an inner vertical scroll area.

### Data quality and failure semantics

Read routes return the last valid values together with an explicit health block, so a failed
refresh is never silently presented as current data:

- `observedAt` and `fetchedAt` — the last successfully persisted observation and platform fetch
  times; `null` when no data exists.
- `lastError` — `{code, message, startedAt, finishedAt}` from the most recent failed run; `null`
  after a successful run.
- `status` — `no_data` when no history exists; `stale` when the most recent run failed and the
  history predates it; `ready` otherwise.

A refresh failure must retain the previous meaningful rows. The cleanup DELETE and the INSERT for
one `observed_at` execute inside a single `BEGIN IMMEDIATE` transaction, so a failure anywhere in
the write rolls the whole statement group back and the existing rows survive. A failed refresh
records an `error` run and leaves the last valid publication readable. An empty upstream response
does not erase a meaningful prior value without an explicit source-level rule.

`POST /overseas/refresh` returns HTTP 503 with per-source health in the detail when the run fails
outright; a partially failing run reports per-source status so the UI can mark only the affected
panels.

### Network and source boundary

Overseas providers are fetched with the project's declared safe client — `httpx` with
`truststore`'s operating-system trust context — and certificate verification stays on by default.
The client tries direct egress first; when a deployment has no direct route, a transport connect
failure is retried through the explicitly configured HTTP(S)_PROXY environment. No proxy address
is hard-coded. Providers must not disable TLS verification, impersonate a browser fingerprint, or
depend on an undeclared HTTP client. The browser never fans out to these sources; only the Platform
API fetches, normalizes and persists them.

Refresh runs and history points are written through the shared
`research_a_share_refresh_runs` / `research_a_share_history` owners; the overseas modules do not
create a parallel run or history store. Tests for this capability fully mock the network and must
never contact CME, Farside UK or Deribit.

## A-share board production and interaction

Research reads require `research.read`, including member accounts. The shared core pool is maintained by roles with `research.write` (CEO, technical lead, or wildcard administrator). Recent focus belongs to the authenticated account and uses `profile.update_self`; CSRF is required for browser writes. Both the common middleware and route dependencies enforce these permissions. Adding/removing a core member is an atomic configuration edit; it leaves private focus and market timestamps intact. There is no GitHub sync action or success-only no-op endpoint.

Opening or refreshing the board rereads persisted data and refreshes the live sections. “更新收盘数据” is a separate privileged action: one producer gathers each required input once, calculates the read models, and commits all snapshots, histories and final run status together. Concurrent production returns `busy`; partial acquisition returns `partial`; a complete failure returns HTTP 503 and retains the last valid publication. GETs also expose a failed latest run as stale after page reload. A failed stock does not freeze healthy stocks; missing index series retain their prior observations with an explicit partial message.

The worker checks the cached China exchange trading calendar after 15:05 Asia/Shanghai while enabled. A missing calendar does not authorize a scheduled refresh. Observation dates come from source quotes/history, not the wall clock; Eastmoney limit-pool dates use the response `qdate`, including when a holiday request returns the preceding session's pool. This is an in-process worker, not an independently deployed scheduler. A-share close statistics require source quotes at/after 15:00 or an earlier dated close. Same-day high-turnover revisions replace prior qualifiers and record a valid zero-count day. Cancellation/failure remains visible in refresh status.

Eastmoney's A-share list, live sector-flow, four selected sector-board quotes and innovation-drug quote reads use the public delay-node pair, preferring `push2delay2` and failing over to `push2delay` on transport or payload failure without changing fields or units. A-share refresh status excludes `volatility-*` runs in the shared run table; cumulative-volatility status separately scopes to those runs. This prevents one module's five-minute producer from masking or delaying the daily A-share producer. The 2026-09-24 comparison with Vibe-Research's canonical database-backed snapshot found exact 178-date all-A turnover coverage (maximum relative amount difference below 0.003%), but the platform's four-industry crowding values were derived from constituent sums, had missing turnover points, and were incorrectly marked ready. The repair replaced those four series with the 178 aligned reference dates (712 turnover points), normalized innovation-drug turnover to percentage points, and added five missing >100亿元 history dates (51 stock rows); Vibe was used only for this one-time historical repair. Future updates and retained history are owned by this Platform API and its SQLite store. The market-width and limit-down counts do not share an identical universe/source with Vibe's LeGu effective-stock breadth, so their differences are not treated as errors without a same-universe definition.

The in-process A-share scheduler retries on its configured interval after partial results and catches unexpected cycle exceptions so one transient database/provider error cannot permanently terminate automatic refresh. Cancellation is reserved for application shutdown; status and error details remain in the refresh-run record/log.

Market/index charts expose up to 2,000 stored observations, stock detail up to 300, and high-turnover history the last 90 observed dates with a 10-date comparison. “全部” means all returned stored observations. The chart controls change the displayed range and series; gaps stay gaps. Stock clicks open a read-only quote/day-history drawer, without invoking the separate broad one-click stock collection.

Financial metadata keeps source observation and Platform retrieval times distinct. Missing limit-pool counts, period returns and valuation fields remain null. The pool calculates 5/20-session returns from aligned adjusted closes, and YTD only when a prior year-end base exists. If new daily history fails, existing stored history keeps its original dates and retrieval time; the row is partial. Period returns are unavailable when its last close does not align with the quote date. Stale quotes do not enter current rankings or breadth. The market-width line is `(up − down) / (up + down + flat)`, unavailable for an empty denominator. Total all-A turnover comes from the complete quote snapshot, including stocks without an industry mapping.

Tracked HK quotes retain `currency=HKD`; their prices and amounts are displayed in HKD, never silently converted to CNY or summed into the CNY pool turnover summary. The quote DTO's historical `*_yuan` field names carry native currency specified by `currency`; all-A datasets remain CNY. Tencent HK amount fields are already currency units, while mainland quote amounts are in ten-thousands. Unknown HK turnover/valuation fields remain unavailable.

Live sector-flow and turnover responses keep their actual fetch time and show stale/error information on fallback. The UI polls only while visible. The sector table shows the supplied main-fund **net** flow; it does not present positive/negative parts of net flow as gross inflows/outflows. The daily >100亿元 statistic has its own observation date and is not labeled as the live ranking's current count.

## Public dashboard source extensions

The independent producer's `refresh-research-extensions` command covers FRED GDPNow/SLOOS/Fed components/GVZ/NFCI, Cleveland Fed nowcasts, NY Fed SCE, Treasury auctions, SPDR, CME gold inventory, Yahoo gold-futures/STRC daily prices, DefiLlama, Alternative.me, Deribit OI, BGeometrics URPD, public BTC/ETH treasury snapshots, GLD public borrow fees, FX-adjusted Coinbase/Binance premium and Bybit public VIP 0 USDT borrowing rates. Existing Binance production runs before the derived premium. Existing overseas ETF/IV and strategy-owned high-resolution collectors retain ownership.

Raw responses and exact derived inputs are retained under `raw/research/<source>/`; canonical history is under `public/v1/<domain>/series/`, with current cross-section membership under `crypto/collections/`. JSON publication uses atomic replacement. Each source fails independently, retains prior observations with `degraded`, `isStale` and `upstream_refresh_failed`, and makes the command exit nonzero; `public/v1/research-refresh.json` records the latest run. The existing task continues dashboard building and DuckDB synchronization even after a source command fails. Neither a recent file nor a successful mirror is proof that every source is fresh.

Observation, report and collection times remain distinct. Forecast target month is retained separately from nowcast vintage; FRED GDPNow contains the latest estimate per quarter, not intra-quarter vintages. Treasury issuance is auction `total_accepted` grouped by issue month, including bill rollovers/SOMA; the current month is incomplete. SPDR holdings differences are tonnes, not dollar fund flows. The gold comparison price is labelled COMEX front-month futures, not spot or licensed LBMA fixing. CME inventory uses Activity Date and retains Report Date; pledged inventory is not added a second time. Sparse snapshot history starts with collection and is never backfilled synthetically.

BTC treasury snapshot dates are collection dates and do not claim uniform issuer reporting dates. ETH reserves include only source `ACTIVE` entities; public-report/self-reported/wallet-tracked classifications and source update dates remain visible. URPD buckets describe UTXOs' last-moved price, not verified investor acquisition cost. GLD borrow fees refer to one broker; Bybit rates refer to a public VIP tier and retain hourly units. Coinbase premium uses only matching closed UTC days and actual USDT/USD conversion: `100 * (Coinbase BTCUSD / (Binance BTCUSDT * Coinbase USDTUSD) - 1)`; it is not the branded CoinGlass index. Third-party sources carry attribution and do not grant redistribution rights beyond the local research use.

The shared chart uses separate axes for different units, preserves explicit null gaps, exposes source/date and stale status, and supports bounded date windows and raw-value tables. Cross-sectional tables retain source membership and offer local filtering. Source-specific limitations remain in the three data-source maps; failed or unconnected data is not replaced with a different metric under the same name.

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

The macro panel displays selected monetary-policy, macroeconomic, geopolitical and election event probabilities from a curated public prediction-market feed. The overseas worker refreshes the feed every five minutes into the local platform-data artifact; the browser never calls Polymarket. The backend stores at most 90 observations per event and calculates one-day and seven-day probability-point changes when enough observations exist. Binary-contract, liquidity, volume and expiry gates intentionally omit ambiguous markets, and an unavailable upstream is shown as no-data/stale rather than a fabricated probability.

These probabilities are research observations, not forecasts owned by the platform and not trade signals.

## Safety boundary

Research market data must never be used as the authoritative quote, position, order, fill, risk or accounting input for live execution. Any future reuse in execution requires a separate contract, Issue, review and acceptance process.

### Market overview display (Owner confirmed 2026-09-08)

US overview cards are SPY, QQQ, IWM, DJI; theme cards are SOXX, GDX, XLV, XLF in that order. Newly substituted symbols without a quote show an unavailable value rather than the previous symbol’s sample quote. A-share overview and theme card clicks use the existing official TradingView advanced-chart embed with their exact index symbols; external symbol data availability is controlled by TradingView.

The high-turnover history modal defaults to the latest 10 available trading dates, ordered newest first, and offers 30 or all stored dates. Date cards and industry columns share the same date projection and have separate horizontal scrollbars. The live-turnover response supplies all stored hot-stock dates and aligned counts/industry columns; industry totals remain the latest 90 stored trading dates regardless of the selected display range.

The A-share overview's full-market turnover value is clickable and opens the persisted daily `market` history, newest date first. Each row exposes trading date, total turnover in 亿元, change versus the previous archived trading date, and the recorded source. The Platform API computes the change from consecutive stored market observations; the browser only formats and renders this history. The existing daily A-share refresh derives total turnover from the complete market snapshot and atomically stores it with the dashboard refresh, so opening the history does not trigger an upstream request and ongoing production does not depend on Vibe-Research.

US and A-share navigation uses the same rounded toolbar, red selected market tab and numbered pill section navigation as Commodity and Crypto. A-share refresh and close-data update actions retain their existing permissions and behavior.


## Strategy pretrade research V1

Owner-confirmed scope is single-venue Bybit funding and the existing XAUTUSDT perpetual / fixed-account MT5 XAUUSD mapping. Native MT5 symbol, broker, server, contract size and lot steps come from the Worker specification; the display label is not identity. Delivery futures, term structure, roll templates and OI-weighted funding are outside this module. Initial high-resolution subscriptions are XAUTUSDT/BTCUSDT linear L50, BTCUSDT spot L50 and linear tickers; the 60-second paired-market scanner is explicitly a scan, not tick history. Native public subscriptions are shared within the existing Bybit connection owner. No account borrowing or transfers occur.

Runtime captures through `research_market_capture.py` and `market_spool.py`, using the existing fixed MT5 Worker `copy_ticks_range` with bounded one-second ranges, a two-millisecond overlap and an initial 200ms drain interval. It does not poll only the latest Tick. Existing session identity checks remain; research does not load positions or account financial projections. Research yields to busy Worker calls and pauses MT5 reads while Live Write is enabled. A brief yield to account operations is reported as `deferred`, retaining the last successful read time rather than recording a broker source gap; if no successful MT5 read occurred within 15 minutes, data audit reports an error. An empty MT5 range is informational only when the configured MT5 session is closed and the scan itself is fresh; open or unknown sessions still expose the missing Tick evidence. Raw pybit messages are captured before its synthetic snapshot merge. The public WebSocket owner reconnects when a socket disconnects or either subscribed category receives no accepted message for 120 seconds; the gap remains recorded until fresh native messages arrive. A failed clock resample does not invalidate an earlier calibration while its 120-second validity window remains open. Callback queue overflow/disk limits stop capture with a gap; they never silently drop and continue a healthy book.

Spool restart recovery trusts older sealed, fsynced segments and validates only the active tail segment; full historical checksum verification remains an explicit offline audit rather than startup work. This keeps a large retained archive from blocking the Runtime/API/Web startup path.

Runtime read-only `/v1/market-data/events?after=...&limit=...` is `market-events.v1`: a batch has `after`, `nextCursor`, `events`, `capture`; only fsynced frames are visible. Events retain collector session, string sequence, UTC Runtime receive time, monotonic nanosecond string, native source event/publish millisecond strings, source layer, native payload, quote scope, realtime/backfill mode and quality. Backfill never claims original local availability. MT5 batches preserve native order and all records, with overlapping signatures counted as a multiset; no global native Tick ID is invented. Native prices and times survive abnormalities. A gap invalidates the derived book, snapshot resets it, and ordinary L50 update IDs are not assumed consecutive.

Platform `strategy_research_repository.py` exclusively owns Parquet publication and research SQLite metadata. Platform receives batches in its background lifecycle, independently of pages; request handlers never start capture, migrations or full backfill. See the [database guide](../database/README.md) for manifests, recovery and backup. GETs expose only bounded published history; current provisional prices are explicitly provisional. Original 60-second snapshots and one-second cache are never imported as high-resolution history.

`observed-spread.v1` causally combines only already received quotes, retaining both event IDs. Three event spreads are mid A minus mid B, ask A minus bid B, bid A minus ask B. The one-second layer derives spread OHLC, valid duration and R7 equal-second-close quantiles from those events, not separate leg extrema. The last event has no fabricated future duration. `research-quality.v2` excludes numeric errors, native/receive age beyond two seconds, capture gaps, backfill, unverified clocks and individual bid/ask widths exceeding 5% of bid; raw/all-observation views remain available. Trading-calendar coverage is currently unknown, not assumed open. MT5 time conversion is deliberately unverified until an operator establishes a versioned native-time calibration; no automatic offset repair exists. No future nearest join is allowed. Bybit native events carry the already-observed `bybit-clock-interval.v1` calibration reference and offset interval from the existing owner public server-time request. The raw source/receive timestamps remain unchanged. Calibration rejects RTT above one second, a clock step during the request, or offset above 60 seconds; it expires after 120 seconds and includes a 100ms drift allowance. The conservative source-age upper bound controls freshness. Future, expired, different-session or locally stepped clock evidence is excluded. Older v1 derived records remain immutable with their own quality version; no retrospective calibration repairs earlier availability. MT5 native time is not calibrated from Bybit time. MT5 range queries do use the conservative observed UTC lower bound with monotonic elapsed time, so a fast host clock cannot query future intervals and advance past ticks before they arrive. An unavailable or expired UTC reference holds the MT5 cursor; it does not silently advance. Query-clock evidence is retained separately from unverified native Tick-clock evidence. See the [Bybit server-time contract](https://bybit-exchange.github.io/docs/v5/market/time) and [public VIP margin endpoint](https://bybit-exchange.github.io/docs/v5/spot-margin-uta/vip-margin).

`cashflow.v1` and `experiment.v1` use exact decimal input strings (precision 38 / scale 18), an 80-significant-digit Decimal calculation context and decimal-string outputs. No input is silently rounded; nonterminating derived division uses that declared context. Parquet stores raw decimal text rather than coercing values into binary floats. UTC ISO time, native ms and local monotonic ns are retained separately. Frontend Number conversion is display-only.

Historical bootstrap and ongoing collection use the same Runtime spool and Platform archive. Core Bybit BTC linear/spot trade prices, XAUT linear trade prices and both linear mark-price streams retain a configurable one-year window by default (`VG_RUNTIME_RESEARCH_PRICE_HISTORY_DAYS=365`, bounded by source availability and storage policy) of closed **one-minute** candles, with at most 1,000 bars per request and a separate resolution-specific durable cursor. When the retention window grows, the cursor backfills from the newly requested earlier floor instead of treating the old floor as complete. An old 15-minute cursor cannot mark one-minute history complete. Open candles are excluded; after catch-up only newly closed intervals are requested. Prices retain source decimal strings and original timestamps. This candle layer is an overview, not historical Bid/Ask, original local visibility or a source of synthetic executable spreads. The existing native L50/Ticker capture continues independently. The [official Kline endpoint](https://bybit-exchange.github.io/docs/v5/market/kline) supports a minimum one-minute interval; its availability does not establish historical order-book coverage.

The fixed MT5 account Worker separately scans an initial three-day Tick range in at most 300-second windows, reducing oversized windows under the 20,000-row read budget. Every returned native Tick remains in raw batches; minute-last observations are a separately labelled chart projection with unverified broker clock. Restart resumes the fsynced cursor. The scan watermark means requested range scanned, not uninterrupted market coverage or a count of unique trades; data audit reports the completed historical scan as informational rather than as a live stream. Overlapping native boundary records remain in raw evidence.

`GET /research/strategies/pairs/{pair}/history` reads only published local shards, filters candles and settlements by source time (not retrieval time), and retains the existing private broker-read permission. Windows are bounded to 31 days. The chart selects a last available original close per 1/5/15-minute display bucket for 1/7/30-day views; `sourcePriceCount` and `displayIntervalMs` distinguish stored resolution from display sampling. Old overview shards are retained but excluded from the one-minute projection. Missing price intervals remain gaps. Funding uses actual settlement timestamps; public borrow observations use the five-minute rate collector and retain hourly units. Neither needs price-event frequency. Historical account-specific borrowing and unverified settlement marks remain unknown. Page refresh never initiates venue backfill; visible history polling reads the archive every minute while background capture continues with the page closed.

Scenario cash uses matched economic quantity and income-positive signs: price PnL + funding + borrow + Swap - fees - extra execution cost. Bid/ask or VWAP already includes spread/depth impact. Funding settlement and entry-visible indication/scenario are separate; missing settlement marks remain unknown, and the +/-5-second settlement window returns an inclusion range. Borrow uses a versioned hourly UTA liability rule, initial spot partial-hour charge to the next :05 and unpaid-interest compounding; constant-rate input is explicitly a scenario. Swap supports points and profit-currency modes with direction, contract size, effective time and rollover multiplicity; unsupported modes remain unknown. No missing cost becomes zero. Cross cash currently requires an explicit USD/USDT 1:1 scenario; it does not claim observed FX or exact converted multi-currency realized PnL.

Experiments freeze published shard identities and checksums, parameters, clock, quality/cost/method versions and cutoff. Sequential independent entries cannot overlap and require leave/re-enter rearming. Target, risk and timeout use executable opposite-side quotes; missing paths and right-censored observations are excluded from resolved-return statistics and counted explicitly. MAE/MFE have price and cost-adjusted variants. Quantity scenarios use recorded Bybit depth; MT5 capacity is only top quote plus explicit slippage assumption. Main and hedge action times independently wait for subsequent quotes in positive-latency scenarios, including exits. Zero latency and quote touches never prove fills. Holding curves and exit-rule comparisons use a paired entry cohort; settlement exits use only entry-visible next-settlement indications. Funding/spread groups and settlement-aligned quotes preserve missing cash. Validation is chronological with a holding-period purge, not optimized recommended trades. Limits: 31-day window, 200,000 scanned observations, 10,000 returned chart points, 2,000 independent events per scan, 300,000 computation path points, bounded 5x5 grids. Exceeding a budget fails explicitly. Detailed results are immutable checksummed Parquet, not a second transaction ledger.

Browser endpoints are generated under `/api/v1/research/strategies/`: catalog, data-status, funding/board, pair latest/series/distribution, scenario, experiments (status/events/replay/cancel) and saved drafts. Reads and pure scenarios require `research.read`; persisted experiments/drafts require `research.write`; broker quote scopes additionally require existing `trade.read`. Browser POSTs retain session CSRF. Runs and drafts are user-owned; draft transfer only populates the existing execution form/prepare path. The execution service must independently authenticate, obtain fresh prices, match quantities and apply its unchanged risk/unknown-result and leg-release rules. A saved research draft carries no execution authorization.

The analysis surface retains the funding overview/chart and basis/borrow two-chart, two-table layout, and the cross-venue opportunity/chart/distribution/seasonal/monthly layout. Research inputs extend these surfaces; lack of coverage must remain explicit in place rather than removing the component. The initial high-frequency query uses the most recent five minutes; user-selected windows still obey the existing server budgets. Independent reads publish successful results even if another endpoint fails. Datetime boundaries use the shared research window; date-only end filters include the selected local day. Minute-last indicative funding is drawn separately from settled funding; positive rates are green and negative rates red. Public VIP 0 USDT hourly borrow observations are labelled as a public tier, never as authenticated account fees or historical effective rates.


The chart serving path uses the schema-31 replayable SQLite projection. The projector filters archive rows before decoding JSON, keeps unused raw order-book payloads only in the source archive, and writes every derived row in consistent 500-row chunks before advancing its cursor. A cursor from a release with skipped chunks does not prove historical projection completeness; missing intervals remain gaps until source-backed replay is verified. Background work consumes newly sealed archive parts even with the page closed; default chart GETs read indexed windows, not entire Parquet history. Long-window price display selects the last actual close per bucket in SQL; original minute counts/coverage remain separate. Backend responses own chart gaps, funding board summaries/ranking, and spread histograms/quantiles. Frontend controls request filtering/sorting and render those results; plotting-number conversions are not financial calculations. Funding/borrow retain their lower observation frequency, while raw price events retain native precision.

Funding basis history is a backend-owned `funding_basis` projection. For non-BTC funding symbols it is emitted only when same-bucket spot and perpetual trade candles both exist and pass quality checks; the stored decimal result is shared by the order-analysis history and statistics routes. The browser never subtracts the two legs and a missing leg remains unavailable. Live executable Bid/Ask spread shown in the execution context remains a fresh backend quote calculation and is not replaced by a stale historical projection.

Funding watch defaults are BTC, ETH, SOL, XAUT, CRCL and MSTR, with search, name/rate sorting and explicit addition/removal. The catalog uses actual Bybit perpetual scan evidence, including contracts without a spot listing; availability of a funding quote never proves spot pairing or high-precision history. Missing rates remain unknown. Funding charts omit mark prices, hide spot prices initially, and use green for positive / red for negative rates. The cross-venue historical-price panel omits funding series and settlement details. Its spread legend initially selects only mid spread; buy/sell can be enabled, and legend selection survives data refresh. An empty effective spread window explains missing simultaneous quotes/unverified time, never synthesizing executable spreads from candles or non-overlapping history.
