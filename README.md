# Platform

Platform is the internal fund research, strategy execution, risk, identity, portfolio and reconciliation application. It uses a Vue product frontend, a FastAPI modular-monolith Platform API and an independent Execution Runtime without introducing heavy distributed infrastructure.

当前目标版本：Platform `0.9.3`。

Current version, baseline, active branch, phase and deferred acceptance are maintained in:

`docs/codex/current-state.md`

## 一键本地启动

Windows PowerShell，在仓库根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-platform.ps1
```

该命令按需准备依赖并启动：

- Platform Web：`http://127.0.0.1:4373/index.html`
- Platform API：`http://127.0.0.1:8000/health`
- Execution Runtime：`http://127.0.0.1:8100/health`

默认保持Simulation、Fake Gateway以及Platform/Runtime Live Write关闭。

## 快速入口

| 目的 | 权威入口 |
|---|---|
| 当前工程状态 | `docs/codex/current-state.md` |
| Agent长期规则 | `AGENTS.md` |
| 按任务选择阅读范围 | `docs/codex/context-map.md` |
| 人工理解项目 | `00-人工可读目录/README.md` |
| 架构和代码所有权 | `docs/architecture/OWNERSHIP.md` |
| 系统结构 | `docs/architecture/SYSTEM_MAP.md` |
| Git工作流 | `docs/engineering/GIT_WORKFLOW.md` |
| 数据库、迁移与恢复 | `docs/database/README.md` |
| 运维和验收 | `docs/operations/` |

`docs/codex/CURRENT_CONTEXT.md`仅是旧链接兼容指针，不应作为当前事实来源。

## 当前工程结构

```text
platform-web/          Vue产品前端
platform-api/          FastAPI模块化单体业务API
execution-runtime/     Venue/Broker适配、外部副作用与Runtime Journal
docs/                  架构、合同、运维和工程权威文档
scripts/               启动、版本、审计和质量工具
projects/risk-control/ 外部证据完成前冻结的Legacy生产资产
```

Platform Web、Platform API和Execution Runtime是当前三条物理边界。`projects/risk-control`与`deploy/`在服务器、MySQL和真实消费者证据完成前不得删除、重命名或机械迁移。

## 当前阶段

Phase 0和Phase 0.5已经完成。当前执行Platform 0.9.3 Phase 1A，只处理版本事实、当前入口、有效命令路径和候选分支CI验证；不包含Context优化、批量文档删除、产品代码清理或业务闭环。

## 版本维护

```powershell
python scripts/bump-version.py <major.minor.patch>
python scripts/check-version-consistency.py
python scripts/check-codex-context.py
```

根`VERSION`是版本权威。Platform Web包与显示版本、Platform API包与应用版本、Execution Runtime包与状态版本，以及当前权威文档声明必须保持一致。
