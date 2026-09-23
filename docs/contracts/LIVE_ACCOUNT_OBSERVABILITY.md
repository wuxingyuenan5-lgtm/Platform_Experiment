# Live Account Observability Contract

This contract is maintained under the repository contract index.

Status: `active read-only contract`
Scope: Bybit UTA + MT5 account used by the cross-spread strategy  

## 1. Purpose

The final Windows-host acceptance must be an environment integration exercise, not a product-design session. Before any separately owner-authorized, instruction-bounded real-money write, the Platform must already expose enough read-only evidence to answer:

- Which active and historical Orders exist on each venue?
- Which Fill or Deal produced each position?
- Which identifiers are Order, Deal and Position tickets?
- What is the current account equity, available margin and used margin?
- What liquidation or Stop Out evidence is authoritative?
- Is an empty result a healthy zero, or did the read fail?

This contract adds observability only. It does not authorize Live Write, automatic TP/SL monitoring, limit execution or any execution quantity.

## 2. Runtime read-only endpoints

| Endpoint | Purpose | Write effect |
|---|---|---|
| `GET /venue/orders` | Bounded current and recent Order list | None |
| `GET /venue/order-history` | Explicit active/closed Order page | None |
| `GET /venue/fills` | Targeted Fill/Deal lookup | None |
| `GET /venue/fill-history` | Explicit Fill/Deal history page | None |
| `GET /venue/positions` | Current position and risk fields | None |
| `GET /venue/balances` | Currency balance snapshots | None |
| `GET /venue/account-risk` | Account-level margin and Stop Out evidence | None |
| `GET /venue/instruments/{symbol}` | Current size, step, contract and access evidence | None |

Platform aggregate:

```http
GET /api/v1/trading/cross-spread/observability?historyHours=24&limit=20
```

The Platform API also records a low-frequency Cross market snapshot independently
of browser page visits. The default interval is 60 seconds and the persisted
snapshot includes both executable long/short spread, funding-rate input and the
buyer/seller inventory-fee inputs. This is a monitoring/read-model series, not a
settled accounting fact. Actual funding, swap and fee cash events remain in the
economic-event/financial-fact import path and must not be inferred from a quote
snapshot.

The aggregate reads the configured Bybit and MT5 accounts independently. A failed section is marked `unavailable`; it is never converted into a healthy empty list or zero balance.

## 3. History query rules

### 3.1 Bounded windows

- Every Order/Fill history query has `startTime`, `endTime`, `limit` and optional `cursor`.
- The Runtime rejects windows longer than seven days.
- A caller that needs older evidence advances through explicit non-overlapping windows.
- Page size is bounded to 100 records.
- No endpoint performs an unbounded full-account history scan.

### 3.2 Bybit continuation

Bybit uses the venue `nextPageCursor`. Closed Order history uses the venue history endpoint rather than treating the realtime recent-order cache as permanent history.

### 3.3 MT5 continuation

MT5 Python history functions return a bounded time range rather than a venue cursor. Runtime sorts by time and ticket, then exposes a deterministic integer-offset continuation inside that fixed window. A continuation token is invalid outside the same account, symbol and time-window request.

Internal Terminal reads may extend the query boundary only by a bounded clock-tolerance margin because some brokers expose server-local epochs ahead of UTC. Deal occurrence timestamps retain the stable venue epoch; they must never be replaced with the current read time. Order/position/account `asOf` records observation time separately. A broker timezone cannot be inferred from a read-time offset; preserving the source epoch does not establish corrected wall-clock history. The tolerance must not silently expand the user-visible economic lookback.

MT5 executable quote freshness is independently tracked by account, resolved symbol and actual login/server identity. The first positive native tick timestamp establishes a baseline; only a later strictly increasing `time_msc` proves an update. `lastTickAdvanceObservedAt` records when that advancement was observed, while `sourceAsOf` retains the native epoch unchanged. Execution requires both the observation and last advancement to be within 30 seconds. Equal/stagnant ticks do not refresh this evidence; timestamp rollback, disconnect or identity loss/change requires a new baseline and advancement. This does not infer broker timezone or rewrite historical timestamps.

Management order/fill displays separately expose clock provenance and an optional cumulative order confirmation time; their fields and evidence rules are owned by [API.md](API.md). A source timestamp after a complete confirmation is a clock conflict, not a future trade. Displaying the labelled confirmation does not normalize the broker timezone or change the economic ledger chronology. Unconfirmed MT5 source clocks remain available in details and are excluded from confirmed-date filtering.

## 4. Order and execution identity

| Venue | Order identity | Execution identity | Position identity |
|---|---|---|---|
| Bybit | `orderId` | `execId` | account + symbol + `positionIdx` |
| MT5 | Order Ticket | Deal Ticket | Position Ticket |

Rules:

- `externalOrderId` always means Order identity.
- `externalFillId` always means Bybit Execution or MT5 Deal identity.
- `externalPositionId` always means current venue position identity.
- A route-independent external record uses `dataQualityState=external_only` until mapped to a Platform Order/Command.
- ACK is never interpreted as Fill.
- Missing local route state does not make a real external Order disappear.

## 5. Order diagnostics

When supplied by the venue, Order snapshots include:

- requested, filled and remaining quantity;
- average fill price;
- external client ID;
- `reduceOnly`;
- Bybit `positionIdx` or MT5 Position Ticket target;
- time in force;
- rejection and cancellation reason;
- data-quality state and authoritative timestamp.

Unavailable fields remain `null`. They are not inferred from another Order or from a local UI state.

## 6. Position and liquidation semantics

### 6.1 Bybit

Bybit position snapshots may include venue-reported:

- mark price;
- break-even price;
- liquidation price;
- leverage and position value;
- initial and maintenance margin;
- unrealized and realized PnL;
- TP/SL;
- position status, risk limit, auto-add-margin and reduce-only restriction.

`liquidationPriceSource=venue_reported` only when Bybit returns a positive finite `liqPrice`.

An empty or non-finite Bybit `liqPrice` is represented as:

```text
liquidationPrice = null
liquidationPriceSource = venue_not_finite
```

This does not mean the position has no risk. It means the current account/margin mode did not return one finite position-level value.

### 6.2 MT5

The MT5 Python Position API does not provide one authoritative per-position liquidation price. Runtime therefore uses:

```text
liquidationPrice = null
liquidationPriceSource = not_available_mt5_api
```

No local approximation is permitted in the canonical response.

MT5 liquidation risk is monitored at account level through:

- Equity;
- used and free Margin;
- Margin Level;
- `margin_so_call`;
- `margin_so_so`;
- `margin_so_mode`;
- account and Terminal trading permissions.

The UI must display “MT5 API 不提供单仓强平价” and show Margin Call / Stop Out values beside it.

## 7. Account-risk semantics

### 7.1 Bybit UTA

The account-risk snapshot uses venue-reported account aggregates where available:

- total equity;
- total wallet and margin balance;
- total available balance;
- total initial and maintenance margin;
- account IM/MM rate;
- total perpetual unrealized PnL;
- margin mode.

Bybit account-risk values are not mixed with MT5 currency values or converted inside the Runtime.

UTA aggregate monetary values use **USD**, including equity, wallet/margin balance and available margin. Individual coin wallet/equity values retain their native currency (for example USDT); USD margin is not USDT cash. Spot available balance is nullable and conservatively bounded by unborrowed native cash and the reported margin valuation. Missing locked, order/position margin, borrow or valuation inputs produce unknown availability, never a synthetic zero or an unlimited balance.

The frontend labels these USD aggregates as converted valuation (折合 USD), never as a native USD balance. Actual USD, USDT and USDC cash rows remain separate.

All-account asset overview is a separate, optional USD valuation with `totalAssets`, `assetBreakdown`, `assetOverviewAsOf` and `assetOverviewQuality`. It can contain UTA crypto/stocks/RWA, Earn, Funding, Alpha, TradFi and other venue categories. It never overwrites trading-account risk or supplies order margin. Its total already includes the reported categories; MT5/TradFi must not be added to it again. Failure of this optional overview does not discard a valid UTA snapshot.

### 7.2 MT5

The account-risk snapshot uses `account_info()` and `terminal_info()`:

- Balance and Equity;
- Profit;
- used/free Margin;
- Margin Level;
- Margin Call and Stop Out threshold;
- threshold mode;
- leverage and margin mode;
- account/Terminal Algo Trading permission.

`margin_so_mode=0` means the thresholds are percentages. `margin_so_mode=1` means money values. The UI must preserve this distinction.

Cash, realized profit and account margin use the currency returned by `account_info()`. A USD quote or an XAUUSD instrument name does not establish USD settlement. Strategy unrealized profit can use a venue position's reported profit only with matching Ticket and quantity; a different quote/settlement currency without authoritative conversion leaves the calculated value unknown.

## 8. Data-quality states

| State | Meaning |
|---|---|
| `complete` | The section read succeeded and an empty list is a valid zero result |
| `external_only` | Venue record exists but has no authoritative Platform route mapping |
| `venue_windowed` | Result is complete only for the declared venue time window/page |
| `partial` | Aggregate has both successful and failed sections |
| `unavailable` | The section could not be read; zero/empty must not be inferred |

The aggregate returns per-section states for account risk, positions, active Orders, recent Orders and recent Fills.

Platform persists the last successful account frame atomically with its synchronization status. A running or failed refresh retains that frame with the last successful time and a stale/error indication. Frames older than 90 seconds are stale. Missing sections, wrong account identity, non-finite financial values, future observation timestamps or backwards frames fail validation before replacing current positions. Historical occurrence timestamps retain their source-clock semantics. MT5 `None` results mean query failure, not a flat account. Read transport may recover once on a known IPC error only after reinitializing the account's fixed terminal and proving identity; order writes are never replayed by that recovery.

The account-sync monitor starts with the application and reads current balances, positions and risk on its bounded 30-second cadence using Runtime `includeHistory=false`. It preserves previously stored historical evidence and records current-observation failures per account. Bybit current-only reads bypass the history snapshot lock; historical snapshot fan-out remains serialized. MT5 retains its fixed-account worker and SDK identity boundaries. Bybit signing timestamps use the latest local sample from a server-time read and refresh the verified offset periodically, with a conservative behind-server bias for asymmetric network paths. A failed refresh never replaces a good frame or authorizes a write.

Historical reads and financial projections have a separate application-owned loop: successful accounts refresh every five minutes, failures retry after 30 seconds. Complete history uses a persisted watermark with ten minutes of overlap; a daily full bounded audit and explicit full refresh remain available for late records. Bybit executions and transaction events use the incremental window; order-status history retains the seven-day created-time window so recently closed older orders are not lost. MT5 retains its configured padded query window and uses actual historical read time minus the existing one-day padding and overlap, never the future padded `historyEnd`, as its incremental start. Source epochs are not reinterpreted as Beijing time. Windows and raw native identities survive process restart; only contiguous complete intervals extend coverage. Native events remain persisted independently of the rolling snapshot.

Slow historical responses update only historical sections and cannot replace newer balances, risk, positions or observation time. Settlement/capital-history processing failures cannot turn a successfully persisted current frame into `runtime_unavailable`. Management responses expose `financialSyncStatus`, `financialSyncErrorCode` and `lastSuccessfulFinancialSyncAt` separately from `syncStatus`. The PnL/order area warns when historical or financial processing fails and retains previous results; the account connection warning is reserved for current observation failure/staleness. A missing or unrequested history section is never interpreted as zero fees. `/health/monitors` exposes the history loop separately as `accountHistory`.

Bybit recent history covers an explicit seven-day UTC interval and follows every cursor within a bounded page count. Repeated cursors or an exhausted bound fail instead of silently truncating. Responses state history coverage and actual record totals; the management snapshot includes at most 200 recent Orders/Fills and 1000 comparable account-equity points. Venue financial events are retained across refresh windows by account, source, event type and stable external identity.

### 8.1 Strategy-management projections

- Strategy Order and Fill history is attributed through `StrategyInstruction` / `ExecutionBatch` / `TradeCommand` identities, never by account display name or account-plus-symbol filtering. This is required when strategies share one UTA.
- Platform monitoring resolves legacy order aliases by the exact `(account_id, instrument_id, external_order_id)` tuple. Instrument identity includes the market category; symbol or timestamp similarity is insufficient. A unique command-owned order wins over its monitoring aliases. Multiple command owners remain an identity conflict. Original IDs, rows and native payloads are retained.
- Order-linked settlements follow the same owner even if an older shared-account projection assigned them elsewhere. The strategy settlement table contains only owned events; unassigned funding/swap stays pending and is not counted in Funding merely because that strategy shares the account.
- A strategy being the only recorded historical trader of an instrument does not establish settlement ownership. Without resolved order identity or formal financial-fact attribution, a funding/swap receipt remains account-scoped; overlapping strategy exposure is marked pending, and a receipt outside that exposure is not assigned to the strategy. Manual or incomplete external history must not be silently attributed.
- Bybit Funding settlement ownership can also be established by the native flat-to-settlement execution interval under [Financial Facts](FINANCIAL_FACTS.md). The strategy read model displays its formal instruction/batch attribution; other strategies' assigned events and unrelated symbols or periods without strategy exposure do not invalidate that strategy's settlement total. Missing FX invalidates affected components and net PnL, while independently confirmed base-currency funding remains visible.
- Monitoring does not require every historical symbol to have a trading instrument specification. Such Orders/Fills remain readable with their native receipts; unavailable multiplier or opening basis marks the calculation incomplete instead of failing the account snapshot. A read-model failure is a data-loading error, not proof that configured credentials are disconnected.
- Account snapshots retain native executions and fees, but cannot advance a command-owned order's status, append its execution quantities, or resolve `result_unknown`. Those transitions remain with the execution/reconciliation path and its cumulative-fill ceiling. Monitor-only fill IDs are scoped by account, source and native fill identity; raw tickets remain available separately.
- New operational fills explicitly record `runtime_confirmation` or `venue_execution`, their source and any native fill ID. Each row is an increment within its source representation. Known mixed representations or quantities exceeding a business order's ceiling fail closed. Unclassified historical rows retain the old bounded projection and expose `legacy_fill_provenance_pending`; migration does not infer provenance from a quantity equal to the order size.
- Management uses native executions when their coverage includes the operational confirmation, replacing rather than adding to that confirmation. A native quantity beyond the order size remains visible with `venue_fill_quantity_exceeds_order`; it cannot increase executable quantities. Incomplete native coverage stays pending. Monitor-only orders synthesized from a first fill do not impose that fill's size as an artificial financial ceiling. Stored multipliers and native settlement rules still apply.
- The management fill list, account snapshot and strategy financials share this backend selection. A native partial fill remains visible when the execution path has only an ACK; it does not authorize the next leg. The frontend does not merge account-wide venue fills, infer ownership from symbols, or deduplicate by price and time. Full native, order, instruction and batch identities remain available for inspection, including each Funding attempt and spot release.
- One backend read model owns strategy PnL, fees and timeline. It uses native venue fees, funding, swap and reported realized PnL; the frontend formats these results. MT5 positions retain Ticket identity, including opposite positions on the same instrument. Shared account net positions cannot stand in for an individual strategy's position. Cross account snapshots use the latest venue-synced positions for the current-position view; their historical finance projection remains a PnL and audit source only.
- The Cross position overview values remaining logical groups through this backend read model; its current floating PnL excludes closed PnL and charges. Ownership, executable prices, native Ticket checks, FX and complete-sum rules are defined in [CROSS_SPREAD_EXECUTION.md](CROSS_SPREAD_EXECUTION.md). MT5 position `asOf` is the current observation time, while `openTime` remains the native opening time; the last position modification time does not date a freshly read PnL snapshot.
- Native fees retain their sign and currency, including rebates and Spot fees paid in the base asset. Unsupported conversion, unknown opening basis or missing financial coverage produces a nullable subtotal and an explicit quality issue. Historical USD/USDT parity is never assumed. Unattributed settlements remain separate from strategy profit.
- The management Order/Fill tables expose the same native financial evidence at row level: realized PnL, fee cost, funding PnL, swap/inventory cost and the attributable realized net amount. Fill-provided fees or swap values take precedence over duplicate settlement events; fee cash movements are normalized only for display, while original event sign and currency remain available in the settlement section. The grouped open/close record also shows FIFO matched holding time per account and instrument; an unmatched open group is labeled as still held. Missing currency or ownership stays `--`/pending and is never converted or treated as zero.
- Missing native fee values remain null and mark `fill_details_pending`; only an explicit source zero means zero. Missing fee currency marks `fee_currency_unavailable`. A confirmation without native details cannot prove zero cost. Native settlement rows retain the reported cash sign, while fill fees use positive expense / negative rebate; they are separate evidence views and must not be added twice as costs.
- Account asset curves remain observed balances. Owner confirmed on 2026-09-09 that drawdown excludes capital inflows/outflows. Runtime `GET /venue/capital-flows` reads bounded (at most seven-day) Bybit UTA and Funding logs or MT5 deals through the existing account worker. All pages must succeed before Platform records coverage. Unknown movement classifications retain null amounts, never zero. Native payloads and stable event identities are retained separately from trading/accounting facts.
- Platform independently backfills one window per account synchronization cycle from the earliest observed equity, then refreshes with a ten-minute overlap; it queries at most once per minute and leaves the newest minute pending for source publication. Failed reads retain prior coverage and a separate capital-sync error. An empty successful source window establishes no-flow coverage only for that window. Late source corrections outside the overlap require an explicit historical reread.
- Capital movements are scoped to `unified_trading`, `mt5_trading` or `full_account`. Matched Funding/UTA movements, Earn mint/redemption and documented MT5 internal movements cancel within the full-account overview; unknown transfer counterparts stay unclassified. Fees, interest and trading PnL remain performance. Classification may resolve null to a known value only against identical native evidence; conflicting previously classified financial content fails persistence.
- Flow-adjusted performance uses timestamp-weighted Modified Dietz between observed snapshots: `r = (ending - beginning - sum(flow)) / (beginning + sum(weight * flow))`, where `weight = (end - flowTime) / (end - start)` and positive flow is capital entering the scope. Chain `1+r` and compute percent drawdown relative to its running high-water mark. The first displayed comparable snapshot sets the baseline. This is an estimate because exact valuations at every flow instant do not exist; it is not exact flow-boundary TWR. Missing coverage, unknown classification, missing FX or nonpositive invested capital leaves the affected interval unavailable; after a confirmed coverage gap, the first subsequent comparable point starts a new drawdown baseline instead of hiding all newer observations.
- USD conversions never assume USDT=USD. New snapshots retain Bybit wallet `usdValue/equity` rates; conversion requires a quote within five minutes of the movement. Historical supplementary quotes use completed Coinbase USD one-minute candles, with source/time persisted; BYUSDT uses its documented 1:1 USDT backing as an explicitly identified estimate. Unsupported currency/time pairs remain unavailable. The read-only `execution-runtime/scripts/backfill_capital_valuations.py` accepts local currency/time requests; it sends no account identities or amounts to Coinbase. This is a historical repair utility, not an additional continuous market-data service.
- The strategy history response exposes nullable `equityDrawdown`, `totalAssetsDrawdown` and their quality fields. Frontend account charts, including Cross's three selectable scopes, consume these percentages and show “调整后回撤（估算）”; they do not recalculate raw-asset drawdown. These monitoring results never feed order admission or formal accounting/NAV.
- Funding and Cross calendars and overview curves both consume strategy-owned `strategyDailyPnl`; they never substitute shared account equity changes. The snapshot still exposes account-scoped `dailyPnl` independently, and includes lightweight `strategyDailyPnl` for Funding summary reads. Cross loads strategy PnL on the capital tab as well. This implements the Owner's 2026-09-20 clarification that each strategy's calendar must account for its own hedged positions.
- Live bindings exclude historical demo/testnet orders while retaining genuine historical live accounts. Persisted execution direction and native MT5 entry type distinguish closes from opens. A close outside retained opening history cannot create an opposite position; a native closing receipt remains valid realized evidence, but unavailable opening cost cannot become a complete lifetime net return. MT5 opening tickets come from owned exit plans when legacy confirmations lack native ticket metadata. Spot fees charged in the base asset reduce held quantity as well as contribute fee expense.
- Funding attribution accepts explicit order/fact ownership, or a native settlement receipt whose signed total position size exactly reconciles to the strategy's reconstructed exposure at that instant and has no conflicting explicit ownership. Historical symbol ownership alone remains insufficient. Native MT5 swap/fee receipts resolve through their actual native order IDs, preventing duplicate booking alongside deal receipts.
- Daily net PnL is owned realized PnL plus the change in owned unrealized valuation, minus fees plus funding and swap. Retained Cross quote/position observations and native coin valuation/settlement marks supply historical valuations within five minutes of UTC day end. Matching the complete set of owned MT5 tickets permits the native account floating result, including accrued swap, for those positions only. Historical observations are estimates; missing marks or baseline affect their intervals, not every later day. Current cumulative unrealized PnL is never all booked on the current day.
- Overview curves accumulate the latest continuous, valued daily interval and label its start explicitly as interval net PnL. They never bridge missing days or substitute an unpaired realized-only curve as total return. Lifetime totals remain unavailable when early cost/fee evidence is incomplete. The calendar retains other independently valued dates.
- Bybit's full-account asset overview already contains its reported TradFi/MT5 and spot assets, including floating valuation. Never add MT5 equity to that total a second time. Display the native valuation currency; a current marked asset value is not realized trading loss.
- Strategy curve precision defaults to daily and also supports weekly, hourly and five-minute buckets in Asia/Shanghai. Each bucket uses the last available cumulative observation; missing observations and unimplemented category curves remain absent. Historical timestamps must be retained independently from formatted labels.
- The strategy account snapshot also exposes an account-scoped `dailyPnl` series beside the equity history: each UTC day's closing observation (the last equity of that day within the snapshot's asset scope and currency) differenced against the previous close and reduced by the classified net capital flow of that interval. Owner confirmed on 2026-09-11 that the measure includes unrealized and realized result together with fees, funding and swap, so it is a flow-adjusted reconstruction rather than a venue-reported daily PnL. A day whose interval lacks coverage, flow classification, FX valuation or nonpositive invested capital returns null `pnl`/`returnRate` with a `quality` reason rather than zero, and one unvaluable interval never suppresses the next; the newest day stays pending until the upstream minute is published, so a trailing `missing_history` day is expected rather than a defect. Days and rates cut at UTC, independently of the Platform's localized display time zones. The frontend may only sum intervals and compound the per-day rates for month and year views, marking a period that contains an unvalued day `--`, and never sums or converts across currencies or asset scopes. These results remain read-only observability and never feed order admission or formal accounting.
- Cross strategy PnL uses strategy-owned financial facts, never a sum of shared-account daily returns. Its default `valuationPolicy=mt5_open` selects retained observations where both venues report open and available, excluding stale quotes but not automatic-exit guard windows. All strategy financial amounts are projected at `valuationAsOf`; closed days have null PnL with `market_closed` and do not reset the last valid baseline. Actual settlement costs during closure enter the next valid reporting interval. Unknown historical market states remain unavailable; no weekday/Beijing-time calendar is invented. Account/risk projections remain continuous.
- Position exposure is projected per snapshot scope. `positionValue` is the gross notional of exactly the positions that projection reports and `positionValueNet` is their signed net, both stated in the single reported currency. Legs reported in more than one currency yield null exposure: the frontend groups by original currency and never sums them or assumes an FX rate. A leg whose venue report does not describe the projected quantity is valued from the mark price and the stored contract multiplier, so an MT5 LOT quantity is never read as a contract count. `leverage` is the local ratio of gross notional to account equity; `venueLeverage` is the venue's own reported account parameter and is never substituted for it. The strategy PnL panel's position distribution consumes these per-leg values and invents no value it cannot source.
- Position distribution is a source-row presentation, not a preferred-leg estimate. The catalog projects each strategy's owned current rows into its account snapshot; Cross account funding views use the latest venue-synced rows for current exposure, while historical finance rows are not allowed to resurrect a closed leg. Hedged legs may be grouped by normalized underlying for display and net-quantity risk, but long and short quantities remain separately traceable. The frontend displays gross value and original-asset quantities separately, uses `oz` for XAU and `枚` when the source unit is unknown, and keeps net exposure in the strategy risk card rather than duplicating it in the distribution header. Cross-spread aggregate net exposure may combine its explicitly bound Bybit and MT5 rows; a single venue's one-sided position is not presented as the Cross aggregate. MT5 value currency follows the account report and is not split into a second USDT position.
- `GET /strategies/instances/{strategyInstanceId}/account-snapshot?includeDetails=false` is the management page's summary read. It still returns balances, risk, equity history and current venue positions with backend-provided values, while omitting orders, fills and the historical finance payload; the full default response remains available to order and audit views.
- `snapshot.positions` is the consumer's current-position input in both response modes. The catalog selects venue positions for Cross/read-only account views and strategy-owned positions for trading strategies (including Funding spot holdings); `finance.positions` must not override or fill an empty current array. If the browser further filters rows, it must not retain exposure/leverage totals describing discarded rows. Value currencies remain the reported currencies; USD and USDT are not interchangeable without valuation evidence.
- Browser transport failures retain the last successful frame with a stale/error indication. An initial failure is not proof of an empty account or missing binding. Binding failure, per-account failure and strategy-PnL failure remain distinct from a successful unbound result; recovery clears the relevant failure only after a successful read.

Cross market snapshots retain each venue's observation time and request duration (`asOf`, `fetchLatencyMs`). Request duration is not quote age or order execution latency. Independent Bybit, MT5 and valuation reads run concurrently, concurrent requests share one refresh, and the short market cache expires after one second. The page polls every three seconds without overlapping a pending refresh; unavailable/stale quotes cannot be presented as currently available.

The snapshot separately reports quote visibility and execution capability. `quoteSourceAsOf` is the Venue's native last-price time; `openAllowed`, `closeAllowed`, `executionBlockReason` and aggregate `executionState` determine whether the current quote may enter a normal Cross decision. A positive cached MT5 weekend quote remains observable but is `monitor_only` once its native age exceeds 30 seconds. This state continues spread, position, margin and liquidation-risk reads while preventing normal Open, Close and TP/SL claims. Monitor health reports the background loop separately from the Live Write execution gate, so a running read-only loop is not labelled as a stopped monitor.

## 9. Frontend acceptance panel

The cross-spread page includes a read-only panel showing:

- Bybit and MT5 account-risk metrics;
- current positions and authoritative liquidation/Stop Out semantics;
- current active Orders;
- recent historical Orders;
- recent Fills/Deals and fees;
- section-level failure warnings;
- 24-hour, 3-day and 7-day bounded history selection.

The panel has no Order, Cancel, Close or account-modification control.

Any legacy `1 oz` market-lifecycle default is a historical test convention, not a current owner requirement or readiness fact. The immutable CEO instruction supplies both leg quantities for an authorized batch.

## 10. Controlled-acceptance safeguards

The following remain mandatory:

- immutable CEO instruction quantities and cumulative-fill ceilings for both legs;
- atomic resource claims and balance reservations under the shared-account rules in `../operations/LIVE_ACCEPTANCE_RUNBOOK.md`;
- no duplicate business intent; multiple plans and partial closes follow `CROSS_SPREAD_EXECUTION.md` and retain exact remaining quantity and MT5 Ticket identity;
- execution-mode progression and fallback behavior governed by `../operations/LIVE_ACCEPTANCE_RUNBOOK.md`;
- Platform Live Write disabled by default;
- Runtime Live Write disabled by default;
- automatic exit monitor disabled by default;
- no automatic retry after unknown external result.

Before enabling a changed build for real trading, the owning execution contract and authorized acceptance window require evidence for:

1. successful route-independent Order and Fill/Deal reads;
2. repeated instruction-bounded open/close cycles in both directions;
3. correct position and account-risk reconciliation;
4. Bybit rollback and single-leg exposure handling;
5. Runtime restart, Terminal restart and network interruption drills;
6. no unexplained Order, Fill, Position, Balance, fee, Funding or Swap differences;
7. Kill Switch and gate reset evidence.

The mandatory safeguards above are not candidates for relaxation or removal. A future review may strengthen their implementation or evidence requirements only; passing one small-money test does not authorize weakening any safeguard.

## 11. Windows-host acceptance sequence

1. Keep both Live Write gates and the automatic monitor disabled.
2. Confirm Runtime health, capabilities, connectivity and venue readiness.
3. Open the read-only observability panel.
4. Verify account IDs, symbols, equity, available margin and permissions.
5. Verify current active Orders and positions against the Bybit and MT5 native interfaces.
6. Verify a 24-hour historical Order/Fill window, then a seven-day window.
7. Confirm Bybit liquidation values match the venue UI where a finite value exists.
8. Confirm MT5 shows no fabricated position liquidation price and matches Margin Call / Stop Out settings.
9. Resolve every unavailable or unexplained section before requesting an owner-authorized, instruction-bounded write window.


## Local service and monitor health

`GET /api/v1/system/monitor-health` (and local `/health/monitors`) reports process-local
account-sync and Cross-exit start/completion/last-success timestamps. Disabled,
starting, degraded and stalled are distinct; a successful process health check is
not evidence of a successful account read or exit evaluation. Account sync is
stalled after 180 seconds without progress; Cross exit after 60 seconds. Restart
resets process-local evidence. An unavailable quote or evaluation exception is not
a successful exit evaluation. These reads do not enable TP/SL or Live Write.

The Windows lifecycle starts a separate hidden watchdog. It checks every 15 seconds,
requires three failed local health probes, and uses a five-minute recovery cooldown
with at most three attempts per hour. Repeated failed account reads (six probes) or
stalled monitors may restart the read-only backends. Recovery reuses the existing
managed-service launcher and is serialized with manual lifecycle operations.
Foreign listeners or changed trading modes block automatic recovery. Enabled Live
Write blocks API/Runtime interruption; a failed static Web process may still recover
independently, retaining any backend-blocked report. No saved flag authorizes live startup.
Manual stop stops the watchdog; machine boot/login does not automatically start it.
The strategy management page polls health and displays degradation, disabled exit
monitoring, watchdog failures and health-request failures. This is an in-app alert,
not email or an off-device notification. The watchdog status is saved in
`.codex/dev-platform/watchdog.json`; a report older than 180 seconds is stale.

Native realized cash flows are matched to fills by account, owned order and native
tradeId before cost-basis reconstruction; the matching receipt is counted once.
The daily history audit checks canonical strategy-owned filled orders for missing
native fill quantities and queries one earliest missing two-day window, including
all pages, beyond the rolling seven-day window. It appends original venue receipts
and never changes orders or positions. Missing historical daily marks stay missing.

Cross total-asset chart exposes `sessionEquityHistory` alongside unchanged real-time
`equityHistory`. The default open-session mode filters observations before calling
the existing cash-flow-adjusted drawdown calculation; deposits/withdrawals across
closures remain in the comparison interval. Session-close samples come from the
original risk archive even when the live 1000-point slice is entirely closed.
Legacy snapshots without market-state fields qualify only when retained available bid/ask observations prove an MT5 quote change within 120 seconds. Repeated polling timestamps alone never establish an open session; explicit closed/stale states remain excluded. Reporting archive lookups
use a bounded 30-second cache and revision-keyed daily results; execution and risk
never use this cache. Both total-assets modes are read-only display policies.

Strategy management PnL and account snapshots are served from the durable `strategy_management_projection` table (migration 32). A background worker refreshes active summaries and requested details, targeting 30 seconds; HTTP reads do not reconstruct financial histories. Failed refreshes preserve the last payload and flag it stale after 90 seconds or immediately on refresh error. Cold keys return an explicit retryable 503. Trading validation and execution continue using current authoritative facts, never this serving projection. Monitor health exposes `managementProjection`.

Cross asset history merges recent observations with archived hourly samples for 14 days and daily samples up to 400 days. Missing daily valuations remain missing; charts retain all evidenced segments and disconnect at gaps, resetting segment cumulative values instead of inventing returns across missing data.
