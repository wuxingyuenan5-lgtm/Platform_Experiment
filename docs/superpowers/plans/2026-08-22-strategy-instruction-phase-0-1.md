# Strategy Instruction Phase 0–1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

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

## Explicitly Out of Scope

- Full Phase 2 bounded PostOnly Chase, cancellation terminal-proof state machine, duplicate fill release algorithm, or funding live-write enablement.
- Phase 3 shared batch/orchestrator extraction and removal of the existing cross-spread branch.
- Phase 4 StrategyPositionGroup, dashboard/read-model migration, frontend redesign or sample-data migration.
- Phase 5 one-command Offline E2E, controlled-session schema expansion and deletion of old Catalog paths.
- Any Runtime rewrite, venue SDK work, ledger/Position/Fill/PnL/NAV/Reconciliation rewrite, external account connectivity, credentials, Live Write activation or real order activity.
