# Variable-Global 交易基础设施平台

这是面向内部投研、策略执行、风险控制和账务核对的工程。当前原则是先保证执行安全、可恢复、可审计和可持续维护，再扩展策略与产品能力。

## 快速入口

| 目的 | 文档 |
|---|---|
| 人工理解项目 | `00-人工可读目录/README.md` |
| Agent/Codex 最小上下文 | `docs/codex/context-map.md` |
| 当前工程状态 | `docs/codex/current-state.md` |
| 系统结构 | `docs/architecture/SYSTEM_MAP.md` |
| Git 与版本规则 | `docs/engineering/GIT_WORKFLOW.md` |
| 当前技术债务 | `docs/engineering/TECHNICAL_DEBT.md` |
| 数据库与迁移 | `docs/database/README.md` |
| Platform–Runtime V1 契约 | `docs/contracts/runtime-v1.json` |
| 正式账务 | `docs/technical/FINANCIAL_FACTS.md` |
| 故障注入与实盘验收 | `docs/operations/FAILURE_INJECTION_ACCEPTANCE.md` |
| 发布门槛 | `admin-risk/docs/quality/release-gate.md` |
| 前端入口 | `admin-risk/docs/START-HERE.md` |

## 当前工程原则

- `main` 是唯一正式代码基线。
- 非简单工作采用“一个 Issue、一个任务包、一个分支、一个 PR”。
- 新任务只加载目标模块上下文，不默认扫描整个仓库。
- Platform Backend 不直接导入交易场所 SDK；外部副作用属于 Execution Runtime。
- Platform 与 Runtime 通信使用显式版本契约。
- 关键边界采用单一 Owner；用例编排属于 Service，路由 facade 只保留兼容入口和错误映射，不重复计算、持久化或配置化外部 HTTP 实现。
- 持久化 Repository 是 DDL、直接 SQL、Row Mapping 与受保护事务的唯一 Owner；Policy、Service 与路由 facade 不直接访问数据库。
- `positions`、`pnl_results` 是运营投影，不是正式账务权威。
- 正式账务由不可变 `financial_facts` 重建。
- 数据库变化必须进入有版本和校验和的迁移账本。
- Live Write 默认关闭，工程合并不能自行开启实盘。

精确基线、活动 Issue 和受保护语义见 `docs/codex/current-state.md`。

## 服务入口

| 服务 | 默认地址 | 职责 |
|---|---|---|
| Frontend | `http://127.0.0.1:5173` | 产品交互和状态展示 |
| Platform Backend | `http://127.0.0.1:8000` | 业务、权限、风险、编排、账务和运营 API |
| Execution Runtime | `http://127.0.0.1:8100` | 命令 Journal、Gateway、外部查询和副作用 |

## 默认安全状态

```text
TradingMode=simulation
Gateway=fake
Platform Live Write=false
Runtime Live Write=false
```

实盘验收必须使用受控主机、小资金、最小允许仓位和明确停止条件。

## 目录结构

```text
00-人工可读目录/  给人看的总入口
admin-risk/       Vue 前端产品
platform-backend/ Platform 业务、风险与账务后端
execution-runtime/独立执行 Runtime 与外部适配
docs/             当前状态、架构、合同、数据库、运维和工程规则
tasks/            一个 Issue 对应一个跨会话任务包
outputs/          可丢弃产物，不是事实来源
scripts/          仓库和质量门禁脚本
```

## Git 工作流

```text
Issue
→ tasks/issue-<number>-<slug>.md
→ <type>/issue-<number>-<slug>
→ 一个开放 PR
→ CI/审查通过
→ squash merge main
```

PR 第一行必须声明 `Issue: #<number>`。详细规则见 `docs/engineering/GIT_WORKFLOW.md`。

## 常用验证命令

仓库治理：

```powershell
python scripts/check-workstream.py
python scripts/scan-secrets.py
python scripts/check-repository-structure.py
```

Platform Backend：

```powershell
cd platform-backend
python -m pip install -e ".[dev]"
python -m pip check
python -m ruff check app tests
python -m pyright
python -m pytest
```

Execution Runtime：

```powershell
cd execution-runtime
python -m pip install -e ".[dev]"
python -m pip check
python -m ruff check app tests
python -m pyright
python -m pytest
```

Frontend：

```powershell
cd admin-risk
pnpm install --frozen-lockfile
pnpm exec eslint --max-warnings 0 "src/api/platform/**/*.{ts,tsx}" "src/hooks/trading/**/*.{ts,tsx}" "src/views/strategy/funding-carry/**/*.{vue,ts,tsx}"
pnpm type:check
pnpm build
```

CI 还会对本次新增或修改的所有 `admin-risk/src`、`admin-risk/mock` 源文件执行零警告 ESLint，防止新增历史债务。

## 文档维护规则

- 永久硬规则：`AGENTS.md`。
- 当前事实：`docs/codex/current-state.md`。
- 单次任务进度：`tasks/issue-*.md`。
- 稳定边界：`docs/architecture/`。
- 关键决策：`docs/decisions/`。
- 领域合同：`docs/technical/` 与 `docs/contracts/`。
- 生产流程：`docs/operations/`。
- 暂缓债务：`docs/engineering/TECHNICAL_DEBT.md`。

不要把聊天记录、PR 日志和临时调试过程复制进架构文档。
