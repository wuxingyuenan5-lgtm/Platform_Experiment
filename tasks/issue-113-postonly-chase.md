# Task: Bounded Bybit PostOnly Chase

Issue: #113
Status: active
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
- Live Write, exit monitor, 1 oz and single-lifecycle defaults remain unchanged.

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
- one active external order identity;
- amend when the active order is amendable;
- cancel/repost only after terminal cancel proof;
- manual cancel stops further automatic mutations;
- no unbounded loop.

## Private event contract

- Private Order and Execution events have stable identities.
- Execution identity is deduplicated.
- Cumulative fill is monotonic and cannot exceed requested quantity.
- Sequence regression, sequence gap, disconnect, malformed payload or REST disagreement stops Chase and requires reconciliation.
- Fill/cancel and fill/amend races are resolved by cumulative execution evidence plus final bounded Venue reconciliation.

## Partial fill contract

- Newly confirmed Bybit fill delta is calculated exactly.
- The same fill delta is never emitted twice.
- Full requested quantity emits one normal cumulative Fill for the existing MT5 path.
- Partial fill does not masquerade as full completion.
- Exact valid incremental MT5 mapping is calculated and exposed for policy/testing.
- A below-minimum or off-step residual remains explicit manual-intervention/compensation evidence.

## Expected scope

- pure Chase state machine and policy validation;
- private Order/Execution event DTOs, parser and deduplication;
- injectable event source plus disabled-by-default Pybit private-stream wiring;
- bounded place/amend/cancel/repost orchestration;
- Runtime command contract and Bybit adapter support;
- Platform Limit strategy request/persistence/batch construction;
- frontend strategy selection and Chase evidence;
- race, duplicate, disconnect, partial-fill and regression tests;
- ownership, current-state, API, database, synthetic-execution and operations docs.

## Non-goals

- No IOC.
- No Batch 5 Quote Age, cross-Venue time skew, Bid/Ask width, MT5 deviation, unhedged-duration, realized-spread or fee analytics/protections.
- No safety-limit relaxation.
- No claim that CI proves real Bybit private WebSocket behavior.

## Acceptance criteria

- [ ] Pure state machine is deterministic and bounded.
- [ ] Stable event deduplication prevents duplicate fill deltas.
- [ ] Disconnect/gap/unknown state blocks further automatic Chase.
- [ ] Amend/cancel/repost never exceeds policy or hard price bound.
- [ ] Cancel/fill and amend/fill races fail safely.
- [ ] Full fill enters the existing MT5 hedge path exactly once.
- [ ] Partial/invalid residual exposure is explicit and fail-closed.
- [ ] FOK remains the default Limit strategy and existing behavior is unchanged.
- [ ] PostOnly Chase remains disabled by default.
- [ ] Backend, Runtime, frontend, Repository Safety and Secret Scan pass.

## Progress

- Done: Batch 3 merged; Issue and branch created.
- Current: implement pure Runtime state machine and event model.
- Next: adapter wiring, Platform strategy contract, frontend and documentation.
- Blocked by: none.

## Completion

- PR:
- Merge commit:
- Behavior changed:
- Behavior intentionally unchanged:
- Tests/CI:
- Operational evidence not produced:
- Follow-up: Batch 5 remains deferred for user discussion.
