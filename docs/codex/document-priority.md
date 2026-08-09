# Codex Documentation Priority

## Goal

Avoid conflicting instructions by defining which documents are authoritative.

## Priority Order

When multiple documents describe the project, use this order:

1. `AGENTS.md`

Permanent engineering rules and safety boundaries.

2. Module-specific documentation

Examples:

- frontend docs for frontend work;
- backend docs for backend work;
- runtime docs for execution work.

3. Architecture and ADR documents

Explain design decisions and system structure.

4. Technical specifications

Examples:

- API specification;
- FinancialFact specification;
- execution contracts.

5. README

Human entry point and quick navigation only.

6. Changelog and historical records

Useful for history, not active design authority.

7. Chat transcripts, phase receipts and ad hoc handoffs

Not long-term authorities. Convert only durable facts into the current owning document.

## Conflict Resolution

If historical documents conflict with current implementation:

- prefer current approved code and active specifications;
- do not revive completed historical designs;
- create an ADR when a permanent design decision changes.

## Context Rule

Do not load every document by default.
Select documents according to the task scope first.
