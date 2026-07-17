# Platform V6+ 架构文档入口

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6+  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：架构入口

## 1. 文档定位

本目录定义 Variable-Global 技术架构。

- 产品需求：`docs/modules/`。
- 策略专项需求：`docs/strategies/`。
- 技术架构：本目录。
- 视觉要求：`docs/design/`。
- 术语和文档治理：`docs/governance/`。

总体目标架构以 `platform-target-architecture.md` 为 active 入口。

## 2. 四个不同维度

平台必须区分：

### 2.1 六个一级产品模块

1. 首页。
2. 对冲基金看板。
3. 新闻日历与理财。
4. 策略。
5. 风险管理。
6. 金融AI分析，当前冻结。

产品模块决定用户入口，不直接决定服务、数据库和代码包。

### 2.2 四类架构文档视角

ADR-005 定义：

1. 前端架构。
2. 后端架构。
3. 前后端协作架构。
4. 公共领域模型。

### 2.3 六层逻辑职责

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

核心结论：

- Platform Backend 采用模块化单体。
- Execution Runtime 独立于 Platform API 进程。
- 开发和初期部署可以同机，但不得合并进程和故障边界。
- Platform Backend 不直接导入 Broker、Exchange、MetaTrader5 和 CTP SDK。
- Runtime OMS 和 Local Journal 不形成平台永久业务权威。
- Read Model 不形成业务写入权威。
- 外部组件通过 Adapter／Port 接入。

## 4. 总体架构

- `platform-target-architecture.md`：总体逻辑分层、工程主体、数据权威和演进原则。
- `module-ownership-matrix.md`：产品归属、技术领域和数据权威。
- `security-observability-and-operations.md`：跨层安全和运行治理。
- `2026-07-17-开源与外部能力采用矩阵-DRAFT.md`：外部能力候选和 PoC 边界。

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
- 实时 Event 不是恢复的唯一来源。

## 6. 后端架构

核心文档：

- `backend/backend-overview.md`
- `backend/service-boundaries.md`
- `backend/trading-execution-reliability.md`
- `backend/execution-runtime-and-gateway.md`
- `backend/storage-ledger-and-audit.md`
- `backend/query-and-read-models.md`
- `backend/research-data-and-content-boundaries.md`

核心原则：

- 每个对象只有一个主责模块。
- StrategyAccountBinding 归 Strategy，Account 主档归 Account。
- Trading 不直接连接外部交易系统。
- Execution Runtime 不拥有平台 ExecutionBatch、Risk 和 PnL。
- Execution Market Data、Research Data 和 Content Data 分开。
- Strategy Economic Ledger 不等于财务总账。
- 同库部署不允许跨模块任意写入。

## 7. Execution Runtime 与 Gateway

专项文档：

- `backend/execution-runtime-and-gateway.md`
- `backend/trading-execution-reliability.md`

已确认：

- Runtime Main 与 Worker 分层。
- MT5 和 Crypto 属于初期目标能力。
- CTP 可以延后。
- Port 和 GatewayCapability 按能力设计。
- platformOrderId 在外部提交前存在。
- Runtime 需要本地可靠 Journal。
- 采用至少一次传输、幂等和结果未知语义。
- 外部手工订单和未归属对象必须如实摄取。

待专项确认：

- Runtime 语言和进程框架。
- Command／Event 传输产品。
- Local Journal 技术。
- MT5 Worker 和 Terminal 资源模型。
- Crypto 使用 CCXT、官方 SDK 或组合 Adapter。
- 正式 Envelope Schema 和部署拓扑。

## 8. 前后端协作架构

核心文档：

- `integration/frontend-backend-integration.md`
- `integration/api-contract-and-versioning.md`
- `integration/realtime-events-and-recovery.md`

核心原则：

- Query、Command 和 Event 分开。
- Command accepted 不等于外部执行完成。
- API 具备稳定错误码、幂等和版本。
- 实时通道不是唯一数据来源。
- 断线后通过权威 Query 恢复。
- 结果未知时不得盲目重复操作。

统一交易链：

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

- DTO、Domain Model、ORM Model、Read Model 和 View Model 分开。
- TradeCommand 表达命令受理，ExecutionBatch 表达执行过程。
- Order、Fill、Position、Exposure、PnL 和 Risk 分开。
- 权限、审批、风险和审计不能互相替代。

下一批需要补充：

- ExecutionPlan。
- RuntimeDefinition／RuntimeInstance／RuntimeSession。
- GatewayDefinition／GatewayRuntime／GatewayCapability。
- WorkerDefinition／WorkerInstance。
- RecoveryRun。
- RuntimeCommandEnvelope／RuntimeEventEnvelope。
- ExternalOrderReference。
- ExternalExecutionProfile。
- SignalRecord 和 ViolationRecord。

## 10. 数据权威速查

| 内容 | 主责 |
|---|---|
| 用户、Capability 和 Data Scope | IAM |
| 策略定义、版本、实例和账户绑定 | Strategy |
| 平台命令、批次、腿和平台订单 | Trading and Execution |
| 外部订单、成交、余额和持仓事实 | 外部交易系统；平台标准化并持久化 |
| 账户主档、余额、保证金和持仓 | Account and Position |
| 风险规则、判断和事件 | Risk |
| 对账和数据质量 | Reconciliation and Data Quality |
| EconomicEvent、策略账本和 PnL | PnL and Strategy Economic Ledger |
| Runtime、Gateway 和 Worker 实时状态 | Execution Runtime |
| 页面聚合 | Query and Read Models，非写入权威 |
| 审计证据 | Audit |

## 11. 外部组件

中央讨论文档：

- `2026-07-17-开源与外部能力采用矩阵-DRAFT.md`

当前原则：

- 按能力采用，不整体采用某一仓库。
- 平台自建业务模型和数据权威。
- vn.py 可 PoC EventEngine、OmsEngine、CTP、Spread、Algo 和底层 Risk。
- CCXT 可 PoC Crypto 公共行情、元数据和部分私有接口。
- MetaTrader5 官方包是 MT5 基础访问候选。
- aiomql、NautilusTrader、rotki 和 Freqtrade 提供局部实现或设计参考。
- 正式采用需要 PoC、许可证、安全、恢复、对账和必要 ADR。

## 12. 产品需求与策略文档

产品需求：

- `../modules/首页-需求文档.md`
- `../modules/对冲基金看板-需求文档.md`
- `../modules/新闻日历与理财-需求文档.md`
- `../modules/策略-需求文档.md`
- `../modules/交易平台-需求文档.md`
- `../modules/策略管理-需求文档.md`
- `../modules/风控管理-需求文档.md`

策略专项：

- `../strategies/资费套利.md`
- `../strategies/跨所价差.md`
- `../strategies/海内外价差.md`
- `../strategies/抄底.md`
- `../strategies/短线交易员L.md`
- `../strategies/短线交易员W.md`

金融AI分析保留一级产品模块，但当前冻结专项需求、架构、领域对象和开发安排。

## 13. 架构决策

- `decisions/ADR-001-一级架构保持不变.md`
- `decisions/ADR-002-交易平台与策略管理策略范围不同.md`
- `decisions/ADR-003-策略注册表作为唯一策略定义来源.md`
- `decisions/ADR-004-交易工具由Markdown生成.md`
- `decisions/ADR-005-技术架构分层.md`
- `decisions/ADR-006-后端优先采用模块化单体.md`
- `decisions/ADR-007-部署环境与交易模式分离.md`
- `decisions/ADR-008-总体逻辑分层与独立交易Runtime.md`

## 14. 当前成熟度

| 层级 | 当前状态 |
|---|---|
| 产品架构 | 当前推进五个模块与六份策略已完成第一轮深化；金融AI冻结 |
| 总体架构 | 六层逻辑职责、三个工程主体和独立 Runtime 已 active |
| 前端架构 | 规范已形成，代码仍需逐步接入 |
| 后端架构 | 模块化单体、模块边界、交易可靠性和 Runtime 专项已形成 |
| 公共领域模型 | 业务对象已形成，Runtime／Gateway 对象待同步 |
| 协作契约 | 基础 API 和前端实时规范已形成，Runtime Envelope 待正式 Schema |
| 数据架构 | 现有专题已形成，下一步需要统一数据架构收敛 |
| 实盘能力 | 尚未接入，不具备真实交易条件 |

## 15. 文档读取顺序

### 页面与前端

1. 对应模块需求。
2. 对应策略文档。
3. `platform-target-architecture.md`。
4. 前端架构。
5. 协作契约。
6. 代码。

### 后端领域

1. 对应模块和策略需求。
2. `platform-target-architecture.md`。
3. 公共领域对象和状态。
4. `backend/service-boundaries.md`。
5. 对应后端专题。
6. 协作契约和 ADR。

### Runtime 与 Gateway

1. 对应策略需求。
2. `platform-target-architecture.md`。
3. ADR-008。
4. `backend/execution-runtime-and-gateway.md`。
5. 开源与外部能力采用矩阵。
6. PoC 和采用 ADR。

## 16. Draft 与暂缓内容

以下 draft 不自动覆盖 active 架构：

- `implementation-roadmap.md`
- `2026-07-17-Variable-Global交易平台总体架构方案-DRAFT.md`
- `2026-07-17-初创阶段可落地架构方案-DRAFT.md`
- `2026-07-17-开源与外部能力采用矩阵-DRAFT.md`
- `2026-07-16-平台新增功能初步方案-DRAFT.md`

总体架构讨论稿中已确认部分已经通过 `platform-target-architecture.md` 和 ADR-008 进入 active；未确认技术选型继续保留为 draft。

Superseded：

- `2026-07-16-vnpy平台架构初步方案-DRAFT.md`

金融AI暂缓：

- `2026-07-17-金融AI分析暂缓说明-DRAFT.md`
