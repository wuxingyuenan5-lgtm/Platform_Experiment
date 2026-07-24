# Issue #55 — Machine-checked architecture ownership documentation

Issue: #55
Branch: `docs/issue-55-architecture-ownership`

## Objective

Create one canonical architecture ownership catalog and a blocking consistency check so Agent context and architecture Markdown cannot silently drift behind implemented module boundaries.

## Scope

### Included

- `docs/architecture/OWNERSHIP.md` canonical ownership catalog.
- Correct stale ownership in `docs/codex/context-map.md`.
- Keep current-state compact and link to the canonical catalog.
- Add `scripts/check-documentation-consistency.py`.
- Add direct tests for missing files and stale ownership mappings.
- Run the check in Repository Safety.
- Update directly authoritative Markdown and Changelog.

### Excluded

- Runtime behavior, API, SQL, Schema, Seed or formula changes.
- Trading, credentials, deployment, Release, Staging, SLO or Live Write changes.
- Mass Markdown formatting or historical documentation cleanup.

## Protected semantics

- Existing module ownership established by merged PRs.
- One human entrypoint and one Agent entrypoint.
- `AGENTS.md` remains durable rules only.
- `current-state.md` remains compact current truth.
- Architecture documentation remains stable structure, not a PR diary.

## Direct context

- `AGENTS.md`
- `docs/codex/context-map.md`
- `docs/codex/current-state.md`
- `docs/architecture/README.md`
- `scripts/check-repository-structure.py`
- `.github/workflows/platform-ci.yml`
- direct script tests

## Acceptance evidence

- Canonical ownership document exists and all listed repository paths resolve.
- Context map reflects separated FinancialFact ownership.
- Consistency checker fails for a missing canonical owner path.
- Consistency checker fails for a stale context ownership statement.
- Repository Safety invokes the checker.
- Full Platform CI and independent Secret Scan pass on the frozen PR head.

## Rollback

Revert the final squash commit. No runtime or persisted state is introduced.
