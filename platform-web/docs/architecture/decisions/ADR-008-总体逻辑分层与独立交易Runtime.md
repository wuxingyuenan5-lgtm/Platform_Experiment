# ADR-008：总体逻辑分层与独立交易 Runtime

状态：`accepted`
日期：2026-07-17
适用分支：`refactor/frontend-architecture-v6`

## 背景

Platform V6 已经通过 ADR-005 将架构文档分为前端、后端、协作和公共领域四类视角，并通过 ADR-006 确认后端优先采用模块化单体。

随着 MT5、Crypto、多腿执行、恢复、对账和外部组件采用需求进一步明确，现有决策仍不足以回答：

- 六层架构是否意味着六个服务。
- Platform Backend 与交易执行进程是否应运行在同一进程。
- Runtime、Gateway、Worker 和平台业务领域之间如何划分权威。
- vn.py、CCXT、MetaTrader5 等组件应位于哪一层。
- 初创阶段需要多少工程和部署主体。

如果继续模糊处理，容易出现：

- 将六层逻辑职责误拆成大量服务。
- Platform API 直接加载 Broker SDK 和 MT5 Terminal 依赖。
- Runtime OMS、外部框架数据库或前端状态成为第二套交易权威。
- API 重启、浏览器关闭或 Gateway 故障影响已受理交易。
- 外部组件反向定义平台 Strategy、Order、Risk 和 PnL 模型。

## 决策

### 1. 六层作为逻辑职责

Platform V6+ 采用以下六层逻辑职责：

1. 产品与交互层。
2. 平台应用与控制层。
3. 核心业务领域层。
4. 交易执行与连接层。
5. 数据、账本与查询层。
6. 运行保障与基础设施层。

六层不代表六个服务、六个数据库、六个仓库、六个部署单元或六支团队。

### 2. 四类架构文档视角继续有效

ADR-005 定义的前端、后端、前后端协作和公共领域模型四类架构视角继续有效。

四类视角回答“从什么角度描述架构”，六层回答“系统职责如何分层”，两者不冲突。

### 3. 初期采用三个工程主体

初期工程主体为：

- `platform-web`：Vue 前端。
- `platform-api`：模块化单体业务后端。
- `execution-runtime`：独立交易执行、Gateway 和 Worker 运行时。

三个主体可以运行于同一台机器，但不得因此合并代码、依赖、进程、凭证和故障边界。

### 4. Execution Runtime 必须独立进程

`execution-runtime` 必须独立于 Platform API／BFF 进程运行。

原因包括：

- 外部连接、Broker SDK、MT5 Terminal 和交易所 WebSocket 具有独立生命周期。
- API 重启不应导致外部订单、订阅和运行状态丢失。
- Runtime 需要独立完成重连、同步、对账、恢复和事件补发。
- MT5、Crypto 和后续 CTP 需要不同 Worker、依赖和故障隔离。
- 浏览器或 HTTP 请求生命周期不能控制交易生命周期。

独立进程不等于立即采用微服务、多机部署或 Kubernetes。

### 5. Platform Backend 拥有业务控制与永久事实

Platform Backend 拥有：

- StrategyDefinition、StrategyVersion、StrategyInstance 和 StrategyAccountBinding。
- TradeIntent、TradeCommand、ExecutionBatch、ExecutionPlan 和 LegInstruction。
- 平台 Order 身份和标准化 Order／Fill 记录。
- Account、Position、Risk、Approval、Reconciliation、EconomicEvent、PnL 和 Audit。
- Query and Read Models。

Platform Backend 不直接导入或调用交易所、Broker、MetaTrader5 或 CTP SDK。

### 6. Runtime 拥有实时运行状态

Execution Runtime 拥有：

- Runtime、Gateway、Worker 和外部 Session 的实时状态。
- 外部连接、订阅、限频、重连和健康。
- 当前活动订单、成交缓存和外部请求状态。
- 已处理 Command、待发送 Event 和恢复位置的本地运行记录。
- 外部错误、状态和 ID 映射上下文。

Runtime OMS 和本地 Journal 不成为平台永久 Order、Fill、Position、PnL 或账本权威。

### 7. Platform 与 Runtime 使用自有契约

Platform Backend 与 Runtime 通过平台自有 Command／Event／Port 契约协作。

传输语义采用：

- 至少一次传输。
- 幂等处理。
- 结果未知状态。
- 主动查询、同步和对账恢复。

不依赖单次 RPC 或 HTTP 超时判断外部交易最终失败。

### 8. 外部组件按能力接入

vn.py、CCXT、MetaTrader5、aiomql、交易所 SDK 和其他组件通过 Adapter／Port 接入。

可以复用或参考：

- 事件循环。
- Gateway。
- 实时 OMS。
- 行情和合约接口。
- 低层订单检查。
- 多腿和算法执行工具。
- Session、重试和恢复设计。

不得直接复用为平台权威：

- Strategy、TradeCommand 和 ExecutionBatch。
- 平台永久 Order、Fill 和 Position。
- RiskDecision。
- EconomicEvent、LedgerEntry 和 PnLResult。
- IAM、Approval 和 Audit。

最终采用结论需要 PoC 和必要 ADR。

### 9. 接入优先级不写入本 ADR

Crypto 与 MT5 已属于初期目标能力，CTP 可以延后；但具体交易所、经纪商、SDK、版本、数据库、消息通道和部署产品不由本 ADR 决定。

### 10. 金融AI分析冻结

金融AI分析继续保留产品入口，但当前不参与总体架构专项深化，不作为 Platform Backend、Runtime 或 V1 的前置依赖。

## 原因

- 保留模块化单体的开发和运维简单性。
- 隔离最容易发生外部故障和状态不确定性的交易运行环境。
- 允许 MT5、Crypto 和 CTP 使用不同依赖和 Worker 模型。
- 避免 API、浏览器和外部框架成为交易生命周期控制者。
- 为幂等、结果未知、恢复、对账和人工处理建立明确边界。
- 避免在初创阶段过度拆分微服务。
- 为后续部署拆分保留稳定契约。

## 影响

- 新增 `platform-target-architecture.md` 作为总体目标架构 active 文档。
- `backend/backend-overview.md` 需要明确 Platform Backend 与 Execution Runtime 的边界。
- 后续新增交易 Runtime 与 Gateway 专项架构。
- 公共领域模型需要增加 Runtime、Gateway、Recovery 和外部引用候选对象。
- API 和 Runtime 通信需要独立契约和可靠性方案。
- Platform Backend 代码不得直接依赖 Broker SDK 和 MetaTrader5 包。
- Runtime 不得直接写入平台业务模块内部表。
- 开发和早期部署可以同机，但必须保持进程隔离。

## 与既有 ADR 的关系

- ADR-005 继续有效：其定义架构文档视角。
- ADR-006 继续有效：Platform Backend 仍采用模块化单体。
- ADR-007 继续有效：DeploymentEnvironment 与 TradingMode 分离。
- 本 ADR 补充并正式确定独立 Execution Runtime，而不替代上述决策。

## 禁止事项

- 不把六层直接拆成六个服务。
- 不把产品菜单直接映射成同名后端服务。
- 不让 Platform API 直接持有外部交易 Session。
- 不让 Runtime 本地存储成为平台永久业务数据库。
- 不让外部框架对象直接进入 Platform Domain。
- 不以浏览器关闭、API 超时或连接断开直接判定交易失败。
- 不因独立 Runtime 而提前引入无必要的微服务和 Kubernetes。

## 重新讨论条件

出现以下情况时可以形成新 ADR 替代或扩展本决策：

- 实际负载要求进一步拆分 Runtime 或业务模块。
- 合规、安全或账户隔离要求强制多机或多区域部署。
- 某交易系统无法通过独立 Runtime 接入。
- 平台业务后端不再采用模块化单体。
- 团队、部署和运维能力发生显著变化。
