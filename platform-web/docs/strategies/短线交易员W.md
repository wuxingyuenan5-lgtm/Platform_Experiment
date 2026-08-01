# 短线交易员 W：策略定位与需求

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6+  
适用分支：`refactor/frontend-architecture-v6`  
策略 ID：`shortLineTraderW`  
文档层级：策略专项需求与业务口径

上位与配套约束：

- `docs/modules/策略-需求文档.md`
- `docs/modules/策略管理-需求文档.md`
- `docs/architecture/strategy-capability-matrix.md`
- `docs/architecture/domain/status-enums-and-lifecycles.md`
- `docs/architecture/backend/query-and-read-models.md`
- `docs/architecture/backend/storage-ledger-and-audit.md`
- `docs/architecture/reference-code-adoption-matrix.md`

## 1. 文档定位

本文定义短线交易员 W 策略账户的业务定位、独立身份、外部执行来源、账户和交易归属、交易日与日界线、订单成交持仓、EconomicEvent、日内和区间 PnL、风险额度、违规事件、对账、数据质量、策略管理 Read Model、外部组件候选和验收标准。

短线交易员 W 当前不通过平台交易模块下单。平台只接收和管理其外部执行事实、账户状态、风险记录和统计结果。

V1 只做策略管理入口和外部来源占位，不建设完整外部同步、TradeCycle、ViolationRecord、风险额度计算和正式 PnL 体系。没有真实外部数据或人工确认来源时，页面只能显示 `missing`、`not_connected`、`unverified` 或等价状态。

本文必须保证：

- W 与 L 使用独立 StrategyId、StrategyVersion、StrategyInstance 和 Account。
- 两者可以共享页面组件，但不得共享业务数据、风险状态和 PnLResult。
- 外部交易归属需要稳定证据，不能只通过交易员展示名称判断。
- 未确认的标的、时段、风险和违规规则集中列为未决事项。

## 2. 策略定位与核心约束

短线交易员 W 是纳入平台统一统计、风险观察、数据核对和复盘的独立短线方向性交易策略账户。

当前正式约束：

1. `platform.enabled = false`。
2. 当前执行来源为外部交易终端、经纪商、交易所、文件或人工确认记录。
3. 策略管理不提供正式下单、改单、撤单和复制交易入口。
4. 账户、订单、成交、持仓、费用和风险事件必须可追溯。
5. 资金出入、内部划转和交易 PnL 必须分开。
6. 日内亏损、总回撤和风险额度必须使用明确的统计基准和日界线。
7. 违规状态必须由正式 RiskRule／ViolationRule 产生或经人工确认，不能只通过颜色或单笔亏损推断。
8. W 与 L 的正式差异必须进入各自 StrategyVersion 或 ExternalExecutionProfile。

## 3. 产品能力

| 能力 | 是否属于当前正式范围 |
|---|---:|
| 交易平台·行情分析 | 否 |
| 交易平台·交易执行 | 否 |
| 策略管理·策略损益 | 是 |
| 策略管理·账户资金 | 是 |
| 策略管理·订单信息 | 是 |
| 外部订单、成交与持仓同步 | 是 |
| 风险与违规记录 | 是 |
| 外部数据导入 | 是 |
| 自动下单／复制交易 | 否 |

V1 阶段，短线交易员 W 只要求进入策略管理并保留外部数据占位：展示独立 StrategyInstance、账户绑定、外部来源状态、最近数据时间、基础账户／持仓／订单占位和 DataQualityStatus。完整外部同步、TradeCycle、ViolationRecord、风险额度计算、订单自动归属和正式 PnL 归因不作为 V1 必做项。

V1 不展示正式 PnL、胜率、盈亏比、TradeCycle、ViolationRecord、风险额度和是否允许继续交易的正式判断，除非底层账户、订单、Deal／Fill、持仓、费用、资金流和风险规则已经接入并完成最小质量标记。不得使用 Mock、样例或前端静态数据包装成真实表现。

## 4. 核心用户问题

### 4.1 策略损益

- 当日、本周、本月和自定义区间赚亏多少？
- 已实现、未实现和交易成本分别是多少？
- 收益主要来自哪些标的、方向、时段和 TradeCycle？
- 日内累计 PnL 的峰值、谷值和最大回撤是多少？
- 当前表现是否稳定，连续亏损和异常损失如何？
- 数据是否完整、已对账并排除资金出入影响？

### 4.2 账户资金

- 当前账户 Balance、Equity、可用资金和保证金是多少？
- 当日亏损、总回撤和风险额度是否接近或突破限制？
- 当前是否允许继续交易，还是处于 read_only、blocked 或需人工复核？
- 当前持仓名义价值、杠杆和集中度如何？
- 是否存在无法归属或外部手工持仓？

### 4.3 订单、成交与风险

- 当前持仓和当日订单是什么？
- 每笔 Order 产生了哪些 Deal／Fill？
- 止损和止盈是计划值、外部订单还是事后记录？
- 是否存在拒单、撤单、部分成交、失败或手工干预？
- 哪个 RiskEvent／ViolationRecord 与具体订单、持仓和时间有关？
- 外部数据是否有缺失、重复或状态冲突？

## 5. 策略身份、版本与实例

### 5.1 StrategyDefinition

稳定定义：

- `strategyId = shortLineTraderW`。
- 正式名称：短线交易员 W。
- 执行类型：外部执行策略。
- 腿模型：单腿方向性交易。
- 当前产品能力：仅策略管理。

### 5.2 StrategyVersion

每个正式版本至少可以记录：

- 可交易市场和 Instrument 范围。
- 允许交易时段和禁止时段。
- 是否允许隔夜和周末持仓。
- 新闻事件或流动性时段规则，确认后。
- 基准资金和收益率分母。
- 日内亏损、总回撤和单笔风险口径。
- 最大持仓、杠杆和集中度。
- 止损、止盈和风险减仓要求。
- 违规类型、严重度和处置方式。
- PnL、手续费、Commission 和 Swap 口径。
- businessDate、交易日和日界线。
- 数据来源、账户归属和质量门槛。
- 生效时间、审批和替代关系。

未确认字段必须标记为未确认，不得由页面默认值替代。

### 5.3 StrategyInstance

至少表达：

- `strategyInstanceId`。
- StrategyVersionId。
- DeploymentEnvironment 和 TradingMode。
- AccountId 或明确账户集合。
- ExternalExecutionProfileId。
- 资金分配和风险额度。
- 当前实例状态。
- 数据截止时间和对账状态。
- 当前 TradingPermissionState 只作为外部账户是否允许继续交易的管理结果，不赋予平台下单能力。

### 5.4 StrategyAccountBinding

至少记录：

- AccountId。
- 外部平台、Broker 或终端。
- 账户用途。
- 允许归属的 Instrument。
- Magic Number、Comment、Client Order ID、Tag、Subaccount 或其他规则。
- TradingMode 和环境。
- 生效和失效时间。
- 是否允许自动归属。
- 数据同步方式和责任人。

## 6. ExternalExecutionProfile

### 6.1 业务定位

ExternalExecutionProfile 用于描述 W 的外部执行环境和归属规则，不保存密码、Secret 或完整登录凭证。

至少可以包含：

- externalExecutionProfileId。
- Broker／Exchange／Terminal 类型。
- AccountId。
- 数据源和同步 Adapter。
- 账户模式，例如 Hedging／Netting。
- Base Currency。
- 服务器时区和日界线。
- 允许的 Instrument 和 Symbol Mapping。
- Magic Number、Comment、Tag 或 Subaccount 范围。
- Commission、Swap 和费用数据来源。
- 数据补查询范围。
- 手工订单识别规则。
- 当前能力和健康状态。

### 6.2 W 与 L 分离要求

W 与 L 至少在以下一种或多种正式维度上分开：

- 独立 AccountId。
- 独立 Subaccount。
- 独立 Magic Number／Tag 范围。
- 独立策略实例。
- 独立数据导入来源。

如果无法从外部数据稳定区分，相关记录必须进入 `unallocated` 或人工确认流程，不能由展示名称强行归属。

## 7. 外部订单、成交与持仓

### 7.1 Order

至少表达：

- platformOrderId。
- externalOrderId。
- AccountId 和 StrategyInstanceId。
- InstrumentId 和原始 symbol。
- 方向和订单类型。
- 委托价格和数量。
- Stop Loss／Take Profit，适用时。
- 创建、提交、更新时间和到期时间。
- 平台状态和外部原始状态。
- Magic Number、Comment 或其他归属证据。
- 数据来源和对账状态。

### 7.2 Fill／Deal

至少表达：

- fillId／executionId。
- externalTradeId／dealId。
- OrderId。
- 成交时间、价格和数量。
- Commission、Fee 和 Swap，按数据结构。
- 已实现 PnL，外部提供时。
- 数据来源和稳定去重依据。

### 7.3 Position

至少表达：

- positionId。
- AccountId 和 StrategyInstanceId。
- InstrumentId。
- 方向和数量。
- 平均成本。
- 当前价格和估值时间。
- 未实现 PnL。
- 名义价值和保证金。
- Stop Loss／Take Profit，适用时。
- 来源、质量和对账状态。

### 7.4 MT5 场景

外部来源为 MT5 时必须区分：

- Order。
- Deal。
- Position。

并处理：

- Hedging／Netting。
- Magic Number 和 Comment。
- 手工订单。
- Commission 和 Swap。
- Broker symbol 后缀。
- 部分平仓。
- Terminal 重启和历史补查询。

## 8. 交易日、时段与统计口径

### 8.1 时间语义

至少区分：

- occurredAt。
- sourceTime。
- receivedAt。
- businessDate。
- Broker／Exchange Server Time。
- 用户展示时区。

### 8.2 日界线

“当日损益”和“日内亏损限制”必须明确日界线，例如：

- Broker Server 日界线。
- 纽约日界线。
- UTC。
- 北京时间或其他正式业务日。

最终口径由 StrategyVersion 确认。页面不能按浏览器本地零点自行切日。

### 8.3 交易时段

数据源支持时记录：

- 亚洲、欧洲和美国时段。
- 自定义交易时段。
- 开盘、收盘和低流动性区间。
- 新闻或事件窗口。
- 是否跨日和隔夜。

按时段归因必须使用正式时段定义和版本。

## 9. EconomicEvent 与 PnL

### 9.1 EconomicEvent

至少记录：

- Fill／Deal。
- Commission／TradingFee。
- Swap／OvernightFee。
- Financing／Interest，适用时。
- Deposit／Withdrawal／Transfer，作为资金事件，不直接作为交易 PnL。
- ManualAdjustment。

### 9.2 资金事件与 PnL 分离

- Deposit、Withdrawal 和内部划转改变账户 Balance，但不直接形成交易收益。
- 策略净值和收益率需要使用资金流调整后的口径。
- 外部平台提供的 Balance 变化不能全部解释为 PnL。

### 9.3 PnLResult

至少包含：

- StrategyVersionId 和 StrategyInstanceId。
- businessDate 和统计期间。
- 原始币种和报告币种。
- 当日、区间和累计损益。
- 已实现和未实现损益。
- Commission、Fee 和 Swap。
- AdjustmentEntry。
- 资金流调整。
- 数据截止时间。
- 计算版本。
- DataQualityStatus 和 ReconciliationStatus。

### 9.4 归因维度

按数据能力支持：

- Instrument。
- 交易时段。
- 多空方向。
- Order／Fill／TradeCycle。
- 已实现和未实现。
- Commission、Fee 和 Swap。
- 人工交易和规则外交易。
- RiskEvent／ViolationRecord。

“异常损失”或“违规相关损益”必须关联正式事件，不能将全部亏损自动标记为违规。

### 9.5 绩效指标

可以包括：

- 当日、本周、本月和区间损益。
- 区间收益率。
- 日度收益。
- 净值和回撤曲线。
- 最大日内回撤。
- 交易次数。
- 胜率和盈亏比。
- 平均持有时间。
- 连续盈利和连续亏损。
- Profit Factor，具备正式定义时。

## 10. TradeCycle 与执行质量

为了分析短线表现，可以建立 TradeCycle 或等价派生对象：

- 开仓和关闭时间。
- Instrument 和方向。
- 最大持仓。
- 加仓、减仓和部分平仓。
- 平均入场和出场价格。
- 已实现 PnL。
- Commission、Fee 和 Swap。
- 持有时间。
- 最大有利和不利变化，数据支持时。
- 退出原因。
- 风险和违规事件。

TradeCycle 是派生分析对象，不修改底层 Order、Fill 和 Position 事实。

## 11. 账户资金

至少展示：

- 初始资金或正式基准资金。
- Balance、Equity 和 Available Funds。
- 已用保证金和 Margin Level。
- 当前持仓名义价值。
- 当日和累计 PnL。
- 资金出入。
- 当日最大亏损。
- 当前和最大回撤。
- 当前风险额度和剩余额度。
- 当前账户状态和是否允许继续交易。
- 数据时间、质量和对账状态。

V1 如需展示净值，只能显示 `estimated`、`missing`、`not_connected` 或 `unverified` 状态，不作为正式收益表现。未接入真实外部数据前，不计算或展示正式策略净值。

## 12. 风险、限制与违规

### 12.1 主要风险

- 日内亏损超限。
- 总回撤超限。
- 单笔或单标的风险过高。
- 杠杆和持仓集中度过高。
- 高频连续亏损。
- 未按正式规则止损。
- 隔夜或新闻持仓违反规则，确认后。
- 外部数据缺失、延迟或重复。
- 手工订单无法归属。
- 人工操作与 StrategyVersion 不一致。

### 12.2 RiskSnapshot

至少可以展示：

- 当日 PnL。
- 当日峰值 Equity。
- 当日最大亏损。
- 当前和最大回撤。
- 单笔风险。
- 当前名义价值和杠杆。
- Instrument 集中度。
- 连续亏损次数。
- 未设置止损的持仓数量，规则适用时。
- 未归属订单和持仓数量。

### 12.3 ViolationRecord

至少表达：

- violationId。
- StrategyInstanceId 和 AccountId。
- 规则和版本。
- 违规类型和严重度。
- 触发值、阈值、币种和单位。
- 发生时间和持续时间。
- 关联 Order、Fill、Position 或 TradeCycle。
- 自动或人工确认状态。
- 处置、备注和审批。
- 是否影响继续交易。

### 12.4 是否允许继续交易

该结果由 RiskDecision、账户状态和正式规则共同形成，可以是：

- enabled。
- read_only。
- blocked。
- pending_review。

它是管理和风险状态，不赋予平台向外部账户下单的能力。

## 13. 外部数据导入、归属与对账

### 13.1 来源

- MT5 或其他终端 API。
- Broker／Exchange API。
- 文件导入。
- 人工录入。

### 13.2 ImportBatch／SyncRun

每次导入或同步至少记录：

- 来源和 Account。
- 覆盖时间范围。
- 记录总数、成功、失败和重复数。
- Symbol Mapping。
- Magic／Tag 归属结果。
- 数据质量。
- 对账和提交状态。
- 操作人、任务和审计。

### 13.3 对账范围

至少覆盖：

- Order。
- Fill／Deal。
- Position。
- Balance／Equity／Margin。
- Commission、Fee 和 Swap。
- Deposit／Withdrawal。
- RiskEvent 和 ViolationRecord 所需输入。
- PnLResult 与底层 EconomicEvent。

### 13.4 差异处理

- 优先补查询和重新同步。
- 不无痕覆盖原始外部事实。
- 未归属和冲突记录不进入正式策略统计。
- 正式归属、差异接受和修正需要权限与审计。
- 影响 PnL 时产生新计算版本。

## 14. 策略管理 Read Model

### 14.1 策略损益

至少展示：

- 当日、本周、本月和自定义区间损益。
- 已实现和未实现损益。
- Commission、Fee 和 Swap。
- 净值、回撤、胜率和盈亏比。
- 按 Instrument、时段、方向和 TradeCycle 归因。
- 异常和违规关联。
- 数据截止时间、版本、质量和对账状态。

### 14.2 账户资金

至少展示：

- 基准资金、Balance、Equity 和 Available Funds。
- Margin、名义价值和杠杆。
- 当日亏损、当前回撤和剩余风险额度。
- 账户状态和 RiskDecision。
- 资金出入。
- 数据与对账状态。

### 14.3 订单信息

固定视图：

- 当前持仓。
- 历史订单。
- Deal／Fill。
- TradeCycle。
- RiskEvent。
- ViolationRecord。
- 人工干预。
- ImportBatch／SyncRun。
- 对账差异。

## 15. Query、Command 与 Event

### 15.1 Query 候选

- `GetShortLineTraderWSummary`。
- `GetShortLineTraderWPnlView`。
- `GetShortLineTraderWAccountView`。
- `GetShortLineTraderWPositionView`。
- `GetShortLineTraderWOrderView`。
- `GetShortLineTraderWTradeCycleView`。
- `GetShortLineTraderWRiskView`。
- `GetShortLineTraderWViolationView`。
- `GetShortLineTraderWReconciliationView`。

### 15.2 Command 候选

不提供正式交易 Command。

数据和治理 Command：

- `CreateStrategyImportBatch`。
- `RequestExternalAccountSynchronization`。
- `AllocateExternalExecutionToShortLineTraderW`。
- `ConfirmShortLineTraderWViolation`。
- `ResolveShortLineTraderWViolation`。
- `ConfirmReconciliationDifference`。
- `RequestStrategyDataCorrection`。
- `CreateAdjustmentEntry`。
- `RecalculateStrategyPnl`。

### 15.3 Event 候选

- `ShortLineTraderWDataSynchronized`。
- `ShortLineTraderWOrderImported`。
- `ShortLineTraderWPositionUpdated`。
- `ShortLineTraderWRiskChanged`。
- `ShortLineTraderWViolationDetected`。
- `ShortLineTraderWViolationResolved`。
- `ShortLineTraderWReconciliationCompleted`。
- `ShortLineTraderWPnlRecalculated`。

## 16. 实现能力依赖与外部组件候选

本节只描述候选能力，不改变策略业务定义。

### 16.1 平台必须自建

- StrategyVersion、StrategyInstance 和 ExternalExecutionProfile。
- W 与 L 独立归属规则。
- 平台 Order、Fill、Position、TradeCycle 和 ViolationRecord。
- businessDate、日界线和风险口径。
- EconomicEvent、资金流调整、PnLResult 和对账。
- 数据质量、人工处理和审计。

### 16.2 MT5／aiomql 候选

外部来源为 MT5 时：

- 官方 MetaTrader5 Python 包用于 Account、Order、Deal、Position 和历史查询候选。
- aiomql 用于异步、初始化、重试、Session、账户和历史查询设计参考或局部封装。
- Magic Number、Comment、Account 和 Broker Server Time 进入归属与统计。
- 自建 Worker／Supervisor 负责多账户、Terminal、凭证和恢复隔离。

aiomql 的 Bot、Strategy、RAM 和 SQLite 结果库不默认成为平台策略、Risk 和 PnL 权威。

### 16.3 vn.py 候选

根据实际外部市场可以参考或封装：

- EventEngine／MainEngine／OmsEngine：Runtime 内部接入和状态缓存。
- Gateway：账户、订单、成交和持仓接入。
- DataManager／Recorder：历史行情和导入参考。
- PortfolioManager：交易组合统计思想参考。

当前不使用 vn.py 执行 W 的交易，也不使用其 PnL、账户和风险对象替代平台模型。

### 16.4 其他外部市场

若数据来自 Crypto：

- CCXT 或官方交易所 API／SDK 作为接入候选。
- Client Order ID、Subaccount 和 Tag 用于归属。

若来自其他 Broker：

- 按独立 Adapter 评估，不在页面直接依赖外部字段。

## 17. 明确不包含

- 交易平台行情分析和交易执行。
- 自动下单、复制交易和账户跟单。
- 未经确认的风险阈值。
- 未接入真实外部数据时展示正式 PnL、胜率、盈亏比、TradeCycle、ViolationRecord 和风险额度。
- 将 W 与 L 合并为同一策略实例或 PnL。
- 仅依据姓名、symbol 或时间接近归属订单。
- 将 Deposit／Withdrawal 当作交易收益。
- 将所有亏损自动判定为违规损失。
- 将外部组件对象作为平台业务权威。
- 在本文确定具体仓库最终采用、Fork 或版本锁定。

## 18. 可测试验收标准

### 18.1 产品和身份

- W 只出现在策略管理，不出现在交易平台。
- StrategyId 固定为 `shortLineTraderW`。
- StrategyVersion、Instance、Account 和 ExternalExecutionProfile 独立。
- W 与 L 页面骨架可共享，但所有数据和状态隔离。

### 18.2 外部执行

- Order、Deal／Fill、Position 和 Account 事实可追溯。
- Magic Number、Comment、Tag 或账户绑定用于稳定归属。
- 未归属和冲突数据不会进入正式统计。
- MT5 Order、Deal 和 Position 正确区分。

### 18.3 PnL 和时间

- 当日口径使用正式 businessDate 和日界线。
- Deposit、Withdrawal 和 PnL 分开。
- 已实现、未实现、Commission、Fee 和 Swap 可核对。
- 净值、回撤、胜率和盈亏比具有计算版本和数据质量。

### 18.4 风险和违规

- 日内亏损、总回撤、单笔风险和集中度使用正式规则。
- ViolationRecord 可关联 Order、Fill、Position 和时间。
- 是否允许继续交易与具体规则、账户和数据状态关联。
- 未确认规则不会被页面硬编码。

### 18.5 对账和组件边界

- 外部 Order、Fill、Position、Balance、Margin、Fee、Swap 和资金流可对账。
- 差异和修正不无痕覆盖原始事实。
- MetaTrader5、aiomql、vn.py 和其他 Adapter 不拥有平台 Strategy、Risk 和 PnL 权威。
- 具体采用经过 PoC、许可证、安全和数据完整性评审后形成 ADR。

## 19. 未决事项

1. W 的正式 Broker／Exchange／Terminal。
2. 独立 AccountId、Subaccount 或 Magic Number 范围。
3. 可交易 Instrument 和 symbol mapping。
4. 允许交易时段、日界线和 businessDate。
5. 是否允许隔夜、周末和新闻持仓。
6. 初始或基准资金和资金流调整方法。
7. 日内亏损、总回撤、单笔风险和集中度限制。
8. 止损、止盈和风险减仓规则。
9. 违规类型、严重度和处置方式。
10. PnL 的报告币种和汇率口径。
11. 外部手工订单的归属和排除规则。
12. W 与 L 的正式业务差异清单。
13. MT5、vn.py 或其他 Adapter 的 PoC 范围。

上述关键差异未确认前，不得通过复制 L 的配置并只修改展示名称形成正式 W 策略版本。

以上未决事项不阻塞资费套利和跨所价差 V1。短线交易员 W 进入完整管理闭环前，必须先确认外部执行来源、账户归属证据、日界线、资金流调整、风险规则和违规口径。
