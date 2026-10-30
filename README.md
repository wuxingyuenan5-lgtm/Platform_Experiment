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

## 日常使用

Windows 下可双击根目录的 `启动平台.bat`，启动成功后打开 [本地平台](http://127.0.0.1:4373)，使用已有账号登录。停止平台使用 `关闭平台.bat`；启动或恢复异常按[运行手册](docs/operations/RUNBOOK.md)定位。

- 看行情、宏观及市场研究：进入「对冲基金看板」。
- 看账户、策略和执行记录：进入「策略 → 策略管理」；研究分析与执行操作分开。
- 检查数据是否更新：进入「风控管理 → 数据审计」，同时核对具体页面的数据日期、缺数和失败状态。

研究页的计算与统计不代表已成交；交易操作仍以明确账户、方向、数量和实际回执为准。显示缺数或更新失败时，不把旧数据当作最新值，也不把缺失当零。

## Authorities

| Need | Authority |
|---|---|
| What is being done now, next and later | `docs/PROJECT.md` |
| How an active multi-task stage continues | `docs/workstreams/<stage-slug>.md` when that stage exists |
| Stable engineering baseline and known external limits | `docs/BASELINE.md` |
| Documentation navigation | `docs/README.md` |
| AI and engineering rules | `AGENTS.md` |
| Service and data-flow boundaries | `docs/architecture/SYSTEM_MAP.md` |
| Code and data ownership | `docs/architecture/OWNERSHIP.md` |
| Domain contracts | `docs/contracts/README.md` |
| Database and migration rules | `docs/database/README.md` |
