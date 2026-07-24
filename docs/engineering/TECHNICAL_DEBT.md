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

Status: active; connection and Bootstrap extraction completed through Issues #48 and #50
Owner: Platform Backend / persistence

Problem: `app/database.py` still combines initializer orchestration and fixed reference-data seeding. Shared connections are isolated in `app/database_connection.py`; core Schema and legacy compatibility DDL are isolated in `app/database_bootstrap.py`.

Risk: the remaining fixed Seed block is large, and careless movement could change reference identifiers, statuses, credentials references, trading modes or contract defaults.

Completed evidence:

- DDL Owner inventory and additive migration ledger;
- dynamic path, Row Factory, Foreign Key and transaction-boundary tests;
- exact compatibility identities for existing `app.database` imports;
- core Schema SHA-256 `421f0625ffe3a8a26ca48bc827e64bd6aa6b2e49d95faef0b17313e808375801`;
- fresh table/index and Seed-count snapshot;
- repeated-initialization idempotency;
- existing legacy database compatibility-column/index test;
- explicit initialization-order test: Connection → Bootstrap → Seed;
- Repository Safety DDL ownership transferred to `app/database_bootstrap.py`.

Deferred because: fixed Seed ownership requires its own exhaustive value snapshot and review; combining it with Schema movement would obscure regressions.

Trigger: complete the dedicated fixed reference Seed extraction.

Protected semantics: every Seed ID/value, existing tables/indexes/compatibility columns, simulation/live defaults and financial/trading behavior.

Safe approach: extract `seed_reference_data` and all fixed vectors into `app/database_seeds.py`, preserve `app.database` compatibility identity and initialization order, and require exhaustive Seed plus fresh/existing/repeated startup equivalence.

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

Status: active; critical execution, FinancialFact and SQLite Connection/Bootstrap boundaries selected
Owner: Platform Backend and Execution Runtime

Problem: much of the legacy code remains outside static type checking.

Risk: untyped database rows, arbitrary payloads and large orchestration modules can still drift.

Completed prerequisite:

- Pyright is installed and blocking in CI;
- Platform execution DTOs, FinancialFact DTOs/Normalization/Repository/Projection Service, SQLite Connection/Bootstrap, Runtime contracts, schema migrations, schema governance and authoritative order submission are selected;
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
