# Issue #55 — Machine-checked architecture ownership documentation

Issue: #55
Branch: `docs/issue-55-architecture-ownership`
Status: complete pending final PR merge

## Objective

Create one canonical architecture ownership catalog and a blocking consistency check so Agent context and architecture Markdown cannot silently drift behind implemented module boundaries.

## Delivered

- Added `docs/architecture/OWNERSHIP.md` as the canonical major module ownership catalog.
- Corrected stale FinancialFact ownership in `docs/codex/context-map.md`.
- Reduced context-map to context selection and kept current-state focused on current invariants.
- Added `scripts/check-documentation-consistency.py` with deterministic validation units.
- Added architecture tests for current-repository consistency, missing Owner paths, wrong mappings and obsolete context statements.
- Added the checker to the Platform CI Repository Safety job.
- Synchronized durable Agent rules, architecture entrypoint, current-state and Changelog.

## Excluded and unchanged

- Runtime behavior, API, SQL, Schema, Seed and formulas.
- Trading, credentials, deployment, Release, Staging, SLO and Live Write.
- Historical Markdown content outside the directly affected ownership/context surfaces.

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
- `docs/architecture/OWNERSHIP.md`
- `scripts/check-documentation-consistency.py`
- `.github/workflows/platform-ci.yml`
- `platform-backend/tests/test_architecture_documentation_consistency.py`

## Acceptance evidence

- [x] Canonical ownership document exists and protected Owner paths resolve.
- [x] Context map reflects separated FinancialFact ownership.
- [x] Consistency checker rejects a missing canonical Owner path.
- [x] Consistency checker rejects a wrong Owner mapping.
- [x] Consistency checker rejects the obsolete `financial_facts.py` shortcut.
- [x] Repository Safety invokes and passes the checker.
- [x] Backend architecture suite executes the direct tests.
- [x] No business or runtime source file changed.
- [ ] Final frozen-head Platform CI and independent Secret Scan evidence is recorded in PR #56.

## Rollback

Revert the final squash commit. No runtime or persisted state is introduced.
