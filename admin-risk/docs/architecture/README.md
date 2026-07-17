# Platform V6+ 架构文档入口

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6+  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：架构入口

## 1. 文档定位

本目录定义 Variable-Global 的技术架构。

- 产品功能由 `docs/modules/` 和 `docs/strategies/` 管理。
- 视觉要求由 `docs/design/` 管理。
- 术语和文档状态由 `docs/governance/` 管理。
- 本目录说明系统如何组织、各层如何协作、业务对象由谁负责以及安全可靠性要求。

总体目标架构以 `platform-target-architecture.md` 为当前 active 唯一入口。

## 2. 四个不同维度

平台必须区分：

### 2.1 六个一级产品模块

1. 首页。
2. 对冲基金看板。
3. 新闻日历与理财。
4. 策略。
5. 风险管理。
6. 金融AI分析，当前冻结。

产品模块决定用户入口，不直接决定技术服务、数据库和代码包。

### 2.2 四类架构文档视角

ADR-005 继续有效：

1. 前端架构。
2. 后端架构。
3. 前后端协作架构。
4. 公共领域模型。

### 2.3 六层逻辑职责

总体目标架构采用：

1. 产品与交互层。
2. 平台应用与控制层。
3. 核心业务领域层。
4. 交易执行与连接层。
5. 数据、账本与查询层。
6. 运行保障与基础设施层。

六层不代表六个服务或六个部署单元。

### 2.4 三个初期工程主体

```text
admin-risk
+
platform-backend
+
execution-runtime
```

- `admin-risk`：Vue 前端。
- `platform-backend`：模块化单体业务后端。
- `execution-runtime`：独立交易执行、Gateway 和 Worker 运行时。

## 3. 当前 active 目标结构

```text
Browser
  ↓ Query / Command / Subscription
admin-risk
  ↓ REST / WebSocket / SSE
Platform API / BFF
  ↓
Application Modules
  ↓
Domain Modules
  ↓ Repository / Query / Command / Event Ports
Platform Persistence and Read Models
  ↓ Runtime Command / Event Contract
Execution Runtime
  ├─ Crypto Gateway Worker(s)
  ├─ MT5 Worker(s)
  └─ CTP Worker(s)，后续
       ↓
External Trading Systems
```

关键原则：

- Platform Backend 采用模块化单体。
- Execution Runtime 必须独立于 Platform API 进程。
- 开发和初期部署可以同机，但不得合并为同一进程。
- Platform Backend 不直接导入 Broker、Exchange、MetaTrader5 和 CTP SDK。
- Runtime OMS 不是永久业务数据库。
- Read Model 不是业务写入权威。
- 外部组件通过 Adapter／Port 接入。

## 4. 总体架构

核心文档：

- `platform-target-architecture.md`
- `module-ownership-matrix.md`
- `security-observability-and-operations.md`
- `2026-07-17-开源与外部能力采用矩阵-DRAFT.md`

总体架构负责：

- 产品模块、架构视角、逻辑分层和工程主体的关系。
- Platform Backend 与 Execution Runtime 的边界。
- Command、Event、数据权威、恢复和对账原则。
- 外部组件采用边界。

## 5. 前端架构

核心文档：

- `frontend/frontend-overview.md`
- `frontend/routing-permission-and-environment.md`
- `frontend/data-adapter-and-view-model.md`
- `frontend-state-ownership.md`
- `frontend/全局导航运行上下文与统一状态-DRAFT.md`
- `shared-ui-governance.md`
- `strategy-registry.md`

核心原则：

- 路由表达可恢复主上下文。
- 页面不直接依赖 API DTO 和大型 Mock。
- DeploymentEnvironment、TradingMode 和 TradingPermissionState 分开。
- 权限展示不替代后端校验。
- Domain Model、View Model 和请求状态分开。
- 实时 Event 不是页面恢复的唯一来源。

前端内部：

```text
Router
→ Module Shell
→ Page Orchestrator
→ Use Case / Composable
→ Domain Model / View Model
→ Repository Interface
→ Mock Adapter / API Adapter
```

## 6. 后端架构

核心文档：

- `backend/backend-overview.md`
- `backend/service-boundaries.md`
- `backend/trading-execution-reliability.md`
- `backend/storage-ledger-and-audit.md`
- `backend/query-and-read-models.md`
- `backend/research-data-and-content-boundaries.md`

核心原则：

- Platform Backend 采用模块化单体。
- 每个对象具有唯一主责模块。
- StrategyAccountBinding 归 Strategy，Account 主档归 Account。
- Execution Market Data、Research Data 和 Content and Calendar Data 分开。
- Strategy Economic Ledger 不等于完整财务会计总账。
- Backend Read Model 不形成第二套数据权威。
- Broker SDK 和 Runtime 内部实现不进入 Domain 层。

## 7. Execution Runtime 与外部接入

总体边界已经由 ADR-008 接受。

后续专项文档需要继续形成：

- Runtime Definition、Instance、Session 和 Worker。
- Gateway Definition、Runtime 和 Capability。
- Runtime Command／Event Envelope。
- Runtime Local Journal。
- MT5 Worker 和 Terminal 管理。
- Crypto Gateway 和账户模式。
- 后续 CTP Gateway、平今平昨和交易日。
- 启动同步、对账、恢复和 READY。
- 外部手工订单和结果未知。

当前已确认：

- Crypto 与 MT5 属于初期目标接入。
- CTP 可以延后。
- Runtime 独立进程不等于立即采用微服务或多机部署。

## 8. 前后端协作架构

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
- 外部操作结果未知时不得盲目重复执行。

交易链路：

```text
TradeIntent
→ TradeCommand
→ ExecutionBatch
→ ExecutionPlan
→ LegInstruction
→ pre-created Order
→ Runtime Command
→ External Order
→ Runtime Event
→ platform Order / Fill / Position
```

## 9. 公共领域模型

核心文档：

- `domain/domain-overview.md`
- `domain-model-boundaries.md`
- `domain/status-enums-and-lifecycles.md`
- `domain/approval-and-dual-control.md`

核心原则：

- DTO、Domain Model、ORM Model、Backend Read Model、API DTO 和 View Model 分开。
- TradeCommand 表达命令受理，ExecutionBatch 表达执行过程。
- Order、Fill、Position、Exposure、PnL 和 Risk 分开。
- ExecutionBalanceStatus 不表示账户余额。
- 权限、审批、风险和审计不能互相替代。

下一批需要正式补充：

- ExecutionPlan。
- RuntimeDefinition／RuntimeInstance／RuntimeSession。
- GatewayDefinition／GatewayRuntime／GatewayCapability。
- RecoveryRun。
- RuntimeCommandEnvelope／RuntimeEventEnvelope。
- ExternalOrderReference。
- ExternalExecutionProfile。
- SignalRecord 和 ViolationRecord。

## 10. 数据权威速查

| 内容 | 主责 |
|---|---|
| 用户、角色、Capability 和 Data Scope | IAM |
| 策略定义、版本、实例和账户绑定 | Strategy |
| 平台交易命令、批次、腿和平台订单 | Trading and Execution |
| 外部订单、成交、余额和持仓事实 | 外部交易系统；平台标准化并持久化 |
| 账户主档、余额、保证金和持仓 | Account and Position |
| 风险规则、判断和事件 | Risk |
| 对账和数据质量 | Reconciliation and Data Quality |
| EconomicEvent、策略账本和 PnL | PnL and Strategy Economic Ledger |
| Runtime、Gateway 和 Worker 实时状态 | Execution Runtime |
| 查询聚合 | Query and Read Models，非写入权威 |
| 审计证据 | Audit |

## 11. 外部组件

中央讨论文档：

- `2026-07-17-开源与外部能力采用矩阵-DRAFT.md`

当前原则：

- 按能力采用，不整体采用某一仓库。
- 平台自建业务领域模型和数据权威。
- vn.py 可优先 PoC EventEngine、OmsEngine、CTP、Spread、Algo 和底层 Risk 能力。
- CCXT 可优先 PoC Crypto 公共行情、元数据和部分私有接口。
- MetaTrader5 官方包作为 MT5 基础访问候选。
- aiomql、NautilusTrader、rotki 和 Freqtrade 主要提供局部实现或设计参考。
- 所有正式采用需要 PoC、许可证、安全、恢复、对账和必要 ADR。

## 12. 产品需求与策略文档

产品架构入口：

- `../modules/一级模块定位总表.md`
- `../modules/首页-需求文档.md`
- `../modules/对冲基金看板-需求文档.md`
- `../modules/新闻日历与理财-需求文档.md`
- `../modules/策略-需求文档.md`
- `../modules/交易平台-需求文档.md`
- `../modules/策略管理-需求文档.md`
- `../modules/风控管理-需求文档.md`

策略文档：

- `../strategies/资费套利.md`
- `../strategies/跨所价差.md`
- `../strategies/海内外价差.md`
- `../strategies/抄底.md`
- `../strategies/短线交易员L.md`
- `../strategies/短线交易员W.md`

技术设计必须以对应产品和策略需求为前置输入。

金融AI分析继续保留一级产品模块，但当前冻结专项需求、架构、领域对象和开发安排。

## 13. 架构决策

- `decisions/ADR-001-一级架构保持不变.md`
- `decisions/ADR-002-交易平台与策略管理策略范围不同.md`
- `decisions/ADR-003-策略注册表作为唯一策略定义来源.md`
- `decisions/ADR-004-交易工具由Markdown生成.md`
- `decisions/ADR-005-技术架构分层.md`
- `decisions/ADR-006-后端优先采用模块化单体.md`
- `decisions/ADR-007-部署环境与交易模式分离.md`
- `decisions/ADR-008-总体逻辑分层与独立交易Runtime.md`

历史 ADR 不直接覆盖修改；新的 accepted ADR 通过说明补充或替代关系生效。

## 14. 当前成熟度

| 层级 | 当前状态 |
|---|---|
| 产品架构 | 当前推进的五个模块和六份策略需求已完成第一轮深化；金融AI冻结 |
| 总体架构 | 六层逻辑职责、三个工程主体和独立 Runtime 已形成 active 基线 |
| 前端架构 | 规范已形成，代码仍需逐步接入 |
| 后端架构 | 模块化单体和领域边界已形成，需同步独立 Runtime 契约 |
| 公共领域模型 | 主要业务对象已形成，Runtime／Gateway 对象待正式补充 |
| 前后端协作 | 基础契约已形成，具体 OpenAPI 和 Runtime Envelope 尚未建立 |
| 实盘能力 | 尚未接入，不具备真实交易条件 |

## 15. 文档读取顺序

### 页面与前端任务

1. 对应模块需求。
2. 对应策略文档，适用时。
3. `platform-target-architecture.md`。
4. 前端架构文档。
5. 协作契约。
6. 相关代码。

### 后端领域任务

1. 对应模块和策略需求。
2. `platform-target-architecture.md`。
3. 公共领域对象和状态。
4. `backend/service-boundaries.md`。
5. 对应后端专题。
6. 协作契约和 ADR。

### Runtime 与 Gateway 任务

1. 对应策略需求。
2. `platform-target-architecture.md`。
3. ADR-008。
4. 开源与外部能力采用矩阵。
5. Runtime 与 Gateway 专项架构。
6. PoC 和采用 ADR。

## 16. Draft 与暂缓内容

以下内容为 draft，不自动覆盖 active 架构：

- `implementation-roadmap.md`
- `2026-07-17-Variable-Global交易平台总体架构方案-DRAFT.md`
- `2026-07-17-初创阶段可落地架构方案-DRAFT.md`
- `2026-07-17-开源与外部能力采用矩阵-DRAFT.md`
- `2026-07-16-平台新增功能初步方案-DRAFT.md`

其中总体架构讨论稿中已经确认的部分，已通过 `platform-target-architecture.md` 和 ADR-008 进入 active 架构；未确认技术选型仍保留为 draft。

以下文件为 superseded：

- `2026-07-16-vnpy平台架构初步方案-DRAFT.md`

金融AI分析暂缓范围见：

- `2026-07-17-金融AI分析暂缓说明-DRAFT.md`
