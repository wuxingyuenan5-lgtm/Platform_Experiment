# Platform V6 后端架构总览

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：后端架构

## 1. 文档定位

本文档定义 Platform V6 后端的目标职责、总体形态和稳定建设原则。

当前尚未确定具体交易内核、数据库、消息队列、Gateway 实现和部署拓扑，因此本文不作为具体技术选型方案或实施计划。

后端负责业务事实、规则执行、数据持久化和系统可靠性；前端负责交互、展示和用户输入。订单、成交、账户、持仓、损益、风险、审批和审计的最终权威不得存在于浏览器本地状态中。

## 2. 目标架构形态

当前优先采用模块化单体后端，并为交易执行、Gateway、行情接入和重型异步任务保留独立进程边界。

```text
Web / Client
    ↓
Platform API / BFF
    ↓
Application Services
    ↓
Domain Modules
    ↓
Repositories / Event Ports / Gateway Ports
    ↓
Database / Cache / External Gateways
```

在业务边界、团队和负载尚未稳定前，不直接拆分大量微服务。

## 3. 逻辑领域

### 3.1 IAM

负责：

- 用户身份认证。
- 角色、能力和数据范围。
- 会话和安全策略。
- 高风险操作的二次认证结果。

### 3.2 Market Data

负责 Execution Market Data：

- 标的和合约规则。
- 实时报价、K 线、资金费率和汇率。
- 报价新鲜度和数据质量。
- 市场数据事件。

### 3.3 Research Data

负责：

- 宏观、资产、公司和行业研究数据。
- 历史修订和观察期。
- 研究衍生指标及计算版本。

### 3.4 Content and Calendar

负责：

- 新闻和摘要。
- 宏观、财报和政策事件。
- 理财信息。
- 内容版本、审核和失效状态。

### 3.5 Strategy

负责：

- StrategyDefinition、StrategyVersion 和 StrategyInstance。
- 策略参数和版本。
- StrategyAccountBinding。
- 策略运行状态。

前端策略注册表不是后端策略运行状态的最终来源。

### 3.6 Trading and Execution

负责：

- TradeIntent 和 TradeCommand。
- ExecutionBatch 和 LegInstruction。
- Order、Fill、配平和暴露。
- 幂等、重试、异常恢复和人工处理。

### 3.7 Account and Position

负责：

- Account 主档。
- BalanceSnapshot 和 MarginSnapshot。
- Position 和持仓快照。
- CapitalAllocation。

Account 不拥有 StrategyAccountBinding。

### 3.8 PnL and Strategy Economic Ledger

负责：

- EconomicEvent 和 LedgerEntry。
- 实际损益和归因。
- 费用、资金费、隔夜费和汇率影响。
- 重算、估值和调整记录。

Strategy Economic Ledger 不等于完整财务会计总账。

### 3.9 Risk

负责：

- 风险规则和额度。
- RiskDecision 和 RiskSnapshot。
- 风险事件、处置和全局交易阻断。

### 3.10 Reconciliation and Data Quality

负责：

- 订单、成交、持仓、余额、损益和账本核对。
- 数据完整、延迟、重复和冲突。
- 差异记录和数据修正流程。

### 3.11 Approval and Control

负责：

- ApprovalPolicy。
- ApprovalRequest 和 ApprovalDecision。
- Maker／Checker。
- 与目标对象、参数和有效期绑定的 ApprovalGrant。

### 3.12 Audit and Notification

负责：

- 关键操作、审批和配置审计。
- 安全事件和人工干预记录。
- 通知生成、投递和阅读状态。

### 3.13 Reporting and AI Support

负责：

- 报表定义、任务、版本和导出。
- 为金融 AI 提供受权限控制、可追溯的数据查询能力。

### 3.14 Integration Gateway

负责：

- 外部交易和数据系统连接。
- 认证、协议转换和状态映射。
- 限频、重试和连接健康。

Gateway 不承担策略、风险和损益规则。

### 3.15 Query and Read Model

负责：

- 页面和报表聚合查询。
- 可缓存、可重建的只读投影。
- 数据时间、来源版本和质量状态。

Read Model 不拥有业务写入权。

详细所有权参见 `service-boundaries.md`。

## 4. 产品模块与后端领域

| 产品入口 | 主要后端领域 |
|---|---|
| 对冲基金看板 | Research Data、部分 Market Data、Query Read Model |
| 新闻日历与理财 | Content and Calendar |
| 交易平台 | Strategy、Trading、Market Data、Account、Risk、Approval |
| 策略管理 | PnL、Account、Position、Trading、Reconciliation、Read Model |
| 风险管理 | Risk、Account、IAM、Approval、Audit、Notification、Reporting、Observability |
| 金融 AI | AI Support、Research Data、Content、Permission |

同一领域可以被多个产品模块读取，但只有一套权威规则和事实。

## 5. Query、Command 和 Event

### Query

- 读取数据，不改变核心业务事实。
- 可以使用 Backend Read Model。
- 返回数据时间、来源和质量。

### Command

- 请求改变业务状态。
- 需要权限、模式、风险、审批和幂等检查。
- 返回受理结果，不把受理等同于完成。

### Event

- 通知已经发生的事实。
- 支持异步协作和实时状态更新。
- 具有稳定 ID、时间、来源和对象版本。

## 6. 数据权威

| 数据 | 权威来源 |
|---|---|
| 用户、角色和权限 | IAM |
| DeploymentEnvironment 配置 | Configuration／Operations |
| TradingMode 和交易能力结果 | Trading／Risk／IAM／Configuration 综合结果 |
| Instrument 和 Execution Market Data | Market Data |
| Research Data | Research Data |
| 新闻和日历 | Content and Calendar |
| 策略版本、实例和账户绑定 | Strategy |
| Account、余额和保证金 | Account |
| TradeCommand、ExecutionBatch、Order 和 Fill | Trading and Execution |
| Position | Account and Position |
| 实际损益和策略经济账本 | PnL and Strategy Economic Ledger |
| 风险规则和事件 | Risk |
| 审批请求和授权 | Approval and Control |
| 对账结果 | Reconciliation |
| 审计记录 | Audit |

前端缓存、Mock、Read Model、页面表格和导入文件均不是最终权威。

## 7. 数据和存储原则

具体技术后续确认，但必须满足：

- 稳定平台业务 ID 与外部 ID 分开。
- TradeCommand、ExecutionBatch、Order 和 Fill 分开。
- 当前状态、历史变化、快照和派生结果分开。
- 金额保留币种和精度。
- 时间保留来源和业务语义。
- DeploymentEnvironment 与 TradingMode 分开。
- 人工修正不覆盖原始事实。
- 审批、审计和对账记录可追溯。
- Read Model 可以重建。

## 8. 实时和异步处理

适合实时：

- 报价和数据质量。
- Order、Fill 和 ExecutionBatch 状态。
- 账户、保证金、持仓和风险状态。
- Gateway、审批和系统状态。

适合异步：

- 历史和研究数据同步。
- 损益重算。
- 对账。
- Read Model 投影。
- 报表生成。
- 大批量导入。
- AI 分析任务。

前端实时连接断开不应导致后台交易或任务停止。

## 9. 安全与可靠性

后端至少具备：

- 服务端权限和数据范围校验。
- DeploymentEnvironment 与 TradingMode 隔离。
- 敏感凭证加密和最小权限。
- 命令幂等和并发控制。
- 超时、重试和结果未知边界。
- Gateway 异常隔离。
- 高风险审批，适用时。
- 关键操作审计。
- 对账、备份和恢复。

前端禁用按钮不能替代后端安全控制。

## 10. 架构依赖原则

以下是架构依赖，不是已批准实施计划：

- 真实交易命令依赖稳定领域对象、权限、风险、幂等和审计。
- Live 依赖 Simulation／Paper 已验证的状态映射、恢复和对账。
- 复杂页面查询优先依赖 Read Model，而不是跨模块任意访问。
- 技术选型应在业务边界确认后进行。

候选演进阶段记录在 `../implementation-roadmap.md`，该文件当前为 draft。

## 11. 待专项确认

以下内容不得由本文直接决定：

- 是否采用 vn.py 或其他交易内核。
- MT5、加密交易所和国内期货接入方式。
- 数据库、时序库、缓存和消息队列选型。
- 模块和独立进程的部署拓扑。
- 高可用、灾备和生产规模。
- 首个 Gateway、账户和 Live 策略。

上述事项需要技术验证、专项方案和 ADR。

## 12. 详细文档

- `service-boundaries.md`
- `trading-execution-reliability.md`
- `storage-ledger-and-audit.md`
- `query-and-read-models.md`
- `research-data-and-content-boundaries.md`
- `../domain/approval-and-dual-control.md`
