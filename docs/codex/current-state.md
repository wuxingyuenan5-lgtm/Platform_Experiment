# Current Engineering State

Last updated: 2026-08-04

This is the sole repository document for current version, default branch, active engineering phase and known limits. Durable execution rules live in `AGENTS.md`; system boundaries and owners live in `docs/architecture/SYSTEM_MAP.md` and `docs/architecture/OWNERSHIP.md`.

## Delivery

- Current target version: Platform `0.10.0`.
- Active/default branch: `main`.
- Final Platform 0.10.0 release-promotion PR: #153, merged by Merge Commit `cf6030d53b3e9a759263455569503b6c7242174e`.
- The complete delivery chain is merged: PR #135, #139, #141, #148, #149, #150, #151, #152 and #153.
- Frontend package-manager authority remains `pnpm@9.15.9`.
- `main` remains protected and must not be modified directly; repository changes continue through reviewed branches and pull requests.

## Current phase

- There is no active engineering phase after the Platform 0.10.0 release promotion.
- Platform 0.9.3 Phases 1 through 6 and their stacked reviews are closed and merged; no prior Draft PR remains the active engineering authority.
- Any subsequent feature, fix, refactor, hardening or release work must begin from a new Issue, a new branch and a new pull request under the repository workstream rules.
- The current Platform 0.10.0 tree is the starting baseline for future work; historical Phase branches and PRs are evidence, not active delivery surfaces.

## Release governance

- Platform Baseline Audit is `not_applicable_on_main_push` and `not_triggered_by_release_diff_path_scope`.
- The underlying Platform baseline is satisfied by prior verified evidence from the Platform 0.9.3 code tree and the successful checks applicable to PR #153.
- Evidence Waiver: No.
- Platform 0.9.3 Phase 6 Verification and Platform 0.9.3 Phase 6 Performance are not applicable on `main` Push and are satisfied by same-tree frozen-head evidence.

## Safety and known limits

- Platform Live Write and Platform Execution Runtime Live Write remain closed by default.
- Browser Sessions cannot authorize Live Write.
- Simulation and Fake Gateway remain the local defaults.
- No cleanup, routing, build or future feature change may weaken permission, Kill Switch, two-person approval, Decimal, accounting, reconciliation, idempotency or Result Unknown behavior.
- Real Broker, real Venue and production deployment acceptance remain separate from the Platform 0.10.0 repository release.
- External server, GitLab Runner, domain, TLS, systemd, MySQL, backup/restore and real Venue/Broker evidence remain deferred acceptance items.
- Duplicate risk-log pages remain because backend dynamic-route consumers are not externally proven absent.
- Deprecated cross-spread panels remain because layout verification records their non-mounted reference responsibility.
- Research Provider results may remain Partial when upstream providers or external networks are unavailable; Partial results are non-authoritative and require human review.
- Node Action runtime deprecation notices, Starlette/httpx deprecation notices and frontend large-chunk notices remain tracked P2 maintenance items.

## Authority links

- Documentation hierarchy: `docs/README.md`.
- Minimal task context: `docs/codex/context-map.md`.
- System boundaries: `docs/architecture/SYSTEM_MAP.md`.
- Ownership: `docs/architecture/OWNERSHIP.md`.
- Operating commands: `docs/operations/RUNBOOK.md`.
- Database and recovery: `docs/database/README.md`.
- Domain contracts: `docs/contracts/README.md`.

Legacy production evidence remains specialist reference in `docs/architecture/PLATFORM_LEGACY_DEPLOYMENT_AUDIT.md` and `docs/architecture/PLATFORM_LEGACY_GITLAB_DEPLOYMENT_AUDIT.md`. Do not delete or rename `projects/risk-control`, alter `deploy/`, delete `platform-web/.gitlab-ci.yml`, migrate external names or declare the Legacy production path retired without external evidence and owner approval.
