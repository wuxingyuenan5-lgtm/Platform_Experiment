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

Bybit recent history covers an explicit seven-day UTC interval and follows every cursor within a bounded page count. Repeated cursors or an exhausted bound fail instead of silently truncating. Responses state history coverage and actual record totals; the management snapshot includes at most 200 recent Orders/Fills and 1000 comparable account-equity points. Venue financial events are retained across refresh windows by account, source, event type and stable external identity.

### 8.1 Strategy-management projections

- Strategy Order and Fill history is attributed through `StrategyInstruction` / `ExecutionBatch` / `TradeCommand` identities, never by account display name or account-plus-symbol filtering. This is required when strategies share one UTA.
- Platform monitoring resolves legacy order aliases by the exact `(account_id, instrument_id, external_order_id)` tuple. Instrument identity includes the market category; symbol or timestamp similarity is insufficient. A unique command-owned order wins over its monitoring aliases. Multiple command owners remain an identity conflict. Original IDs, rows and native payloads are retained.
- Order-linked settlements follow the same owner even if an older shared-account projection assigned them elsewhere. The strategy settlement table contains only owned events; unassigned funding/swap stays pending and is not counted in Funding merely because that strategy shares the account.
- Monitoring does not require every historical symbol to have a trading instrument specification. Such Orders/Fills remain readable with their native receipts; unavailable multiplier or opening basis marks the calculation incomplete instead of failing the account snapshot. A read-model failure is a data-loading error, not proof that configured credentials are disconnected.
- Account snapshots retain native executions and fees, but cannot advance a command-owned order's status, append its execution quantities, or resolve `result_unknown`. Those transitions remain with the execution/reconciliation path and its cumulative-fill ceiling. Monitor-only fill IDs are scoped by account, source and native fill identity; raw tickets remain available separately.
- New operational fills explicitly record `runtime_confirmation` or `venue_execution`, their source and any native fill ID. Each row is an increment within its source representation. Known mixed representations or quantities exceeding a business order's ceiling fail closed. Unclassified historical rows retain the old bounded projection and expose `legacy_fill_provenance_pending`; migration does not infer provenance from a quantity equal to the order size.
- Management uses native executions when their coverage includes the operational confirmation, replacing rather than adding to that confirmation. A native quantity beyond the order size remains visible with `venue_fill_quantity_exceeds_order`; it cannot increase executable quantities. Incomplete native coverage stays pending. Monitor-only orders synthesized from a first fill do not impose that fill's size as an artificial financial ceiling. Stored multipliers and native settlement rules still apply.
- The management fill list, account snapshot and strategy financials share this backend selection. A native partial fill remains visible when the execution path has only an ACK; it does not authorize the next leg. The frontend does not merge account-wide venue fills, infer ownership from symbols, or deduplicate by price and time. Full native, order, instruction and batch identities remain available for inspection, including each Funding attempt and spot release.
- One backend read model owns strategy PnL, fees and timeline. It uses native venue fees, funding, swap and reported realized PnL; the frontend formats these results. MT5 positions retain Ticket identity, including opposite positions on the same instrument. Shared account net positions cannot stand in for an individual strategy's position.
- The Cross position overview values remaining logical groups through this backend read model; its current floating PnL excludes closed PnL and charges. Ownership, executable prices, native Ticket checks, FX and complete-sum rules are defined in [CROSS_SPREAD_EXECUTION.md](CROSS_SPREAD_EXECUTION.md). MT5 position `asOf` is the current observation time, while `openTime` remains the native opening time; the last position modification time does not date a freshly read PnL snapshot.
- Native fees retain their sign and currency, including rebates and Spot fees paid in the base asset. Unsupported conversion, unknown opening basis or missing financial coverage produces a nullable subtotal and an explicit quality issue. Historical USD/USDT parity is never assumed. Unattributed settlements remain separate from strategy profit.
- Missing native fee values remain null and mark `fill_details_pending`; only an explicit source zero means zero. Missing fee currency marks `fee_currency_unavailable`. A confirmation without native details cannot prove zero cost. Native settlement rows retain the reported cash sign, while fill fees use positive expense / negative rebate; they are separate evidence views and must not be added twice as costs.
- Account asset curves remain observed balances. Owner confirmed on 2026-09-09 that drawdown excludes capital inflows/outflows. Runtime `GET /venue/capital-flows` reads bounded (at most seven-day) Bybit UTA and Funding logs or MT5 deals through the existing account worker. All pages must succeed before Platform records coverage. Unknown movement classifications retain null amounts, never zero. Native payloads and stable event identities are retained separately from trading/accounting facts.
- Platform independently backfills one window per account synchronization cycle from the earliest observed equity, then refreshes with a ten-minute overlap; it queries at most once per minute and leaves the newest minute pending for source publication. Failed reads retain prior coverage and a separate capital-sync error. An empty successful source window establishes no-flow coverage only for that window. Late source corrections outside the overlap require an explicit historical reread.
- Capital movements are scoped to `unified_trading`, `mt5_trading` or `full_account`. Matched Funding/UTA movements, Earn mint/redemption and documented MT5 internal movements cancel within the full-account overview; unknown transfer counterparts stay unclassified. Fees, interest and trading PnL remain performance. Classification may resolve null to a known value only against identical native evidence; conflicting previously classified financial content fails persistence.
- Flow-adjusted performance uses timestamp-weighted Modified Dietz between observed snapshots: `r = (ending - beginning - sum(flow)) / (beginning + sum(weight * flow))`, where `weight = (end - flowTime) / (end - start)` and positive flow is capital entering the scope. Chain `1+r` and compute percent drawdown relative to its running high-water mark. The first displayed comparable snapshot sets the baseline. This is an estimate because exact valuations at every flow instant do not exist; it is not exact flow-boundary TWR. Missing coverage, unknown classification, missing FX or nonpositive invested capital leaves the affected and subsequent points unavailable; the curve never bridges such a gap.
- USD conversions never assume USDT=USD. New snapshots retain Bybit wallet `usdValue/equity` rates; conversion requires a quote within five minutes of the movement. Historical supplementary quotes use completed Coinbase USD one-minute candles, with source/time persisted; BYUSDT uses its documented 1:1 USDT backing as an explicitly identified estimate. Unsupported currency/time pairs remain unavailable. The read-only `execution-runtime/scripts/backfill_capital_valuations.py` accepts local currency/time requests; it sends no account identities or amounts to Coinbase. This is a historical repair utility, not an additional continuous market-data service.
- The strategy history response exposes nullable `equityDrawdown`, `totalAssetsDrawdown` and their quality fields. Frontend account charts, including Cross's three selectable scopes, consume these percentages and show “调整后回撤（估算）”; they do not recalculate raw-asset drawdown. These monitoring results never feed order admission or formal accounting/NAV.
- Strategy curves show accumulated realized PnL with the stated coverage. Values of different currencies or asset scopes are not summed into a fabricated combined equity.
- Strategy curve precision defaults to daily and also supports weekly, hourly and five-minute buckets in Asia/Shanghai. Each bucket uses the last available cumulative observation; missing observations and unimplemented category curves remain absent. Historical timestamps must be retained independently from formatted labels.

Cross market snapshots retain each venue's observation time and request duration (`asOf`, `fetchLatencyMs`). Request duration is not quote age or order execution latency. Independent Bybit, MT5 and valuation reads run concurrently, concurrent requests share one refresh, and the short market cache expires after one second. The page polls every three seconds without overlapping a pending refresh; unavailable/stale quotes cannot be presented as currently available.

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
