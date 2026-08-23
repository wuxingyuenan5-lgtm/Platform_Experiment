# Strategy Instruction Phase 0–1 Implementation Plan

**Status (2026-08-23):** Phase 0–1 and the third cross-spread funding-transfer template are complete. Funding Phase 2 has an Attempt/cancel/atomic-release simulation skeleton through `ab27f3ca`, but controlled-live remains blocked pending residual-quantity chase, explicit TTL/mutation/same-price tests, final reconciliation, shared-account resource isolation and balance reservation. The accelerated continuation plan is recorded at the end of this document; Phase 3–5 are maintenance work, not prerequisites for the first controlled-live acceptance of cross-spread or funding.

**Goal:** Semantically upgrade the existing `strategy_runs` business record into the single CEO `StrategyInstruction` entry point, with a versioned immutable `ExecutionPlan`, explicit strategy adapters, and legacy entry-point compatibility without changing live execution semantics.

**Architecture:** The existing `strategy_runs` table remains the durable business identity and gains append-only instruction/plan columns; no parallel long-lived `StrategyInstruction` table is introduced. A small `app/strategies` boundary validates manual input, selects a statically registered adapter and persists an immutable plan plus a single `ExecutionBatch` claim before any existing batch executor is invoked. Funding controlled-live is explicitly rejected until Phase 2 provides bounded PostOnly Chase and authoritative incremental release.

**Tech Stack:** Python 3, FastAPI, Pydantic v2, SQLite, `Decimal`, timezone-aware UTC timestamps, pytest.

**Spec:** `docs/superpowers/specs/2026-08-21-founder-operated-strategy-kernel-design.md`

## Global Constraints

- Scope is only design phases 0 and 1; Phase 2 PostOnly Chase, Phase 3 shared orchestration migration, Position Groups, dashboard migration and Offline E2E remain excluded.
- All requests remain CEO/manual initiated. No scheduler, auto-selection, auto-sizing, background strategy loop, venue SDK import, credentials or Live Write activation is introduced.
- Financial amounts are `Decimal` / canonical Decimal strings; persisted times are UTC-aware ISO-8601 values.
- Preserve existing Platform/Runtime dual Live Write gates, Kill Switch, execution lease, idempotency, cumulative limits, reconciliation and `result_unknown` fail-closed semantics.
- Use append-only schema migrations only. Preserve existing fields, routes and response contracts while consumers remain.
- Do not add strategy-key branching to the shared batch executor. Existing cross-spread branch is recorded as Phase 3 migration debt, not expanded here.
- Existing untracked `.workbuddy/`, `data/`, `docs/codex/.cp*.new`, `execution-runtime/_wtest.py`, and `platform-api/.pytest-basetemp/` are outside this work set.
- Keep the startup boundary small: the cross-spread funding transfer is a dedicated internal-account action, not a StrategyInstruction leg, generic treasury workflow, approval system, or new service.

## Phase 0 Baseline Findings

- `strategy_runs` is defined in the platform bootstrap schema, exposed by `app/strategy_runs.py`, and consumed through `POST/GET /api/v1/strategies/instances/{id}/runs` in `app/catalog_routes.py`; no production `platform-web` request targets this endpoint.
- The old gold entry is `POST /api/v1/trading/cross-spread/market-command`, implemented by `app.cross_spread.submit_cross_spread_market_command`; the old funding entry is `POST /api/v1/trading/funding/market-command`, implemented by `app.funding.submit_funding_market_command`.
- `ExecutionBatch` creates `execution_batch_legs`, then deterministic per-leg `TradeCommand`s. Current batch orchestration still has a `cross_venue_spread`/Bybit role branch for MT5 resize; this plan adds no further strategy-name branch.
- `app.catalog.py` has a historical direct `trade_commands` implementation in addition to `app.trade_commands`; it is not used by the new instruction path and must not be selected.
- Safety remains owned by `app.execution_risk`, `app.live_trading_sessions`, `app.trade_command_execution` and Runtime contracts: execution lease, Kill Switch, session claims and both Live Write gates remain downstream of the instruction boundary.
- Funding currently sends perpetual then spot as two `market` legs. It has neither bounded PostOnly Chase nor authoritative incremental release, so it is not an approved controlled-live funding execution and must remain fail-closed.

## Exact Write Set

- Create: `platform-api/app/strategies/__init__.py`, `domain.py`, `instruction_service.py`, `plan_service.py`, `adapters/__init__.py`, `adapters/cross_spread.py`, `adapters/funding_carry.py`.
- Modify: `platform-api/app/schema_migrations.py`, `platform-api/app/strategy_runs.py`, `platform-api/app/execution_batches.py`, `platform-api/app/execution_schemas.py`, `platform-api/app/schemas.py`, `platform-api/app/catalog_routes.py`, `platform-api/app/trading_routes.py`, `platform-api/app/funding.py`, `platform-api/app/cross_spread.py`, and `docs/operations/LIVE_ACCEPTANCE_RUNBOOK.md`.
- Create tests: `platform-api/tests/test_strategy_instructions.py`, `platform-api/tests/test_strategy_plan_adapters.py`, and `platform-api/tests/test_funding_phase2_safety_gate.py`.
- Modify tests only if a legacy response contract requires explicit compatibility coverage: `platform-api/tests/test_strategy_runs_v1.py`, `platform-api/tests/test_funding_local_closed_loop.py`, `platform-api/tests/test_cross_spread.py`.
- Funding-transfer slice: modify `platform-web/src/views/strategy/spread-carry/components/SpreadExecutionCommand.vue` and its owning composable/API types; add only a thin Platform API module, additive transfer record migration, focused API/UI tests, and a FakeGateway transfer capability.

### Task 1: Freeze the P0 funding safety contract

**Files:**
- Create: `platform-api/tests/test_funding_phase2_safety_gate.py`
- Modify: `platform-api/app/funding.py`, `platform-api/app/trading_routes.py`

**Interfaces:**
- Produces `assert_funding_controlled_live_capability()` that raises HTTP 423 before any funding write when Phase 2 capability is unavailable.
- Legacy `POST /trading/funding/market-command` retains its response type but delegates through the instruction compatibility path.

- [ ] **Step 1: Write failing tests** for controlled-live funding rejection, the current two-market-leg shape, no silent `post_only_chase → market` downgrade, no repost without cancel terminal proof, and no duplicate downstream release for duplicate fill identity.
- [ ] **Step 2: Run** `python -m pytest tests/test_funding_phase2_safety_gate.py -q`; confirm each failure identifies absent safety behavior rather than a fixture error.
- [ ] **Step 3: Implement the minimal capability gate.** Keep default-disabled funding controlled-live rejection explicit; do not implement chase or fill release.
- [ ] **Step 4: Run** `python -m pytest tests/test_funding_phase2_safety_gate.py tests/test_funding_local_closed_loop.py -q`.
- [ ] **Step 5: Commit** the verified safety contract with explicit paths.

### Task 2: Add versioned immutable strategy domain and adapters

**Files:**
- Create: `platform-api/app/strategies/domain.py`, `platform-api/app/strategies/plan_service.py`, `platform-api/app/strategies/adapters/__init__.py`, `platform-api/app/strategies/adapters/cross_spread.py`, `platform-api/app/strategies/adapters/funding_carry.py`, `platform-api/tests/test_strategy_plan_adapters.py`

**Interfaces:**
- `StrategyInstructionAction`, `StrategyInstructionStatus`, `ExecutionPolicy`, `ReleaseCondition`, `ExecutionPlanLeg`, `ExecutionPlan` use Pydantic and Decimal.
- `PlanService.build_plan(instance_id, action, parameters)` returns a frozen, versioned `ExecutionPlan`; only a static adapter registry is used.
- Cross-spread plans use `terminal_full_fill`; funding plans put perpetual first with `post_only_chase` and spot `incremental_cumulative_fill`.

- [ ] **Step 1: Write failing adapter/domain tests** with literal Decimal conversion, UTC serialization, contract multiplier/step snapshots, funding ordering, policy and release conditions, and read-only account rejection.
- [ ] **Step 2: Run** `python -m pytest tests/test_strategy_plan_adapters.py -q`; verify failures are missing types/services.
- [ ] **Step 3: Implement only domain schemas, static registration and pure plan generation.** Adapters cannot call a venue, store fills or choose a symbol/size.
- [ ] **Step 4: Run** `python -m pytest tests/test_strategy_plan_adapters.py -q`.
- [ ] **Step 5: Commit** the verified immutable plan boundary with explicit paths.

### Task 3: Atomically create the upgraded instruction and one Batch claim

**Files:**
- Modify: `platform-api/app/schema_migrations.py`, `platform-api/app/execution_batches.py`, `platform-api/app/strategy_runs.py`, `platform-api/app/execution_schemas.py`, `platform-api/app/schemas.py`
- Create: `platform-api/app/strategies/instruction_service.py`, `platform-api/app/strategies/__init__.py`, `platform-api/tests/test_strategy_instructions.py`

**Interfaces:**
- `create_instruction(instance_id, request)` normalizes the request, replays exact idempotency keys, reports mismatched payloads as HTTP 409, and returns an instruction response.
- `ExecutionBatch` exposes an internal transaction-safe claim/persist seam; execution side effects remain after successful local commit.
- `strategy_runs` receives only additive `requested_parameters_json`, `execution_plan_json`, `action`, `position_group_id`, `requested_by`, and a unique batch-instruction association / plan version trace.

- [ ] **Step 1: Write failing integration tests** for same-payload replay, different-payload conflict, one instruction/one batch, database failure leaving no orphan Batch, immutable plan after `executing`, restart readback from original plan, distinct keys creating distinct instructions, and `result_unknown → manual_intervention`.
- [ ] **Step 2: Run** `python -m pytest tests/test_strategy_instructions.py -q`; confirm red failures against the previous run-only behavior.
- [ ] **Step 3: Add the append-only migration and minimally split batch claim from post-commit dispatch.** Persist instruction, frozen normalized plan and Batch declaration in one `BEGIN IMMEDIATE` transaction; do not change runtime ordering or safety gates.
- [ ] **Step 4: Run** `python -m pytest tests/test_strategy_instructions.py tests/test_execution_batches_v1.py tests/test_idempotency_conflicts.py -q`.
- [ ] **Step 5: Commit** the verified instruction transaction boundary with explicit paths.

### Task 4: Expose stable APIs and delegate old entries

**Files:**
- Modify: `platform-api/app/catalog_routes.py`, `platform-api/app/trading_routes.py`, `platform-api/app/funding.py`, `platform-api/app/cross_spread.py`, `platform-api/tests/test_strategy_runs_v1.py`, `platform-api/tests/test_funding_local_closed_loop.py`, `platform-api/tests/test_cross_spread.py`
- Modify: `docs/operations/LIVE_ACCEPTANCE_RUNBOOK.md`

**Interfaces:**
- Add `POST/GET /api/v1/strategies/{instanceId}/instructions` and `GET /api/v1/strategy-instructions/{instructionId}`.
- The public request permits only `idempotencyKey`, `action`, `parameters`, optional `positionGroupId`, and `reason`.
- Legacy gold/funding endpoints and `/runs` map their old business input into the Instruction Service and preserve required legacy response envelopes.

- [ ] **Step 1: Write failing API/compatibility tests** proving each old entry produces one Instruction, replay creates no extra TradeCommand, approved-safety gates are still reached, and legacy response fields remain available.
- [ ] **Step 2: Run** the three target test modules; confirm route/contract failures.
- [ ] **Step 3: Add routes and thin mappers only.** Frontend payloads cannot supply account IDs, leg sequence or runtime bypass fields. Funding controlled-live remains rejected by Task 1.
- [ ] **Step 4: Update the Runbook** so authorization covers one complete scenario (open, authoritative verification, matching close, reconciliation, reset) while retaining explicit account/strategy/symbol/quantity/policy/expiry plus dual Live Write, Kill Switch, idempotency, caps, unknown-result and reconciliation gates.
- [ ] **Step 5: Run** `python -m pytest tests/test_strategy_runs_v1.py tests/test_funding_local_closed_loop.py tests/test_cross_spread.py tests/test_auth_assurance.py tests/test_live_safety_failure_injection.py -q`.
- [ ] **Step 6: Commit** compatibility and runbook changes with explicit paths.

### Task 5: Validate the slice and document exclusions

**Files:**
- Modify: this plan to check completed tasks and record exact commands/results.

- [ ] **Step 1: Run relevant regression**: `python -m pytest tests/test_strategy_instructions.py tests/test_strategy_plan_adapters.py tests/test_funding_phase2_safety_gate.py tests/test_strategy_runs_v1.py tests/test_execution_batches_v1.py tests/test_idempotency_conflicts.py tests/test_funding_local_closed_loop.py tests/test_cross_spread.py tests/test_live_safety_failure_injection.py -q`.
- [ ] **Step 2: Run required repository checks**: `python -m unittest scripts.tests.test_no_fixed_receipt_contract scripts.tests.test_context_for -v`; `git diff --check`; `python scripts/context-for.py --check-budgets --json`; `python scripts/check-version-consistency.py`; `python scripts/check-repository-structure.py`; and `python scripts/check-documentation-consistency.py`.
- [ ] **Step 3: Inspect** `git status --short`, `git diff`, and `git diff --cached`; add only the exact task paths, make the final 0.11.2 commit, and do not push.

### Task 6: Add the third cross-spread funding-transfer template

**Product boundary:** The existing execution card has three peer templates: `open`, `close`, and `funding transfer`. Transfer is an internal Bybit/MT5 capital movement and never becomes an ExecutionPlan leg or ExecutionBatch.

- [ ] Add the third template to `SpreadExecutionCommand.vue` without redesigning the page. Show Bybit transferable balance, MT5 withdrawable balance, direction, an automatically prefilled amount, projected balances, confirmation, progress and exact failure state.
- [ ] Add quote/create/status Platform API endpoints. The public create payload contains only `idempotencyKey`, `direction`, and Decimal-string `amount`; account identities and low-level account types come from authoritative strategy bindings.
- [ ] Persist one lightweight `InternalCapitalTransfer` record for idempotency and audit. Do not add approvals, queues, schedulers or a generic treasury subsystem.
- [ ] Calculate the default amount as half of the absolute difference between the two real transferable balances, capped by the source transferable/withdrawable amount. Allow CEO override and direction swap.
- [ ] Treat UTA → Funding → MT5 and MT5 → Funding → UTA as resumable internal steps. If a later step fails, report that funds remain in Funding; do not auto-reverse and do not blindly retry `result_unknown`.
- [ ] Implement and test a bidirectional FakeGateway closed loop. Enable real automatic transfer only when an exact Bybit MT5 Transfer In/Out interface is verified. Otherwise deliver the usable assisted mode: calculate/copy the amount, open the configured official Bybit MT5 funds page, then refresh and reconcile balances.
- [ ] Add focused tests for automatic amount, manual override, Decimal precision, duplicate-click idempotency, pending/unknown behavior, partial two-step completion, balance refresh and the three-template UI.

## Explicitly Out of Scope

- Full Phase 2 bounded PostOnly Chase, cancellation terminal-proof state machine, duplicate fill release algorithm, or funding live-write enablement.
- Phase 3 shared batch/orchestrator extraction and removal of the existing cross-spread branch.
- Phase 4 StrategyPositionGroup, dashboard/read-model migration, frontend redesign or sample-data migration.
- Phase 5 one-command Offline E2E, controlled-session schema expansion and deletion of old Catalog paths.
- Any Runtime rewrite, venue SDK work, ledger/Position/Fill/PnL/NAV/Reconciliation rewrite, external account connectivity, credentials, Live Write activation or real order activity.

The exclusions above describe the original Phase 0–1 slice. They do not exclude the approved accelerated continuation below.

## Phase 0–1 Review Remediation

### Root causes recorded before remediation

1. Instruction POST is absent from the dynamic strategy-write route classification, and the route does not receive a `Principal`; `requested_by` is consequently hard-coded.
2. Adapter inputs are unconstrained dictionaries and Plan Service substitutes hard-coded IDs/specifications and a `bindings[0]` fallback for authoritative directory resolution.
3. Idempotency compares only part of the business request; close/disposition have no Position Group fail-closed boundary.
4. The generic recursive camel-case response mapper mutates business identifiers such as account IDs.
5. The funding gate treats all enabled paths as controlled-live and therefore blocks the existing local FakeGateway simulation regression.
6. Existing `/runs`, funding and cross-spread routes still independently create batches rather than delegating to one instruction claim.

### Remediation write set

- Modify: `platform-api/app/auth.py`, `catalog_routes.py`, `funding.py`, `cross_spread.py`, `strategy_runs.py`, `execution_batches.py`, `execution_schemas.py`, `schema_migrations.py`, `strategies/domain.py`, `strategies/plan_service.py`, `strategies/instruction_service.py`, and both adapters.
- Modify/Add tests: `test_auth_rbac.py`, `test_strategy_instructions.py`, `test_strategy_plan_adapters.py`, `test_funding_phase2_safety_gate.py`, `test_strategy_runs_v1.py`, `test_funding_local_closed_loop.py`, and `test_cross_spread.py`.
- Add migration 10 only for new immutable request fingerprint / trace fields; migration 9 remains unchanged.

### TDD order and acceptance

1. Add authorization, actor and exact-idempotency red tests; run the focused tests.
2. Add strict parameter/directory-resolution and fail-closed close tests; run focused tests.
3. Add environment-aware funding gate tests and restore all three FakeGateway funding regressions.
4. Extract the minimum batch-claim/dispatch seam, then add legacy delegation tests without a second batch.
5. Run the two owner-specified pytest groups to completion, Ruff, Pyright and root checks. Document any pre-existing bootstrap/structure failure without changing unrelated evidence.

## Accelerated continuation approved 2026-08-23

### Product boundary

- Active trading scope: cross-venue spread and funding carry only.
- Cross-venue spread is already in final live acceptance; do not restart it from a read-only onboarding phase and do not wait for Phase 3–5.
- Funding carry reuses the same real Bybit UTA, Platform `account_id` and credential reference as cross-spread. It may proceed to small controlled-live after the focused items below pass.
- Bottom-fishing and short-term trader A/B remain read-only. Home/abroad spread remains paused.
- Do not create a generic portfolio engine, service split, scheduler, event bus or same-symbol multi-strategy allocation system.

### One integrated implementation batch

The next execution AI should complete the following in one bounded task and normally one final receipt, using separate logical commits only where rollback value is clear:

1. **Correct Funding Phase 2.** Repost only the residual perpetual quantity (`maximumQuantity - authoritative cumulative fills across all attempts`), reject non-positive or over-cap quantities, require at least one tick of price change before a mutation, and add direct tests for TTL, maxMutations, restart, residual-quantity repost, cumulative overfill prevention and reconciliation completion evidence. Preserve cancel-terminal proof, atomic Spot claim, Decimal and `result_unknown` fail-closed behavior.
2. **Stabilize cross-spread interaction.** Persist/reuse a client idempotency key, recover the original Instruction/Batch after timeout or refresh, distinguish accepted/partial/hedged/reconciling/manual-intervention/result-unknown, show per-plan results for close-all, and block confirmation on stale/partial market or invalid sizing. Add focused component/composable/browser tests without redesigning the page.
3. **Enable shared-account concurrency.** Bind funding live `primary` to the same logical Bybit account as cross-spread only after tests prove the model. Replace account-wide batch blocking with atomic resource claims keyed by account/category/symbol; allow disjoint resources and reject same-resource overlap. Capital transfer and ambiguous account state retain account-wide exclusion.
4. **Add lightweight balance reservation.** Atomically reserve the instruction's maximum planned account/currency usage, subtract active reservations from authoritative available balance, release only after terminal external state and required reconciliation, and retain on unknown/cancel ambiguity/residual exposure. No generic portfolio risk engine.
5. **Complete reconciliation seam.** Funding remains `reconciling` until authoritative Order/Fill/Position/Balance evidence matches the immutable plan; only then mark completed. Query unavailability remains non-completion.

### Acceptance

- Cross-spread duplicate-click, timeout, refresh, partial leg, result-unknown and close-all partial failure tests pass.
- Funding tests prove residual attempt quantity, no cumulative overfill, cancel terminal before repost, one-tick mutation, TTL, maxMutations, partial cumulative releases, duplicate fill, concurrent resume, restart and reconciliation completion.
- Shared-account tests prove cross-spread XAUT and funding BTC/ETH may execute concurrently, while the same account/category/symbol conflicts; reservations prevent double spending and unknown results retain claims.
- Existing focused cross-spread, funding, instruction, batch, idempotency, live-safety and FakeGateway regressions pass, plus targeted Ruff/Pyright, frontend typecheck/lint/build and `git diff --check`.
- Controlled-live funding remains 423 in repository tests. Do not enable credentials, Live Write or real orders in this implementation task; operational activation is a separate Owner-authorized action after review.

### Commit and delivery shape

- Prefer no more than three commits: cross-spread interaction, shared-account execution isolation, and Funding correction/reconciliation. A smaller number is acceptable if ownership remains clear.
- Return one consolidated receipt with commits, exact changed files, behavioral evidence, test commands/results, remaining blockers and protected-file status. Do not push.
