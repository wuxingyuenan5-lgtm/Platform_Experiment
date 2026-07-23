# Release Status

## Current Baseline

The repository uses `main` as the single source of truth for released code.

Feature branches are temporary delivery branches and must be merged through Pull Request after validation.

## Completed Engineering Phases

- Phase 1: Trading safety foundation
- Phase 2: Execution command and recovery framework
- Phase 3: Financial facts, formal accounting, Position/PnL/NAV reconstruction
- Phase 4A: Execution risk controls
- Phase 4B: Venue reconciliation and external fact ingestion foundation
- Phase 4C: Live venue adapter foundation (Bybit / MT5 controlled integration)
- Phase 4D: End-of-day reconciliation framework
- Production Gate: Authentication, RBAC, approval and operational safety foundation

## Current Focus

Codex context optimization and engineering workflow improvements.

The objective is to keep repository understanding efficient while preserving production safety and auditability.

## Runtime Safety Baseline

Default mode:

```text
TradingMode=simulation
Gateway=fake
Platform Live Write=false
Runtime Live Write=false
```

Real-account testing, when enabled, must use:

- explicit approval;
- risk controls;
- minimum position size;
- reconciliation verification;
- audit trail.

## Documentation Authority

Order of authority:

1. AGENTS.md
2. Module documentation
3. Architecture decisions
4. Technical specifications
5. README
6. Historical changelog

Historical documents provide context only and do not override current implementation.

## Development Rule

All meaningful changes follow:

```text
Issue
 -> Branch
 -> Code
 -> Test
 -> CI
 -> Pull Request
 -> Merge main
 -> Documentation update
```
