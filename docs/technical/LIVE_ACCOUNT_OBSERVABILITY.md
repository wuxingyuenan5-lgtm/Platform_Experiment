# Live Account Observability Contract

Status: `active / read-only acceptance contract`  
Scope: Bybit UTA + MT5 account used by the cross-spread strategy  
Related Issues: #39, #96, #98

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

## 8. Data-quality states

| State | Meaning |
|---|---|
| `complete` | The section read succeeded and an empty list is a valid zero result |
| `external_only` | Venue record exists but has no authoritative Platform route mapping |
| `venue_windowed` | Result is complete only for the declared venue time window/page |
| `partial` | Aggregate has both successful and failed sections |
| `unavailable` | The section could not be read; zero/empty must not be inferred |

The aggregate returns per-section states for account risk, positions, active Orders, recent Orders and recent Fills.

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
- global serialization of new execution batches;
- no scale-in or duplicate open;
- execution-mode progression and fallback behavior governed by `../operations/LIVE_ACCEPTANCE_RUNBOOK.md`;
- Platform Live Write disabled by default;
- Runtime Live Write disabled by default;
- automatic exit monitor disabled by default;
- no automatic retry after unknown external result.

They may only be changed by a dedicated Issue/PR after Issue #39 contains mature evidence for:

1. successful route-independent Order and Fill/Deal reads;
2. repeated instruction-bounded open/close cycles in both directions;
3. correct position and account-risk reconciliation;
4. Bybit rollback and single-leg exposure handling;
5. Runtime restart, Terminal restart and network interruption drills;
6. no unexplained Order, Fill, Position, Balance, fee, Funding or Swap differences;
7. Kill Switch and gate reset evidence.

A future review must list each safeguard separately as `retain`, `relax` or `remove`. Passing one small-money test does not automatically delete any safeguard.

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
