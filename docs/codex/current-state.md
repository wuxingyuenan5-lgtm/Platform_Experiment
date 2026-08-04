# Current Engineering State

Last updated: 2026-08-02

This is the sole repository document for current version, branch, phase and known limits. Durable execution rules live in `AGENTS.md`; system boundaries and owners live in `docs/architecture/SYSTEM_MAP.md` and `docs/architecture/OWNERSHIP.md`.

## Delivery

- Current target version: Platform `0.10.0`.
- Active branch: `refactor/platform-0-9-3-codebase-and-build-simplification`.
- Active review: stacked Draft PR #148, based on `refactor/platform-0-9-3-repository-and-context-optimization`; it remains Open and Unmerged until explicit owner acceptance.
- Accepted Phase 1A head: `4e4a6b7992c332c71c90dcf5b2bc18ca18302737`.
- Accepted Phase 1B head: `3c5bc4f0c700129c0716765103604bc16e0335c4`.
- Accepted Phase 2A-R1 head: `e4f12ed2da270943a15c25ae58db51bfb2315c49`.
- Accepted Phase 2 head: `cd825fe6bd9ecdf42082069b2785844eda2efac8`.
- GitHub PR #141 remains Open, Draft and Unmerged as the accepted Phase 2 review; no Phase 3 code is added to it.
- Frontend package-manager authority: `pnpm@9.15.9`.
- `main` remains protected and is not modified directly.

GitHub PR #148 owns the active branch, Draft PR, HEAD, CI and review state.

## Current phase

- Platform 0.9.3 Phase 3 — Codebase Reduction and Build Simplification is implemented on the current Draft PR #148 head and awaits owner acceptance.
- Removed proven non-product inputs: the test-server Workspace, upstream Demo View/API/locale assets, the root template Mock system, the hidden useRequest template route, and the unreferenced Legacy account manager.
- Formal consumers formerly located under Demo paths now use bounded product-owned security and API modules with the same requests and UI behavior.
- Route-module discovery is limited to top-level formal modules, and dynamic View discovery is limited to twenty explicit product roots; fifteen formal route modules are frozen by a machine-readable manifest and permanent gate.
- Strategy-local deterministic fixtures, browser E2E fixtures, Replica components, Deprecated cross-spread reference panels and Legacy production assets remain protected.
- Workspace, dependency and build inputs are reduced without a package upgrade, package-manager change or product behavior change.
- Seven Context Packs retain explicit Required/Optional budgets, stable machine-readable metrics and CI enforcement; default startup context remains below 4,000 estimated tokens.
- Production-confirmation and owner-decision materials remain protected; Financial AI remains deferred.
- Phase 4 core-code hotspot decomposition has not started.
- Phase 8 owns cross-venue spread and funding-fee arbitrage business closure; it has not started.

## Safety and known limits

- Platform Live Write and Platform Execution Runtime Live Write remain closed by default.
- Browser Sessions cannot authorize Live Write.
- Simulation and Fake Gateway remain the local defaults.
- No cleanup, routing or build change may weaken permission, Kill Switch, two-person approval, Decimal, accounting, reconciliation, idempotency or Result Unknown behavior.
- External server, GitLab Runner, domain, TLS, systemd, MySQL, backup/restore and real Venue/Broker evidence remain deferred acceptance items.
- Duplicate risk-log pages remain because backend dynamic-route consumers are not externally proven absent.
- Deprecated cross-spread panels remain because layout verification records their non-mounted reference responsibility.

## Authority links

- Documentation hierarchy: `docs/README.md`.
- Minimal task context: `docs/codex/context-map.md`.
- System boundaries: `docs/architecture/SYSTEM_MAP.md`.
- Ownership: `docs/architecture/OWNERSHIP.md`.
- Operating commands: `docs/operations/RUNBOOK.md`.
- Database and recovery: `docs/database/README.md`.
- Domain contracts: `docs/contracts/README.md`.

Legacy production evidence remains specialist reference in `docs/architecture/PLATFORM_LEGACY_DEPLOYMENT_AUDIT.md` and `docs/architecture/PLATFORM_LEGACY_GITLAB_DEPLOYMENT_AUDIT.md`. Do not delete or rename `projects/risk-control`, alter `deploy/`, delete `platform-web/.gitlab-ci.yml`, migrate external names or declare the Legacy production path retired without external evidence and owner approval.
