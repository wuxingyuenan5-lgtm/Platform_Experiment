# Task: Complete Live Account Observability

Issue: #98
Status: in_progress
Branch: `feature/issue-98-live-account-observability`
Base commit: `6eb92ded8bfd439ad30654219597023cc91db7e9`

## Objective

Complete the read-only live venue, account and risk evidence required before the supervised 1 oz real-money acceptance run, so the Windows-host phase requires only environment-specific configuration and defect correction.

## Confirmed gaps

- Current order listing has no explicit time window or continuation contract.
- Fill/Deal history has no unified bounded paging contract.
- Order snapshots omit key debugging attributes.
- Position snapshots omit venue risk and liquidation fields.
- Balance snapshots do not represent account-level margin and Stop Out state.
- MT5 has no authoritative per-position liquidation price; it must remain unavailable rather than estimated.
- The strategy frontend has no consolidated read-only acceptance dashboard and still defaults to 100 oz.

## Expected changed files

### Execution Runtime

- `execution-runtime/app/models.py`
- `execution-runtime/app/gateway.py`
- `execution-runtime/app/bybit_acceptance_adapter.py`
- `execution-runtime/app/mt5_acceptance_adapter.py`
- `execution-runtime/app/bybit_live_adapter.py`
- `execution-runtime/app/mt5_live_adapter.py`
- `execution-runtime/app/bybit_mt5_gateway.py`
- `execution-runtime/app/fake_gateway.py`
- `execution-runtime/app/main.py`
- focused Runtime tests

### Platform Backend

- bounded cross-spread observability schemas/service/routes
- `platform-backend/app/main.py`
- focused Backend tests

### Frontend

- read-only observability API client
- bounded acceptance dashboard component
- lifecycle workspace integration
- 1 oz default correction

### Documentation

- `docs/technical/API_SPEC.md`
- `docs/technical/LIVE_VENUE_ADAPTERS.md`
- `docs/technical/VENUE_RECONCILIATION.md`
- `docs/operations/V6-小资金实盘验收手册.md`
- `docs/architecture/OWNERSHIP.md`
- `docs/codex/current-state.md`
- this task packet

## Implementation rules

- Preserve current list endpoints for compatibility; add explicit paged history endpoints.
- Every history query has a bounded time window, page size and deterministic continuation.
- Unknown, stale, partial, external-only and unsupported states remain distinguishable.
- Bybit `liqPrice` is venue-reported evidence and may be null/empty under account modes where no finite value is supplied.
- MT5 per-position liquidation price is always unavailable unless the broker API explicitly supplies it in a future contract; account-level Margin Call and Stop Out are authoritative instead.
- No field may be populated from an unlabelled local estimate.
- No observability endpoint may create, cancel or modify an order.
- Existing 1 oz, single-lifecycle, Market-only and disabled-monitor restrictions remain unchanged.

## Acceptance criteria

- [ ] Route-independent Bybit and MT5 history supports time filters and continuation.
- [ ] Order snapshots expose remaining quantity and venue diagnostics when available.
- [ ] Bybit positions expose mark, break-even, liquidation, leverage, margin and risk status fields.
- [ ] MT5 positions expose current price, PnL, Swap, TP/SL and explicit unavailable liquidation semantics.
- [ ] Account risk exposes Bybit UTA IM/MM metrics and MT5 margin/Stop Out metrics.
- [ ] Platform exposes one read-only aggregate cross-spread observability API.
- [ ] Frontend shows account risk, positions, orders and fills without write controls.
- [ ] Frontend acceptance quantity defaults to 1 oz.
- [ ] Canonical Markdown documents fields, availability and local acceptance procedure.
- [ ] All required CI and Secret Scan checks pass.

## Stop conditions

- Stop if implementation requires enabling Live Write or the automatic exit monitor.
- Stop if an MT5 liquidation price would need to be inferred or guessed.
- Stop if history retrieval becomes an unbounded full-account scan.
- Stop if credentials or raw secret values would enter responses, logs, tests or Markdown.
- Stop if scope expands into limit execution, WebSocket migration or production alerting.
