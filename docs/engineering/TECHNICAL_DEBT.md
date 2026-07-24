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

Status: active; inventory and migration-ledger prerequisites completed
Owner: Platform Backend / persistence

Problem: `app/database.py` still combines connection handling, core DDL, incremental compatibility changes and reference-data seeding. Additional DDL remains owned by domain modules.

Risk: large review surface and implicit startup ordering if future schema changes bypass the migration ledger.

Completed prerequisite:

- DDL Owner inventory in `docs/database/README.md`;
- additive `schema_migrations` ledger;
- ordered version and checksum validation;
- existing-schema V1 baseline;
- repeated-startup and mutation-detection tests;
- FinancialFact schemas, normalization, persistence and projection services are separated from the core database module.

Deferred because: physically moving connection, DDL or seed logic can affect fresh and existing databases even when SQL text looks unchanged.

Trigger: dedicated Issues prove fresh-database and existing-database behavior before and after each extraction.

Protected semantics: existing tables, indexes, seed identifiers, live defaults and financial/trading behavior.

Safe approach: extract connection → bootstrap → seeds in small PRs; keep the migration ledger authoritative and do not combine a structural extraction with a business schema change.

## TD-002 — Financial facts module concentration

Status: completed through Issues #40, #42, #44 and #46
Owner: Platform Backend / formal accounting

Original problem: `app/financial_facts.py` combined public DTOs, normalization/content hashing, direct persistence, formal Position/PnL/NAV calculations, rebuild orchestration and API behavior.

Resolved ownership:

- `app/financial_fact_schemas.py`: public FinancialFact/formal-accounting DTOs;
- `app/financial_fact_normalization.py`: canonicalization, FX/data-quality policy and normalized-content hash;
- `app/financial_fact_repository.py`: SQL, DDL, row mapping and protected transaction units;
- `app/financial_projection_service.py`: average cost, realized and component PnL, formal projection rebuild and NAV calculation;
- `app/financial_facts.py`: catalog/context resolution, immutable fact recording, validation/HTTP mapping, compatibility wrappers and API routes.

Evidence:

- public schema identity and JSON Schema snapshots;
- exact normalized-dictionary and SHA-256 golden vectors;
- API status and persisted-value equivalence;
- fact+audit, Position+PnL, rebuild-clear and NAV+audit forced-rollback tests;
- average-cost, component attribution, incomplete quality, rebuild audit and NAV calculation goldens;
- architecture ownership checks and progressive Pyright coverage;
- unchanged end-to-end accounting, normalization and repository transaction suites.

Protected semantics: fact identity, normalized content hashing, currency conversion, contract multiplier, position average cost, component PnL, rebuild results, NAV results and transaction atomicity.

Future rule: changes must stay within the established owner and require explicit compatibility evidence when immutable fact identity or accounting formulas change. Do not recombine these modules for convenience.

## TD-003 — Operational projection retirement criteria

Status: accepted
Owner: Platform Backend / trading operations

Problem: operational `positions` and `pnl_results` coexist with formal accounting projections.

Risk: consumers may accidentally treat low-latency operational values as auditable truth.

Deferred because: the operational views remain useful for immediate monitoring.

Trigger: every consumer is classified and a replacement latency/SLA is proven.

Protected semantics: formal accounting never reads operational projections as inputs.

Safe approach: usage telemetry and consumer inventory before any deprecation.

## TD-004 — Frontend inherited lint debt

Status: active; no-new-debt gate completed
Owner: Frontend

Problem: inherited template code outside the maintained trading surface is not yet clean enough for a whole-`src/` zero-warning gate.

Risk: legacy warnings still exist in untouched modules.

Completed prerequisite:

- active trading paths remain fully linted with zero warnings;
- every added or modified `admin-risk/src` and `admin-risk/mock` source file is checked with zero warnings;
- no mass formatting was introduced.

Deferred because: a one-shot cleanup would create an unreviewable change.

Trigger: clean one product module when that module receives real work; expand the maintained full-directory set after it is clean.

Protected semantics: no mass formatting and no product behavior change.

Safe approach: module-by-module cleanup until full `src/` can replace the changed-file gate.

## TD-005 — Progressive Python typing

Status: active; critical execution, FinancialFact and persistence boundaries selected
Owner: Platform Backend and Execution Runtime

Problem: much of the legacy code remains outside static type checking.

Risk: untyped database rows, arbitrary payloads and large orchestration modules can still drift.

Completed prerequisite:

- Pyright is installed and blocking in CI;
- Platform execution DTOs, FinancialFact DTOs/Normalization/Repository/Projection Service, Runtime contracts, schema migrations, schema governance and authoritative order submission are selected;
- Runtime models, Runtime contracts and Gateway Protocol are selected.

Deferred because: strict whole-project typing would create noisy changes unrelated to current risk boundaries.

Trigger: when a module is materially modified, add it to Pyright after making its public boundary explicit.

Protected semantics: no runtime behavior or dependency-injection change solely to satisfy typing.

Safe approach: expand by domain boundary, never through a single repository-wide suppression baseline.

## TD-006 — Live production evidence

Status: active; tracked by Issue #39
Owner: Operations

Problem: offline tests cannot prove broker-specific timing, partial-fill and recovery behavior in a real account.

Risk: production assumptions may differ from controlled test doubles.

Completed prerequisite:

- automated failure-injection matrix covers incompatible versions, result unknown, duplicate and out-of-order events;
- controlled acceptance order and stop conditions are documented in `docs/operations/FAILURE_INJECTION_ACCEPTANCE.md`;
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
- all engineering branch patterns run Platform CI;
- duplicate historical work branches were reviewed and returned to the stable baseline;
- Issue #38 records the exact settings and evidence required from an administrator.

Deferred because: the available repository connector does not expose branch-protection or ruleset mutation.

Trigger: repository administrator opens Settings → Rules/Branches and verifies the rule against the actual required check names.

Protected semantics: administrators must not routinely bypass safety gates.

Safe approach: protect `main`, require Platform CI and Secret Scan, require conversation resolution and current branch state, disallow force push/deletion, prefer squash-only delivery, and enable automatic deletion of merged head branches.
