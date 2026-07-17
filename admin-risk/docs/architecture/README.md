# Platform V6 架构文档入口

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：架构入口

## 1. 文档定位

本目录定义 Platform V6 技术架构。产品功能由 `docs/modules/` 和 `docs/strategies/` 管理，视觉要求由 `docs/design/` 管理；本目录说明系统如何组织、各层如何协作、业务对象由谁负责以及安全可靠性要求。

V6 技术架构分为：

1. 前端架构。
2. 后端架构。
3. 前后端协作架构。
4. 公共领域模型。
5. 跨层安全、可观测性和治理。

## 2. 产品架构与技术架构

平台保持六个一级产品模块：

- 首页。
- 对冲基金看板。
- 新闻日历与理财。
- 策略。
- 风险管理。
- 金融AI分析。

正式模块名称以 `docs/governance/glossary.md` 为唯一来源。

一级模块决定用户从哪里进入功能，不直接决定后端服务、数据库表或代码包归属。

| 维度 | 回答的问题 | 主要文档 |
|---|---|---|
| 产品归属 | 用户从哪里进入、页面服务什么任务 | `docs/modules/`、`module-ownership-matrix.md` |
| 前端归属 | 路由、页面、组件和状态如何组织 | `frontend/` |
| 后端归属 | 规则、模块、存储和可靠性由谁负责 | `backend/` |
| 协作契约 | API、Command、Query、Event 和错误如何交换 | `integration/` |
| 领域归属 | Strategy、Order、PnL 等对象的共同语义 | `domain/`、`domain-model-boundaries.md` |
| 跨层治理 | 安全、监控、发布、恢复和文档治理 | 本目录跨层文档、`docs/governance/` |

## 3. 当前目标结构

```text
Vue Frontend
    ↓ Query / Command / Subscription
Platform API / BFF
    ↓
Application Modules
    ↓
Domain Modules
    ↓
Repository / Event / Gateway Ports
    ↓
Database / Cache / External Gateways
```

前端内部：

```text
Router
  ↓
Module Shell
  ↓
Page Orchestrator
  ↓
Use Case / Composable
  ↓
Domain Model / View Model
  ↓
Repository Interface
  ↓
Mock Adapter / API Adapter
```

双腿交易：

```text
TradeIntent
  ↓
TradeCommand
  ↓
ExecutionBatch
  ↓
LegInstruction
  ↓
Order
  ↓
Execution / Fill
```

## 4. 前端架构

核心文档：

- `frontend/frontend-overview.md`
- `frontend/routing-permission-and-environment.md`
- `frontend/data-adapter-and-view-model.md`
- `frontend-state-ownership.md`
- `shared-ui-governance.md`
- `strategy-registry.md`

核心原则：

- 路由表达可恢复主上下文。
- 页面不直接依赖 API DTO 和大型 Mock。
- DeploymentEnvironment、TradingMode 和 TradingPermissionState 分开。
- 权限展示不替代后端校验。
- Domain Model、View Model 和请求状态分开。

## 5. 后端架构

核心文档：

- `backend/backend-overview.md`
- `backend/service-boundaries.md`
- `backend/trading-execution-reliability.md`
- `backend/storage-ledger-and-audit.md`
- `backend/query-and-read-models.md`
- `backend/research-data-and-content-boundaries.md`

当前后端优先采用模块化单体，并为 Gateway、交易执行、行情接入和重型异步任务保留独立进程边界。

核心原则：

- 每个对象具有唯一主责模块。
- StrategyAccountBinding 归 Strategy，Account 主档归 Account。
- Execution Market Data、Research Data 和 Content and Calendar Data 分开。
- Strategy Economic Ledger 不等于完整财务会计总账。
- Backend Read Model 不形成第二套数据权威。

## 6. 前后端协作架构

核心文档：

- `integration/frontend-backend-integration.md`
- `integration/api-contract-and-versioning.md`
- `integration/realtime-events-and-recovery.md`

核心原则：

- Query、Command 和 Event 分开。
- 命令已受理不等于交易已完成。
- API 具备稳定错误码、幂等和版本策略。
- 实时通道不是唯一数据来源。
- 断线后通过权威 Query 恢复状态。

## 7. 公共领域模型

核心文档：

- `domain/domain-overview.md`
- `domain-model-boundaries.md`
- `domain/status-enums-and-lifecycles.md`
- `domain/approval-and-dual-control.md`

核心原则：

- DTO、Domain Model、Backend Read Model、API DTO 和 View Model 分开。
- TradeCommand 只表达命令受理，ExecutionBatch 表达执行过程。
- Order、Fill、Position、Exposure、PnL 和 Risk 分开。
- ExecutionBalanceStatus 不表示账户余额。
- 权限、审批、风险和审计不能相互替代。

## 8. 产品模块文档完整性

产品架构入口：

- `../modules/一级模块定位总表.md`

六个一级模块均已具备定位和需求文档：

- 首页。
- 对冲基金看板。
- 新闻日历与理财。
- 策略。
- 风险管理。
- 金融AI分析。

策略下的交易平台和策略管理继续具有独立完整定位和需求文档。

架构文档不重新定义具体页面功能；技术设计必须以对应产品需求为前置输入。

## 9. 跨层规范

- `module-ownership-matrix.md`：产品归属、技术领域和数据权威。
- `strategy-capability-matrix.md`：策略页面能力。
- `security-observability-and-operations.md`：安全、日志、指标、告警、发布和恢复。
- `../governance/document-rules.md`：文档状态、元数据和唯一来源。
- `../governance/glossary.md`：统一术语。

## 10. 架构决策

- `decisions/ADR-001-一级架构保持不变.md`
- `decisions/ADR-002-交易平台与策略管理策略范围不同.md`
- `decisions/ADR-003-策略注册表作为唯一策略定义来源.md`
- `decisions/ADR-004-交易工具由Markdown生成.md`
- `decisions/ADR-005-技术架构分层.md`
- `decisions/ADR-006-后端优先采用模块化单体.md`
- `decisions/ADR-007-部署环境与交易模式分离.md`

## 11. 唯一事实来源速查

| 内容 | 主文档 |
|---|---|
| 产品模块完整性 | `../modules/一级模块定位总表.md` |
| 公共对象 | `domain-model-boundaries.md` |
| 状态枚举和生命周期 | `domain/status-enums-and-lifecycles.md` |
| 模块所有权 | `backend/service-boundaries.md` |
| 产品归属和数据权威 | `module-ownership-matrix.md` |
| 交易可靠性 | `backend/trading-execution-reliability.md` |
| API、错误、幂等和版本 | `integration/api-contract-and-versioning.md` |
| 实时事件和恢复 | `integration/realtime-events-and-recovery.md` |
| 审批和 Maker／Checker | `domain/approval-and-dual-control.md` |
| 研究、行情和内容数据 | `backend/research-data-and-content-boundaries.md` |
| Backend Read Model | `backend/query-and-read-models.md` |
| 中文术语 | `../governance/glossary.md` |

## 12. 当前成熟度

| 层级 | 当前状态 |
|---|---|
| 产品架构 | 六个一级模块定位和需求已形成正式基线 |
| 前端架构 | 规范已形成，代码仍需逐步接入 |
| 公共领域模型 | 主要对象、状态和审批边界已形成 |
| 前后端协作 | 基础契约已形成，具体 OpenAPI 尚未建立 |
| 后端架构 | 逻辑边界已形成，真实服务和存储尚未建设 |
| 实盘能力 | 尚未接入，不具备真实交易条件 |

## 13. 文档读取顺序

### 前端页面任务

1. `docs/README.md`
2. 对应模块定位和需求
3. 对应策略文档，适用时
4. 前端架构文档
5. 共享 UI 规范
6. 相关代码

### 后端领域任务

1. 对应模块和策略需求
2. 公共领域对象和状态
3. 服务边界
4. 对应后端专题
5. 协作契约
6. 专项技术方案和 ADR

### API 和实时任务

1. 对应产品需求
2. 公共领域模型
3. 前后端协作总览
4. API 契约
5. 实时事件与恢复
6. 具体 OpenAPI 和事件契约

## 14. 暂不生效内容

以下文档为 draft，不进入 active 架构：

- `implementation-roadmap.md`
- `2026-07-16-vnpy平台架构初步方案-DRAFT.md`
- `2026-07-16-平台新增功能初步方案-DRAFT.md`
