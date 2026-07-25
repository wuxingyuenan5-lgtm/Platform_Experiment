# Current Project State

Last updated: 2026-07-25
Stable branch: `main`
Product release: `0.7.0`
Latest completed engineering scope: Issue #96 / PR #97
Latest completed documentation scope: Issue #96 / PR #97

This file is the compact cross-session handoff. It records current truth, not a PR diary. Read the actual open Issues and PRs before assuming that work is active.

## Current architecture

- `admin-risk/`: Vue product frontend.
- `platform-backend/`: modular-monolith business, risk, execution orchestration and accounting API.
- `execution-runtime/`: isolated venue/Gateway process and runtime journal.
- SQLite remains the approved persistence technology for the current stage.
- Canonical major module ownership is recorded in `docs/architecture/OWNERSHIP.md`.
- Frontend responsive layout, viewport support, page-shell, scroll, overflow and fixed-position governance are canonically defined in `admin-risk/docs/architecture/frontend/responsive-layout-architecture.md`.
- Cross-viewport test matrices, layout defect severity and release acceptance are canonically defined in `admin-risk/docs/quality/responsive-layout-acceptance.md`.
- Homepage-specific hierarchy, width, Hero and dashboard-grid behavior are defined in `admin-risk/docs/design/homepage-layout-standard.md`.

## Safety defaults

```text
TradingMode=simulation
Gateway=fake
Platform Live Write=false
Runtime Live Write=false
Cross-spread Exit Monitor=false
Cross-spread acceptance max quantity=1 oz
Cross-spread non-closed lifecycle max=1
```

Real-account acceptance remains controlled-host, small-capital and minimum-size. The 1 oz and single-lifecycle values are temporary acceptance restrictions, not permanent product limits. Their removal criteria are canonical in `docs/operations/V6-小资金实盘验收手册.md`.

## Current invariants

- Root `VERSION` is the product release source of truth; maintained Backend/Runtime package versions and frontend display follow it.
- FastAPI metadata and Platform–Runtime contract versions describe component/API compatibility and are independent from the product release number.
- Platform Backend does not import venue SDKs; external execution remains inside `execution-runtime/`.
- `platform-backend/app/main.py` is a composition root only.
- `platform-backend/app/trade_command_execution.py` is the single local Order creation, Safety and Runtime submission owner; `trading.submit_order` remains a deprecated legacy compatibility delegate.
- The Backend deprecated `POST /api/v1/trading/orders` compatibility endpoint remains available until external usage evidence and a dedicated migration support removal.
- Maintained funding execution uses ExecutionBatch; the unused frontend legacy single-order submit client and submit-state hook path have been removed.
- Cross-spread trading continues to use the nominal `Bybit Ask - MT5 Bid` and `Bybit Bid - MT5 Ask` formulas; USDT/USD normalization is not part of order triggering.
- Cross-spread market execution submits Bybit first, requires a terminal confirmed fill and sizes the MT5 hedge from the actual filled quantity; an acknowledgement or unresolved status cannot trigger the hedge.
- A terminal Bybit partial fill may be hedged only when its confirmed quantity maps exactly to the MT5 contract minimum, step and current contract size; otherwise the batch fails closed.
- Live cross-spread sizing reads current Bybit and MT5 instrument specifications through Runtime immediately before submission; database Seed specifications are not authoritative for real writes.
- Runtime independently converts MT5 lots through the current contract size before enforcing the temporary 1 oz cap; `1 lot` is never assumed to equal `1 oz`.
- Runtime Order/Fill reads do not require a local Route. Orders created before Runtime startup, externally, or after Route loss remain readable and are marked `external_only` until Platform identity is proven.
- MT5 Order Ticket, Deal Ticket and Position Ticket remain separate identities. A Deal Ticket may resolve its Order Ticket but cannot be used as a Position Ticket.
- Cross-spread CLOSE intent is persisted by TradeCommand idempotency key and transmitted through the versioned Runtime command contract.
- Bybit market close requires one matching live position, submits `reduceOnly=true` with its `positionIdx` and rejects wrong-side or oversized close requests.
- MT5 market close requires the intended live Position Ticket and rejects symbol, side, quantity or ticket ambiguity before `order_send`.
- At most one non-closed cross-spread exit plan is allowed during the acceptance phase. Any unresolved or manual-intervention batch blocks a new open.
- A successfully hedged cross-spread OPEN is healthy only after exact external Bybit and MT5 Position verification, then creates one persistent operational exit plan with one mapped MT5 Position Ticket.
- A cross-spread CLOSE is closed only after both external target positions are verified flat.
- If Bybit is terminally filled and MT5 definitively rejects or fails, the Platform may submit one idempotent Bybit reduce-only rollback only after current external positions prove the expected first-leg exposure and no MT5 exposure.
- If external positions are already flat, the rollback path does not create a duplicate reverse order.
- MT5 `accepted`, `processing`, `acknowledged` or `result_unknown` must not trigger automatic rollback or duplicate execution.
- LONG_SPREAD exit thresholds observe `shortSpread`; SHORT_SPREAD exit thresholds observe `longSpread`. TP/SL submits a market close only after an atomic plan claim.
- The automatic exit monitor is a separate disabled-by-default capability gate; unknown or manual-intervention plans are not automatically retried.
- Direct MT5 market-data access reads raw swap long/short and related symbol metadata through `symbol_info()` when available; the file bridge remains a fallback/diagnostic read path rather than the authoritative execution path.
- The original market/limit frontend design remains visible. The legacy execution card is read-only and a bounded real market-lifecycle panel owns actual market open/close actions so limit choices cannot misroute.
- Frontend responsive remediation is page-shell-first: defect baseline → Application Shell → Page Shell/layout primitives → shared components → core pages → visual regression.
- Application Shell owns top navigation, sidebar, main content sizing, the primary vertical scroll context and global overlay base.
- Page Shell owns page header, toolbar, summary, main/secondary regions, responsive reflow and fixed-bottom-action content reservation.
- Business blocks own their minimum usable size, internal reflow and explicitly bounded local scrolling; page main layout must not use absolute positioning or resolution-specific coordinates.
- The homepage uses a bounded `1840px` wide frame, content-driven height, deterministic Hero reflow and a stable two-column dashboard grid across the supported desktop range.
- Homepage content, routes and placeholder values remain unchanged; Issue #87 changes responsive placement, spacing and visual hierarchy only.
- `src/views/dashboard/**/*` is included by `tsconfig.full.json`, allowing changed-file type-aware ESLint to protect the homepage.
- Existing pages outside the homepage are not assumed to comply with the responsive standard merely because the homepage has been remediated.
- EOD Reconciliation public status types and request/response DTOs are owned only by `eod_reconciliation_schemas.py`; `eod_reconciliation.py` imports identical compatibility objects.
- EOD report status, scale-gate, historical-Difference and immutable-review decisions are owned only by the pure `eod_reconciliation_policy.py` module.
- EOD Reconciliation DDL, direct SQL, report row mapping, report identity and atomic review persistence are owned only by `eod_reconciliation_repository.py`.
- EOD report creation/read/list/review sequencing, cross-domain coordination, exact partial-failure capture and explicit service failures are owned only by `eod_reconciliation_service.py`.
- `eod_reconciliation.py` retains per-call dependency wiring, compatibility delegates, exact service-error-to-HTTP mapping and routes; `eod_policy.py` coordinates order-window and historical-Difference persistence without duplicating decisions.
- Venue Reconciliation public DTOs and difference status types are owned only by `venue_reconciliation_schemas.py`; the facade re-exports identical objects.
- Venue Reconciliation external-status mapping and Order/Position/Balance difference decisions are owned only by the pure `venue_reconciliation_policy.py` module.
- Venue Reconciliation DDL, direct SQL, row mapping and protected persistence transactions are owned only by `venue_reconciliation_repository.py`.
- Venue Reconciliation configured Runtime GET transport is owned only by `venue_reconciliation_runtime_client.py`.
- Venue Reconciliation use-case sequencing and explicit domain failures are owned only by `venue_reconciliation_service.py`; `venue_reconciliation.py` retains compatibility delegates, exact HTTP mapping and routes.
- Operational `positions` and `pnl_results` remain separate from FinancialFact-based formal accounting.
- Formal accounting is reconstructed from immutable facts and does not read operational projections as inputs.
- Operational and formal projections share the exact `position_math.calculate_position_update` callable for per-fill quantity, average price and realized PnL.
- Platform–Runtime Command/Event traffic uses explicit V1.0 contracts and snapshots.
- Database changes use an ordered migration ledger with immutable checksums.
- Backend and Runtime tests have exactly one primary taxonomy marker.
- Ownership or compatibility-boundary changes must update `docs/architecture/OWNERSHIP.md` in the same PR.
- Repository Safety validates canonical entrypoints, protected Owner mappings and active local Markdown file targets.
- Non-trivial task packets identify expected changed files, required verification and task-specific stop conditions.
- Venue fill reconciliation sums persisted text quantities with exact `Decimal` arithmetic and does not coerce them through SQLite `REAL`.

## Completed engineering baseline

1. Composition and module-boundary cleanup.
2. Whole-directory lint, dependency and repository-structure gates.
3. Execution-schema ownership extraction.
4. Operational/formal financial projection separation.
5. Executable Backend and Runtime test taxonomy.
6. Canonical human/Agent context system and bounded task packets.
7. One-Issue/one-branch/one-PR machine governance.
8. DDL ownership inventory and non-destructive schema migration ledger.
9. Versioned Platform–Runtime V1 contracts and compatibility snapshots.
10. Progressive Pyright gates for critical Backend/Runtime boundaries.
11. Frontend changed-file no-new-debt lint enforcement.
12. Failure-injection tests and controlled production-acceptance matrix.
13. FinancialFact public-schema ownership extraction.
14. FinancialFact persistence ownership extraction with transaction rollback evidence.
15. FinancialFact normalization and immutable-content hash ownership extraction.
16. Formal Position/PnL/NAV projection-service extraction.
17. SQLite connection/path transaction boundary extraction.
18. Core database Bootstrap/Schema ownership extraction with exact checksum.
19. Fixed database Seed ownership extraction with exhaustive all-value snapshot and repeated-startup equivalence.
20. Canonical architecture ownership catalog with blocking documentation-consistency checks.
21. Lightweight task-packet controls and active local Markdown-link validation.
22. Exact Decimal venue fill reconciliation with fractional/high-precision regression evidence.
23. Shared Position Math ownership with ten long/short golden cases and compatibility-identity evidence.
24. Unified Platform order submission with exact legacy/V1 payload, Safety and unknown-result regression evidence.
25. Venue Reconciliation public-schema ownership with exact pre-extraction JSON Schema/OpenAPI and compatibility-identity evidence.
26. Venue Reconciliation Difference Policy ownership with exact status, key, value and precedence Goldens.
27. Venue Reconciliation Repository ownership with exact DDL, SQL, idempotency and rollback evidence.
28. Venue Reconciliation Runtime Client ownership with configured URL/parameter/timeout and transport-error equivalence evidence.
29. Venue Reconciliation Service ownership with exact domain-error/HTTP compatibility and EOD/API regression evidence.
30. EOD Reconciliation public-schema ownership with exact object-identity, JSON Schema and validation-message evidence.
31. EOD Reconciliation Repository ownership with exact DDL, report identity, immutable-review transaction and rollback evidence.
32. Pure EOD report/review Policy ownership with exhaustive status, gate, replay, conflict and approval Goldens.
33. EOD Reconciliation Service ownership with per-call compatibility injection, exact partial-failure and HTTP-mapping evidence.
34. Platform 0.7.0 product-version consolidation with blocking drift checks and verified frontend dead-code removal.
35. Canonical responsive-layout, Page Shell and cross-viewport acceptance architecture with an explicit phased remediation sequence.
36. Homepage-first responsive remediation with deterministic Hero reflow, stable desktop dashboard density and type-aware changed-file lint coverage.
37. Cross-spread market-order minimum loop with terminal Bybit fill confirmation, actual-fill-proportional MT5 hedge sizing, fail-closed unresolved states and direct MT5 swap reads.
38. Cross-spread market-only lifecycle with venue-safe reduce-only close semantics, MT5 Position Ticket binding, persistent exit plans and executable-spread TP/SL market exits.
39. Route-independent live Order/Fill reads, current Venue specification checks, temporary 1 oz/single-lifecycle controls, external position verification and definitive-failure-safe Bybit rollback.

## Active work

No engineering code workstream is active by default after PR #97 merges.

The next cross-spread scopes must remain separately bounded:

1. run controlled real-environment minimum-size acceptance under Issue #39, including Windows MT5 Terminal supervision and Venue permissions;
2. replace bounded Bybit fill polling with private WebSocket order/execution confirmation after operational acceptance;
3. implement real spread-limit entry, exit and limit TP/SL as a separate execution-engine scope;
4. integrate or refactor the retained large visual execution component only after the bounded lifecycle panel is operationally accepted.

Remaining responsive work must be evidence-driven rather than a full-platform CSS rewrite:

1. record concrete S0/S1 defects on representative non-homepage routes;
2. repair shared Application Shell or Page Shell behavior only when multiple pages prove the same root cause;
3. handle isolated S2/S3 page issues in bounded page-specific Issues;
4. add Playwright viewport screenshots and overflow/occlusion checks as a separate automation scope.

Before starting another code change:

1. verify current `main`, open Issues and open PRs;
2. reuse an Issue only when the outcome exactly matches;
3. create one matching task packet, Issue-numbered branch and open PR;
4. preserve the ownership boundaries recorded in `docs/architecture/OWNERSHIP.md` and the responsive architecture;
5. stop when the required change exceeds the task packet's expected files or protected semantics.

Separate non-code follow-ups remain:

- Issue #38: repository administrator verifies GitHub protection and merge settings.
- Issue #39: controlled real-environment operational acceptance; it is not an engineering refactor and does not run in CI.
- After Issue #39 contains mature repeated evidence, create a separate “temporary live restriction review” Issue before changing 1 oz, concurrency, Market-only or monitor defaults.

## Known constraints

- Existing table structures, Seed identifiers, financial formulas and trading state transitions are protected semantics.
- Operational projections remain supported and must not become formal-accounting inputs.
- Compatibility surfaces require usage evidence and a dedicated migration before removal.
- The current Bybit fill-confirmation loop is a bounded synchronous minimum implementation, not the final private-WebSocket architecture.
- One market open must map to exactly one MT5 Position Ticket; multiple matching hedging positions fail closed into manual intervention in this phase.
- The automatic TP/SL monitor is code-complete but disabled by default and still requires controlled-host operational enablement and observation.
- The retained legacy market/limit execution card is intentionally read-only during this phase; real market actions use the bounded lifecycle panel until the large component is safely refactored in a later scope.
- CI proves provider mapping, state transitions and safety behavior; it does not prove real Bybit/MT5 permissions, broker execution modes, Terminal stability or live liquidity.
- 1 oz, one non-closed lifecycle, Market-only execution and disabled automatic monitor are temporary acceptance restrictions; they may be reviewed only through the evidence and process in `docs/operations/V6-小资金实盘验收手册.md`.
- ACK/Fill separation, result-unknown no-blind-retry, independent Platform/Runtime write gates, exact close identity and secret isolation are permanent safety principles and must not be deleted with temporary limits.
- Inherited frontend lint debt remains outside untouched modules; new and changed files cannot add debt.
- The homepage responsive implementation is linted, type-checked and production-built, but automated multi-viewport screenshots are not yet part of CI.
- Existing non-homepage pages still contain unverified layout debt across viewport widths, heights and zoom levels.
- Desktop workstation use remains the primary target; mobile-first redesign is not part of the current responsive architecture.
- Pyright coverage is progressive rather than whole-repository strict.
- Live Write cannot be enabled by an engineering refactor or test result.
- GitHub repository-level branch protection/ruleset configuration must be verified by an administrator because it is not mutable through the available connector.

## Update rule

Replace stale facts when architecture, authority, safety defaults or a genuine active workstream changes. Do not append chat transcripts, long histories or speculative ideas. Detailed progress belongs in the matching task packet, Issue and PR.
