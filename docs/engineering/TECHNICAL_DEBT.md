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
- repeated-startup and mutation-detection tests.

Deferred because: physically moving DDL or seed logic can affect fresh and existing databases even when SQL text looks unchanged.

Trigger: a dedicated Issue proves fresh-database and existing-database behavior before/after extraction.

Protected semantics: existing tables, indexes, seed identifiers, live defaults and financial/trading behavior.

Safe approach: extract connection → bootstrap → migrations → seeds in small PRs; do not combine with a business schema change.

## TD-002 — Financial facts module concentration

Status: active; public schema extraction in Issue #40 and persistence extraction in Issue #42
Owner: Platform Backend / formal accounting

Problem: `app/financial_facts.py` still contains normalization, content hashing, projection calculations, rebuild orchestration and API behavior. Direct SQL and row mapping are isolated in `app/financial_fact_repository.py`.

Risk: remaining normalization and formal-projection calculations still share one review surface.

Completed prerequisite:

- operational/formal projection ownership is machine-checked;
- database authority is documented;
- cross-service execution contracts are versioned;
- existing golden tests cover idempotency, content conflicts, FX completeness, contract multiplier, average cost, component PnL, rebuild and NAV coverage;
- Issue #40 establishes `app/financial_fact_schemas.py` as the authoritative public DTO owner while preserving `app.financial_facts` compatibility exports;
- Issue #42 establishes `app/financial_fact_repository.py` as the direct SQL, row-mapping and DDL owner;
- fact+audit, Position+PnL, rebuild-clear and NAV+audit transaction units have forced-rollback tests;
- both extracted boundaries are included in progressive Pyright and protected by machine checks.

Deferred because: normalization policy and projection calculations require separate ownership boundaries and equivalence evidence; combining them with persistence movement would make review unsafe.

Trigger: after Issue #42 merges, create separate Issues in this order: normalization policy extraction → projection service extraction.

Protected semantics: fact idempotency, normalized content hashing, currency conversion, contract multiplier, position average cost, component PnL, rebuild results and transaction atomicity.

Safe approach: one concern per PR; preserve formulas byte-for-byte where possible, keep compatibility imports, and require the existing financial golden suite plus repository transaction suite on every step.

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
- every added or modified `admin-risk/src` and `admin-risk/mock` source file is now checked with zero warnings;
- no mass formatting was introduced.

Deferred because: a one-shot cleanup would create an unreviewable change.

Trigger: clean one product module when that module receives real work; expand the maintained full-directory set after it is clean.

Protected semantics: no mass formatting and no product behavior change.

Safe approach: module-by-module cleanup until full `src/` can replace the changed-file gate.

## TD-005 — Progressive Python typing

Status: active; first boundary baseline completed
Owner: Platform Backend and Execution Runtime

Problem: much of the legacy code remains outside static type checking.

Risk: untyped database rows, arbitrary payloads and large orchestration modules can still drift.

Completed prerequisite:

- Pyright is installed and blocking in CI;
- Platform execution DTOs, FinancialFact DTOs and Repository, Runtime contracts, schema migrations, schema governance and authoritative order submission are selected;
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
