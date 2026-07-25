# Current Project State

Last updated: 2026-07-26  
Stable branch: `main`  
Product release: `0.8.0`  
Latest completed engineering scope: Issue #109 / PR #110  
Active engineering scope: Issue #111 / PR #112  
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
```

These values are not relaxed by code completion or CI. PostOnly, Chase and IOC remain unavailable until their dedicated engineering and operational evidence exist.

## Permanent execution invariants

- Platform Backend does not import Venue SDKs.
- Platform and Runtime maintain independent Live Write gates.
- ACK does not equal Fill.
- `result_unknown` never authorizes blind retry, rollback or a second business intent.
- Platform Order, Bybit Order/Execution and MT5 Order/Deal/Position identities remain distinct.
- Synthetic action, execution type and trigger reason remain separate.
- Limit input is a spread constraint, never an unvalidated fixed Bybit price.
- Buy Bybit/sell MT5 uses `Bybit Ask - MT5 Bid` with a maximum spread.
- Sell Bybit/buy MT5 uses `Bybit Bid - MT5 Ask` with a minimum spread.
- FOK pricing applies non-negative Hedge Reserve and conservative Tick rounding.
- Non-executable FOK is rejected before Batch creation.
- Bybit Market/FOK must confirm real fill before MT5.
- FOK requires terminal exact full fill; zero, partial, mismatch and unknown outcomes are distinct.
- MT5 quantity derives from actual Bybit Fill and current contract specification.
- Bybit Close uses `reduceOnly=true` and matching `positionIdx`.
- MT5 Close binds the intended Position Ticket.
- Open is healthy only after both target external positions are verified.
- Close is complete only after both target external positions are verified flat.
- Existing external exposure, unresolved Batch, manual intervention or non-closed Exit Plan blocks a new Open.
- Credentials and secrets never enter Git, Markdown, database responses, tests or logs.

## Batch 3 active contract

Issue #111 / PR #112 adds Exit Plan persistence for:

```text
takeProfitExecutionMode = market | limit
stopLossExecutionMode   = market | limit
```

Current rules:

- Migration v3 adds both fields with `market / market` defaults.
- Existing plans retain data and become Market/Market.
- New Open requests default Market/Market when fields are omitted.
- TP and SL can be selected independently.
- Stop Loss remains Market by default.
- Manual close, automatic TP and automatic SL use the same claimed-plan Close Action.
- Automatic FOK uses the atomic Claim's `triggerSpread` as `limitSpread`.
- Limit never falls through to Market.
- Pre-submit quote movement or clean FOK zero-fill releases the Claim back to `active`.
- Partial, mismatch, timeout or unknown outcomes do not release the Claim and require reconciliation/manual intervention.
- FOK Close idempotency includes `planId + triggeredAt`, allowing a new attempt after a clean released Claim without duplicating one Claim.

The automatic monitor remains disabled by default even after this code is merged.

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

Completed scopes include architecture boundaries, database governance, formal accounting, Venue/EOD reconciliation, command idempotency, live account observability, protected Market execution, route-independent Venue reads, Market lifecycle, synthetic intent, and manual FOK Open/Close with conservative pricing and exact-full-fill gating.

## Next work

1. Complete and merge Issue #111 / PR #112.
2. Execute Batch 4 as a separate Issue/branch/PR from the merged Batch 3 main:
   - Bybit private Order and Execution event consumption;
   - PostOnly create/amend/cancel race state machine;
   - bounded automatic/manual Chase;
   - TTL, threshold, maximum attempts and cooldown;
   - partial-fill exact MT5 mapping or Bybit compensation.
3. Batch 5 is explicitly deferred by the user for later discussion. Quote Age, cross-Venue time skew, bid/ask width, MT5 deviation, unhedged duration, realized-spread variance and fee-quality analytics must not be mixed into Batch 4.

## Operational work

Issue #39 remains the controlled Windows-host acceptance workstream. It must prove real credentials, permissions, symbols, Tick/Step, Broker Hedge Reserve, REST/private-stream behavior, Terminal stability, Market/FOK/automatic-exit cycles, recovery, Kill Switch and clean EOD reconciliation.

## Known constraints

- One successful Open maps to one MT5 Position Ticket; ambiguity fails closed.
- Bybit Market/FOK confirmation currently uses bounded REST polling until Batch 4 is merged.
- Real Venue Tick consistency and Hedge Reserve remain operational evidence.
- CI proves contracts and state transitions, not real liquidity or broker behavior.
- Live Write cannot be enabled by a refactor, migration, merge or test result.

## Update rule

Replace stale operating facts. Detailed progress belongs in the matching task packet, Issue and PR, not in chat transcripts.
