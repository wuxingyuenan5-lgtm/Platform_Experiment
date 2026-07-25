# Task: Release Platform 0.8.0

Issue: #102
Status: in_progress
Branch: `chore/issue-102-release-0-8-0`
PR: pending
Base commit: `489427c03ac4b0dca43b2d81c696a7b903b8d133`

## Objective

Publish a coherent `0.8.0` product release after the completed cross-spread market lifecycle, one-ounce acceptance hardening and live account observability scopes.

## Version decision

Use a backward-compatible minor release:

```text
0.7.0 → 0.8.0
```

The release adds substantial user-visible and API capabilities while retaining maintained compatibility endpoints, Platform–Runtime V1 semantics, database compatibility and all disabled-by-default Live safety controls.

## Expected changed files

- `VERSION`
- `platform-backend/pyproject.toml`
- `execution-runtime/pyproject.toml`
- `admin-risk/.env`
- `README.md`
- `docs/codex/current-state.md`
- `docs/releases/0.8.0.md`
- this task packet

`CHANGELOG.md` remains the detailed pre-release engineering history. The concise product release record is owned by `docs/releases/0.8.0.md` and the current release is owned by root `VERSION`.

## Included release scope

- responsive-layout architecture and homepage-first remediation;
- terminal-fill-confirmed Bybit market execution;
- actual-fill-proportional MT5 hedge sizing;
- venue-safe reduce-only/ticket-bound market close;
- persistent exit plans and executable-close-spread TP/SL;
- route-independent Order/Fill reads and current Venue specifications;
- temporary 1 oz and one-lifecycle acceptance controls;
- bounded historical Order/Fill/Deal reads;
- Bybit liquidation evidence and MT5 Margin Call/Stop Out evidence;
- section-aware two-Venue account observability and read-only frontend acceptance panel.

## Protected semantics

- Platform and Runtime Live Write remain disabled.
- The automatic exit monitor remains disabled.
- The 1 oz, one-lifecycle and Market-only acceptance restrictions remain unchanged.
- Platform–Runtime V1 and FastAPI metadata versions remain independent from the product release.
- No database migration, trading formula, order-state transition or compatibility removal.

## Required verification

- `python scripts/check-version-consistency.py`
- Repository Safety and documentation consistency
- Backend lint, progressive type gate and classified tests
- Runtime lint, progressive type gate and classified tests
- Frontend lint, no-new-debt, type check and production build
- Version Consistency workflow
- Secret Scan

## Acceptance criteria

- [x] Root and all maintained release declarations equal `0.8.0`.
- [x] Frontend displays `0.8.0`.
- [x] `README.md` links the current release notes.
- [x] `docs/codex/current-state.md` records Product release `0.8.0`.
- [x] Release notes accurately distinguish engineering completion from Windows-host operational acceptance.
- [ ] Required CI and Secret Scan checks pass.

## Stop conditions

- Stop if the change requires a product behavior, contract, migration or safety-default change.
- Stop if release notes claim real Bybit/MT5 operational acceptance.
- Stop if any maintained version declaration diverges from root `VERSION`.
- Stop if scope expands into tagging, deployment, private WebSocket or Limit execution.
