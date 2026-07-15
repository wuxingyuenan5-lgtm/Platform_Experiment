# Platform V6 架构文档入口

状态：`active`  
适用分支：`refactor/frontend-architecture-v6`

## 1. 文档定位

本目录用于定义 Platform V6 的技术架构。产品模块、页面功能和视觉要求分别由 `docs/modules/`、`docs/strategies/` 和 `docs/design/` 管理；本目录重点说明系统如何组织、各层如何协作以及业务对象由谁负责。

V6 技术架构划分为四层：

1. 前端架构。
2. 后端架构。
3. 前后端协作架构。
4. 公共领域模型。

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

- “账户与资产”可以位于风险管理菜单内，但技术上仍属于 Account／Asset 领域。
- “用户与权限”可以位于风险管理菜单内，但技术上属于 IAM／Permission 领域。
- “审计”可以位于风险管理菜单内，但技术上属于 Audit 领域。

因此必须区分：

| 维度 | 回答的问题 | 主要文档 |
|---|---|---|
| 产品归属 | 用户从哪里进入、页面服务什么任务 | `docs/modules/`、`module-ownership-matrix.md` |
| 前端归属 | 路由、页面、组件和状态如何组织 | `frontend/` |
| 后端归属 | 业务规则、服务、存储和可靠性由谁负责 | `backend/` |
| 协作契约 | 前后端如何交换命令、查询、事件和错误 | `integration/` |
| 领域归属 | Strategy、Order、PnL 等对象的共同语义 | `domain/`、`domain-model-boundaries.md` |

## 3. 四层技术架构

### 3.1 前端架构

负责：

- 路由和页面装配。
- 页面、模块和全局状态。
- 用户输入、交互反馈和权限结果展示。
- 图表、表格和 Design Token。
- API／Mock 数据适配。
- 前端构建、测试和发布门槛。

入口：

- `frontend/frontend-overview.md`
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

入口：

- `backend/backend-overview.md`

当前文档只确定稳定边界和建设原则，不提前绑定 vn.py、数据库或消息队列等具体技术方案。

### 3.3 前后端协作架构

负责：

- API 和 WebSocket 边界。
- 命令、查询和事件的区别。
- 鉴权、权限、幂等、错误码和版本兼容。
- 时间、币种、单位、分页和状态枚举。
- Mock 数据向真实接口迁移的方式。

入口：

- `integration/frontend-backend-integration.md`

### 3.4 公共领域模型

负责：

- 定义前后端共同理解的业务对象。
- 区分订单、成交、执行批次、持仓和损益。
- 定义对象身份、生命周期和关联关系。
- 避免页面字段或接口字段直接成为业务模型。

入口：

- `domain/domain-overview.md`
- `domain-model-boundaries.md`

## 4. 当前架构状态

| 层级 | 当前成熟度 | 说明 |
|---|---|---|
| 产品架构 | 已形成正式基线 | 六个一级模块和核心职责已确认 |
| 前端架构 | 已有规范，代码逐步接入 | 页面仍存在 V5 硬编码和大型组件 |
| 公共领域模型 | 初步建立 | 需逐步补齐执行批次、报价快照和对账等对象 |
| 前后端协作 | 建立基础规范 | 尚未形成具体接口清单和 OpenAPI 契约 |
| 后端架构 | 目标边界已定义 | 真实服务、存储和交易接入尚未建设 |

## 5. 当前有效架构规范

### 5.1 跨层规范

- `module-ownership-matrix.md`
- `strategy-capability-matrix.md`
- `domain-model-boundaries.md`

### 5.2 前端规范

- `frontend/frontend-overview.md`
- `frontend-state-ownership.md`
- `shared-ui-governance.md`
- `strategy-registry.md`

### 5.3 后端规范

- `backend/backend-overview.md`

### 5.4 协作规范

- `integration/frontend-backend-integration.md`

### 5.5 领域规范

- `domain/domain-overview.md`
- `domain-model-boundaries.md`

### 5.6 架构决策

- `decisions/ADR-001-一级架构保持不变.md`
- `decisions/ADR-002-交易平台与策略管理策略范围不同.md`
- `decisions/ADR-003-策略注册表作为唯一策略定义来源.md`
- `decisions/ADR-004-交易工具由Markdown生成.md`
- `decisions/ADR-005-技术架构分层.md`

## 6. 文档使用顺序

### 前端页面任务

1. `docs/README.md`
2. 对应模块和策略文档
3. `frontend/frontend-overview.md`
4. `frontend-state-ownership.md`
5. `shared-ui-governance.md`
6. 相关代码

### 后端设计任务

1. 对应模块和策略文档
2. `domain/domain-overview.md`
3. `domain-model-boundaries.md`
4. `backend/backend-overview.md`
5. `integration/frontend-backend-integration.md`
6. 专项技术方案和 ADR

### 前后端接口任务

1. 对应业务需求
2. `domain-model-boundaries.md`
3. `integration/frontend-backend-integration.md`
4. 前端 View Model 和后端 API DTO
5. 具体接口契约

## 7. 治理原则

- 产品导航变化、技术服务拆分和数据库设计是不同决策，不得混为一体。
- 前端不得成为订单、账户、损益和风险的最终数据权威。
- 后端不得通过接口字段结构直接控制页面布局。
- 公共领域模型只定义稳定业务语义，不包含页面样式和数据库实现细节。
- 具体技术选型应通过专项方案和 ADR 确认。
- `DRAFT` 文档不替代本入口列出的 `active` 规范。
