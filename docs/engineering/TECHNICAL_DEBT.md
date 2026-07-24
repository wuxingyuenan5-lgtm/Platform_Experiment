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

## TD-001 — Database bootstrap concentration

Status: active
Owner: Platform Backend / persistence

Problem: `app/database.py` combines connection handling, core DDL, incremental migration and reference-data seeding. Additional schema fragments also exist in domain modules.

Risk: schema ownership becomes difficult to audit and startup order can become an implicit migration mechanism.

Deferred because: table movement or migration changes can affect persistent state and require explicit inventory and compatibility tests first.

Trigger: the schema inventory and migration ledger are in place, or a schema-changing feature is approved.

Protected semantics: existing tables, indexes, seed identifiers, live defaults and financial/trading behavior.

Safe approach: inventory → ownership map → version ledger → extract migration files → only then move DDL.

## TD-002 — Financial facts module concentration

Status: active
Owner: Platform Backend / formal accounting

Problem: `app/financial_facts.py` contains API models, normalization, persistence, projection rebuild and query behavior.

Risk: large review surface around auditable financial logic.

Deferred because: splitting code before contract and data-ownership tests can obscure semantic changes.

Trigger: contract snapshots and static type boundaries cover its public API and projection inputs.

Protected semantics: fact idempotency, content hashing, currency conversion, position average cost and PnL formulas.

Safe approach: extract API schemas, repository, normalization policy and projection service without changing SQL or calculations.

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

Status: active
Owner: Frontend

Problem: zero-warning lint currently protects the active trading surface, while inherited template code outside that surface is not yet held to the same standard.

Risk: unrelated legacy warnings make full-repository lint noisy and encourage broad formatting diffs.

Deferred because: a one-shot cleanup would create an unreviewable change.

Trigger: no-new-debt baseline is executable and changed files are gated.

Protected semantics: no mass formatting and no product behavior change.

Safe approach: changed-file gate plus module-by-module cleanup until full `src/` is clean.

## TD-005 — Progressive Python typing

Status: active
Owner: Platform Backend and Execution Runtime

Problem: Ruff catches syntax and lint defects but does not verify cross-module type contracts.

Risk: DTO, database row and event shape drift can survive static checks.

Deferred because: strict whole-project typing would create noisy debt unrelated to risk boundaries.

Trigger: Pyright baseline exists for selected execution, risk and financial boundaries.

Protected semantics: no runtime behavior or dependency injection changes solely to satisfy typing.

Safe approach: strict selected modules, then expand only when each new module is clean.

## TD-006 — Live production evidence

Status: active
Owner: Operations

Problem: offline tests cannot prove broker-specific timing, partial-fill and recovery behavior in a real account.

Risk: production assumptions may differ from controlled test doubles.

Deferred because: real-account validation requires explicit operational approval and bounded funds exposure.

Trigger: controlled host, approved account, minimum order size and observation checklist are ready.

Protected semantics: Live Write remains disabled by default.

Safe approach: simulation → broker demo where representative → real account with smallest size and pre-defined stop conditions.
