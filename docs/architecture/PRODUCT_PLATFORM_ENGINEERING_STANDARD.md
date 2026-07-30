# Product Platform Engineering Standard

Status: `active`
Baseline: `Platform 0.9.1`

This document defines the durable implementation standard for product-facing research, data, dashboard and workflow features in Platform Experiment. It supplements `SYSTEM_MAP.md`, `OWNERSHIP.md`, `LIGHTWEIGHT_OPTIMIZATION_PLAN.md` and product-specific design standards. It does not redefine trading execution, accounting, authorization or live-write semantics.

## 1. Governing principles

1. Preserve the three-service boundary:
   - `admin-risk/`: Vue product frontend.
   - `platform-backend/`: business, research, orchestration, persistence and API contracts.
   - `execution-runtime/`: venue and broker adapters plus external side effects.
2. Product research data belongs in Platform Backend and must not be implemented in Execution Runtime.
3. The frontend must consume Platform API contracts and must not directly call databases, venue SDKs or third-party research providers.
4. Research data is decision-support data. It must never automatically become authoritative execution, risk or accounting input.
5. Prefer the smallest coherent implementation. Do not add a framework, service, state layer or directory only to make the architecture look more formal.
6. One responsibility has one authoritative owner. Compatibility modules may delegate or re-export but must not duplicate business rules.

## 2. Change classification and required evidence

| Change class | Typical scope | Required evidence |
|---|---|---|
| Local | One module, no public contract or schema change | Targeted test or browser check |
| Standard | Repeated UI/data rule, reusable component or contract refinement | Relevant type check, guard and formal standard update |
| Boundary | Producer/consumer contract, authorization or data ownership change | Issue, task packet, architecture evidence and synchronized ownership docs |
| Migration | Persistent schema or authority transition | Migration test, rollback/recovery evidence and task packet |
| Production | Deployment, live-write, credentials, monitoring or recovery | Operational runbook, explicit acceptance and protected semantics |

A task must not be described as a local refactor when it changes API meaning, persistence authority, permissions, execution behavior or data ownership.

## 3. Frontend architecture

### 3.1 Responsibility split

- Page components own route-level orchestration and layout.
- Product components own visible UI and interaction boundaries.
- Composables own state, loading, refresh, synchronization and API calls.
- Mappers own API-to-view conversion, display normalization and fallback mapping.
- Fixtures own deterministic mock, seed and degraded-mode data.
- API modules own request and response contracts; Vue templates must not contain provider-specific request logic.

### 3.2 Component extraction rule

Extract a component only when at least one condition is true:

- it is a stable business section;
- it owns an interaction lifecycle;
- it has independent loading, empty or error state;
- it is reused;
- the parent page has become difficult to review because unrelated business sections are interleaved.

Do not split trivial markup into single-use files without a business boundary. Avoid both giant pages and directory theatre.

### 3.3 Product UI rules

- Preserve the platform design system, spacing, typography, table and status conventions.
- Do not copy visual systems from reference repositories.
- Product pages must not display engineering notes, implementation commentary or acceptance instructions.
- Names and labels align left; numeric values align right.
- Missing values display as `—` unless a domain-specific state is required.
- Amount units must be explicit and consistent within one table or module.
- Red/green direction follows the platform's existing market convention.
- Repeated headings, duplicate module titles and parallel interaction patterns are not allowed.
- Drawer, modal, collapse and table interactions must be consistent across the same workflow.

### 3.4 Frontend state model

Data modules should use explicit states where applicable:

- `loading`
- `ready`
- `partial`
- `no_data`
- `stale`
- `error`

A parent page must allow one module to fail without blanking unrelated modules. Loading and failure states must be scoped to the smallest useful business section.

## 4. Platform Backend architecture

### 4.1 Layer responsibilities

- Routes validate transport input, enforce authorization and return public schemas.
- Schemas define stable request and response models.
- Services orchestrate use cases, calculations, provider fallback and partial-failure handling.
- Policies own pure formulas and classification decisions.
- Providers call one upstream source and normalize its response.
- Repositories own SQL, row mapping and persistence transactions.
- Cache modules own TTL, last-known-good and freshness metadata.

Routes must not contain provider parsing, complex calculations or direct SQL. Providers must not decide product authorization, execution behavior or persistence policy.

### 4.2 Provider result contract

Every external research result should expose, directly or through a module envelope:

- `source`
- `source_timestamp`
- `fetched_at`
- `status`
- `is_stale`
- `error_code`
- optional human-readable `message`

The displayed source must be the actual upstream source used for the result, not a reference repository or generic label.

### 4.3 Failure and cache rules

- Apply bounded timeouts to all external calls.
- Isolate failures by module or provider group.
- Empty or malformed pulls must not overwrite valid cached data.
- Stale data may be served only when visibly labelled.
- Last-known-good data must retain its original source timestamp.
- Cache TTL must reflect the business frequency of the data rather than use one global duration.
- Provider fallback must not silently change classification semantics.

### 4.4 Persistence rule

Persist only data that has durable product value, including:

- account-owned watchlists or preferences;
- versioned classification mappings;
- last-known-good snapshots where upstream continuity matters;
- cache metadata needed for freshness and traceability.

Do not build a full market-data warehouse as a side effect of a dashboard feature.

## 5. Research and market-data rules

1. Free public sources may be used only through Platform Backend providers.
2. Reference repositories may inform formulas, endpoint discovery and workflow design, but the platform must own its contracts, providers, cache and domain models.
3. The platform must not depend on a reference GitHub repository at runtime.
4. Adapted code must retain required license notices and attribution.
5. Classification dimensions must be explicit. Eastmoney or another provider's industry taxonomy must not be presented as Shenwan.
6. Research market data must remain separated from execution market data and formal accounting authority.
7. A displayed metric must define its formula, period, adjustment method, missing-data rule and unit in code or technical documentation.

## 6. API contract rules

- Public response fields use stable domain names rather than provider field names.
- Provider-specific identifiers remain internal unless they are necessary traceability fields.
- Nullability and unavailable states must be deliberate; do not use zero as a substitute for missing data.
- Contract changes that alter meaning require synchronized frontend, backend and tests.
- Compatibility aliases must have a removal or ownership plan and must not become a second implementation.
- Frontend requests must use the Platform `/api/v1` boundary and the platform authentication/session contract.

## 7. Testing and acceptance

### 7.1 Minimum automated checks

Use the smallest relevant set, expanding with task risk:

Frontend:

```text
npx pnpm@9.15.9 type:check
npx pnpm@9.15.9 test:hedge-board-layout
npx pnpm@9.15.9 build
```

Platform Backend:

```text
python -m ruff check app tests
python -m pyright
python -m pytest
```

Architecture and documentation:

```text
python scripts/check-repository-structure.py
python scripts/check-documentation-consistency.py
python scripts/check-codex-context.py
```

Run commands from the directory expected by the repository configuration. A task must not claim a check passed unless the exact command or its CI equivalent completed successfully.

### 7.2 Browser acceptance

Product workflows that include account persistence, authentication, filters, drawers or cross-session behavior should have browser-level coverage. External unstable sources may be replaced by deterministic fixtures for workflow tests, but fixture-based tests must not be presented as live-provider validation.

### 7.3 Manual acceptance

Manual acceptance is required where automation cannot prove the outcome, including:

- real-provider values and source links;
- trading-hours versus non-trading-hours freshness;
- stale and last-known-good behavior;
- responsive visual checks at agreed viewport widths;
- operational credentials, deployment or live-write behavior.

## 8. Documentation and governance

- Durable cross-task rules belong in `AGENTS.md`, architecture standards or product design standards.
- Current operating truth belongs in `docs/codex/current-state.md`.
- Task progress belongs in an Issue, task packet and pull request when the work classification requires them.
- Historical plans are not active authority after implementation unless explicitly marked current.
- Update `OWNERSHIP.md` only when an authoritative owner or boundary actually changes.
- A unified release branch may contain closely coupled standard, implementation, acceptance and release work when one Issue and phased task packet explicitly own the full Platform version scope.
- Do not combine unrelated user-system, trading, research or release changes into a nominally narrow pull request.

## 9. Prohibited shortcuts

The following are prohibited unless separately approved as an architecture change:

- frontend direct calls to third-party research providers;
- Platform Backend imports of venue SDKs;
- research logic in Execution Runtime;
- a second FastAPI service created only for one dashboard;
- silent use of stale data;
- empty provider responses overwriting valid data;
- provider taxonomy relabelled as another standard;
- mock or fixture data represented as live data;
- execution or accounting behavior changed inside a research/UI task;
- React, microservices, Kafka, Kubernetes, GraphQL or a new global state framework introduced without a demonstrated requirement.

## 10. Definition of done

A product-platform feature is complete only when:

1. the authoritative owner and service boundary are clear;
2. contracts, formulas, units and missing-data behavior are explicit;
3. frontend responsibilities are separated by real business boundaries;
4. provider failures are isolated and freshness is visible;
5. relevant automated checks pass;
6. live-provider or visual items that cannot be automated are explicitly recorded as pending or accepted;
7. no execution, authorization, risk or accounting semantics changed unintentionally;
8. the branch remains unmerged until owner approval.
