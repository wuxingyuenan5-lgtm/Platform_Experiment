# Task: Version Consolidation and Dead Code Cleanup

Issue: #83
Status: active
Branch: `chore/issue-83-version-and-dead-code-cleanup`
Base commit: `7da3b89fc7841b093f016a1d03cd8f70c74f13e6`

## Objective

Publish maintained platform version `0.7.0` consistently and remove only frontend legacy order-submission code proven unused by current application pages.

## Non-goals

- Do not remove Backend `POST /trading/orders` or `trading.submit_order` in this task.
- No route/module refactor, database/schema change, Runtime contract change or trading behavior change.
- No broad deletion of historical documents, completed task packets or compatibility exports.

## Expected changed files

- `VERSION`
- `platform-backend/pyproject.toml`
- `platform-backend/app/application.py`
- `execution-runtime/pyproject.toml`
- `execution-runtime/app/main.py`
- `admin-risk/.env`
- `admin-risk/src/api/platform/trading.ts`
- `admin-risk/src/api/platform/trading.types.ts`
- `admin-risk/src/hooks/trading/usePlatformTrading.ts`
- version consistency check and direct tests
- `CHANGELOG.md`
- `docs/codex/current-state.md`
- `docs/engineering/GIT_WORKFLOW.md`
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
pnpm lint
pnpm type:check
pnpm build
cd ..
python scripts/check-repository-structure.py
python scripts/check-documentation-consistency.py
```

Final delivery requires Platform CI and Secret Scan on the final PR head.

## Stop conditions

- Stop if the removed frontend functions have an active import or page call.
- Stop if version synchronization requires changing a public Runtime contract version.
- Stop if Backend compatibility API removal becomes necessary.

## Acceptance criteria

- [ ] Root `VERSION`, Backend package/API, Runtime package/API and frontend displayed version equal `0.7.0`.
- [ ] A machine check prevents maintained version drift.
- [ ] Unused `createTradingOrder`, CreateOrderInput/OrderResult frontend types and submit-state hook code are absent.
- [ ] Funding execution remains ExecutionBatch-based and snapshot refresh remains unchanged.
- [ ] Backend compatibility endpoint remains intact and documented as retained.
- [ ] Full CI and Secret Scan pass.

## Progress

- Done: usage audit, scope, Issue and branch.
- Current: implement version synchronization and verified dead-code deletion.
- Next: focused checks, full CI, review and squash merge.
- Blocked by: none.

## Completion

- PR:
- Merge commit:
- Behavior changed: none.
- Behavior intentionally unchanged: Backend compatibility endpoint, all execution/recovery/safety and Live Write behavior.
- Tests/CI:
- Follow-up debt: remove Backend compatibility order endpoint only after external usage evidence and a dedicated migration.