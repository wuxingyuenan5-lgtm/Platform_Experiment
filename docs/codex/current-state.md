# Current Engineering State

Last updated: 2026-08-01

This is the sole repository document for current version, branch, phase and known limits. Durable execution rules live in `AGENTS.md`; system boundaries and owners live in `docs/architecture/SYSTEM_MAP.md` and `docs/architecture/OWNERSHIP.md`.

## Delivery

- Current target version: Platform `0.9.3`.
- Active branch: `refactor/platform-0-9-3-repository-and-context-optimization`.
- Active review: Draft PR #141, which remains Open and Unmerged until explicit owner acceptance.
- Accepted Phase 1A head: `4e4a6b7992c332c71c90dcf5b2bc18ca18302737`.
- Accepted Phase 1B head: `3c5bc4f0c700129c0716765103604bc16e0335c4`.
- Frontend package-manager authority: `pnpm@9.15.9`.
- `main` remains protected and is not modified directly.

GitHub PR #141 owns the active branch, Draft PR, HEAD, CI and review state.

## Current phase

- Phase 1B passed acceptance at `3c5bc4f0c700129c0716765103604bc16e0335c4`.
- Current work is Platform 0.9.3 Phase 2A-R1 — documentation gate scope correction.
- Phase 2B owns the approved 114-file D-class process-material cleanup; it has not started.
- Phase 8 owns cross-venue spread and funding-fee arbitrage business closure; it has not started.

## Safety and known limits

- Platform Live Write and Platform Execution Runtime Live Write remain closed by default.
- Browser Sessions cannot authorize Live Write.
- Simulation and Fake Gateway remain the local defaults.
- No documentation or naming change may weaken permission, Kill Switch, two-person approval, Decimal, accounting, reconciliation, idempotency or Result Unknown behavior.
- External server, GitLab Runner, domain, TLS, systemd, MySQL, backup/restore and real Venue/Broker evidence remain deferred acceptance items.

## Authority links

- Documentation hierarchy: `docs/README.md`.
- Minimal task context: `docs/codex/context-map.md`.
- System boundaries: `docs/architecture/SYSTEM_MAP.md`.
- Ownership: `docs/architecture/OWNERSHIP.md`.
- Operating commands: `docs/operations/RUNBOOK.md`.
- Database and recovery: `docs/database/README.md`.
- Domain contracts: `docs/contracts/README.md`.

Legacy production evidence remains specialist reference in `docs/architecture/PLATFORM_LEGACY_DEPLOYMENT_AUDIT.md` and `docs/architecture/PLATFORM_LEGACY_GITLAB_DEPLOYMENT_AUDIT.md`. Do not delete or rename `projects/risk-control`, alter `deploy/`, delete `platform-web/.gitlab-ci.yml`, migrate external names or declare the Legacy production path retired without external evidence and owner approval.
