# 人工可读目录

这是给非开发者和未来的自己看的项目总入口。先判断“我现在要做什么”，再进入对应文档，不需要理解全部代码。

## 1. 先选阅读路线

| 你的目的 | 第一入口 | 后续入口 |
|---|---|---|
| 了解产品有哪些模块 | 本文“产品模块” | `../admin-risk/docs/modules/` |
| 继续一个正在开发的任务 | 对应 GitHub Issue | `../tasks/issue-<编号>-<名称>.md` |
| 了解当前代码已经做到哪里 | `../docs/codex/current-state.md` | `../README.md` |
| 了解系统怎么连接 | `../docs/architecture/SYSTEM_MAP.md` | `../docs/architecture/README.md` |
| 修改数据库 | `../docs/database/README.md` | 对应 Owner 模块和迁移测试 |
| 修改 Platform–Runtime 通信 | `../docs/contracts/runtime-v1.json` | `../admin-risk/docs/architecture/integration/runtime-command-event-contract.md` |
| 了解 Git 和版本规则 | `../docs/engineering/GIT_WORKFLOW.md` | `../AGENTS.md` |
| 查看暂缓的技术问题 | `../docs/engineering/TECHNICAL_DEBT.md` | 对应 Issue |
| 进行实盘验收 | `../docs/operations/FAILURE_INJECTION_ACCEPTANCE.md` | `../docs/operations/V6-小资金实盘验收手册.md` |

## 2. 当前最重要结论

- `main` 是唯一正式代码基线，不存在第二套主版本。
- 当前系统由前端、Platform Backend 和独立 Execution Runtime 组成。
- 默认是 Simulation + Fake Gateway，Platform 和 Runtime Live Write 均关闭。
- 工程任务采用“一个 Issue、一个任务包、一个分支、一个 PR”。
- 新对话不再重读全仓，只读取当前状态、任务包和直接相关模块。
- 交易、风控、账务和数据库属于高风险边界，不能顺手重构。

精确当前状态以 `../docs/codex/current-state.md` 为准，不在本文硬编码容易过期的 PR 或 commit。

## 3. 产品模块

| 一级模块 | 定位 | 业务文档 | 当前方向 |
|---|---|---|---|
| 首页 | 品牌入口、摘要和导航 | `../admin-risk/docs/modules/首页-模块定位.md` | 保持简洁入口 |
| 对冲基金看板 | 宏观、资产类别和跨市场研究 | `../admin-risk/docs/modules/对冲基金看板-模块定位.md` | 后续完善数据和工具 |
| 新闻日历与理财 | 新闻、日历和理财信息筛选 | `../admin-risk/docs/modules/新闻日历与理财-模块定位.md` | 后续完善 |
| 策略 | 策略分析、交易、管理、统计和复盘 | `../admin-risk/docs/modules/策略-模块定位.md` | 当前核心业务模块 |
| 风险管理 | 账户、资金、权限、审计和监控 | `../admin-risk/docs/modules/风控管理-模块定位.md` | 支撑安全执行与生产门禁 |
| 金融AI分析 | 授权数据的归纳和结构化分析 | `../admin-risk/docs/modules/金融AI分析-模块定位.md` | 暂缓功能扩展 |

模块总表：`../admin-risk/docs/modules/一级模块定位总表.md`。

## 4. 策略模块

| 子模块 | 负责什么 | 需求文档 |
|---|---|---|
| 交易平台 | 行情、交易准备、指令和执行状态 | `../admin-risk/docs/modules/交易平台-需求文档.md` |
| 策略管理 | 实例、账户、订单、成交、持仓、费用、PnL、净值和复盘 | `../admin-risk/docs/modules/策略管理-需求文档.md` |

当前策略文档：

| 策略 | 文档 | 当前范围 |
|---|---|---|
| 资费套利 | `../admin-risk/docs/strategies/资费套利.md` | 分析、执行、成交、持仓、Funding、费用、PnL 和净值闭环 |
| 跨所价差 | `../admin-risk/docs/strategies/跨所价差.md` | Crypto/MT5 双腿、Deal、Swap、费用、PnL 和净值闭环 |
| 海内外价差 | `../admin-risk/docs/strategies/海内外价差.md` | 当前以分析、模拟和字段预留为主 |
| 抄底 | `../admin-risk/docs/strategies/抄底.md` | 策略管理入口和外部数据占位 |
| 短线交易员 L | `../admin-risk/docs/strategies/短线交易员L.md` | 策略管理入口和外部数据占位 |
| 短线交易员 W | `../admin-risk/docs/strategies/短线交易员W.md` | 策略管理入口和外部数据占位 |

## 5. 工程结构怎么理解

```text
admin-risk/
  用户看到的页面、API 客户端和交易交互

platform-backend/
  业务身份、权限、策略、风险、订单编排、账务和运营 API

execution-runtime/
  外部交易所/Broker 适配、命令 Journal、真实外部副作用

docs/
  当前状态、架构、技术合同、数据库、运维和工程规则

tasks/
  每个 Issue 的最小上下文和跨会话进度
```

最简系统图：`../docs/architecture/SYSTEM_MAP.md`。

## 6. 如何继续一个任务

只需要给新的对话或 Agent：

```text
仓库：wuxingyuenan5-lgtm/Platform_Experiment
Issue：#<编号>
任务包：tasks/issue-<编号>-<名称>.md
先核验 main、Issue、分支和开放 PR，再继续。
```

不需要粘贴全部旧聊天，也不要让 Agent 默认扫描所有目录。

## 7. 哪些文档不要先读

- `admin-risk/docs/archive/`：历史资料。
- `admin-risk/docs/audit/`：盘点和旧债记录。
- 带 `DRAFT` 的架构文档：讨论稿，不是当前事实。
- `outputs/`：临时产物，不是权威来源。
- 关闭 PR 的完整讨论：只在追溯历史时读取。

## 8. 文档的权威顺序

1. `AGENTS.md`：永久硬规则。
2. `docs/codex/current-state.md`：当前工程事实。
3. 当前 `tasks/issue-*.md`：这次任务范围和进度。
4. 对应模块文档和代码。
5. 架构决策、技术合同和运维手册。
6. README、Changelog 和历史计划。

发生冲突时，不要猜测；核验 `main`、Issue、PR、代码和测试，再更新过期文档。
