# Platform V6 后端架构总览

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：后端架构

## 1. 文档定位

本文档定义 Platform V6 后端的目标职责、逻辑边界和建设原则。当前尚未确定具体交易内核、数据库、消息队列或部署拓扑，因此本文不作为具体技术选型方案。

后端负责业务事实、规则执行、数据持久化和系统可靠性；前端负责交互、展示和用户输入。订单、成交、账户、持仓、损益、风险和审计的最终权威不得存在于浏览器本地状态中。

## 2. 目标架构形态

当前阶段采用模块化单体后端，并为交易执行、行情接入、Gateway 和重型异步任务保留独立进程边界。

```text
Web / Client
    ↓
Platform API / BFF
    ↓
Application Services
    ↓
Domain Services
    ↓
Repositories / Event Publishers
    ↓
Database / Cache / External Gateways
```

不在业务边界尚未稳定前直接拆成大量微服务。

## 3. 逻辑领域

### Identity and Access Management

负责用户、角色、能力权限、数据范围、会话和安全策略。

### Execution Market Data

负责交易执行所需行情、标的、合约规则、报价、资金费率、汇率和数据新鲜度。

### Research Data

负责宏观、资产、公司、行业、ETF、流动性和研究衍生数据及其版本、修订和质量。

### Content and Calendar

负责新闻、摘要、宏观事件、财报事件和理财信息等内容数据。

### Strategy

负责 StrategyDefinition、StrategyVersion、StrategyInstance、参数和 StrategyAccountBinding。

### Trading and Execution

负责 TradeIntent、TradeCommand、ExecutionBatch、LegInstruction、Order、Fill、执行配平、暴露、幂等和异常恢复。

### Account and Position

负责 Account 主档、余额、权益、保证金、Position 和快照。

### PnL and Strategy Economic Ledger

负责 EconomicEvent、实际损益、策略归因、估值、重算和 AdjustmentEntry，不等于完整财务会计总账。

### Risk

负责风险指标、规则、判断、事件、处置和 GlobalTradingBlock。

### Reconciliation and Data Quality

负责订单、成交、持仓、余额、费用和损益对账，以及数据完整、延迟、重复、冲突和修正记录。

### Approval and Control

负责 ApprovalPolicy、ApprovalRequest、ApprovalDecision、ApprovalGrant 和 Maker／Checker。

### Audit and Notification

负责关键操作审计、配置和修正追踪，以及通知投递和阅读状态。

### Reporting

负责正式报表定义、生成任务、版本和导出。

### AI Support

为金融AI分析提供受权限控制、可追溯的查询、任务和结果支持，不拥有原始业务事实。

## 4. 产品模块与后端领域

| 产品入口 | 主要后端领域 |
|---|---|
| 首页 | Query Read Model、各领域摘要 |
| 对冲基金看板 | Research Data、部分 Execution Market Data |
| 新闻日历与理财 | Content and Calendar |
| 交易平台 | Strategy、Trading、Market Data、Account、Risk |
| 策略管理 | PnL、Account、Position、Trading、Reconciliation、Read Model |
| 风险管理 | Risk、Account、IAM、Approval、Audit、Notification、Reporting、Observability |
| 金融AI分析 | AI Support、Research Data、Content、Permission、Read Model |

前端菜单不等于后端服务边界。同一后端领域可以被多个页面读取，但只维护一套权威规则和事实。

## 5. 命令与查询

### Query

- 可以重复调用。
- 可以缓存。
- 返回数据时间、来源和质量。
- 不改变核心业务事实。

### Command

- 请求改变业务状态。
- 需要权限、数据范围、风险、审批和幂等检查，适用时。
- 返回受理或拒绝结果，不把“已受理”等同于“已完成”。
- 形成审计和追踪上下文。

提交双腿交易后，后端返回 TradeCommand 或 ExecutionBatch 标识，不直接返回“交易成功”。

## 6. 数据权威

| 数据 | 权威来源 |
|---|---|
| 用户、角色和权限 | IAM |
| 交易标的、合约和执行行情 | Execution Market Data |
| 宏观和研究数据 | Research Data |
| 新闻、日历和理财内容 | Content and Calendar |
| 策略版本、实例和账户绑定 | Strategy |
| 交易命令、执行批次、订单和成交 | Trading and Execution |
| 账户、余额、保证金和持仓 | Account and Position |
| 实际损益和策略经济记录 | PnL and Strategy Economic Ledger |
| 风险规则、判断和事件 | Risk |
| 对账和数据质量 | Reconciliation and Data Quality |
| 审批 | Approval and Control |
| 审计 | Audit |
| AI 任务和结果 | AI Support；输入事实仍归源领域 |

前端缓存、Mock、Read Model、页面表格和导入文件均不是最终权威来源。

## 7. 数据存储原则

- 核心对象使用稳定业务 ID。
- 外部 ID 与平台 ID 分开。
- 订单和成交分开。
- 当前状态与历史事件分开。
- 金额保留币种、单位和精度。
- 时间保留业务时间、外部时间、接收时间和更新时间。
- 汇率记录来源和时间。
- 人工修正不覆盖原始事实。
- 审计和对账记录不可被普通操作无痕修改。
- 敏感凭证与普通业务数据分离。

## 8. 实时与异步处理

适合实时：

- 报价和行情质量。
- 命令、执行批次、订单和成交状态。
- 账户、持仓、暴露和风险状态。
- Gateway 和服务健康。

适合异步：

- 历史数据同步。
- 损益重算。
- 对账。
- 报表生成。
- 大批量导入。
- 金融AI分析任务。

实时连接断开不应导致后台交易或异步任务停止。

## 9. 安全与可靠性

后端至少具备：

- 服务端权限和数据范围校验。
- 敏感凭证加密与隔离。
- 命令幂等。
- 超时、重试和结果未知边界。
- Gateway 异常隔离。
- 高风险审批和双人复核。
- 关键操作审计。
- 数据备份、恢复和对账。
- 未完成执行和未知结果的人工处理。

前端禁用按钮不能替代后端安全控制。

## 10. 待专项确认事项

以下内容不得由本文直接决定：

- 是否采用 vn.py 或其他交易内核。
- MT5、加密交易所和国内期货接入方式。
- 数据库、时序库、缓存和消息队列选型。
- 单体与独立进程的具体部署拓扑。
- 高可用、灾备和生产规模。
- 金融AI分析的模型供应商和推理部署方案。

上述事项分别形成技术验证、专项方案和 ADR。
