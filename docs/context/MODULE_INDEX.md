# Module Context Index

Use this index to select the smallest useful context set. Paths not listed for a task are out of scope unless the task file explicitly adds them.

## Frontend: `admin-risk/`

Responsibilities:

- user workflows and visualization;
- Platform API clients;
- trading hooks and strategy pages;
- no direct venue or database access.

Start with:

- `admin-risk/docs/START-HERE.md`;
- the page directory under `src/views/`;
- its API client under `src/api/platform/`;
- its hooks under `src/hooks/trading/`;
- `tsconfig.strategy.json` and affected tests/checks.

## Platform Backend: `platform-backend/`

Responsibilities:

- business APIs and authorization;
- strategy catalog and lifecycle;
- risk policy and approvals;
- execution orchestration without venue SDKs;
- immutable financial facts and formal accounting projections;
- operational APIs and EOD control.

Important ownership:

- composition root: `app/main.py`;
- execution DTOs: `app/execution_schemas.py`;
- operational fill projections: `app/trading.py`;
- formal financial authority: `app/financial_facts.py`;
- database bootstrap: `app/database.py` pending migration extraction;
- architecture checks: `tests/test_*boundar*.py` and `scripts/check-repository-structure.py`.

## Execution Runtime: `execution-runtime/`

Responsibilities:

- venue adapters and SDK access;
- execution command journal;
- live-write safety and credential references;
- external order/fill/result normalization;
- connectivity and venue-query behavior.

Platform Backend must not import this module or venue SDKs directly. Communication must use versioned contracts.

## Cross-module contracts

Canonical location: `docs/contracts/` plus executable Schema modules in the owning service.

Contract work must inspect:

- producer model;
- consumer model;
- serialization aliases;
- version policy;
- compatibility tests;
- OpenAPI/JSON Schema snapshots.

## Database and accounting

Canonical documentation: `docs/database/` and `docs/technical/FINANCIAL_FACTS.md`.

Before database work, classify each object as one of:

- reference/master data;
- command or execution journal;
- operational projection;
- immutable financial fact;
- formal accounting projection;
- audit/operations data.

No table may have ambiguous ownership.

## Repository governance

- `AGENTS.md`: hard rules.
- `docs/START-HERE.md`: entrypoint.
- `docs/context/`: current orientation.
- `docs/architecture/`: stable system boundaries.
- `docs/engineering/TECHNICAL_DEBT.md`: deferred work with triggers.
- `tasks/`: current task packets.
- `scripts/check-repository-structure.py`: machine-enforced boundaries.
- `.github/workflows/`: CI execution.
