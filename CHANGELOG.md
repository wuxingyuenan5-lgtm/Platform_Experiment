# Changelog

## Unreleased

### Execution risk controls and Kill Switch — Phase 4A

- Added global, strategy, and account Kill Switches with idempotent writes, payload-conflict detection, versioning, actor/reason metadata, and AuditEvent records.
- Added Kill Switch checks before ExecutionBatch claim and before every Batch Leg, returning `423 Locked` before new TradeCommand or Runtime side effects.
- Added per-Strategy execution-risk policies for maximum leg delay, maximum residual notional, and failure action.
- Added immutable per-Batch risk-policy snapshots so later policy changes do not rewrite historical execution boundaries.
- Added Batch risk states: `clear`, `residual_exposure`, `disposition_in_progress`, `resolved`, and `escalated`.
- Added first-fill and last-leg timestamps and enforced maximum leg delay before the next Leg is submitted.
- Added residual-exposure calculation using Fill Quantity, Fill Price, Contract Multiplier, side, and Settlement Currency.
- Added conservative `MIXED / incomplete` handling for multi-currency exposure without a risk FX snapshot.
- Changed normal Batch completion so `hedged` requires both Legs completed and a complete zero-residual risk result.
- Added idempotent RiskActions: `hold_and_escalate`, `flatten_filled_legs`, `cancel_open_legs`, and `substitute_hedge`.
- Routed automatic flattening and substitute hedges through authoritative TradeCommand rather than direct Order insertion.
- Preserved `action_required` for external Orders that cannot yet be canceled through Venue APIs; Phase 4A does not pretend local state changes canceled an external Order.
- Added golden tests for pre-claim Kill Switch blocking, residual-notional limits, automatic flattening, Position returning to zero, RiskAction replay/conflict, and leg-deadline enforcement.
- Expanded Platform CI strict gates to include `execution_risk.py` and `test_execution_risk.py`.
- Added `docs/planning/V6-Phase4A-执行风险与Kill-Switch.md` and `docs/technical/EXECUTION_RISK_CONTROLS.md`.
- Synchronized the V6 plan, API Specification, Release Gate, README, START-HERE, Issue #14, PR #15, and this Changelog.
- Retained Simulation / Fake Gateway only; external Venue query/cancel, Bybit Demo, MT5 Demo, daily reconciliation, authentication, and Live remain deferred to Phase 4B–4D or later review.

### Immutable financial facts and formal accounting — Phase 3

- Added immutable `financial_facts` with client idempotency keys, external fact identities, normalized payload hashes, event time, source metadata, and explicit data quality.
- Rejected reuse of a FinancialFact identity with a different normalized payload using `409 Conflict`.
- Derived Trade Fact settlement currency, quantity unit, and contract multiplier from the backend Instrument Catalog rather than accepting client overrides.
- Added rebuildable `formal_positions` and `formal_pnl_results` projections.
- Separated Trading, Funding, Swap, Fee, FX, and Total PnL.
- Included Contract Multiplier and explicit FX conversion in the formal Trading PnL boundary.
- Preserved cross-currency facts with `incomplete` quality when FX is missing instead of silently using a 1:1 rate.
- Added `formal_strategy_nav_snapshots` using one valuation time across all active strategy-account bindings.
- Added required/included account counts and `missingAccountIds` so incomplete NAV coverage cannot be presented as complete.
- Added FinancialFact ingestion/listing, formal projection rebuild, formal Position/PnL, and formal NAV APIs.
- Added audit events for fact ingestion, projection rebuild, and formal NAV creation.
- Added golden tests for duplicate facts, payload conflicts, Contract Multiplier PnL, component attribution, projection rebuild, missing FX, and multi-account NAV completeness.
- Split the Platform Backend composition root from the existing business routes so the Phase 3 router can be added without rewriting the established Phase 1–2 endpoints.
- Expanded Platform CI strict gates to include the Phase 3 module, tests, composition root, and `docs/technical/**`.
- Added `docs/planning/V6-Phase3-金融事实与正式账务.md` and `docs/technical/FINANCIAL_FACTS.md`.
- Synchronized the overall V6 plan, API Specification, Release Gate, README, START-HERE, Issue #7, PR #9, and this Changelog.
- Completed Platform CI `#127 / run 29993137286`: Platform Backend, Execution Runtime, frontend type-check, and production build all passed.
- Merged Phase 3 to `main@77bf4223c2059d5a56fc08a2d49214351c396abc` through PR #9.
- Retained Simulation / Fake Gateway only; external venue ingestion, residual-leg risk handling, authentication, and Live remained deferred.

### Product surface cleanup

- Removed the explanatory redirect paragraph from the login card so the page contains only identity, authentication, and registration actions required by the user.
- Removed the now-unused login subhead styles and preserved the existing redirect behavior in code.
- Restored the product-surface rule in the root README: implementation explanations, redirect mechanics, integration notes, and other nonessential auxiliary copy belong in Markdown rather than the primary product interface.

### Command authority and recovery — Phase 2

- Added `platform-backend/app/trade_commands.py` as the authoritative TradeCommand service.
- Required active closed-loop StrategyInstance, active StrategyAccountBinding, active Account, Instrument, and ContractSpecification before creating a TradeCommand.
- Made TradeCommand creation atomically idempotent through the unique client-provided `idempotencyKey`.
- Rejected reuse of a TradeCommand idempotency key with a different Strategy, Account, Instrument, side, order type, quantity, or price.
- Required every ExecutionBatch to provide `strategyInstanceId` and `idempotencyKey`.
- Changed ExecutionBatch legs to create deterministic TradeCommands using `<batch-key>:<role>` rather than bypassing the command layer.
- Rejected reuse of an ExecutionBatch idempotency key with a different batch or leg payload.
- Added full-leg Catalog validation before the first leg executes, reducing preventable residual-exposure failures.
- Marked direct `POST /api/v1/trading/orders` as a deprecated compatibility endpoint.
- Added `POST /api/v1/trading/orders/{orderId}/reconcile` to recover `result_unknown` orders from Runtime Journal without resubmitting the order.
- Added Runtime event identity validation for `command_id` and `platform_order_id`.
- Made Fill replay idempotent: duplicate event IDs no longer update Position, EconomicEvent, or PnL twice.
- Added tests for successful unknown-result recovery, unavailable-Runtime behavior, fill replay, authoritative per-leg commands, repeated batch requests, and idempotency payload conflicts.
- Replaced funding execution panel demo UUID mappings with dynamic Strategy, Binding, Account, Instrument, and ContractSpecification Catalog queries.
- Disabled unsupported assets and incomplete Catalog configurations with explicit frontend messages; missing Position/PnL now displays unknown rather than zero.
- Updated the platform smoke script to use TradeCommand, ExecutionBatch idempotency, StrategyInstance, and authoritative Catalog IDs.
- Added `docs/planning/V6-Phase2-命令入口与结果恢复.md` and Issue #4 / PR #5 as the Phase 2 delivery trail.
- Updated README, START-HERE, API Specification, Release Gate, overall V6 plan, CI strict gates, and this Changelog.
- Added authoritative Markdown paths to Platform CI so engineering documentation changes are validated with the codebase.
- Completed Platform CI run `29986397987`: Platform Backend, Execution Runtime, frontend strategy type-check, and production build all passed.
- Explicitly retained Simulation / Fake Gateway as the only allowed execution mode; real Bybit/MT5, formal PnL/NAV, and automatic residual-leg risk handling remained deferred.

### Trading safety hardening — Phase 1

- Established `main@76effbff6391533db7b9954965aaf1b09051081f` as the V6 engineering baseline.
- Added `docs/planning/V6-交易安全加固实施计划.md`, Pull Request #3, and GitHub Issue #2 as the authoritative delivery trail.
- Changed order validation to fail closed for unknown accounts, inactive accounts, unknown instruments, missing contract specifications, invalid quantity steps, and invalid price ticks.
- Preserved the global Live trading switch and strengthened the safety policy to require every account to be active before submission.
- Replaced the Runtime check-then-insert command flow with an atomic database claim before any Gateway side effect.
- Added tests proving duplicate Runtime commands reuse persisted events and do not call the Gateway twice.
- Added backend tests for unknown accounts, unknown instruments, contract quantity validation, and catalog-authoritative execution batches.
- Split Windows-only MetaTrader5 and Crypto gateway packages into optional Runtime dependencies so core Linux CI remains reproducible.
- Expanded GitHub Actions to cover `main`, hardening branches, and pull requests into `main`.
- Aligned frontend CI and the lockfile on `pnpm@9.15.9`, disabled Husky installation in CI, and retained failure artifacts for dependency and type-check diagnostics.
- Added the `/@/* -> src/*` TypeScript path mapping so Vite imports resolve under `vue-tsc`.
- Upgraded frontend CI from type checking only to frozen-lockfile installation, strategy type checking, and a production build.
- Completed Platform CI run `29983926790`: Platform Backend, Execution Runtime, frontend type-check, and frontend production build all passed.
- Updated the root README, START-HERE, V6 release gate, implementation plan, and this Changelog so code, tests, operational limits, and Markdown documentation use the same baseline.

### Previous V6 workspace changes

- Standardized local development around frontend port `5173` and platform backend `/api/v1`.
- Removed backend/debug UI panels from strategy product pages.
- Restored the start page to the dark star-map Variable Global landing screen, removed legacy top-right labels `平台入口` / `研究框架` / `新闻日历`, renamed `金融AI` to `金融AI分析`, and routed protected start-page clicks through `/login?redirect=...`.
- Increased the logged-in top navigation font size to 16px with regular 400 weight, and added functional icons for `首页`, `新闻日历与理财`, `风控管理`, and `金融AI分析`.
- Adjusted the public start-page entry cards to match the larger icon and serif-title treatment in the reference landing layout.
- Restored `#/home/index` as the logged-in Home Dashboard: butterfly-water topology hero background, right-side market/portfolio summaries, and four product cards for market pulse, portfolio, strategy, and calendar.
- Refined the Home Dashboard hero so the butterfly-water topology uses the high-resolution original-color asset as a controlled local visual layer without baked-in legacy text, and softened dashboard typography to match the reference layout.
- Changed the Home Dashboard hero to use one continuous butterfly-water image across the full top area, with summary cards floating over it and the four dashboard modules pulled upward into the hero edge.
- Started non-destructive project folder reorganization.
- Added `.ignore` and expanded `.gitignore` to reduce Codex/search noise from dependencies, virtual environments, build outputs, generated files, and large reference code.
- Moved root SQL reference files into `references/database/` without deleting source material.
- Moved the large `参考代码/` reference-code directory out of the project root to `C:\Users\jiuxi\Desktop\codex\平台设计其他辅助内容\平台移动文件夹，例如参考代码等\参考代码`.