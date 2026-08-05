# 全球变量金融平台（Variable-Global）

全球变量金融平台覆盖 Research、Market Data、Strategy、Trading、Execution、Risk、Accounting、Reconciliation、User & Access、Member Portfolio 与 Operations。`Platform`仅作为工程简称。

The maintained deployable subjects are:

- `platform-web` — Vue frontend;
- `platform-api` — modular-monolith business API;
- `execution-runtime` — isolated execution runtime and venue boundary.

## Local startup

From Windows PowerShell at the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-platform.ps1
```

Operating details and safety defaults are in `docs/operations/RUNBOOK.md`.

## Authorities

| Need | Authority |
|---|---|
| Current baseline, target, branch and limits | `docs/codex/current-state.md` |
| Documentation navigation | `docs/README.md` |
| AI and engineering rules | `AGENTS.md` |
| Minimal context selection | `docs/codex/context-map.md` |
| Service and data-flow boundaries | `docs/architecture/SYSTEM_MAP.md` |
| Code and data ownership | `docs/architecture/OWNERSHIP.md` |
| Domain contracts | `docs/contracts/README.md` |
| Database and migration rules | `docs/database/README.md` |
