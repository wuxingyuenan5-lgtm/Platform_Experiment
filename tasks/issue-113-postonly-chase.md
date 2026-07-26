# Task: Bounded Bybit PostOnly Chase

Issue: #113
Status: done
Branch: `feature/issue-113-postonly-chase`
Base commit: `a254109cdeea7a53a8095ea2bbca20282e16c300`

## Objective

Implement a bounded Bybit PostOnly Chase main-leg strategy driven by private Order and Execution events, while preserving the existing four synthetic actions and MT5 actual-fill hedge rules.

## Protected semantics

- PostOnly Chase is an internal LIMIT strategy, not a fifth business action.
- Existing Market and FOK behavior remains unchanged.
- Bybit remains the main leg; MT5 remains the following Market hedge/close leg.
- MT5 quantity is never based on requested Bybit quantity.
- Duplicate, out-of-order or replayed private events cannot duplicate MT5 hedge quantity.
- Reduce-only, positionIdx, MT5 Position Ticket, external-position verification, rollback and reconciliation remain authoritative.
- Live Write, exit monitor, PostOnly enablement, 1 oz and single-lifecycle defaults remain unchanged.

## Limit strategy contract

- `limitStrategy=fok` remains the backward-compatible default.
- `limitStrategy=post_only_chase` selects bounded Chase.
- TP and SL persist their own Limit strategy when their execution mode is Limit.
- A PostOnly command carries one hard Bybit price bound derived from the user spread limit.
- Runtime chooses maker-safe initial and amended Bybit prices without crossing that hard bound.
- Runtime does not silently convert PostOnly to FOK, Market or IOC.

## Chase policy

- disabled by default;
- explicit TTL;
- minimum amend distance in Tick units;
- maximum amend/repost count;
- cooldown between mutations;
- one active child order identity at a time;
- amend when safe;
- cancel/repost only after terminal cancel proof;
- private-stream disconnect or invalid event state stops Chase;
- no unbounded loop.

## Private event contract

- Private Order and Execution events have stable identities.
- Execution identity is deduplicated.
- Cumulative fill is monotonic and cannot exceed requested quantity.
- Sequence regression, sequence gap, disconnect, malformed payload, unexpected child identity or REST disagreement stops Chase and requires reconciliation.
- Fill/cancel and fill/amend races are resolved by cumulative execution evidence plus final bounded Venue reconciliation.

## Partial fill contract

- Newly confirmed Bybit fill delta is calculated exactly.
- The same fill delta is never counted twice.
- Full requested quantity emits one normal cumulative Fill for the existing MT5 path.
- Partial fill does not masquerade as full completion.
- Current first release stops automatic Chase and MT5 submission on partial/uncertain exposure.
- Below-minimum, off-step or otherwise unresolved residual remains explicit manual-intervention/compensation evidence.
- Automatic incremental MT5 partial hedging is not claimed by this batch.

## Actual scope

- pure Chase state machine and policy validation;
- private Order/Execution DTOs, parser, prefix filtering and deduplication;
- injectable event source plus disabled-by-default Pybit private-stream wiring;
- private-stream connection health and malformed-payload failure evidence;
- bounded place/amend/cancel/repost orchestration;
- Runtime `execution_policy` contract and Bybit adapter support;
- Platform Limit strategy request, persistence and Batch construction;
- TP/SL independent Limit strategy persistence;
- additive migration v4 with FOK/default compatibility;
- frontend FOK/PostOnly selection inside the existing transaction area;
- race, duplicate, disconnect, partial-fill, migration and regression tests;
- ownership, current-state, API, database, synthetic-execution and operations documentation.

## Non-goals

- No IOC.
- No dynamic MT5 reference-price recomputation during Chase.
- No Quote Age, cross-Venue time skew, Bid/Ask width, MT5 deviation, unhedged-duration, realized-spread or fee analytics/protections.
- No post-trade analysis panel or assumed frontend placement for the deferred analysis scope.
- No safety-limit relaxation.
- No claim that CI proves real Bybit private WebSocket behavior.

## Acceptance criteria

- [x] Pure state machine is deterministic and bounded.
- [x] Stable event deduplication prevents duplicate fill deltas.
- [x] Disconnect/gap/unknown state blocks further automatic Chase.
- [x] Amend/cancel/repost never exceeds policy or hard price bound.
- [x] Cancel/fill and amend/fill races fail safely.
- [x] Exact full fill enters the existing MT5 hedge path once.
- [x] Partial/invalid residual exposure is explicit and fail-closed.
- [x] FOK remains the default Limit strategy and existing behavior is unchanged.
- [x] PostOnly Chase remains disabled by default.
- [x] TP/SL and manual Close persist/select FOK or PostOnly through the unified Close Action.
- [x] Backend, Runtime, frontend, Repository Safety and Secret Scan pass.
- [x] Deferred post-trade analysis remains Markdown-only with no transaction-page implementation.

## Risk and rollback

Risk: high

- Primary risks: duplicate hedge quantity, stale child identity, unbounded mutation, private-stream uncertainty, Cancel/Fill race and partial Bybit exposure.
- Detection: pure state tests, adapter tests, private-stream tests, Platform strategy/migration tests and full repository gates.
- Rollback: revert the squash merge. Migration v4 is additive; applied migration history is not edited, so a forward fix may be required for databases that already applied it.

## Completion

- PR: #114
- Merge commit: GitHub PR/main history is authoritative; no post-merge metadata PR will be created.
- Behavior changed: added disabled-by-default PostOnly Chase, execution-policy propagation, stored TP/SL Limit strategies and existing-page strategy selection.
- Behavior intentionally unchanged: Market/FOK execution, four synthetic actions, Live Write, exit monitor, acceptance quantity and single-lifecycle controls.
- Tests/CI: Platform CI #1657 and Secret Scan #895 passed on the completed code/documentation head; the final task-metadata head must repeat repository gates.
- Operational evidence not produced: real credentials, Private WebSocket stability, Venue Tick/Step, liquidity, Broker behavior and Windows Terminal execution remain Issue #39.
- Follow-up: the former Batch 5 is only a Markdown list of possible post-trade analysis/execution-review fields. Development and product placement require a later user decision.
