# Task: Complete Live Account Observability

Issue: #98
Status: review
Branch: `feature/issue-98-live-account-observability`
Base commit: `6eb92ded8bfd439ad30654219597023cc91db7e9`

## Objective

Complete the read-only live Venue, account and risk evidence required before the supervised 1 oz real-money acceptance run, so the Windows-host phase requires only environment-specific configuration and bounded defect correction.

## Confirmed gaps addressed

- Current Order listing had no explicit time window or continuation contract.
- Fill/Deal history had no unified bounded paging contract.
- Order snapshots omitted key diagnostics.
- Position snapshots omitted Venue risk and liquidation fields.
- Balance snapshots did not represent account-level margin and Stop Out state.
- MT5 has no authoritative per-position liquidation price and must not receive a fabricated estimate.
- The strategy frontend had no consolidated read-only acceptance dashboard and defaulted to 100 oz.

## Changed files

### Execution Runtime

- `execution-runtime/app/models.py`
- `execution-runtime/app/gateway.py`
- `execution-runtime/app/bybit_acceptance_adapter.py`
- `execution-runtime/app/live_observability.py`
- `execution-runtime/app/strict_live_acceptance_adapters.py`
- `execution-runtime/app/bybit_mt5_gateway.py`
- `execution-runtime/app/fake_gateway.py`
- `execution-runtime/app/main.py`
- `execution-runtime/tests/test_live_observability.py`

### Platform Backend

- `platform-backend/app/cross_spread_live_read_client.py`
- `platform-backend/app/cross_spread_observability_schemas.py`
- `platform-backend/app/cross_spread_observability_service.py`
- `platform-backend/app/cross_spread_observability_routes.py`
- `platform-backend/app/main.py`
- `platform-backend/tests/test_cross_spread_observability.py`

### Frontend

- `admin-risk/src/api/platform/crossSpreadObservability.ts`
- `admin-risk/src/views/strategy/spread-carry/components/CrossSpreadLiveObservabilityPanel.vue`
- `admin-risk/src/views/strategy/spread-carry/components/SpreadExecutionWorkspace.vue`
- `admin-risk/src/views/strategy/spread-carry/components/CrossSpreadMarketLifecyclePanel.vue`

### Documentation

- `docs/technical/LIVE_ACCOUNT_OBSERVABILITY.md`
- `docs/technical/API_SPEC.md`
- `docs/operations/V6-小资金实盘验收手册.md`
- `docs/architecture/OWNERSHIP.md`
- `docs/codex/current-state.md`
- this task packet

## Implementation decisions

- Existing current-list endpoints remain compatible; explicit paged history endpoints own time-window retrieval.
- Every history query has a bounded time window, page size and deterministic continuation.
- Runtime rejects a history window longer than seven days and a page size greater than 100.
- Unknown, partial, external-only and unavailable states remain distinguishable from a healthy empty result.
- Bybit `liqPrice` is displayed only when supplied by the Venue as a positive finite value.
- MT5 per-position liquidation price remains null with `not_available_mt5_api`; Account Margin Level, Margin Call and Stop Out are authoritative.
- No response field is populated from an unlabelled estimate.
- The Platform aggregate reads each Venue section independently so one failure does not erase other evidence.
- The frontend observability panel is read-only and contains no Order, Cancel, Close or Position-modification control.
- Existing 1 oz, single-lifecycle, Market-only and disabled-monitor restrictions remain unchanged.

## Acceptance criteria

- [x] Route-independent Bybit and MT5 history supports time filters and continuation.
- [x] Order snapshots expose remaining quantity and Venue diagnostics when available.
- [x] Bybit positions expose mark, break-even, liquidation, leverage, margin and risk fields.
- [x] MT5 positions expose current price, PnL, Swap, TP/SL and explicit unavailable liquidation semantics.
- [x] Account risk exposes Bybit UTA IM/MM metrics and MT5 Margin/Stop Out metrics.
- [x] Platform exposes one read-only aggregate cross-spread observability API.
- [x] A failed aggregate section is not represented as a healthy zero or empty list.
- [x] Frontend shows account risk, positions, Orders and Fills without write controls.
- [x] Frontend acceptance quantity defaults to 1 oz.
- [x] Canonical Markdown documents fields, availability and local acceptance procedure.
- [x] Focused Runtime and Backend regression tests cover liquidation, Stop Out, paging and partial reads.
- [x] Platform CI #1431 and Secret Scan #784 passed on the final code head.
- [ ] Final documentation head passes Platform CI and Secret Scan.

## Stop conditions

- Stop if implementation requires enabling Live Write or the automatic exit monitor.
- Stop if an MT5 liquidation price would need to be inferred or guessed.
- Stop if history retrieval becomes an unbounded full-account scan.
- Stop if credentials or raw secret values would enter responses, logs, tests or Markdown.
- Stop if scope expands into limit execution, WebSocket migration or production alerting.

## Completion

- PR: #99
- Current: implementation complete; final documentation-head verification in progress.
- Live external behavior proven: no. Real Bybit/MT5 field availability and Windows-host execution remain Issue #39 operational evidence.
- Follow-up: controlled local/Windows acceptance, private WebSocket confirmation and real Limit execution remain separately bounded scopes.
