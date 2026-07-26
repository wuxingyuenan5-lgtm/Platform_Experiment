# Current Project State

Last updated: 2026-07-26  
Stable branch: `main`  
Product release: `0.8.0`  
Latest completed engineering scope: Issue #111 / PR #112  
Active engineering scope: Issue #113 / PR #114  
Latest product release scope: Issue #102 / PR #104

This file records compact operating truth. Always verify open Issues, PRs, commits and CI before assuming an active workstream is complete.

## Current release

Platform `0.8.0` remains the current coherent product release. Root `VERSION` is authoritative. Cross-spread work after the release is engineering progress and does not prove real Windows-host execution.

## Architecture

- `admin-risk/`: Vue product frontend.
- `platform-backend/`: modular-monolith business, risk, execution orchestration and accounting API.
- `execution-runtime/`: isolated Venue/Gateway process and Runtime Journal.
- SQLite remains approved for the current stage.
- Ownership: `docs/architecture/OWNERSHIP.md`.
- API: `docs/technical/API_SPEC.md`.
- Synthetic execution: `docs/technical/CROSS_SPREAD_SYNTHETIC_EXECUTION.md`.
- Operational acceptance: `docs/operations/V6-小资金实盘验收手册.md`.

## Safety defaults

```text
TradingMode=simulation
Gateway=fake
Platform Live Write=false
Runtime Live Write=false
Cross-spread Exit Monitor=false
Cross-spread acceptance max quantity=1 oz
Cross-spread non-closed lifecycle max=1
Cross-spread FOK hedge reserve=0 unless explicitly configured
Bybit PostOnly Chase=false
```

These values are not relaxed by code completion or CI. IOC remains unavailable. PostOnly Chase must remain disabled until controlled Issue #39 evidence exists.

## Permanent execution invariants

- Platform Backend does not import Venue SDKs.
- Platform and Runtime maintain independent Live Write gates.
- ACK does not equal Fill.
- `result_unknown` never authorizes blind retry, rollback or a second business intent.
- Platform Order, Bybit Order/Execution and MT5 Order/Deal/Position identities remain distinct.
- Synthetic action, execution type, Limit strategy and trigger reason remain separate.
- Limit input is a spread constraint, never an unvalidated fixed Bybit price.
- Buy Bybit/sell MT5 uses `Bybit Ask - MT5 Bid` with a maximum spread.
- Sell Bybit/buy MT5 uses `Bybit Bid - MT5 Ask` with a minimum spread.
- FOK and PostOnly hard pricing use non-negative Hedge Reserve and conservative Tick rounding.
- Non-executable Limit is rejected before Batch creation.
- Bybit Market/FOK/PostOnly must confirm real fill before MT5.
- FOK requires terminal exact full fill; zero, partial, mismatch and unknown outcomes are distinct.
- PostOnly requires exact cumulative full fill before entering the existing MT5 path.
- Duplicate private Execution events cannot duplicate cumulative fill or MT5 quantity.
- Private-stream disconnect, sequence fault, malformed payload or terminal disagreement stops Chase and requires reconciliation.
- Cancel/Repost requires terminal Cancel evidence and is bounded by TTL, threshold, cooldown and maximum mutations.
- MT5 quantity derives from actual Bybit Fill and current contract specification.
- Bybit Close uses `reduceOnly=true` and matching `positionIdx`.
- MT5 Close binds the intended Position Ticket.
- Open is healthy only after both target external positions are verified.
- Close is complete only after both target external positions are verified flat.
- Existing external exposure, unresolved Batch, manual intervention or non-closed Exit Plan blocks a new Open.
- Credentials and secrets never enter Git, Markdown, database responses, tests or logs.

## Completed Batch 3 contract

Exit Plans persist independent TP/SL execution modes and Limit strategies. Existing plans remain Market/Market and old Limit behavior defaults to FOK. Manual close, automatic TP and automatic SL use the same claimed-plan Close Action. Automatic Limit uses the atomic Claim's `triggerSpread`; it never silently falls through to Market.

The automatic exit monitor remains disabled by default.

## Batch 4 active contract

Issue #113 / PR #114 implements bounded Bybit PostOnly Chase as an internal Limit strategy:

```text
limitStrategy = fok | post_only_chase
Runtime executionPolicy = default | fok | post_only_chase
```

Current rules:

- FOK remains backward-compatible default.
- PostOnly Chase is disabled by default.
- Initial and amended Bybit prices remain maker-safe and inside the hard Bybit price bound.
- Private Order and Execution events are the primary state source after acknowledgement.
- Execution IDs are deduplicated and cumulative fill is monotonic.
- TTL, minimum amend Tick distance, maximum mutation count and cooldown bound all Chase activity.
- Amend is preferred; rejected Amend may enter Cancel/Repost only after terminal Cancel proof.
- Private stream disconnection or invalid state stops further Chase.
- Only exact cumulative full fill produces one normal Fill for the existing MT5 path.
- Partial or uncertain Bybit exposure remains explicit and blocks MT5.
- No IOC, no automatic safety-limit relaxation and no claim that CI proves real private-stream behavior.

PostOnly's hard Bybit bound is derived from the pre-submit MT5 reference quote. Chase currently follows the Bybit maker book without dynamically recomputing MT5 reference price. This limitation keeps PostOnly disabled pending controlled operational evidence.

## Frontend boundary

Batch 4 only extends the existing cross-spread trading execution area with FOK/PostOnly strategy selection and risk wording. It does not redesign the page, sidebar, navigation or visual system.

The former Batch 5 scope is not assigned to the trading execution page. It is now only a Markdown list of possible post-trade analysis/execution-review capabilities. The user will later decide whether to build it and where it belongs.

## Live read and observability invariants

- Current Order, Order History and Fill/Deal History are separate surfaces.
- Reads do not require a local Runtime Route; unproven records use `external_only`.
- Query failure is not a healthy empty list or zero value.
- Bybit liquidation is displayed only when Venue reports a positive finite value.
- MT5 per-position liquidation remains unavailable; account Margin Level, Call and Stop Out are authoritative.
- The observability panel remains read-only.

## Accounting and governance invariants

- Operational projections remain separate from FinancialFact-based formal accounting.
- Formal accounting rebuilds from immutable FinancialFacts.
- Venue conflicts create explicit Differences.
- EOD covers Order, Fill/Deal, Position, Balance/Risk, Funding, Swap, Fee, Formal PnL and NAV.
- Database changes use ordered migrations with immutable checksums.
- Behavioral or safety-sensitive work requires one Issue, task packet, branch and PR.
- CI and Secret Scan are mandatory.
- GitHub PR/main history owns merge identity; no second metadata PR is created solely for merge SHA.

## Completed engineering baseline

Completed scopes include architecture boundaries, database governance, formal accounting, Venue/EOD reconciliation, command idempotency, live account observability, protected Market execution, route-independent Venue reads, Market lifecycle, synthetic intent, manual FOK Open/Close, and TP/SL execution-mode persistence with one unified Close Action.

## Current work

1. Complete and merge Issue #113 / PR #114.
2. Do not start the former Batch 5. Keep its possible Quote Age, time-skew, Bid/Ask, Deviation, unhedged-duration, realized-spread and fee-review fields in Markdown only until the user decides product scope and placement.

## Operational work

Issue #39 remains the controlled Windows-host acceptance workstream. It must prove real credentials, permissions, symbols, Tick/Step, Broker Hedge Reserve, REST/private-stream behavior, Terminal stability, Market/FOK/PostOnly/automatic-exit cycles, recovery, Kill Switch and clean EOD reconciliation.

## Known constraints

- One successful Open maps to one MT5 Position Ticket; ambiguity fails closed.
- Real Venue Tick consistency and Hedge Reserve remain operational evidence.
- PostOnly private WebSocket wiring and Pybit behavior require real Windows-host evidence.
- PostOnly does not yet dynamically reprice from an updated MT5 quote during Chase.
- CI proves contracts and state transitions, not real liquidity or broker behavior.
- Live Write cannot be enabled by a refactor, migration, merge or test result.

## Update rule

Replace stale operating facts. Detailed progress belongs in the matching task packet, Issue and PR, not in chat transcripts.
