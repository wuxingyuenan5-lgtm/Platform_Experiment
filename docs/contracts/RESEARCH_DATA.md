# Research Data Contract

Status: `active contract`.

## Purpose

The research-data capability supports the hedge-fund dashboard with read-only public-market information. It is a Platform API domain and is not part of trade execution, formal accounting or Venue reconciliation.

## A-share ETF tracking

`GET /research/a-share/etf-tracking` and `GET /research/a-share/etf-tracking/{code}` require `research.read`, use `no-store`, and read local artifacts only. The existing research-enabled API lifespan owns the worker: successful full refreshes are gated for six hours; partial/failed batches retry after one hour, with four concurrent public requests and a 25-second request timeout. Source: `https://wangwang-etf.com/data/` public universe, ETF series, index-turnover and margin JSON. This is a third-party read model, not independently verified issuer disclosure. Unsupported daily instruments and missing optional margin series remain unavailable.

Artifacts live under `HEDGE_BOARD_DATA_ROOT/public/v1/etf-tracking`; validated responses are atomically published with URL, retrieval/attempt timestamps and SHA-256. Exact response text is retained by content hash. HTML returned with HTTP 200, invalid identities/dates and regressing latest observation dates cannot replace a valid series; failures retain the prior data with `stale`, or `no_data` if absent. Reads and writes share a process lock. The background worker has a single in-process refresh owner.

Disclosure report date is independent of quote, share and margin dates. Source qfq prices and shares use the current adjusted share basis. Estimated flow in CNY 100 million equals the change in adjusted shares in 100 million units multiplied by qfq average price; absent average uses qfq close, identified per row. Turnover is also the source's estimate. Decimal computations are serialized as strings. The flow is not attributed to any particular holder. Expanding historical percentiles use observations available as of each row, require 60 valid samples, and use absolute share/flow magnitudes. Group sums cover only eligible catalog members of the same mapped index (or display category when no index is mapped), match exact dates and are null unless every member has the metric. Summed share counts are quantity indicators, not monetary exposure. Group daily returns are turnover-weighted and require every member to have both return and turnover; group percentiles use the same expanding, minimum-60-observation rules. Detail responses include each eligible group member's enriched history and margin rows. Weekly/monthly/three-month summaries use 5/21/63 trading sessions and the close immediately before the window; insufficient history leaves totals unavailable. Financing period totals require every market session in the selected window; balance changes require a prior balance and an observation on the window end date. Index financing uses current constituents, not historical point-in-time membership; dates and source coverage remain visible.

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

Commodity and crypto each use one market-detail subpage containing the main price chart, then the intraday cumulative-movement chart, followed by the volatility index and market-detail table. Main charts and cumulative movement have no separate sidebar entries.

The A-share sidebar separates valuation and crowding into independent subpages. ETF tracking precedes the stock pool. This navigation split uses the existing observation data without changing production or metric definitions.

Charts previously opening at all history now open at three years: shared source-series charts, BTC/ETH ETF history, halving-cycle elapsed ranges and A-share ETF tracking. Shorter existing defaults remain unchanged, and all-history selection stays available. The initial view does not truncate persisted history.

FRED M2SL, PCEPI and PCEPILFE monthly freshness allows their publication lag: an observation month remains within the expected window through the end of its second following month plus three calendar days. These series use month-start observation labels, not publication timestamps; the former 75-day age check incorrectly marked the still-current August observations stale in October. Older months still expire, daily/weekly freshness rules are unchanged, and source observation dates are never relabelled.

Research chart layout responds to available container width, including sidebar and window changes. Research sections and market overviews reduce column counts when their own content area narrows; multi-series comparison charts and matrices retain full-row layouts. Source-series, option-exposure, A-share trend and halving plots adapt their drawing height within 280–420 px while retaining readable axes and controls. SVG coordinates and pointer calculations use the actual drawing size; resizing does not change the selected time range, source values or missing-data semantics.

The three domain dashboard readers share an in-memory snapshot for at most 60 seconds per browser session, including cards mounted later while scrolling. Failed requests are evicted; a session-token change clears the cache. Mounted dashboard-series, CFTC, URPD, halving and option-exposure panels check for updates once per minute while the document is visible and on return to visibility. Deactivated/unmounted panels stop their timers. Reads revalidate the HTTP cache so its prior five-minute lifetime cannot conceal a new producer revision. Refresh replaces data without remounting chart controls; upstream timestamps, missingness and degradation remain authoritative. This polling reads local artifacts only and does not accelerate upstream collection.

Research chart components are code-split at the existing viewport mounting boundary, so entering one board does not eagerly download every board's specialized chart implementation. A reserved-height loading state protects scroll and section navigation while a component module loads. The global/equity market terminal is loaded only when that page is used. Data sources, collection schedules, chart controls and visible coverage are unchanged.

## Observation freshness and cross-asset comparison

U.S. high-yield OAS (`us_hy_oas`, FRED `BAMLH0A0HYM2`) and the 10-year real Treasury yield (`us_10y_real_yield`, FRED `DFII10`) are displayed once in Macro → Rates, after the corporate-rating yields. The U.S. equity structure section no longer renders these macro cards, and the prior Macro risk-appetite OAS card is moved rather than duplicated. Existing canonical series and scheduled collectors supply both charts; relocating presentation does not create another price store or source request.

The Rates section's `corporateYields` group compares U.S. corporate **effective yields**, not option-adjusted spreads: ICE BofA AAA (`BAMLC0A1CAAAEY`), BBB (`BAMLC0A4CBBBEY`), and CCC & Lower (`BAMLH0A3HYCEY`) through FRED. The last group includes ratings below CCC and is labelled accordingly. Values are unadjusted percent at daily close; native month-end weekend observations are retained. The existing `platform-data` FRED scheduled refresh publishes these canonical series, `build-macro-dashboard` exposes the group, and `sync-local-database` mirrors observations and provenance into the existing DuckDB tables. Platform API serves the local artifact through `/api/v1/research/macro/dashboard-v1`; the browser never fetches FRED. The chart follows Polymarket in Rates and retains shared range, table, series-toggle and fullscreen controls.

FRED limits these ICE histories to a rolling three-year window from April 2026. Previously collected dates older than the returned window remain in the canonical local history; source revisions replace dates within the current window. No earlier history or missing values are synthesized. Upstream errors leave the previous publication intact and normal read-time freshness checks apply. ICE metadata is `internal_use_only`; public redistribution requires separate source rights.

The macro, commodity and crypto readers recheck observation age on every read, including after a producer stops with a valid old artifact. Known frequencies use calendar-day tolerances: daily/business-day/exchange-day 7, weekly 14, monthly 75, quarterly 200 and collected daily snapshots 2. Unknown disclosure schedules retain producer quality. Missing observation dates degrade the series; missing/error values remain missing/error. These are stale-data guardrails, not exchange calendars or collection SLAs. JSON file reads run off the API event loop.

Market-detail snapshots preserve quote timestamp, currency and price kind (`intraday`, `close`, `observation`). An unfinished daily bar remains an intraday observation in the table. SPY, GLD and BTC/USD additionally retain up to 260 dated completed observations in the existing snapshot payload. No new database table or upstream provider is required. A-share live fund-flow rankings use Eastmoney first-level industry boards; constituent counts are rising + falling + unchanged counts, with unavailable counts left null. A failed sector/innovation refresh retains prior valid history without treating it as a newly completed collection.

`GET /api/v1/research/cross-asset?days=90` uses the existing research permission and local snapshots only. The UI offers 30/90/180 calendar-day windows. The calculation excludes the current UTC date, intersects available price dates without filling gaps, and normalizes the common start to 100. Returns exclude distributions; GLD is an ETF proxy. Drawdown uses common observations, correlation uses the latest 20 common return intervals (minimum 10), and mean return conditional on SPY declines requires at least five samples. Different market closing times and multi-day intervals remain explicit limitations. Missing assets and stale snapshots are disclosed. US 10-year yield change in basis points requires both exact comparison endpoints; otherwise it is null. This is descriptive research, not proof of hedge effectiveness.

Deribit option-exposure views are scheduled snapshots, not live exposure. Their seven-hour freshness tolerance accommodates the existing six-hour producer cadence; IBIT retains its one-day tolerance. Put/Call open interest is not a long/short position ratio, and the Call+/Put− GEX proxy does not infer actual dealer inventory.

## Authoritative modules

| Responsibility | Owner |
|---|---|
| Public response models and data-quality metadata | `platform-api/app/research_data_schemas.py` |
| Deterministic A-share formulas and Shenwan aggregation | `platform-api/app/a_share_research_policy.py` |
| TTL and last-known-good behavior | `platform-api/app/research_cache.py` |
| Free-source adapters and field normalization | `platform-api/app/research_providers.py` |
| Dashboard assembly and live-query partial-failure semantics | `platform-api/app/research_service.py` |
| Market-isolated production and atomic publication | `platform-api/app/research_a_share_refresh.py`, `research_hk_share_refresh.py` and `research_a_share_repository.py` |
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

The A-share dashboard's `marketHistory.marketBreadthPct` is a derived net advancing
percentage: `100 * (up - down) / (up + down)`, excluding flat stocks. It uses the
same universe and counts as that history row's market structure (currently the
SH/SZ A-share archive), distinct from the all-A sentiment snapshot. Missing
either count or a zero advancing-plus-declining denominator returns null; equal
nonzero counts return zero. The frontend converts this percentage to a ratio
once for percent formatting. Imported native `market_breadth` ratios and the
older platform-daily-v1 percentages remain unchanged in the source archive;
the serving projection derives its value from counts rather than inferring
units from magnitude or splicing the two raw definitions.

## Canonical research series

Hedge-board chart cards expose a top-right expand control, including A-share
history charts and opened terminal instrument charts. Expansion presents the
existing chart in a full-window modal; the close control or Escape restores its
inline position, scroll and focus. Selected ranges and legends remain intact,
and expansion does not start collection or create a second chart instance.
External-reference-only cards are excluded.

BTC and ETH ETF charts use the left axis for their reference price and omit the
prior flow tick labels; daily net-flow bars retain their independent scale.
Price legends are keyboard-accessible toggles. Both overlays use Bybit spot
BTCUSDT/ETHUSDT closed UTC days from the strategy-owned archive: reuse exact
midnight minute closes where present, otherwise shared daily candles. The existing
Runtime history collector owns the daily bootstrap (1,200 days) and durable
forward cursors; Parquet retains raw values and SQLite serves `daily_candle`
separately from minute candles. ETF reads and refreshes do not request price
history or retain per-ticker price copies. Contract/Yahoo prices are excluded.
Original Farside USD flows remain authoritative; coin conversions are recomputed
from shared spot prices only with complete selected-window coverage, otherwise
the entire window remains USD with missing prices null.
Available price observations render even when they cover only part of the ETF
window: missing prices split the line, isolated observations use markers, and
the visible-window price coverage is disclosed. No price history is interpolated
or copied from another instrument to make an overlay appear complete.

A reusable research series has a stable identity and carries the metadata needed to interpret it across dashboard consumers:

- identity, label and methodology version;
- observation timestamp and Platform retrieval timestamp, both with timezone semantics;
- value, unit, currency and frequency;
- upstream source identity and source URL;
- freshness, quality flags, status and rights scope.

Derived values retain their input identities, alignment rule and methodology version. Calendar-aware market data, low-frequency macro observations and continuous crypto markets must not share an assumed session calendar. Missing history, a pending release or an unavailable field remains unavailable; it is never converted to zero or a synthetic trend.

The overseas routes currently expose FedWatch probabilities, BTC spot ETF flows, BTC ATM IV term structure/snapshots, Deribit DVOL history and persisted BTC/gold intraday cumulative movement. They are read-only and public-source backed; each dataset has an independent refresh status and failure boundary. A failed refresh must retain the last valid dataset, and missing settlement/IV/flow/candle values remain null or unavailable. Intraday movement reads the strategy-owned Bybit high-resolution closed trade archive for BTCUSDT/XAUTUSDT, then the backend splits UTC Asia (23:00–07:00), Europe (07:00–15:00) and Americas (15:00–23:00) sessions, accumulates signed close-to-close percentage points, samples only the board's 15m/1h/4h levels, and emits a daily price overlay using the first valid Americas close as the baseline. The gold source is XAUTUSDT; no KuCoin/PAXG fallback or duplicate raw-price store is used. Crypto and Commodity toolboxes expose Seasonal Chart as external TradingView jump buttons, while the board keeps one platform-owned intraday cumulative-movement card per asset. These entry points must not be merged or duplicated.

BTC ATM IV history charts retain each returned observation timestamp and source value, with a data-driven vertical scale rather than a fixed volatility band. The four tenor histories load independently; a failed tenor does not discard successful histories or erase the current snapshot quote. Historical range statistics describe the stored coverage only.

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
| BTC/gold intraday cumulative movement and price overlay; keyed by asset, UTC session, sampling interval and candle timestamp | Strategy research's shared Bybit high-resolution closed trade archive (`BTCUSDT:linear:trade`, `XAUTUSDT:linear:trade`) is the only raw-price store. `research_cumulative_volatility.py` reads that projection, samples it into the board's 15-minute/1h/4h output levels, performs UTC session bucketing and cumulative movement, and uses the first valid Americas-session close per UTC day as the price baseline. It persists only the small derived `cumulative_volatility` read model in SQLite `research_a_share_history` | The strategy research collector owns high-resolution Bybit capture; the Hedge Board producer owns the derived projection and its five-minute overseas-worker refresh. `/api/v1/research/cumulative-volatility` is a read-only serving route. The frontend only renders backend-derived cumulative and price fields; it does not fetch providers or calculate sessions, baselines or returns. Seasonal buttons open TradingView externally | The producer stores calculated 15-minute/1h/4h points with `price`, `priceBaseline` and `priceChangePct`, upserts by `(dataset, observed_at, entity_code)`, and retains prior rows on failure. Reads support 1–365 days, defaulting to the latest one-year window; the UI also offers a custom date range over the returned history and dual-handle dragging. Each session's first returned cumulative sample is rebased to **0**, and explicit no-data/stale metadata is returned. Internal missing UTC days trigger a bounded rebuild only when valid shared minute candles exist in the gap; genuine source gaps do not trigger repeated rebuilds. The chart aligns same-day session sampling buckets on a calendar-day axis, preserves missing-day and missing-bucket gaps, and does not connect across them. Full-history loads and window-rebase reads have separate request generations so precision changes and dragging cannot cancel each other; preset buttons also retry a failed load. The three session curves and the Americas-session price overlay can each be toggled independently from the legend; hiding the price overlay also hides its right-side price scale. Raw BTC/XAUT candles are not duplicated by the Hedge Board; shared archive freshness and strategy collector uptime remain operational concerns. |
| A-share dashboard, market/index history, Shenwan membership, stock-pool, stock snapshots, four-sector crowding history and innovation-drug crowding history; keyed by dataset, source universe, observation identity, classification identity or stock code | Platform-owned adapters use complete paginated Eastmoney delayed all-A snapshots for market breadth and turnover, official Eastmoney limit pools for board counts, Tencent adjusted daily K-lines for the tracked pool, official CSI index history for theme indexes, and versioned Shenwan classification. SQLite keeps `all_a` and `sh_sz_a` market archives separate and stores `000300.SH`, Shenwan `801102.SWI`, Eastmoney `BK0448` and `BK1106` prices with source, definition, raw payload and conflict evidence. The 2026-10-09 initialization read the verified same-host Vibe PostgreSQL tables in a repeatable-read, read-only transaction; future production does not read that source | `research_a_share_refresh.py` starts after Beijing 15:10. The same-day run stays partial and retries until at least 16:15 and each required Eastmoney quote carries that trade date and a time at or after 15:00; only then are the daily crowding, market archive, BK0448/BK1106 closes and >100亿元 history accepted. Prior meaningful observations remain visible with partial status while waiting. Exact `801102.SWI` closes use the computer's existing user-level Choice SDK through an isolated serial child process; SDK files and activation data stay outside the repository. `/api/v1/research/a-share/*` serves read-only data; `/market-history` pages full all-A turnover history while the dashboard returns the bounded chart projection. The browser never calls Vibe Research or upstream providers | `all_a` owns the full-A amount and accepts full-market limit-pool counts only when their trading date matches; `sh_sz_a` owns advance/decline, while its daily limit counts remain NULL unless a matching universe-specific source exists. NULL stays missing. The communication price curve uses only `801102.SWI`; `BK0448` remains a separate retained Eastmoney series and cannot fill an SWI gap. BK1106 keeps its exact Eastmoney identity. Conflicting price candidates project as NULL. Market/crowding charts initially read the latest 90 trading days and keep explicit gaps. Crowd `turnoverPct` fields are percentage points (3.27 means 3.27%). A missing enabled Choice close makes the run partial so the worker retries while retaining the last meaningful publication. The 2026-10-12 prematurely accepted rows were corrected once from later same-source conflict evidence; the original rows remain in the pre-repair backup and corrected conflict records. External source availability, licensing and long-term scheduler operation remain operational concerns |
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

Russia uses the official Moscow Exchange IMOEX local-currency price index, not the liquidating RSX ETF. The stable `global-rsx` catalogue identity remains only for saved account layout reconciliation; both table and regional rotation display IMOEX. Its producer reads verified SNDX/IMOEX/RUB historical closes plus the official current index value using Europe/Moscow timestamps. The current calendar day is marked intraday and excluded from stored close history. The first run loads roughly two years; subsequent runs re-read the latest seven calendar days to capture close revisions, maintaining an atomic source cache at `history/market-detail/moex/imoex.json` (outside canonical serving-series discovery) and SHA256 raw responses under `raw/market-detail/moex`. Normalized rows enter the same persisted market-detail production and 15-minute gate. GET reads only the database. Source failure preserves the same instrument as stale; instrument replacements never relabel old instrument prices. IMOEX index points and RUB-basis price returns are not USD ETF or total returns. Official attribution links to https://www.moex.com/ru/index/IMOEX.

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

US/global overview, details and rotation read this same snapshot. DSPX and COR1M
use Cboe's official historical CSVs, collected by `platform-data` with raw
response retention, canonical JSON and the existing DuckDB mirror. The API's
background refresh reads these local series into the US SQLite snapshot; page
requests never fetch Cboe. Macro market detail reads the same canonical series.
Prelaunch backtested history stays identified; failed refreshes preserve stale
values. A canonical retrieval older than one day is stale even if the API's
snapshot was just refreshed. The A-share CN10Y card reuses the existing official
China treasury series through the macro read API.

Commodity and crypto participation is calculated in the existing market-detail
background producer and persisted in the same SQLite snapshot. The fixed pools
are the eight continuous commodity futures (GC, SI, HG, PL, PA, CL, BZ, NG), and
BTC/ETH/SOL/BNB/XRP/DOGE/HYPE respectively. Only dates before the current source
calendar date (New York for commodity, UTC for crypto) are used. At the latest
available common observation date, members require at least 20/50/200 daily
observations; the numerator is close strictly above the corresponding SMA.
Different-date and insufficient-history members are excluded, with eligible
and expected counts exposed as `sampleSize`/`expectedSampleSize`. Incomplete
coverage is partial and zero eligible members is no_data. Commodity and crypto
market-detail pages omit the participation summary cards; the persisted fields
and market-detail tables remain unchanged. It is research-pool breadth, not whole-market
breadth; no daily delta is fabricated. US S&P 500 constituent breadth, A-share
constituent breadth and wealth-campaign fields remain unavailable until their
required sources and membership are verified. External research-link cards remain external links. No
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

### FedWatch probability semantics

`macro_fedwatch` uses the CME **Aggregated** view (`methodology=cme_aggregated_v1`),
not a compounded tree of conditional meeting outcomes. Full future months without
an FOMC meeting anchor the implied EFFR endpoints; consecutive meeting months are
resolved backwards. Meeting day belongs to the old rate and the following day to
the new rate. Each endpoint is compared with the first meeting month's implied
start rate on a 25 bp grid; actual EFFR determines the current target-range label.
Previous probability-weighted target midpoints must not become the next EFFR.
The calculation follows CME's [methodology](https://www.cmegroup.com/articles/2023/understanding-the-cme-group-fedwatch-tool-methodology.html)
and [Aggregated explanation](https://www.cmegroup.com/articles/2024/the-cme-fedwatch-tool-aggregated-enhancement-explained.html).

Probabilities have explicit unit `percent` (0–100), rounded to two decimals;
values below 1 are still percentages. The 13-month displayed horizon may use a
14th contract as an endpoint anchor. Unknown calendar months are not assumed to
be quiet; unresolved meetings are omitted, listed in `missingMeetings`, and mark
the refresh `partial`. Failed collection retains the prior valid snapshot.

`quoteAsOf` and per-contract `contractQuoteTimes` retain native quotation times,
separately from the collection-hour `observedAt`. Yahoo is a delayed quote fallback,
so this projection is not an official real-time CME probability feed. Normalized
calculation inputs are archived under `history/research/fedwatch/` in the configured
local-data root. The hourly refresh gate invalidates snapshots from older methods.

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
not create artificial breaks. The A-share overview navigator also preserves missing observations as gaps and becomes empty when all series are hidden. Each chart owns a separate SVG clipping region. It does not create an inner vertical scroll area.

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

A-share and Hong Kong stock-pool production are independent in-process tasks. The
A-share producer filters six-digit codes before requesting quotes/history, uses
the cached China exchange calendar after 15:10 Asia/Shanghai, and retains the
16:15 same-day complete-close gate. The HK producer filters five-digit codes, uses
its own HKEX calendar and 16:15 Asia/Hong_Kong close window, and makes no collection
on HK holidays. Its currently verified calendar covers 2026; unknown years remain
not due rather than assuming a trading session. Calendar authority:
https://www.hkex.com.hk/-/media/HKEX-Market/Services/Circulars-and-Notices/Participant-and-Members-Circulars/SEHK/2025/ce_SEHK_CT_075_2025.pdf .

Each market has a separate async lock, network collection batch, completion test,
retry loop and persisted run identity (`a-share-*` / `hk-share-*`). A slow, failed or
closed market cannot hold the other market's collection/publication or force its
completed run to retry. Only short SQLite publication transactions share the research
write lock; network requests are outside it. Per-market publication merges only
that market's stock rows and history, preserving the other market's rows and dates.
HK writes do not advance the A-share stock-pool observation/fetch/run metadata.

The combined stock-pool read model retains its existing table layout, with separate
`marketStatus.CN` / `marketStatus.HK` dates and status. The root metadata remains
A-share-owned. Read-time failure handling marks stale rows only for the failed
market. `/a-share/refresh-status` and `/hk-share/refresh-status` scope to their own
run identities; the corresponding POST refresh routes require `research.write`
and refresh only that market. HK status includes its own expected session in the
stock-pool calendar fields; holiday data retain their original quotation dates.

Observation dates come from source quotes/history, not the wall clock. Eastmoney
limit-pool dates use response `qdate`, including holiday responses returning the
preceding session. A-share close statistics require source quotes at/after 15:00;
HK complete-close quotes require at least 16:00 of the expected session. Same-day
high-turnover revisions replace prior qualifiers and record a valid zero-count
day. Cancellation/failure remains visible in the owning market's refresh status.


Eastmoney's A-share list, live sector-flow, four selected sector-board quotes and innovation-drug quote reads use the public delay-node pair, preferring `push2delay2` and failing over to `push2delay` on transport or payload failure without changing fields or units. A-share refresh status excludes `volatility-*` runs in the shared run table; cumulative-volatility status separately scopes to those runs. This prevents one module's five-minute producer from masking or delaying the daily A-share producer. The 2026-10-09 read-only initialization imported 8,738 `all_a` and 8,738 `sh_sz_a` dates, 6,005 CSI 300 closes, 6,485 `801102.SWI` closes, 25 valid BK0448 closes and 183 BK1106 observations from the verified same-host source. Each imported row retains its raw payload and source; rerunning the complete 30,174-row import skips identical natural keys and records value/quality conflicts without overwriting the accepted value. Full-A amount coverage begins 1990-12-19, advance/decline and limit-count coverage begins 2017-01-24, and `801102.SWI` coverage begins 1999-12-30; earlier unavailable fields remain NULL. Future updates and retained history are owned by this Platform API and its SQLite store. Market-width and limit-count comparisons require the same explicit universe before a difference is treated as an error.

The in-process A-share scheduler retries on its configured interval after partial results and catches unexpected cycle exceptions so one transient database/provider error cannot permanently terminate automatic refresh. External collection stays outside the shared research SQLite write lock; refresh-run, archive and publication writes use that lock so A-share production coordinates with the other research producers. The data audit registers all three archive tables and reports archive identities, invalid/missing prices and retained conflicts separately from short-window snapshot freshness. Cancellation is reserved for application shutdown; status and error details remain in the refresh-run record/log.

Market/index charts expose up to 2,000 stored observations, stock detail up to 300, and high-turnover history the last 90 observed dates with a 10-date comparison. “全部” means all returned stored observations. The chart controls change the displayed range and series; gaps stay gaps. Stock clicks open a read-only quote/day-history drawer, without invoking the separate broad one-click stock collection.

Financial metadata keeps source observation and Platform retrieval times distinct. Missing limit-pool counts, period returns and valuation fields remain null. The pool calculates 5/20-session returns from aligned adjusted closes, and YTD only when a prior year-end base exists. If new daily history fails, existing stored history keeps its original dates and retrieval time; the row is partial. Period returns are unavailable when its last close does not align with the quote date. Stale quotes do not enter current rankings or breadth. The market-width line is `(up − down) / (up + down + flat)`, unavailable for an empty denominator. Total all-A turnover comes from the complete quote snapshot, including stocks without an industry mapping.

Tracked HK quotes retain `currency=HKD`; their prices and amounts are displayed in HKD, never silently converted to CNY or summed into the CNY pool turnover summary. The quote DTO's historical `*_yuan` field names carry native currency specified by `currency`; all-A datasets remain CNY. Tencent HK amount fields are already currency units, while mainland quote amounts are in ten-thousands. Unknown HK turnover/valuation fields remain unavailable.

Live sector-flow and turnover responses keep their actual fetch time and show stale/error information on fallback. The UI polls only while visible. The sector table shows the supplied main-fund **net** flow; it does not present positive/negative parts of net flow as gross inflows/outflows. The daily >100亿元 statistic has its own observation date and is not labeled as the live ranking's current count.

## Public dashboard source extensions

Native dashboard time-series charts size their plotting area to the container without scaling down axis text. They preserve source dates, units, missing observations and exact source values in tooltips/tables; distinct units use separate axes. Range presets and the draggable time window change presentation only, and tables paginate the complete selected history rather than silently truncating it. Contract curves use actual contract-month spacing, with endpoint labels and complete point values in tooltips/tables. URPD and halving charts retain their dedicated source semantics while adapting their plotting width to the container.

Crypto `etfPremium` contains separate IBIT, BITB and HODL issuer disclosures, not a market aggregate. iShares' public chart is reconciled with its latest dated disclosure and retains issuer display precision. Bitwise's public product-page chart uses the premium block's own date (not the fund-details date) and reconciles the displayed percentage against its ratio field. VanEck's historical-prices workbook supplies the authoritative reported percentage; it is never recalculated from rounded NAV/market prices. HODL excludes prelisting rows and empty-volume calendar carry-forwards, but preserves numeric zero-volume dated records, without asserting a separately verified exchange calendar. Raw pages/workbooks retain original precision and date semantics; missing history is never interpolated.

WGC ingestion uses only public, non-login-restricted chart/report content. The public monthly ETF commentary chart supplies weekly/monthly USD flows for North America, Europe, Asia and Other; a labelled regional sum is null if any component is missing. Its weekly observations follow the public commentary chart's release, not a live weekly feed. Both weekly and monthly regional stacked-bar views overlay the shared `xauusd_daily_close` as a separate USD/oz price line with an independent axis and legend toggle; prices retain their native daily dates and never enter regional totals or stacks. Public country-reserves `snapshot` supplies only its latest quarter, with `AWAITED` preserved as null; country rows do not constitute a global total or synchronized central-bank reporting dates. The monthly central-bank report contributes only unambiguous, explicitly dated country purchases/sales in its prose (rounded tonnes, selected countries); YTD totals, reserve stocks, approximate amounts and unreported-purchase estimates are excluded. Gated XLSX downloads and historical reserve views remain outside coverage.

Crypto `optionExposure` contains source-backed Deribit BTC and IBIT option snapshots. Deribit uses public instrument metadata plus book-summary mark IV, forward price, expiry and OI; model gamma is `exp(-r*T)*phi(d1)/(F*sigma*sqrt(T))`, with `d1=(ln(F/K)+sigma^2*T/2)/(sigma*sqrt(T))` and ACT/365 time. Exposure is `gamma*OI*F^2*0.01` for a parallel 1% forward-curve move: OI is already in BTC and is not multiplied by contract size again. IBIT uses Cboe's publicly embedded delayed chain and published gamma, `gamma*OI*100*S^2*0.01`; adjusted roots, expired contracts and positive-OI/zero-IV records are excluded. Both retain positive call/put magnitudes; the UI's call-positive/put-negative net is a proxy, never dealer inventory. Coverage counts and included/total OI remain visible. Cboe's time-only quote stamp and missing OI date are not invented; underlying last-trade time is separate from collection time. Deribit stale threshold is 20 minutes and IBIT collection threshold 24 hours, independently of the existing four-times-daily producer schedule; these are collected snapshots, not streaming feeds. Original inputs and timestamped canonical snapshots remain archived, current snapshots are atomically published under `crypto/gex/`, and DuckDB `option_exposure_snapshots` mirrors the complete JSON with decimal strings. API timestamps are timezone-aware and numeric boundaries remain Decimal.

BTC DVOL daily history is produced by `platform-data` from official Deribit `get_volatility_index_data` with `resolution=1D`. Raw pages are retained, continuation cursors must advance, the fifth OHLC element is close, and only completed UTC days are published as `btc_dvol` in the Crypto `dvol` group. Source gaps remain absent/null; no interpolation or percent rescaling is applied. The older hourly endpoint retains its hourly contract, using close and complete pagination. URPD canonical series optionally carry `priceLower` / `priceUpper`; the API exposes these as decimal strings and the rebuildable DuckDB metadata mirror stores them as DECIMAL(38,12). All bucket boundaries are validated before series publication; the UI uses these numeric boundaries rather than parsing labels.

The independent producer's `refresh-research-extensions` command covers FRED GDPNow/SLOOS/Fed components/GVZ/NFCI, Cleveland Fed nowcasts, NY Fed SCE, Treasury auctions, SPDR, CME gold inventory, shared MT5 XAUUSD / Yahoo STRC daily prices, DefiLlama, Alternative.me, Deribit OI, BGeometrics URPD, public BTC/ETH treasury snapshots, GLD public borrow fees, FX-adjusted Coinbase/Binance premium and Bybit public VIP 0 USDT borrowing rates. Existing Binance production runs before the derived premium. Existing overseas ETF/IV and strategy-owned high-resolution collectors retain ownership.

Raw responses and exact derived inputs are retained under `raw/research/<source>/`; canonical history is under `public/v1/<domain>/series/`, with current cross-section membership under `crypto/collections/`. JSON publication uses atomic replacement. Each source fails independently, retains prior observations with `degraded`, `isStale` and `upstream_refresh_failed`, and makes the command exit nonzero; `public/v1/research-refresh.json` records the latest run. The existing task continues dashboard building and DuckDB synchronization even after a source command fails. Neither a recent file nor a successful mirror is proof that every source is fresh. The scheduled script also atomically updates `logs/refresh-latest.json` with start/completion times, each command exit code and duration: `running` has no completion time, `partial` means source failures with completed builds/mirror, and `failed` means a build or mirror command failed. Nonzero exit codes remain nonzero and independent commands continue. A completed partial run must still be inspected against `public/v1/research-refresh.json`; it is not an all-sources success. DuckDB uses column-batch inserts with the existing DECIMAL(38,12), NULL, primary-key and atomic replacement semantics.

Observation, report and collection times remain distinct. Forecast target month is retained separately from nowcast vintage; FRED GDPNow contains the latest estimate per quarter, not intra-quarter vintages. Treasury issuance is auction `total_accepted` grouped by issue month, including bill rollovers/SOMA; the current month is incomplete. SPDR holdings differences are tonnes, not dollar fund flows. The gold comparison price is labelled COMEX front-month futures, not spot or licensed LBMA fixing. CME inventory uses Activity Date and retains Report Date; pledged inventory is not added a second time. Sparse snapshot history starts with collection and is never backfilled synthetically.

BTC treasury snapshot dates are collection dates and do not claim uniform issuer reporting dates. ETH reserves include only source `ACTIVE` entities; public-report/self-reported/wallet-tracked classifications and source update dates remain visible. URPD buckets describe UTXOs' last-moved price, not verified investor acquisition cost. GLD borrow fees refer to one broker; Bybit rates refer to a public VIP tier and retain hourly units. Coinbase premium uses only matching closed UTC days and actual USDT/USD conversion: `100 * (Coinbase BTCUSD / (Binance BTCUSDT * Coinbase USDTUSD) - 1)`; it is not the branded CoinGlass index. Third-party sources carry attribution and do not grant redistribution rights beyond the local research use.

BGeometrics Bitcoin address distribution reads the dated public HTML report, validates all six original balance buckets and their current-count total, and stores only the current counts. Addresses are not people or entities; bucket boundaries and the source's unspecified date timezone are preserved. The report's historical-change columns are excluded because their totals were inconsistent in the verified sample. Collection is idempotent per source date and history starts at first collection.

Gold price comparison charts (`spdrFlow`, `chinaGoldEtfFlow`, `spdrHoldings`, `goldDrivers`, `goldRealYield`) share `xauusd_daily_close`. Runtime owns a bounded fixed-primary-account MT5 Worker read of native XAUUSD D1 bars, with position zero excluded; reads yield while the account Worker is busy or Live Write is enabled. The independent producer archives the original OHLC response, retains the daily close at its native bar-open UTC date, and publishes one canonical series. Initial/stale-history reads request at most 1,500 bars; subsequent updates re-read ten bars and merge exact dates, at most once per UTC day after a recent successful publication. Stale history permits retry/full-window recovery rather than locking in an incomplete terminal cache. Broker server and native symbol identity must match existing history before merging. Missing dates remain absent; no sampled Tick close, XAUT, futures splice or Yahoo GC=F fallback is used for these comparison charts. Retired GC=F archives are preserved but no longer refreshed or selected. The scheduled extension producer and DuckDB mirror own ongoing production; page reads never request MT5 history. Other intraday session calculations retain their separately documented source.

SHFE AU term structure uses official daily `SETTLEMENTPRICE` for each actual delivery contract, in CNY/gram and Asia/Shanghai trading dates. The exchange calendar selects the completed session (before 16:00 use the previous session); report date must match the requested date. Subtotals are excluded; missing/invalid settlements fail the source and preserve the last complete curve. Contract histories remain stored after expiry; `canonical/commodity/shfe_gold_curve.json` lists the current contract set only after all records are published. Dashboard construction rejects mixed-date snapshots. The chart spaces maturities by calendar month, never treats daily close or a continuous contract as settlement, and exposes the contract table. A session-date slider selects exact stored observations and changes the displayed delivery contracts and settlements together; missing sessions are not filled. The dashboard exposes retained delivery-contract history in `shfeGoldCurveHistory`, including expired contracts, while the latest curve remains governed by the active manifest. Historical contract age does not degrade current-feed freshness; history before first collection is unavailable. This does not claim global gold open interest coverage.

SHFE gold option volatility uses the official `o_cursigma` rows for `au_o`: `SIGMA * 100` is the published percentage, stored at native precision by underlying delivery month. It is not a separately calculated ATM IV. The active month manifest is `canonical/commodity/shfe_gold_iv.json`; expired months remain in historical series. Dates and response codes must match; missing, duplicate or invalid month values fail the source and preserve the previous complete curve.

Gold open interest is explicitly incomplete exchange coverage. CFTC PRE contract market `088691` provides weekly futures-only COMEX GC OI (100 troy ounces per contract); SHFE daily `au_f` OI sums actual delivery months and must reconcile to the official subtotal (1000 grams per contract). Both retain native contract counts and source dates. The UI switches between markets rather than adding differently sized contracts or displaying weekly counts as daily updates. Other exchange coverage and a global total remain unavailable.

Bitcoin halving comparisons use Blockchain.com `market-price` unsampled daily USD market averages. Incomplete current UTC dates are excluded; early zero quotes become null with a quality flag. The four verified halving UTC dates are 2012-11-28 (block 210000), 2016-07-09 (420000), 2020-05-11 (630000), 2024-04-20 (840000). Each cycle is `100 * daily_price / halving_day_daily_price`, ends before the next halving, and retains actual observation dates and missing gaps. The baseline is the UTC day's market average, not the event-time trade. Raw price history and all four derived histories are stored. `asOf` denotes the input price dataset cutoff for closed cycles; `observationDate` remains the last actual point in that cycle. The API preserves complete cycle histories rather than truncating old cycles to five years; the frontend only aligns elapsed days and draws the stored indices. No forecast cycle or forward fill is produced.

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

## Macro country suites and retained history

Rates, Economy, Inflation and Risk Appetite contain separate US and China groups. China tracks post-August-2019 LPR, unsecured Shibor O/N/1W/3M, ChinaBond 2Y/10Y/30Y government yields, cumulative GDP YoY, industrial output, retail, manufacturing/nonmanufacturing PMI, M2/M1 growth, social-financing stock growth and monthly new RMB loans. Inflation uses CPI/PPI YoY; risk appetite uses financing balance, margin-trading turnover share and SSE Composite 20-session annualized realized volatility. GDP retains its cumulative definition; M1 carries the 2025 statistical-definition break. Shibor is not DR007 and realized volatility is not implied volatility.

The existing platform-data scheduled producer collects paginated Eastmoney public histories and Jin10 Shibor histories; raw responses, native dates and units are retained. China liquidity also includes M2/M1 balances, foreign-exchange reserves and large/small-institution required-reserve adjustment events. Reserve-ratio events use their effective dates and step lines; the latest adjustment is not relabeled as a new daily observation.

The expanded economy suite covers cumulative fixed-asset/manufacturing/infrastructure/private investment, property development investment, sales area/value, starts, USD-denominated export/import growth, fiscal revenue/expenditure growth, industrial profits, urban unemployment by city/age. Inflation adds core/food/nonfood CPI and producer/consumer-goods PPI. Risk appetite also shows consumer confidence/expectations and CNH. Fiscal, investment and property cumulative growth is not monthly growth. Workforce indicators come directly from the NBS public monthly API; blank months remain absent. The reused youth indicator ID is filtered from December 2023 onward for the definition excluding students, without splicing the older population.

Where the verified public endpoints lack the required fields, Choice EDB supplements DR001/DR007, seven-day OMO rates, investment/property/fiscal/credit/price components, alongside CNH (`EMM00618963`) and social-financing stock YoY (`EMM00634721`). Indicator IDs, native units and frequencies are verified against provider search metadata. The core-CPI native index with previous-year same-month=100 is converted by subtracting 100 before display as percent growth. SDK queries stay within the account's three-year license window, retain history locally and cache successful series daily; newly added/failed series cannot force a same-day requery of healthy ones. Per-series no-data failures retain their own history with degraded status and leave other successful series published. Choice CNH is a separate source identity, selected for market detail when the public source lacks usable history; sources are not spliced. Page visits only read published artifacts.

Fed liabilities show currency, ON RRP, TGA and reserve balances; Fed assets show Treasury remaining maturities up to one year, 1–5, 5–10, over 10 years and MBS. Both charts use USD millions. ON RRP's native billions are multiplied by 1,000; the under-one-year Treasury series sums the three H.4.1 short buckets only on exact common observation dates. Native weekly/daily dates are not filled.

Canonical refreshes preserve earlier observations only when series, provider identity, unit, currency, frequency, timezone and methodology match; incoming data owns revisions and nulls within its returned window. Official Treasury histories are initialized from 2000, retaining the discontinued 30Y interval as null. ChinaBond initializes ten years. Yahoo explicitly requests daily granularity with timestamp bounds, rejecting silently downsampled responses. Native Binance funding history is archived from first availability and reduced using the existing daily-mean definition. Every local database sync publishes `history/coverage.json` with per-series dates, counts and state; raw archives and the DuckDB mirror remain persistent. Snapshot-only and source-limited histories remain visibly limited, without fabricated backfill.

## Macro probabilities

The “polymarket” navigation entry and panel initially show only the header, source state and controls. Event categories and cards are collapsed by default; the header's 展开/收起 button toggles them without changing collection, refresh or source freshness semantics.

The macro panel displays selected monetary-policy, macroeconomic, geopolitical and election event probabilities from a curated public prediction-market feed. The overseas worker refreshes the feed every five minutes into the local platform-data artifact; the browser never calls Polymarket. The feed retains at most 8,640 observations per event. Display titles preserve the specific market question and deadline; a verified Chinese translation is used when available, otherwise the original title is retained. History is positioned by observation time, with a single observation rendered only as a point and empty history left empty. One-day and seven-day probability-point changes require an observation at or before the comparison time, no more than one day earlier; larger gaps stay unavailable. Binary-contract, liquidity, volume and expiry gates intentionally omit ambiguous markets, and an unavailable upstream is shown as no-data/stale rather than a fabricated probability.

These probabilities are research observations, not forecasts owned by the platform and not trade signals.

## Safety boundary

Research market data must never be used as the authoritative quote, position, order, fill, risk or accounting input for live execution. Any future reuse in execution requires a separate contract, Issue, review and acceptance process.

### Market overview display (Owner confirmed 2026-09-08)

US overview cards are SPY, QQQ, IWM, DJI; theme cards are SOXX, GDX, XLV, XLF in that order. Newly substituted symbols without a quote show an unavailable value rather than the previous symbol’s sample quote. A-share overview and theme card clicks use the existing official TradingView advanced-chart embed with their exact index symbols; external symbol data availability is controlled by TradingView.

US and global rotation rows retain each instrument's source, observation date and stale/partial status from the same market-detail response as their returns. A response-level collection time does not replace the instrument's trading date; unavailable instruments retain empty returns and dates.

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

### Equity observation artifacts

Within the configured single API process, equity artifact reads and atomic replacements share a short I/O lock so Windows GET read handles cannot block publication. No upstream network operation holds this lock. Persistent I/O failures remain visible and retain the last successful artifact; the separate OS producer lock protects against overlapping producers.

`GET /api/v1/research/equity-observatory/{cn|us}` requires `research.read` and returns `Cache-Control: no-store`. It reads `HEDGE_BOARD_DATA_ROOT/public/v1/equity/{cn,us}.json`; GET never collects upstream data. The existing API research lifespan produces these read models every five minutes, with a process/file lock, six-hour successful source gate and one-hour failed-source retry gate. Raw public responses are retained by SHA256 under `raw/equity`; normalized sources retain observation and retrieval timestamps separately. Failed or regressed responses keep the previous successful source and mark it stale. Projection failure keeps the previous market artifact, recorded in `health.json`; readers mark failed or over-30-minute-old production stale. A-share expected close dates use the cached exchange calendar and the 16:15 publication boundary; unavailable calendars remain partial. US quote retrieval older than two hours is stale.

CN/US theme catalogs are separate representative watch baskets with supply-chain segments and explicit overlap, not complete investable indices. Catalog `equity-themes-2026-10-25-expanded` is effective from 2026-10-25; earlier returns use current membership retrospectively, not point-in-time constituents. Each theme deduplicates symbols across segments; overlap across themes remains explicit. Separate ETF references carry coverage descriptions and official product links and never enter stock medians or breadth. Core and satellite themes are distinguished; satellite baskets are excluded from the core strength overview. Style ETFs are exposed separately under `themes.styles`, never as thematic stock members. CN histories reuse the shared stock-history store and existing Tencent forward-adjusted daily collector; catalog symbols do not become personal stock-pool selections. US histories reuse the scheduled Yahoo market-detail snapshot. US stock-level industry/operating geography is unavailable and remains unclassified; the industry comparison uses 11 sector ETFs, not stock breadth.

The CN theme benchmark is CSI300 (000300); US uses closed SPY history. All 1/5/20-session returns require exact benchmark dates and n+1 positive closes, and 20-session moving-average participation requires all 20 closes. Missing sessions are not shortened or filled; source-provided unchanged closes remain unchanged. Same-date ready spot change may supply the daily observation when history is unavailable. Stale US rows are excluded from stock statistics. Relative 20-session return is each stock's return minus the benchmark return in percentage points. Theme/segment medians and participation use unique valid members, with coverage counts for each window; rankings require at least 3 valid members and 80% coverage. Median stock performance is not a portfolio return. CN/US theme strength views reuse these independent period coverage flags: daily ranks use medianReturn, 5/20-session ranks use return5/return20, and style-reference groups are excluded. The shared stock-pool-style matrix requires both valid daily and 20-session returns; missing values do not become zero. Frontend display converts percentage-point values to ratios once; rankings and matrix link to the existing theme detail. Matrix names are always visible in small labels with collision-aware placement; theme heatmaps are removed. ETF price performance is separate and not a dividend-reinvested total return. Member detail retains at most 65 source price observations.

Style comparisons contain 10 CN and 11 US ETF proxies, collected through the same catalog-driven Tencent and Yahoo jobs. Each proxy uses the same closed benchmark sessions and exact-window validation as themes; stale/missing endpoints produce null returns. CN dynamic quotes are not used as ETF history. Relative20 is ETF return minus market benchmark return; pair spread1/5/20 is numerator ETF return minus denominator ETF return in percentage points. Pair history is the price ratio normalized to 100 on the first of the last 125 benchmark sessions; gaps remain null and an absent initial ratio invalidates normalization. A rising ratio means numerator outperformance, not a buy signal. A-share growth/value instruments have different universes; 159967 combines growth and momentum, 512890 combines dividend and low volatility, and 560700 combines ownership and shareholder return. These are ETF proxy comparisons, not pure long-short factor returns or portfolio attribution. US price histories exclude distributions, so dividend ETF price returns are not total returns.

Transportation separates tanker, container and dry-bulk stock segments; CN also includes ports, airlines/airports and logistics, while US includes railroads, airlines and logistics. IYT and BOAT remain reference ETFs; BWET is explicitly a tanker-freight futures instrument, excluded from all equity-basket statistics. The expanded catalog uses VMRK after the AVB/EQR merger and excludes privatized EA; it does not splice predecessor prices into the new ticker. Official verification: [Vivmark merger closing](https://investors.avalonbay.com/sec-filings/all-sec-filings/content/0001104659-26-097833/tm2623381d1_8k.htm), [EA acquisition completion](https://www.ea.com/ea-studios/ea-sports/news/ea-announces-completion-of-acquisition), [BWET methodology](https://amplifyetfs.com/bwet/).

CN market/31-industry distributions exclude nonpositive PE/PB from positive-value medians; nonpositive observations are counted separately. Below-book share is `0 < PB < 1` divided by positive-PB coverage. Missing amounts remain null. Official CSI current constituents determine broad-index coverage; complete closed snapshots accumulate daily turnover/industry histories without reconstructing past membership from today's list. Crowding percentiles require 60 observations; valuation ranks use the preceding five calendar years and require 252 daily or 36 monthly observations. Ties use midrank. Price trends and US ETF ratios use matched closed-session dates; ETF ratios are price ratios, not total-return portfolios or full-market breadth.

CSI PE1/dividend1 files remain independent from the supplied HS300 Choice export. `scripts/import_equity_reference.py` archives that original without modifying it and imports only original price/valuation fields, recomputing rolling percentiles rather than importing full-sample ranks. No point-in-time financial revision claim is made. Multpl monthly S&P500 PE retains its estimated-value flag; updates within a month replace that month's estimate instead of increasing the rank sample count. The legacy valuation summary retains 120 monthly observations; the selectable chart uses the separately retained source history with a five-year default window. FRED supplies HY OAS and 10-year real yield. Unavailable PB or inadequate history stays null.

CSI historical-performance `peg` (rolling PE) is a separate source and separate table/chart series from PE1; their differing values must never be spliced into one percentile sample. Initial collection requests five years; later collections re-read seven days for revisions, retain source decimals and exclude the current session until 16:15 Shanghai time. A younger index may have less than five years of history; the actual rank count/window remains visible.

The index valuation projection additionally exposes `valuationCharts`: one selected instrument/metric with its own dated observations plus the same index price on a separate axis. CN instruments are CSI300 (000300), SSE50 (000016), ChiNext (399006) and STAR50 (000688). CSI historical rolling PE/close remain separate from Choice PE1. Choice CSD supplies three years of close, PETTM, PBMRQ, PSTTM, PCFTTM and DIVIDENDYIELDTTM in one isolated read-only SDK child, with explicit DelType=1 and FillData=0. Successful snapshots have a 20-hour gate; refreshes merge dated records, retain earlier history and raw hashed responses, and failures preserve previous observations with stale/error status. No credentials or forced login are introduced.

US chart instruments are S&P500 (^GSPC), Nasdaq100 (^NDX), Dow (^DJI), and Russell2000 (^RUT); Yahoo supplies ten-year daily prices. Multpl supplies S&P500 monthly PE/CAPE/dividend yield and quarterly PB/PS. Siblis public Nasdaq100 period-end observations and dated public Nasdaq100/Russell2000 valuation tables retain the provider's definitions and actual snapshot dates; negative aggregate earnings are not converted to positive PE. State Street **Index Characteristics**, not ETF Fund Characteristics, supplies SP500/Dow PE, forward FY1 PE and available PCF snapshots. Forward NTM and FY1 remain separately named; unavailable Nasdaq PB remains empty, and snapshots are not filled into daily history. These sources join the existing collector/archive/read-model path; GET still performs no upstream collection. HK HSIII (Hang Seng Internet & Information Technology Index) is a separate identity from HSTECH and preserves its available daily history.

Hong Kong's four monthly components are HKMA total M2 YoY, mainland PPI YoY, retail YoY and credit impulse. Credit impulse is the year-over-year percentage-point change in rolling-12-month new social financing divided by nominal trailing GDP; cumulative GDP is converted before division. Each component is standardized over at most 60 months with at least 36 observations, and exactly four same-month components contribute 25% each. Missing components never cause weight redistribution. February retail retains the combined January-February definition; revised historical inputs are not a point-in-time predictive backtest. Source dates and insufficient-history states are visible independently of the composite.

Monthly source age is measured from the observation month's end, including quarterly cumulative GDP; it is not measured from the month's first day. PBC current-year national monthly AFRE flow (CNY 100 million) overrides the same month's MOFCOM-republished historical observation in the credit calculation only; both original source artifacts remain separate. Official revisions are applied, not added to old values. The PBC collector follows the statistics-year and AFRE links to the national flow workbook and archives its discovery documents and row-level URL/hash. When direct retrieval is blocked, a verified public-table transcription may seed observations with its representation recorded; it does not clear automated failure/stale status. The 2026-10-16 seed covers January–September from PBC's 2026-10-14 table, including revised April 6238 versus the older republication's 6245. Raw transcriptions are explicitly identified as transcriptions, not original HTTP bodies.

### Gold research artifacts

Analyst method `independent_public_author_v2` retrieves the public Gold Eagle article body after verifying its dedicated byline field against the registered author; sidebar names do not establish authorship. Parsed source inputs are retained in SQLite and raw HTML/RSS is archived with a checksum. Verified article bodies are reused for 24 hours; a failed body refresh retains the prior body. Existing rows recover their inputs from checksum-verified archives and are reorganized without fabricated text. The Midas feed is now `https://floriangrummes.substack.com/feed`, linked by the official Midas homepage and verified by RSS creator; the former Midas WordPress feed remains an inactive historical source, preserving its last success/error without affecting current health.

Explicit bull/bear-market wording and secular horizons are recognized, including separate short- and long-term views for one asset. Negation is scoped to directional wording; questions and purely historical market descriptions are not current calls. Publicly inaccessible paid text remains metadata only. Readers serve persisted articles; neither a page visit nor an API search performs upstream collection or opinion extraction. Active source failures remain partial rather than being hidden by a successful alternative source.

`platform-data refresh-gold-research` runs in the existing four-times-daily local refresh schedule. Gold positioning and the retained daily report own their versioned JSON artifacts and DuckDB snapshots. Analyst collection independently reads 12 verified Gold Eagle author profiles plus the native The Daily Gold and Midas Touch author feeds; it does not consume GoldPulse processed analyst views. Content-addressed raw responses and URL provenance are archived under `raw/research/analyst_collection`. Persistent SQLite `research/analyst_views.sqlite3` owns authors, URL-deduplicated articles, content revisions and per-source attempt/success/error state. Subsequent refreshes accumulate history and preserve prior articles on source failure. `public/v1/commodity/analyst-views.json` is only a collection manifest; old third-party snapshots are historical records, not an API fallback. Platform API opens SQLite read-only and returns bounded SQL pagination (endpoint maximum 50), author, stance and escaped all-term search through `/research/commodity/analyst-views` under `research.read`. GET never fetches sources or organizes opinions.

Gold COT uses official CFTC contract `088691`, datasets `72hh-3qpy` (disaggregated futures), `kh3c-gbw2` (disaggregated combined), and `6dca-aqww` (legacy futures), retaining weekly observations from 2020. Counts remain integer contracts; weekly/4-week/13-week changes require the exact prior report date. Net-position share percentiles require complete 52/156-week windows. Options-equivalent managed-money net is combined minus futures only when report dates match; legacy noncommercial is not managed money. Report dates are observation dates, not claimed publication timestamps.

The gold driver panel uses futures-only COT. Managed long/short shares each include managed spreading in their numerator, divided by total OI; spreading is not directional net exposure. The interval comparison subtracts the selected actual reports, retaining signed changes and separating spreading from OI excluding spreading. Required missing fields remain unavailable. Gold spot uses its independent daily calendar.

`gold-factor-model.json` is an independent descriptive decomposition, not a replication of proprietary report parameters or a forecast. Rate sensitivity D is estimated as minus covariance of daily log gold returns and decimal changes in 10-year nominal yield less breakeven, divided by the latter's variance, over the first 252 common changes from 2020-12-03; later dates do not refit D. Nonpositive/invalid D fails explicitly. From the calibration endpoint, monetary baseline scales with US M2 (effective two calendar months after observation month) divided by assumed annual gold supply growth of 1.5%. TIPS/breakeven factor is exp(D*breakeven/100); nominal-yield factor is exp(-D*yield/100). Residual premium is observed gold divided by the other three factors; it is not identified inflation expectations. Their product equals observed gold. The reference-style contribution view uses four aligned panels (gold price, nominal-rate factor, residual premium, and all factor/gold changes). Changes are 100*(value/window-anchor-1), not additive log contributions. Factor curves use common valid observation dates without inserting nulls for absent same-day rate observations; no values are imputed. Gaps longer than seven calendar days retain a null break. The data table retains original missing rows. The level view uses six aligned area/line panels. Inputs are current-vintage, not point-in-time historical releases. M2 effective age beyond 75 days fails the build and retains the prior artifact as stale.

`gold-options.json` collects official CME Section64 monthly OG/SO chains, retains PDF/hash and daily snapshots, and reconciles strike volume/OI to published monthly totals before publishing. OG is 100 oz/contract; SO is 5,000 oz/contract and bulletin strike cents are converted to USD/oz. Intrinsic value is multiplier times the sum of call OI*max(S-K,0) and put OI*max(K-S,0); max pain retains all sampled minimizing strikes. IV here means intrinsic value, not implied volatility. Without a matching underlying futures settlement no premium/discount or delta-IV is emitted. EMA30 uses 2/31 and first-observation initialization, withheld until 30 observations; any missing weekday conservatively resets the window, including holidays without a verified calendar. Put/Call is the ratio of the two EMAs. No pre-collection history is invented. On 2026-10-25 direct collection timed out: the artifact is unavailable; parser tests are isolated and full live PDF parsing, historical options and settlement matching remain unverified. Public current reports alone do not establish historical-chain coverage.

GoldPulse remains the attributed source only for the retained daily report feed. The commodity page does not render the daily AI report; its archived feed and read-only API remain available with report generation time and the CFTC date used by that report. Official gold positioning is rendered in the existing CFTC commodity report gold tab; other commodity tabs retain their own series. Analyst tracking follows gold intraday cumulative volatility and mounts only after its default-collapsed section is expanded. Analyst organization conservatively tags assets, explicitly worded direction and horizon, with short attributed original evidence. Public excerpts and public bodies are distinguished; gated metadata has no inferred opinion. Targets, drivers and scenarios are not fabricated. This is deterministic evidence organization, not full translated research or model-generated analysis. The daily report is an excerpt with a full-source link, not a locally generated AI report or account-state assertion. No paid model or trading action is invoked. Analyst source failures preserve history and return partial status; a missing initial database remains unavailable. Gold report/positioning refresh failures retain prior snapshots. Reads older than 36 hours since successful retrieval are stale.


### Macro money, PMI and FOMC continuation (2026-10-22)

The liquidity `nyfedRepo` group additionally exposes `us_srf_usage`, the existing exact-date sum of FRED RPONTSYD/RPONAGYD/RPONMBSD restricted to 2021-07-29 onward, when SRF operations began. Amounts are all daily accepted overnight repo volume (including small-value exercises), not an outstanding balance or a facility rate; FRED billion-dollar inputs are multiplied by ten for 亿美元. Earlier temporary repo history remains independently named `nyfed_repo_total` and hidden by default. This is an SRF-era overnight-repo measure, not a separately classified operation-level series. Official zero use stays zero; a missing collateral observation is not filled.

`discountWindow` uses H.4.1/FRED WLCFLPCL, WLCFLSCL and WLCFLSECL for primary, secondary and seasonal credit, respectively. Native units are USD million, weekly Wednesday levels, not weekly averages. The total is an exact-date Decimal sum of all three non-null inputs; missing weeks are not filled, and BTFP/other emergency facilities are excluded. Source dates, raw CSV responses and source-series identifiers are retained through the existing extension collector and canonical artifact path. Weekly freshness allows 14 days, and failed source status propagates to derived totals. Both groups use the existing macro dashboard/API/chart flow; frontend visits do not collect upstream data.

Macro time-series controls default to five years and offer five-/ten-year windows. Dashboard projections retain at least ten years where canonical history exists; a window never fabricates earlier history. Commodity/crypto defaults remain separate.

`cnMoneyStock` reuses the canonical M2/M1 levels and published YoY, TSF stock YoY, plus native Eastmoney/PBOC `BASIC_CURRENCY_SEQUENTIAL` / `CURRENCY_SEQUENTIAL` percentage MoM. Levels use the left axis and percent rates the right; both MoM series start hidden. M1 January 2025 MoM is null across the definition break. `cnMoney` and `cnWorkHours` are retired groups. Work-hours collection is removed from NBS requests; the old canonical file is retained outside the serving tree under `history/retired-series`, and excluded from the rebuilt query mirror.

US ISM manufacturing/services PMI are monthly seasonally adjusted headline indexes, not forecasts. Jin10 actuals retain raw responses and map release dates to the previous survey month-end. Official ISM rolling reports supplement the archive when accessible. When public current observations are unavailable, the existing read-only Choice SDK fallback uses search-verified `EMG00002790` / `EMG00002791` within its three-year license window. Raw native dates and publish dates remain archived, public older history is retained, the resulting artifact is internal licensed research, and successful two-series requests are cached daily. Frontend visits do not fetch data.

The existing five-minute API worker independently produces `public/v1/macro/fomc-meetings.json`. Gamma FOMC series 35 discovers meetings without a permanent event slug; every binary Yes outcome is kept, including tiny probabilities omitted by generic market quality gates. Meeting identity is the source event ID; decision dates use New York dates of source expiry timestamps. Histories are fetched in bounded fourteen-day CLOB windows, persisted by outcome ID with collection watermarks, and subsequently refreshed incrementally. Source responses and request URLs are frozen under `raw/research/polymarket-fomc`. Closed meetings remain archived and are refreshed until resolution; the UI defaults to the nearest upcoming meeting. Missing histories remain empty and source failures retain prior observations with stale status. The existing expectations API carries typed `fomcMeetings`/`fomcStatus` in addition to the generic event feed. No probability normalization, guessed outcome or synthetic flat history is introduced.

FedWatch methodology is unchanged. A controlled input-precision check using the Owner's displayed October quote 96.1163 gives 89.46% hold; using an unrounded 96.11625 gives 89.48% and reproduces the corresponding screenshot rows. This explains how display rounding can generate small differences; it does not establish the unavailable raw CME quote. Live Yahoo delayed quotes may also differ by observation time. Quote prices are never fitted to expected probabilities.


### Gold and crypto chart/data refinement (2026-10-23)

Shared source-series time sliders filter observations before value-axis extents are computed. Multi-pane charts use the same actual date extent and synchronized zoom; short OI histories are not stretched across longer price histories. XAUUSD overlays share the existing MT5 daily series and use a black line. Flow sign colors do not alter values or units. BTC/ETH ETF charts default to the most recent 90 observations and show date, native flow and price on pointer movement; missing prices remain missing. Cumulative movement follows the corresponding IV chart, offers All instead of custom dates, and reads all retained observations for days=0. Session lines remain thin; price is a thicker black line.

Central-bank gold charts default to graphics: global quarterly official-sector demand comes from WGC supply-and-demand chart 43, while reported-country purchases and official reserves remain separate dated country distributions. The global quarterly series is not a sum of selectively reported country purchases. Country snapshot charts do not invent historical country observations. China ETF flow remains the verified WGC mainland monthly USD series: daily/weekly underlying fund disclosures exist, but an equivalent complete public mainland daily aggregate has not been verified. SPDR GLD资金流 remains native daily holdings change in tonnes, despite the shorter product title.

The existing platform-data extension job independently refreshes Deribit option distribution and DefiLlama stablecoin composition. Deribit retains instrument, expiry, strike, Call/Put, BTC OI and 24-hour volume; ITM/OTM uses the separately fetched current BTC USD index. Actual daily distribution snapshots and raw responses are archived. DefiLlama composition tracks the current largest eight USD-pegged assets using their native circulating USD-peg values; it is neither complete market coverage nor a historical membership index or depeg-adjusted valuation. Dates align before stacking, with unavailable observations null. Existing total market cap remains a separate series. Frontend reads these stored products, never initiates venue collection.

Market-detail production includes Sina AU0/AG0/LC0 continuous futures with native CNY units, additional listed securities, date-matched crypto/gold ratios, and Yahoo's verified numbered UNI/HYPE/PEPE/SUI identifiers. CoinGecko cap and dominance rows retain CoinGecko coverage and source dates, and are not relabeled as TradingView indexes. New cap histories accumulate from actual observations; unavailable earlier returns are null. MOVE is collected independently from Yahoo’s ICE BofA index distribution, retaining only completed New York dates; BCOM still has no verified connected source. An article URL returning Gold Eagle's Search page is retired as an unavailable individual article, while its historical metadata is retained; sidebar content is never assigned as the article body.

BTC treasury weekly flow is captured through the visible SoSoValue frontend, without calling its APIs, intercepting requests or reading chart/application internal state. The Codex heartbeat “BTC财库周度前端采集” runs Tuesday 00:00 local time and requires the desktop/Chrome environment to be available. It reuses the page session when needed; login/CAPTCHA/error/blank pages never replace valid evidence. The Tuesday task now captures structured tooltip data only, without creating or publishing new images; existing image evidence is retained.

The browser reads visible tooltip text for new weeks and rechecks the recent week. `platform-data import-treasury-weekly-ui --capture <JSON> --image <image>` validates the source URL, timezone-aware capture time, week date, amounts, BTC quantity/price, distinct company names, displayed-company sum within the source rounding tolerance, and, when an image is supplied, crop dimensions. Historical tooltip-only captures omit `--image`, retain their own text/time/hash, do not claim a per-point screenshot, and never replace the published chart image. The literal source BTC quantity `null` is stored as SQL/JSON NULL and shown as a dash. K/M/B displays are stored with their original text and a separate precision; displayed 359.64M therefore has USD10,000 display precision and is not an exact-to-cent observation. Week dates are source labels, not a claim that the period is closed. Missing/hidden values are not zero and are never inferred from bar height.

Immutable captured text and cropped images, SHA256 and timestamps are retained under `research/treasury-weekly-snapshots/<collection-day>/`. `public/v1/crypto/treasury-weekly-history.json` retains all captured revisions and the latest valid record per week; replay is idempotent and older imports cannot regress the latest publication. The existing DuckDB sync mirrors `treasury_weekly_captures` and `treasury_weekly_companies` with Decimal columns plus original precision/provenance. The manifest and fixed image endpoint retain the prior successful image on invalid imports and serve its actual PNG/JPEG media type. The read-only /crypto/treasury-weekly-history API reads the fixed structured history independently of image manifests. The card renders company-stacked USD bars, BTC quantity and BTC price on separate axes (BTC price on the left; USD flow and BTC quantity on the right), with source-precision tooltips, legend toggles for BTC quantity/price and Strategy only (green Strategy bars; all other companies remain in the stack and tooltip), date presets/inputs, a draggable zoom window and a totals/company table. Missing BTC quantities remain gaps. Price axes scale to the visible zoom window. No SoSoValue request or snapshot image is needed for page rendering. On 2026-10-25 the complete currently displayed chart history was read through frontend tooltips: 93 consecutive source weeks from 2025-01-13 to 2026-10-19, 316 company-week rows and 29 distinct company names. All company sums pass source display-rounding tolerance; the source BTC quantity for 2026-05-04 remains NULL. Historical tooltip captures retain raw text without fabricated per-point images; the final latest-week chart has a verified 1584×1124 crop. Future unattended weekly accumulation still requires live operation.


### Crypto funding: offshore renminbi and OKX USDT/CNY (2026-10-25)

The `cnyUsdt` group reuses the macro `cn_usdcnh_choice` series (USD/CNH, offshore RMB per USD) without copying its canonical price store. The crypto producer adds `okx_usdt_cny_buy` and `okx_usdt_cny_sell` from OKX's public `/v3/c2c/tradingOrders/books` USDT/CNY advertisements. Names use the dashboard user's perspective: advertiser `sell` is user buy, advertiser `buy` is user sell. For a fixed CNY10,000 notional across all payment methods, validate currency, positive finite price, per-order limits and available quantity, exclude blacklisted/own/intention ads, deduplicate ad IDs, then take the median of the five cheapest asks or five highest bids. Fewer than five eligible ads is unavailable; rates are advertised, not executed or guaranteed executable for a particular account.

The existing `refresh-research-extensions` job collects both sides during the existing four daily local refresh runs. Raw response bodies and acquisition URL/time are retained in `raw/research/okx_usdt_cny_{buy,sell}`. Canonical dates are Shanghai collection dates, with one latest collected observation per date; each refresh retains earlier dates, and every raw intraday response remains archived. No pre-connection P2P history is fabricated. One side may fail independently: preserve its last successful observations and retrieval timestamp with degraded status; first-time failure has no observations. GET performs no upstream call. Dashboard publication and the existing DuckDB sync include both series. API additionally marks OKX quotes stale after 12 hours without successful retrieval; weekend USD/CNH retains its native business-day date and existing freshness rule. The chart defaults to three months, uses one comparable quoted-RMB axis with distinct USD/CNH and USDT/CNY labels, supports dates/range, legend toggles and table view, and never fills missing historical P2P quotes or weekend FX values.


### Macro funding, FX and activity expansion (2026-10-25)

The existing independent producer refreshes the new datasets through `refresh-research-extensions`, then builds `macro/dashboard.json` and the existing DuckDB mirror. Each FRED CSV and Philadelphia Fed workbook is archived before parsing; no browser page triggers upstream collection. Treasury refresh now includes 5Y alongside 2Y/10Y/30Y, with 3M retained from DGS3MO; 5Y history was backfilled from verified official annual CSV archives to 2000. All five yields are annualized percentages, not bond prices. Term spreads are 10Y−3M, 10Y−2Y and 30Y−5Y in bp, computed only on common source dates.

NY Fed overnight repo accepted volume sums `RPONTSYD`, `RPONAGYD` and `RPONMBSD` (Treasury, agency debt and agency MBS). Only dates with all three reported amounts are used, including genuine reported zeros. Billions of dollars are multiplied by 10 for the chart's USD100million unit. This excludes term repos and is accepted operation volume, not outstanding balances, ON RRP, or total Fed assets.

SOFR−EFFR and SOFR−IORB use exact-date intersections and `(left−right)×100` bp. IORB superseded IOER in July 2021; the current series is explicitly labeled IORB, without relabeling older IOER observations. The Owner confirmed that the requested 3M/6M SOFR−OIS means corresponding-tenor Term SOFR minus federal-funds OIS. Those curves, USD/JPY and EUR/USD cross-currency basis, and FX swap points do not yet have verified market feeds. Their cards explicitly show missing quotes; no zero series, covered-interest-parity model, backward SOFR average or unrelated futures price is substituted. No synthetic history is published for these missing feeds. Basis measures an extra funding premium relative to cash funding, not the complete USD funding interest rate.

DXY and USD/CNH reuse the existing Yahoo data. Main bilateral rates use Fed H.10/FRED DEXUSEU, DEXJPUS, DEXUSUK, DEXUSAL, DEXSZUS, DEXCAUS and DEXCHUS with original quotation direction. H.10 publishes daily observations for the previous business week on Mondays; `daily_weekly_release` has a 14-day freshness tolerance in producer and API and is displayed as daily observations with weekly publication. Chart-only grouping uses a common USD-per-unit-base-currency axis for EUR/USD, GBP/USD and AUD/USD, and a common RMB/USD axis for CNY/CNH; stored native units are preserved.

European yields currently use public OECD/FRED monthly 10Y benchmark series IRLTLT01FRM156N, IRLTLT01DEM156N and IRLTLT01ITM156N. France−Germany and Italy−Germany spreads retain monthly frequency and require identical observation months. They do not represent daily crisis pricing. Choice EDB discovery found daily candidate IDs, but actual read-only queries returned `10001029 data limit exceeded`; no new failing SDK job or automatic quota-consuming retry was installed.

VXEEM uses Cboe's official daily history CSV; MOVE reuses the existing completed-day ICE/Yahoo series. PCEC96 is monthly real PCE at a seasonally adjusted annual rate. Real core retail is a clearly labeled derived CPI-deflated control measure: seasonally adjusted total retail/food services MRTSSM44X72USS minus motor vehicles MRTSSM441USS, gasoline MRTSSM447USS, building materials MRTSSM444USS and food services MRTSSM722USS, divided by CPIAUCSL and multiplied by 100 (1982–84 CPI base). It is not the BEA chain-weighted consumption series. Monthly growth requires consecutive calendar months. Nonfarm additions are first differences of seasonally adjusted PAYEMS (thousands); ADP additions are first differences of ADPMNUSNERSA (persons) divided by 1000. The BLS total and ADP private-sector populations remain distinct. UNRATE reuses existing unemployment data.

Corporate profit expectations use the Philadelphia Fed SPF median CPROF2 (current survey quarter) and CPROF6 (four quarters ahead), seasonally adjusted annual-rate USD billions. Only 2006 onward is included, maintaining the definition that includes IVA/CCAdj. Observation dates denote survey quarters, not release timestamps or forecast realization dates; this is a macro corporate-profit forecast, not S&P 500 analyst-consensus EPS. China retail adds the native RETAIL_TOTAL amount to the existing report and retains the existing YoY series. February reports cover January–February jointly; no January value or separate February monthly value is fabricated.

GVLQUSD (Bloomberg US Government Securities Liquidity Index) is reserved for the exact Bloomberg measure, described by UBS as the equally weighted average yield error for US Treasury notes/bonds with at least one year remaining maturity. Higher values indicate worse liquidity. The US rates section ends with its definition and verified UBS/ECB/Bloomberg Data License reference links. As of 2026-10-25 no usable canonical history is connected: Bloomberg public quote page reports no security page, Choice EDB searches yielded no matching measure, and the UBS Q3 2024 report links a dated public chart whose CSV was access-denied. No values, units conversion, current reading or history are fabricated; no MOVE/funding-rate/net-liquidity proxy is labeled GVLQUSD. The card explicitly reports history unconnected and issues no upstream data call. Licensed historical data would require a verified source/entitlement before ingestion.


### Macro narrative observation (2026-10-25)

`GET /api/v1/research/macro/narratives` is a research.read-protected, read-only projection of existing canonical macro/commodity histories and closed market-detail snapshots. No collector, duplicate price store, external request or write is triggered by this endpoint. Existing source refreshes automatically flow into the projection. Method version: `macro-narrative-proxies-v1`.

Nineteen explicitly named market proxies cover US duration/front-end/curve/real yields, breakeven inflation, broad USD, yen/AUD/CNY FX, HY OAS, VIX+MOVE, SOFR-EFFR, China duration, MT5 XAUUSD, SPY, QQQ vs XLI, XLE, XLI and BTC/USD. Names describe observable proxies: XLE is energy equities, not global oil; BTC returns are risk pricing, not measured crypto liquidity. Current theme histories are not news sentiment, position data, inferred crowding, or causal proof. Missing original-reference coefficients are not reconstructed from screenshot positions.

For each leg, a 21-observation window produces a 20-period price ratio change or rate/spread level difference. Z uses the preceding up to252 changes, minimum126, excluding the current change from its baseline. Nonpositive prices, nonfinite values and zero baseline variance are unavailable. A gap longer than14 calendar days resets warmup; ordinary extended exchange holidays do not reset the baseline. Financial input arithmetic retains Decimal; dimensionless scores use floating-point statistics. Multi-leg composites average signed leg z-scores on exact common dates; a missing leg never changes weights. Momentum equals current composite score minus five common observations earlier, only if within14 calendar days. Output retains at most5 years of actually computable history. The chart breaks gaps longer than7 days; no missing segment is connected.

The map uses strength (x) and five-period score change (y), with small persistent theme names. It intentionally does not label x as consensus/crowding. Historical map selection uses only observations <=selected date and within14 days, showing each actual date. This is a dated snapshot lookup, not an undisclosed filled time series. Axes adapt to selected points; series colors stay consistent across map, table and trajectory. The trajectory defaults to5 years with90-day/1/3/5-year controls and zoom. Source definition, direction, source date, status and upstream link remain inspectable for every theme, including those excluded from the current map.

Macro state is a separate latest-evidence panel for US/China growth, inflation, policy, liquidity, fiscal and risk-premium dimensions. It compares each series' last observation in each month, recent3-month mean against previous3-month mean, requiring6 consecutive months. The current month may be incomplete. A growth/inflation quadrant is a descriptive PMI/CPI heuristic, not a regime probability or trade recommendation; the9 narrative lenses remain explanatory definitions, and unsupported fiscal/productivity/crowding inferences are not made. Latest macro evidence does not rewind with the market map. Canonical histories may be revised and may use reference-period rather than publication dates: this view cannot establish point-in-time backtest performance. US fiscal impulse and China risk-premium evidence remain explicitly unavailable, rather than substituting issuance volume or equity volatility for those constructs.

User-supplied reference screenshots are preserved unchanged in public/images/gold-references. Five option snapshots are shown in the option panel; three COT and two factor snapshots are expandable beside their corresponding features. Each names the specific unimplemented part, marks it 未落地, and states it is a reference snapshot rather than current market data. Clicking opens the complete original image. Cycle boundaries, source-specific calibration, trend lines and threshold annotations are not inferred from screenshots.


### JP10Y and US credit OAS in FX (2026-10-26)

The FX/overseas-spread page reads `jpTreasury` (`jp_treasury_10y`), `riskInvestmentGradeOas` (`us_ig_oas`) and existing `riskHighYieldOas` (`us_hy_oas`) groups from the same macro dashboard contract. JP10Y is the Japan Ministry of Finance official constant-maturity 10Y reference yield in percent, Asia/Tokyo daily observations; it is not asserted to equal an intraday TradingView quote. The CSV 10Y header is selected by name, missing cells remain absent, negative/zero yields remain valid. MOF historical and current-month raw CSVs and retrieval metadata are archived. Bootstrap and month rollover read the historical CSV; other runs read the full current-month CSV. Returned windows own their revisions and same-source older history is retained. Invalid/nonfinite/empty source responses do not replace the prior canonical file.

IG OAS maps only to FRED `BAMLC0A0CM`, HY OAS only to `BAMLH0A0HYM2`; these are option-adjusted spreads, not effective yields or unadjusted corporate-minus-Treasury spreads. Both retain percent units (1%=100bp). ICE series use internal-use-only metadata, and local observations preceding FRED's rolling three-year public window are preserved. IG is collected in the existing research-extension refresh; HY reuses the existing FRED-core collection. JP10Y is another independently failure-handled job in that same existing extension refresh. No new scheduler or duplicate HY collector is introduced. Canonical JSON feeds the existing dashboard builder, DuckDB mirror and read-only API. All three cards have source links and default to1 year; older available history remains selectable.
