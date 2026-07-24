# Technical Debt Register

This file records intentionally deferred engineering work. It is not a backlog of ideas. Add an item only when the current implementation is understood and deferral has a reason.

## Required fields

- ID and status;
- problem and risk;
- affected owner/module;
- reason for deferral;
- trigger for action;
- protected semantics;
- proposed safe approach.

## TD-001 — Database module decomposition

Status: completed through Issues #48, #50 and #53
Owner: Platform Backend / persistence

Original problem: `app/database.py` combined configured path/connection management, core Schema, legacy compatibility DDL, initializer orchestration and all fixed reference-data Seeds.

Resolved ownership:

- `app/database_connection.py`: dynamic path, parent creation, SQLite connection, Row Factory, Foreign Keys and Commit/Rollback/Close;
- `app/database_bootstrap.py`: complete core Schema and legacy compatibility DDL;
- `app/database_seeds.py`: every fixed Seed vector and insertion statement;
- `app/database.py`: compatibility exports and `Connection → Bootstrap → Seed` initialization orchestration only.

Evidence:

- connection behavior and rollback tests;
- exact compatibility identities for existing `app.database` imports;
- core Schema SHA-256 `421f0625ffe3a8a26ca48bc827e64bd6aa6b2e49d95faef0b17313e808375801`;
- exhaustive all-row/all-field Seed SHA-256 `d42f7e4f95a6efa9044b1e91b4e603f1d87f515923a57d941ee16e75109e6183`;
- fresh table/index snapshot;
- legacy compatibility-column/index coverage;
- repeated-initialization idempotency;
- explicit initialization-order test;
- static ownership checks and progressive Pyright;
- Repository Safety DDL ownership assigned to `app/database_bootstrap.py`.

Protected semantics: every table/index/compatibility column, every Seed ID/value, simulation/live defaults and all financial/trading behavior.

Future rule: Connection, Schema or Seed changes must stay within their established Owner. Schema and Seed changes are explicit persistence/business-data changes and may not be hidden inside structural refactors.

## TD-002 — Financial facts module concentration

Status: completed through Issues #40, #42, #44 and #46
Owner: Platform Backend / formal accounting

Resolved ownership:

- `app/financial_fact_schemas.py`: public DTOs;
- `app/financial_fact_normalization.py`: canonicalization and immutable-content hash;
- `app/financial_fact_repository.py`: SQL, DDL, row mapping and protected transactions;
- `app/financial_projection_service.py`: formal Position/PnL/NAV calculations and rebuild;
- `app/financial_facts.py`: context resolution, recording, HTTP mapping and API.

Evidence includes public schema snapshots, exact hash goldens, API equivalence, forced rollback tests, formula/orchestration goldens, architecture checks and progressive Pyright.

Protected semantics: fact identity, normalized content, FX, multiplier, average cost, component PnL, rebuild/NAV results and transaction atomicity.

Future rule: changes stay within the established owner and require explicit compatibility evidence when immutable identity or accounting formulas change.

## TD-003 — Operational projection retirement criteria

Status: accepted
Owner: Platform Backend / trading operations

Problem: operational `positions` and `pnl_results` coexist with formal accounting projections.

Risk: consumers may accidentally treat low-latency operational values as auditable truth.

Deferred because: operational views remain useful for immediate monitoring.

Trigger: every consumer is classified and a replacement latency/SLA is proven.

Protected semantics: formal accounting never reads operational projections as inputs.

Safe approach: usage telemetry and consumer inventory before deprecation.

## TD-004 — Frontend inherited lint debt

Status: active; no-new-debt gate completed
Owner: Frontend

Problem: inherited template code outside the maintained trading surface is not yet clean enough for a whole-`src/` zero-warning gate.

Risk: legacy warnings still exist in untouched modules.

Completed prerequisite:

- active trading paths remain fully linted with zero warnings;
- every added or modified source file is checked with zero warnings;
- no mass formatting was introduced.

Deferred because: a one-shot cleanup would create an unreviewable change.

Trigger: clean one product module when that module receives real work.

Protected semantics: no mass formatting and no product behavior change.

Safe approach: module-by-module cleanup until full `src/` can replace the changed-file gate.

## TD-005 — Progressive Python typing

Status: active; critical execution, FinancialFact and SQLite Connection/Bootstrap/Seeds boundaries selected
Owner: Platform Backend and Execution Runtime

Problem: much of the legacy code remains outside static type checking.

Risk: untyped database rows, arbitrary payloads and large orchestration modules can still drift.

Completed prerequisite:

- Pyright is installed and blocking in CI;
- Platform execution DTOs, FinancialFact DTOs/Normalization/Repository/Projection Service, shared Position Math, Venue Reconciliation DTOs/Difference Policy, SQLite Connection/Bootstrap/Seeds, Runtime contracts, schema migrations, schema governance and authoritative order submission are selected;
- Runtime models, contracts and Gateway Protocol are selected.

Deferred because: strict whole-project typing would create noisy changes unrelated to current risk boundaries.

Trigger: when a module is materially modified, add it after making its public boundary explicit.

Protected semantics: no runtime behavior or dependency-injection change solely to satisfy typing.

Safe approach: expand by domain boundary, never through a repository-wide suppression baseline.

## TD-006 — Live production evidence

Status: active; tracked by Issue #39
Owner: Operations

Problem: offline tests cannot prove broker-specific timing, partial-fill and recovery behavior in a real account.

Risk: production assumptions may differ from controlled test doubles.

Completed prerequisite:

- automated failure-injection matrix;
- controlled acceptance order and stop conditions;
- Issue #39 separates operational evidence from engineering refactors.

Deferred because: real-account validation requires explicit operational approval and bounded funds exposure.

Trigger: controlled host, approved account, minimum order size and observation checklist are ready.

Protected semantics: Live Write remains disabled by default.

Safe approach: simulation → read-only live → shadow reconciliation → minimum-size real order → multiple clean EOD cycles.

## TD-007 — GitHub repository-level branch protection

Status: operational setting pending verification; tracked by Issue #38
Owner: Repository administration

Problem: repository CI and workstream rules are stored in code, but repository-level protection must also require those checks and restrict direct pushes to `main`.

Risk: an administrator could bypass the intended PR path if GitHub branch protection/rulesets are not configured.

Completed prerequisite:

- one-Issue/one-branch/one-PR machine check;
- PR and Issue templates;
- all engineering branches run Platform CI;
- Issue #38 records required settings and evidence.

Deferred because: the available connector does not expose branch-protection or ruleset mutation.

Trigger: repository administrator verifies the rule in GitHub Settings.

Protected semantics: administrators must not routinely bypass safety gates.

Safe approach: protect `main`, require Platform CI and Secret Scan, current branch state and conversation resolution, disallow force push/deletion, prefer squash-only delivery, and auto-delete merged branches.
