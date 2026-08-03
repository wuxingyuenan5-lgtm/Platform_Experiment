# Variable-Global 交易基础设施平台

内部基金投研、策略执行、风险控制、用户管理、资产与账务核对平台。当前采用Vue产品前端、FastAPI模块化单体Platform API和独立Execution Runtime，不引入重型分布式基础设施。

当前版本、冻结基线、活动分支、优化阶段和延期验收统一由以下文件维护：

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
| 0.9.2系统优化总方案 | `docs/architecture/PLATFORM_0_9_2_SYSTEM_OPTIMIZATION_MASTER_PLAN.md` |
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

Platform Web、Platform API和Execution Runtime三条物理边界已经完成目录治理。`projects/risk-control`与`deploy/`在服务器、MySQL和真实消费者证据完成前不得删除、重命名或机械迁移。

## 当前优化阶段

Phase A–D、Research、Identity、Portfolio、Frontend热点和高风险路由治理已经完成。当前继续Phase J / J2 GitHub仓库减负；服务器、GitLab Runner、MySQL、TLS、Windows真实本地和真实Venue/Broker验收延期，不再阻塞仓库内安全优化。

## 工作流

- Fast：Markdown和同步版本维护。
- Standard：边界清晰的单模块改动。
- Critical：交易、执行、Runtime、风险、权限、认证、数据库、迁移、合同、Live或跨服务工作。

PR按受影响范围运行检查；正式验收阶段运行完整矩阵。详细规则见`docs/engineering/GIT_WORKFLOW.md`。

## 版本维护

```powershell
python scripts/bump-version.py <major.minor.patch>
python scripts/check-version-consistency.py
python scripts/check-codex-context.py
```

根`VERSION`、两个Python包、前端显示环境和`platform-web/package.json`必须保持一致。
