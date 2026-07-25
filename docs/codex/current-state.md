# Current Project State

Last updated: 2026-07-26  
Stable branch: `main`  
Product release: `0.8.0`  
Latest completed engineering scope: Issue #109 / PR #110  
Latest completed documentation scope: Issue #100 / PR #101  
Latest product release scope: Issue #102 / PR #104

This file is the compact cross-session handoff. It records current operating truth, not a PR diary. Read the actual open Issues and PRs before assuming a workstream is active.

## Current release

Platform `0.8.0` is the current coherent product release. Root `VERSION` is authoritative; Platform Backend, Execution Runtime and the frontend displayed version must match it. Release notes are in `docs/releases/0.8.0.md`.

The release records engineering completion through live account observability. Later cross-spread execution work is code-level engineering progress and does not prove real Windows-host Bybit/MT5 credentials, permissions, broker fields, Terminal stability, history retention or execution behavior; those remain Issue #39 operational evidence.

## Current architecture

- `admin-risk/`: Vue product frontend.
- `platform-backend/`: modular-monolith business, risk, execution orchestration and accounting API.
- `execution-runtime/`: isolated Venue/Gateway process and Runtime Journal.
- SQLite remains the approved persistence technology for the current stage.
- Major authority boundaries are canonical in `docs/architecture/OWNERSHIP.md`.
- Runtime/Platform APIs are documented in `docs/technical/API_SPEC.md`.
- Synthetic cross-spread action/execution/trigger semantics and phased Limit roadmap are canonical in `docs/technical/CROSS_SPREAD_SYNTHETIC_EXECUTION.md`.
- Live Venue and account observability semantics are canonical in `docs/technical/LIVE_ACCOUNT_OBSERVABILITY.md`.
- Small-capital operational acceptance is canonical in `docs/operations/V6-小资金实盘验收手册.md`.

## Safety defaults

```text
TradingMode=simulation
Gateway=fake
Platform Live Write=false
Runtime Live Write=false
Cross-spread Exit Monitor=false
Cross-spread acceptance max quantity=1 oz
Cross-spread non-closed lifecycle max=1
Cross-spread FOK hedge reserve=0 price units unless explicitly configured
```

The 1 oz, one-lifecycle, disabled-monitor and Market/FOK-only controls are temporary acceptance restrictions. PostOnly, chase and IOC remain unavailable. These restrictions are not automatically removed after one successful test; their evidence and review process are defined in the operational acceptance manual.

## Permanent execution invariants

- Platform Backend does not import Venue SDKs; external effects remain in `execution-runtime/`.
- `platform-backend/app/main.py` and `execution-runtime/app/main.py` remain composition/routing roots rather than domain owners.
- Platform and Runtime maintain independent Live Write gates.
- ACK does not equal Fill.
- `result_unknown` never authorizes blind retry, rollback or a second business intent.
- Platform Order, Bybit Order/Execution and MT5 Order/Deal/Position identities remain distinct and traceable.
- Synthetic business action, execution type and trigger reason are separate concepts.
- Business actions are `OPEN_LONG_SPREAD`, `CLOSE_LONG_SPREAD`, `OPEN_SHORT_SPREAD` and `CLOSE_SHORT_SPREAD`.
- Execution types are `MARKET` and `LIMIT`; TP/SL are trigger reasons that submit ordinary close actions.
- A Limit request never silently falls through to Market.
- Limit input is a spread constraint, not an unvalidated fixed Bybit price.
- Buy-Bybit/sell-MT5 uses `Bybit Ask - MT5 Bid` with a maximum spread.
- Sell-Bybit/buy-MT5 uses `Bybit Bid - MT5 Ask` with a minimum spread.
- FOK pricing applies a non-negative configured MT5 hedge reserve and conservative Tick rounding.
- A non-executable FOK spread is rejected before Batch creation or Venue submission.
- Bybit Market execution is terminal-fill confirmed before MT5 hedge submission.
- Cross-spread Bybit Limit uses FOK and requires terminal exact full fill before MT5 hedge submission.
- FOK zero fill submits no MT5; a clean manual-close no-fill restores the exit plan to `active`.
- FOK partial, quantity-mismatch, timeout or unknown outcome does not create a normal hedge-driving Fill and requires reconciliation/manual intervention.
- MT5 hedge quantity derives from actual Bybit fill and current MT5 contract size/minimum/step.
- Bybit Close uses `reduceOnly=true` and the matching live `positionIdx`.
- MT5 Close binds the intended Position Ticket and rejects side, quantity, symbol or ticket ambiguity.
- A new cross-spread Open is blocked by existing external exposure, unresolved Batch, manual intervention or a non-closed Exit Plan.
- An Open becomes healthy only after both external positions are verified.
- A Close becomes complete only after both target external positions are verified flat.
- MT5 definitive rejection/failure may permit one idempotent Bybit rollback after external-position proof; MT5 accepted/processing/unknown never does.
- LONG_SPREAD exits observe `Bybit Bid - MT5 Ask`; SHORT_SPREAD exits observe `Bybit Ask - MT5 Bid`.
- Automatic TP/SL remains Market-executed until a later batch stores explicit exit execution methods.
- The automatic exit monitor remains a separate disabled-by-default capability.
- Credentials, passwords and API secrets never enter Git, Markdown, database responses, tests or logs.

## Live read and observability invariants

- Runtime Order/Fill reads do not depend on a local Route. External records without a proven Platform route use `dataQualityState=external_only`.
- Current-order reads, closed-order history and Fill/Deal history are separate surfaces.
- History queries require an explicit bounded window; one Runtime request cannot exceed seven days or 100 records per page.
- Bybit history uses Venue cursor continuation.
- MT5 history uses deterministic offset continuation inside a fixed account/symbol/time window.
- Query failure is not a healthy empty list, zero balance or zero position.
- Per-section aggregate states distinguish `complete`, `partial` and `unavailable`.
- Bybit position liquidation price is displayed only when the Venue reports a positive finite `liqPrice`.
- MT5 Python Position data has no authoritative per-position liquidation price. Canonical responses keep it null and use Account Margin Level, Margin Call and Stop Out evidence.
- Bybit UTA account risk exposes Venue-reported equity, available balance, IM/MM and account IM/MM rates when available.
- MT5 account risk exposes Balance, Equity, Profit, used/free Margin, Margin Level, `margin_so_call`, `margin_so_so` and `margin_so_mode`.
- The frontend observability panel is read-only and has no Order, Cancel or Position-modification control.
- The transaction lifecycle panel supports Market and manual FOK Limit, while preserving the 1 oz acceptance default.

## Accounting, reconciliation and ownership invariants

- Operational `positions` and `pnl_results` remain separate from FinancialFact-based formal accounting.
- Formal accounting is rebuilt from immutable FinancialFacts and does not use operational projections as calculation inputs.
- Operational and formal projections share the exact `position_math.calculate_position_update` callable.
- Venue Reconciliation external conflicts produce explicit Differences; they are not silently overwritten.
- EOD Reconciliation covers Order, Fill/Deal, Position, Balance/Account Risk, Funding, Swap, Fee, FinancialFact, Formal PnL and Formal NAV.
- Database changes use an ordered migration ledger with immutable checksums.
- Platform–Runtime command/event traffic uses explicit V1 contracts and snapshots.
- Every Backend and Runtime test has exactly one primary taxonomy marker.
- Ownership changes update `docs/architecture/OWNERSHIP.md` in the same PR.

## Workstream governance

- Behavioral, safety-sensitive, cross-module or otherwise ambiguous work uses the full engineering track: one Issue, one task packet, one Issue-numbered branch and one linked PR.
- Bounded non-behavioral Markdown and synchronized product-version maintenance may use one lightweight PR with `Maintenance: true`, `Behavior change: none` and `Safety change: none`.
- Maintenance mode is machine-limited to Markdown and the four maintained version declarations; source, runtime configuration, workflows, database, contracts, migrations, credentials and safety defaults require the full engineering track.
- CI and Secret Scan remain mandatory in both tracks.
- GitHub PR/main history owns merge identity. Do not create a second Issue or PR solely to record a merge SHA.
- The canonical workflow is `docs/engineering/GIT_WORKFLOW.md`.

## Completed engineering baseline

Completed scopes include:

1. architecture/module boundary cleanup and whole-directory quality gates;
2. database connection, bootstrap, seed and migration ownership;
3. FinancialFact normalization, persistence and formal Position/PnL/NAV projection;
4. Venue and EOD Reconciliation schema/policy/repository/service extraction;
5. unified Platform order submission and Runtime command idempotency;
6. responsive-layout architecture and homepage-first remediation;
7. Bybit terminal-fill-confirmed market execution with actual-fill MT5 hedge sizing;
8. market-only cross-spread lifecycle, reduce-only/ticket-bound close and executable-spread TP/SL;
9. route-independent Order/Fill reads, current Venue specification checks, temporary 1 oz/single-lifecycle controls, external position verification and definitive-failure-safe Bybit rollback;
10. bounded Order/Fill history, rich Order diagnostics, Bybit liquidation evidence, MT5 Margin Call/Stop Out evidence, section-aware two-Venue aggregation and a read-only acceptance dashboard;
11. coherent Platform `0.8.0` release declarations and release documentation;
12. normalized cross-spread synthetic action/execution/trigger intent with unchanged Market execution;
13. manual Open/Close FOK spread-limit execution with two-direction pricing, conservative Tick rounding, exact-full-fill gating, clean no-fill recovery and abnormal-outcome fail-closed behavior.

Detailed implementation history belongs in merged Issues, PRs and task packets rather than this file.

## Next engineering work before local live acceptance

The transaction page still needs the remaining bounded batches from `CROSS_SPREAD_SYNTHETIC_EXECUTION.md`:

1. store TP and SL execution methods on exit plans so manual close and automatic exits use the same Market/FOK Close Action;
2. Bybit private Order/Execution WebSocket plus PostOnly chase, amend/cancel race handling and partial-fill repair;
3. quote-age, bid/ask-width, MT5 deviation, unhedged-duration, realized-spread and fee-quality protections/analytics;
4. final transaction-page consolidation so trigger, external identities and execution quality are visible in one workflow.

Each batch must remain independently testable. Existing Market and FOK semantics are not redesigned by later PostOnly work.

## Operational work after the core execution batches

Issue #39 remains the controlled Windows-host real-environment acceptance workstream. After the core execution batches are code-complete, it must validate:

1. real Bybit and MT5 credentials, permissions, account IDs and symbol mappings;
2. current and historical Order/Fill/Deal reads against native Venue interfaces;
3. real Bybit liquidation fields and MT5 Margin Call/Stop Out fields;
4. Runtime and Terminal restart, Route Store loss, timeout and network interruption behavior;
5. Platform Contract `priceTick` against the real Bybit Instrument Tick and quantity Step;
6. evidence-based `VG_CROSS_SPREAD_LIMIT_HEDGE_RESERVE_PRICE` for the selected MT5 Broker;
7. repeated supervised 1 oz Market Open/Close cycles in both directions;
8. supervised 1 oz FOK Limit full-fill, zero-fill and abnormal-outcome cycles before any PostOnly chase test;
9. external Position verification, rollback/manual takeover and Kill Switch behavior;
10. Funding, Swap, fee and end-of-day reconciliation without unexplained Differences.

The Windows-host phase is expected to require environment-specific configuration and bounded defect correction, not redesign of the synthetic action, FOK state, history, risk or observability contracts.

## Separately bounded future work

- Real IOC partial-fill execution after minimum-unit evidence.
- Retained large execution-component refactor only after the bounded panels are operationally accepted.
- Temporary restriction review only after Issue #39 contains mature repeated evidence.
- Repository branch-protection/ruleset verification by an administrator.

## Known constraints

- Existing financial formulas, protected state transitions, Seed identifiers and compatibility surfaces require dedicated migration evidence before change or removal.
- One successful Open currently maps to one MT5 Position Ticket; ambiguous multi-position cases fail closed.
- Bybit Market/FOK fill confirmation currently uses bounded REST polling, not the final private-WebSocket architecture.
- FOK uses the versioned Platform Contract Tick at submission; real Venue consistency is an operational acceptance requirement.
- Hedge Reserve defaults to zero and must not be represented as proven broker slippage protection before controlled-host evidence.
- The automatic TP/SL monitor is code-complete but disabled and remains Market-only until the next execution-method batch.
- CI proves contracts, mappings, state transitions and safety behavior; it does not prove real Bybit/MT5 permissions, broker execution mode, Terminal stability, liquidity, Tick consistency, history retention or final field availability.
- Inherited frontend debt remains outside untouched modules; changed files may not add debt.
- Desktop workstation use remains the primary frontend target.
- Pyright coverage remains progressive rather than whole-repository strict.
- Live Write cannot be enabled by an engineering refactor, version bump or test result.

## Update rule

Replace stale facts when architecture, authority, safety defaults, product release or genuine workflow governance changes. Do not append chat transcripts or speculative plans. Detailed engineering progress belongs in the matching task packet, Issue and PR; lightweight maintenance has no task packet.
