# Task: Version Consolidation and Dead Code Cleanup

Issue: #83
Status: complete
Branch: `chore/issue-83-version-and-dead-code-cleanup`
Base commit: `7da3b89fc7841b093f016a1d03cd8f70c74f13e6`

## Objective

Publish product release version `0.7.0` consistently and remove only frontend legacy order-submission code proven unused by current application pages.

## Version boundary

- Root `VERSION` is the product release source of truth.
- Platform Backend and Execution Runtime package versions follow it.
- Frontend displayed version follows it.
- FastAPI metadata and Platform–Runtime contract versions describe component/API compatibility and remain independent.

## Non-goals

- Do not remove Backend `POST /trading/orders` or `trading.submit_order` in this task.
- Do not change FastAPI metadata or Platform–Runtime contract versions solely to match the product release.
- No route/module refactor, database/schema change, Runtime contract change or trading behavior change.
- No broad deletion of historical documents, completed task packets or compatibility exports.

## Expected changed files

- `VERSION`
- `platform-backend/pyproject.toml`
- `execution-runtime/pyproject.toml`
- `admin-risk/.env`
- `admin-risk/src/api/platform/trading.ts`
- `admin-risk/src/api/platform/trading.types.ts`
- `admin-risk/src/hooks/trading/usePlatformTrading.ts`
- `scripts/check-version-consistency.py`
- direct version-consistency test/workflow
- `docs/engineering/GIT_WORKFLOW.md`
- `docs/releases/0.7.0.md`
- `docs/codex/current-state.md`
- this task packet

## Protected semantics

- Existing maintained ExecutionBatch flow and snapshot refresh behavior.
- Backend compatibility order endpoint and all order recovery/safety behavior.
- Runtime API and Platform–Runtime V1 contract.
- Database schema and migration ledger.
- Both Live Write defaults.

## Required verification

```text
cd platform-backend
python -m ruff check app tests
python -m pyright
python -m pytest
cd ../execution-runtime
python -m ruff check app tests
python -m pyright
python -m pytest
cd ../admin-risk
pnpm type:check
pnpm build
cd ..
python scripts/check-version-consistency.py
python scripts/check-repository-structure.py
python scripts/check-documentation-consistency.py
```

Final delivery requires Platform CI and Secret Scan on the final PR head.

## Stop conditions

- Stop if removed frontend functions have an active import or page call.
- Stop if version synchronization requires changing a public Runtime contract version.
- Stop if Backend compatibility API removal becomes necessary.

## Acceptance criteria

- [x] Root `VERSION`, Backend package, Runtime package and frontend display equal `0.7.0`.
- [x] A machine check prevents maintained product-release version drift.
- [x] Unused `createTradingOrder`, `CreateOrderInput` and submit-state hook code are absent.
- [x] `OrderResult`, order reads/recovery and the Backend compatibility endpoint remain intact.
- [x] Funding execution remains ExecutionBatch-based and snapshot refresh remains unchanged.
- [x] Platform CI, Version Consistency and Secret Scan passed on the validated helper-free head.

## Progress

- Done: usage audit, product/API version boundary, direct changes, release notes, version guard, complete CI and removal of temporary helpers.
- Current: ready for review and squash merge.
- Next: merge PR #84 and close Issue #83.
- Blocked by: none.

## Completion

- PR: #84
- Merge commit: pending squash merge.
- Behavior changed: none.
- Behavior intentionally unchanged: Backend compatibility endpoint, order reads/recovery, all execution/safety and Live Write behavior.
- Tests/CI: Platform CI #1196 pass; Version Consistency #7 pass; Secret Scan #649 pass.
- Follow-up debt: remove Backend compatibility order endpoint only after external usage evidence and a dedicated migration.
