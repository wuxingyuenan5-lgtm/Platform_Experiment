# Codex Module Context Boundaries

## Purpose

Define the minimum context required for AI-assisted engineering tasks.
The default rule is: load the smallest relevant module context first.

## Module Ownership

### Frontend

Path:

```text
platform-web/
```

Load:

- `platform-web/`
- frontend documentation
- API contract only when UI integration changes

Avoid loading backend implementation details unless required.

### Backend

Path:

```text
platform-backend/
```

Load:

- backend source
- API specification
- relevant domain documentation

Avoid loading frontend assets or runtime gateway internals unless required.

### Execution Runtime

Path:

```text
execution-runtime/
```

Load:

- runtime source
- gateway documentation
- execution risk documents

Avoid loading product UI documentation.

### Financial Accounting

Load:

- FinancialFact documentation
- PnL/NAV specifications
- accounting-related backend modules

Avoid loading venue adapter details unless reconciliation is involved.

### Operations / Production

Load:

- operations documentation
- security documentation
- release gate
- incident procedures

## Cross-module Changes

Only load additional modules when:

- API contracts change;
- database schemas change;
- execution behavior changes;
- financial semantics change.

## Forbidden Default Scans

Do not recursively scan:

- `node_modules/`
- `.venv/`
- `dist/`
- generated outputs
- external references
- archived historical material

unless explicitly required by the task.
