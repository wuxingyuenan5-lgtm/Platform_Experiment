# Platform V6 架构文档入口

状态：`active`  
适用分支：`refactor/frontend-architecture-v6`

## 1. 文档定位

本目录定义 Platform V6 的技术架构。产品模块、页面功能和视觉要求分别由 `docs/modules/`、`docs/strategies/` 和 `docs/design/` 管理；本目录重点说明系统如何组织、各层如何协作、业务对象由谁负责，以及平台如何从前端原型逐步演进到受控实盘。

V6 技术架构划分为四层：

1. 前端架构。
2. 后端架构。
3. 前后端协作架构。
4. 公共领域模型。

安全、可观测性、数据治理和实施路线作为跨层规范管理。

四层必须分别设计，但使用统一的策略、账户、订单、成交、持仓、损益和风险语义。

## 2. 产品架构与技术架构的关系

平台继续保持六个一级产品模块：

- 首页。
- 对冲基金看板。
- 新闻日历与理财。
- 策略。
- 风险管理。
- 金融 AI。

一级模块决定用户从哪里进入功能，不直接决定后端服务、数据库表或代码包的归属。

例如：

- “账户与资产”可以位于风险管理菜单内，但技术上属于 Account／Asset 领域。
- “用户与权限”可以位于风险管理菜单内，但技术上属于 IAM／Permission 领域。
- “审计”可以位于风险管理菜单内，但技术上属于 Audit 领域。

必须区分：

| 维度 | 回答的问题 | 主要文档 |
|---|---|---|
| 产品归属 | 用户从哪里进入、页面服务什么任务 | `docs/modules/`、`module-ownership-matrix.md` |
| 前端归属 | 路由、页面、组件和状态如何组织 | `frontend/` |
| 后端归属 | 业务规则、服务、存储和可靠性由谁负责 | `backend/` |
| 协作契约 | 前后端如何交换命令、查询、事件和错误 | `integration/` |
| 领域归属 | Strategy、Order、PnL 等对象的共同语义 | `domain/`、`domain-model-boundaries.md` |
| 跨层治理 | 安全、监控、发布、恢复和实施顺序 | 本目录跨层文档 |

## 3. 架构总览

### 3.1 前端架构

负责：

- 路由和页面装配。
- 页面、模块和全局状态。
- 用户输入、交互反馈和权限结果展示。
- 图表、表格和 Design Token。
- API／Mock 数据适配。
- 前端构建、测试和发布门槛。

核心文档：

- `frontend/frontend-overview.md`
- `frontend/routing-permission-and-environment.md`
- `frontend/data-adapter-and-view-model.md`
- `frontend-state-ownership.md`
- `shared-ui-governance.md`
- `strategy-registry.md`

### 3.2 后端架构

负责：

- 身份认证和权限判定。
- 行情、账户、持仓、订单、成交和执行服务。
- 损益、风险、对账、审计和数据质量。
- 数据存储、事件处理、任务调度和系统恢复。
- 交易所、经纪商和其他外部系统接入。

核心文档：

- `backend/backend-overview.md`
- `backend/service-boundaries.md`
- `backend/trading-execution-reliability.md`
- `backend/storage-ledger-and-audit.md`

当前后端目标采用模块化单体，并为交易执行、Gateway、行情接入和重型异步任务保留独立进程边界。

当前文档不提前绑定 vn.py、数据库或消息队列等具体技术方案。

### 3.3 前后端协作架构

负责：

- API、WebSocket 和 SSE 边界。
- 命令、查询和事件的区别。
- 鉴权、权限、幂等、错误码和版本兼容。
- 时间、币种、单位、分页和状态枚举。
- 实时事件、断线重连和权威状态恢复。
- Mock 数据向真实接口迁移的方式。

核心文档：

- `integration/frontend-backend-integration.md`
- `integration/api-contract-and-versioning.md`
- `integration/realtime-events-and-recovery.md`

### 3.4 公共领域模型

负责：

- 定义前后端共同理解的业务对象。
- 区分订单、成交、执行批次、持仓和损益。
- 定义对象身份、状态、生命周期和关联关系。
- 避免页面字段或接口字段直接成为业务模型。

核心文档：

- `domain/domain-overview.md`
- `domain-model-boundaries.md`
- `domain/status-enums-and-lifecycles.md`

### 3.5 跨层规范

- `module-ownership-matrix.md`：产品归属、技术领域和数据权威。
- `security-observability-and-operations.md`：安全、日志、指标、追踪、告警、发布和恢复。
- `implementation-roadmap.md`：从当前前端原型到受控实盘的分阶段路线。
- `strategy-capability-matrix.md`：策略页面能力。

## 4. 当前目标架构

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

双腿交易核心链路：

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
  ↓
Position / Exposure / PnL
```

## 5. 当前架构状态

| 层级 | 当前成熟度 | 说明 |
|---|---|---|
| 产品架构 | 已形成正式基线 | 六个一级模块和核心职责已确认 |
| 前端架构 | 详细规范已形成，代码待接入 | 页面仍存在 V5 硬编码、Mock 直连和大型组件 |
| 公共领域模型 | 核心模型和生命周期已形成 | 后续需结合具体接口和策略继续校验 |
| 前后端协作 | 契约、实时和恢复规范已形成 | 尚未形成具体 OpenAPI 接口清单 |
| 后端架构 | 模块、交易可靠性和存储边界已形成 | 真实服务、数据库和 Gateway 尚未实现 |
| 安全与运维 | 目标规范已形成 | 具体工具、SLO、RPO 和 RTO 尚待实施阶段确认 |

## 6. 架构决策

当前有效 ADR：

- `decisions/ADR-001-一级架构保持不变.md`
- `decisions/ADR-002-交易平台与策略管理策略范围不同.md`
- `decisions/ADR-003-策略注册表作为唯一策略定义来源.md`
- `decisions/ADR-004-交易工具由Markdown生成.md`
- `decisions/ADR-005-技术架构分层.md`
- `decisions/ADR-006-后端优先采用模块化单体.md`

具体交易内核、数据库、消息队列、Gateway 和实盘部署方式仍需专项方案和新 ADR。

## 7. 文档使用顺序

### 7.1 前端页面任务

1. `docs/README.md`
2. 对应模块和策略文档
3. `frontend/frontend-overview.md`
4. `frontend/routing-permission-and-environment.md`
5. `frontend-state-ownership.md`
6. `frontend/data-adapter-and-view-model.md`
7. `shared-ui-governance.md`
8. 相关代码

### 7.2 后端模块设计任务

1. 对应模块和策略需求
2. `domain/domain-overview.md`
3. `domain-model-boundaries.md`
4. `domain/status-enums-and-lifecycles.md`
5. `backend/backend-overview.md`
6. `backend/service-boundaries.md`
7. 相关专项文档
8. ADR

### 7.3 交易执行任务

1. `modules/交易平台-需求文档.md`
2. 对应策略文档
3. `domain-model-boundaries.md`
4. `domain/status-enums-and-lifecycles.md`
5. `backend/trading-execution-reliability.md`
6. `integration/api-contract-and-versioning.md`
7. `integration/realtime-events-and-recovery.md`
8. 安全、审计和测试方案

### 7.4 前后端接口任务

1. 对应业务需求
2. `domain-model-boundaries.md`
3. `domain/status-enums-and-lifecycles.md`
4. `integration/frontend-backend-integration.md`
5. `integration/api-contract-and-versioning.md`
6. 前端 View Model 和后端 API DTO
7. 具体 OpenAPI 契约

### 7.5 数据、账本和审计任务

1. 对应策略损益和账户需求
2. `domain-model-boundaries.md`
3. `backend/storage-ledger-and-audit.md`
4. `module-ownership-matrix.md`
5. 数据库和迁移专项方案

### 7.6 发布和运维任务

1. `security-observability-and-operations.md`
2. `implementation-roadmap.md`
3. `docs/quality/release-gate.md`
4. `docs/quality/smoke-checklist.md`
5. 环境专项部署方案

## 8. 实施顺序

架构实施按 `implementation-roadmap.md` 分阶段推进：

0. 文档与前端代码基线对齐。
1. 公共领域与接口契约。
2. 后端基础与身份权限。
3. 只读数据服务。
4. 模拟交易执行。
5. 测试网、沙盒或 Paper Trading。
6. 受控小范围实盘。
7. 扩展策略、账户和 Gateway。

当前最优先是阶段 0，不直接开始实盘交易系统。

## 9. 治理原则

- 产品导航变化、技术服务拆分和数据库设计是不同决策，不得混为一体。
- 前端不得成为订单、账户、损益和风险的最终数据权威。
- 后端不得通过接口字段结构直接控制页面布局。
- 公共领域模型只定义稳定业务语义，不包含页面样式和数据库实现细节。
- 查询、命令和事件必须分开。
- 订单、成交、执行批次、配平、风险和数据质量状态必须分开。
- 演示、模拟、测试、Paper 和实盘环境必须明确隔离。
- 具体技术选型通过专项方案和 ADR 确认。
- `DRAFT` 文档不替代本入口列出的 `active` 规范。
