# Variable-Global 交易基础设施平台

内部投研、策略执行、风险控制、用户管理与账务核对平台。当前优先级是先完成受控本地运行和真实环境验收，再扩展产品范围。

## 当前发布

产品版本：`0.9.1`  
集成分支：`feature/issue-117-platform-0.9.1`  
基线 `main`：`a4e22021c71cf5cd703cb0bc35676ff5adbfec36`  
发布说明：`docs/releases/0.9.1.md`

`0.9.1` 在最新平台、对冲基金看板、跨所价差、资金费与 Runtime 更新基础上，接入浏览器用户系统、四种业务角色、用户后台、运营备注、会员持仓与资产视图。该分支不代表真实 Bybit/MT5 环境或生产 HTTPS 主机已经验收，也不会自动开启 Platform 或 Runtime Live Write。

## 一键本地启动

Windows PowerShell，在仓库根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev-platform.ps1
```

首次运行会按需创建 Python 虚拟环境、安装依赖、读取前端声明的 pnpm 版本，并启动：

- Frontend: `http://127.0.0.1:4373/index.html`
- Platform Backend: `http://127.0.0.1:8000/health`
- Execution Runtime: `http://127.0.0.1:8100/health`

后续通常不会重复安装依赖。强制重装使用 `-ForceInstall`，跳过前端使用 `-SkipFrontend`。

默认仍是 Simulation + Fake Gateway，Platform/Runtime Live Write 均关闭。

## 快速入口

| 目的 | 文档 |
|---|---|
| 人工理解项目 | `00-人工可读目录/README.md` |
| Agent 规则 | `AGENTS.md` |
| Codex 当前上下文 | `docs/codex/CURRENT_CONTEXT.md` |
| 当前稳定状态 | `docs/codex/current-state.md` |
| 0.9.1 发布说明 | `docs/releases/0.9.1.md` |
| 用户系统本地交接 | `docs/operations/USER_SYSTEM_LOCAL_INTEGRATION_HANDOFF.md` |
| 用户系统部署准备 | `docs/operations/USER_SYSTEM_DEPLOYMENT_READINESS.md` |
| 轻量减负方案 | `docs/architecture/LIGHTWEIGHT_OPTIMIZATION_PLAN.md` |
| 系统结构 | `docs/architecture/SYSTEM_MAP.md` |
| 主要所有权 | `docs/architecture/OWNERSHIP.md` |
| Git 工作流 | `docs/engineering/GIT_WORKFLOW.md` |
| 数据库 | `docs/database/README.md` |
| 实盘验收 | `docs/operations/V6-小资金实盘验收手册.md` |

## 工程结构

```text
admin-risk/          Vue 前端
platform-backend/    业务、风险、用户、编排和账务 API
execution-runtime/   Venue/Broker 适配与外部副作用
docs/                稳定架构、合同、运维与工程文档
scripts/             启动、版本和质量工具
```

## 工作流

- Fast：Markdown 和同步版本。
- Standard：普通单模块改动，不强制 Issue 或任务包。
- Critical：交易、执行、Runtime、风险、权限、认证、数据库、合同、Live 或跨服务工作，保留严格 Issue/任务包/PR 流程。

PR 只运行受影响模块；`main` 始终运行完整矩阵。详细规则见 `docs/engineering/GIT_WORKFLOW.md`。

## 版本更新

```powershell
python scripts/bump-version.py 0.9.1
python scripts/check-version-consistency.py
python scripts/check-codex-context.py
```
