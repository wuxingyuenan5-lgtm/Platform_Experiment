# Workspace Hygiene

This project contains active code, generated dependencies, build outputs, virtual environments, large reference repositories, and historical documentation. The goal is to keep Codex and command-line search focused on the active surface.

## Current Noise Sources

| Path | Approximate size | Files | Policy |
|---|---:|---:|---|
| `admin-risk/node_modules/` | 1.09 GB | 72,456 | Ignore; do not delete unless dependencies will be reinstalled |
| `admin-risk/dist/` | 42.48 MB | 3,681 | Ignore; safe to regenerate |
| `execution-runtime/.venv/` | 136.73 MB | 5,303 | Ignore; keep while runtime is working |
| `platform-backend/.venv/` | 75.33 MB | 3,043 | Ignore; keep while backend is working |
| `admin-risk/project_structure.txt` | 0.08 MB | 1 | Ignore as generated structure dump |
| `admin-risk/CHANGELOG.md` | 0.22 MB | 1 | Ignore for routine search; it is vendor/history noise |

## Ignore Strategy

- `.gitignore` keeps generated dependencies, outputs, and large local reference material out of Git.
- `.ignore` keeps `rg` and Codex searches away from high-noise folders.
- `references/` is not fully ignored because curated SQL/reference notes may be useful.
- Large raw reference repositories have been moved outside the project root.

## Do Not Clean Automatically

Do not delete:

- `node_modules/`
- `.venv/`
- `platform-backend/data/`
- `execution-runtime/data/`

These may be large, but they support local development or contain runtime state. Prefer ignoring over deleting.

## External Reference Code

Large reference code now lives outside this project:

```text
C:\Users\jiuxi\Desktop\codex\平台设计其他辅助内容\平台移动文件夹，例如参考代码等\参考代码
```

Verified moved content:

- Approximate size: 2.47 GB
- Files: 157,674

Inspect explicit subprojects only when a task needs reference-code absorption.

## When The Machine Feels Slow

1. Check duplicate dev servers.
2. Keep only the needed frontend on `5173`.
3. Keep `8000` backend only when frontend needs live API data.
4. Keep `8100` Runtime only when testing execution integration.
5. Close browser tabs with heavy TradingView/ECharts dashboards when not needed.

## Safe Search Examples

```powershell
rg -n "StrategyBackendSnapshot" admin-risk/src
rg -n "createExecutionBatch" admin-risk/src platform-backend/app execution-runtime/app
rg --files
```
