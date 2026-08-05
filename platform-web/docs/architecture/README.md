# Platform 0.10.x 简化架构入口

状态：`active`
产品基线：Platform V5
架构版本：Platform V6 Simplified
适用分支：`refactor/frontend-architecture-v6`
文档层级：架构文档入口

## 1. 当前架构结论

平台第一阶段定位为内部投资研究与交易平台，重点支持：

- 策略管理。
- 账户与持仓查看。
- 模拟及外部账户交易执行。
- 基础风险控制。
- 订单、成交和持仓对账。
- 策略收益计算和归因。

当前不建设完整基金行政管理、投资人份额、申赎和正式 NAV 会计。

总体架构唯一入口：

- `platform-target-architecture.md`

参考代码采用规则：

- `reference-code-adoption-matrix.md`

当前实施状态：

- `../../../docs/codex/current-state.md`

复杂度控制决策：

- `decisions/ADR-012-初期架构简化与复杂度控制.md`

## 2. 三个工程主体

```text
platform-web
+
platform-api
+
execution-runtime
```

| 工程 | 职责 |
|---|---|
| `platform-web` | Vue 前端、查询展示、交易命令输入 |
| `platform-api` | 模块化单体、业务数据、订单成交、风险、PnL 和 API |
| `execution-runtime` | Crypto／MT5 连接、外部订单执行、回报接收和本地 Journal |

三个工程初期可以部署在同一台机器，但 Platform Backend 与 Execution Runtime 必须保持独立进程。

## 3. 简化后的总体结构

```text
Browser
  ↓
platform-web
  ↓ REST / WebSocket
platform-api
  ↓ Runtime Command / Event
execution-runtime
  ↓
Fake Gateway / Crypto / MT5
```

第一阶段不拆微服务，不引入复杂消息平台和分布式基础设施。

## 4. 第一阶段最小领域模型

### 4.1 组织与策略

```text
Fund
→ Default Portfolio
→ Default Book
→ StrategyInstance
→ Account
```

Portfolio 和 Book 作为系统默认结构保留，但普通用户不需要管理。

### 4.2 标的

```text
Instrument
InstrumentMapping
ContractSpecification
```

详见：

- `domain/instrument-minimum-model.md`

### 4.3 账户与持仓

```text
Account
BalanceSnapshot
PositionSnapshot
```

详见：

- `domain/account-position-minimum-model.md`

### 4.4 交易

```text
TradeCommand
→ ExecutionBatch
→ Order
→ Fill
```

ExecutionPlan、LegInstruction 和复杂算法执行不是第一阶段硬要求。

### 4.5 收益

```text
EconomicEvent
→ PnLResult
→ PnLAttributionItem
```

详见：

- `domain/economic-event-pnl-minimum-model.md`

## 5. 第一条必须跑通的链路

```text
前端模拟下单
→ Platform Backend 受理
→ 基础风险检查
→ 创建 Order
→ Runtime Command
→ Fake Gateway
→ Runtime Event
→ Fill
→ Position
→ EconomicEvent
→ PnL
→ 前端查询
```

这条链路未跑通前，不继续增加新的领域对象和基础设施。

## 6. 必须保留的金融正确性

架构虽然简化，但以下原则不能删除：

- 金额、价格和数量使用 Decimal。
- Money 带 Currency。
- Quantity 带 Unit。
- 合约乘数和下单单位通过 ContractSpecification 转换。
- Stablecoin 不自动视为 USD。
- occurredAt、receivedAt 和 businessDate 分开。
- 缺失值不能自动当作零。
- 外部订单、成交和持仓差异不能无痕覆盖。
- 重复命令不能产生重复订单。
- `result_unknown` 不能直接视为失败并盲目重试。

相关文档：

- `domain/value-currency-unit-and-time-contract.md`
- `integration/runtime-command-event-contract.md`
- `decisions/ADR-010-Platform与Runtime可靠消息语义.md`

## 7. 数据与技术选择

第一阶段默认：

```text
一个关系型数据库
+
Runtime 本地 Journal
```

暂不引入：

- Kafka。
- ClickHouse。
- 数据湖。
- Event Sourcing。
- Kubernetes。
- 微服务拆分。
- 通用工作流引擎。

具体技术在建立工程骨架时选择，以成熟、简单和团队容易维护为优先。

## 8. 状态模型的使用方式

完整状态语义仍保存在：

- `domain/status-enums-and-lifecycles.md`

但第一阶段实现不要求一次性落地全部状态。

前端普通页面默认归并展示：

```text
可用
处理中
受限
异常
未知
```

只有交易处理、恢复和排障页面才展示细分状态。

## 9. 当前明确延后

- Investor、ShareClass、申购和赎回。
- 完整基金会计与正式 NAV。
- 复杂多 Portfolio／多 Book 管理。
- CTP 接入。
- 高频与复杂算法交易。
- 通用 PnL 归因树。
- 完整事件平台和数据平台。
- 金融 AI 分析模块。

## 10. 工程实施顺序

```text
1. platform-api 工程骨架
2. execution-runtime 工程骨架
3. 最小数据库表
4. Fake Gateway
5. 模拟下单闭环
6. 前端替换核心 Mock
7. Crypto Paper Trading PoC
8. MT5 Demo PoC
9. 基础风险与对账
```

## 11. 近期开发阅读顺序

1. `platform-target-architecture.md`
2. `reference-code-adoption-matrix.md`
3. `../../../docs/codex/current-state.md`
4. `decisions/ADR-012-初期架构简化与复杂度控制.md`
5. `domain/instrument-minimum-model.md`
6. `domain/account-position-minimum-model.md`
7. `domain/economic-event-pnl-minimum-model.md`
8. `integration/runtime-command-event-contract.md`

其余完整领域、状态、数据和安全文档作为查询资料，不代表首期必须全部实现。

## 12. 架构阶段状态

简化架构现已具备进入工程阶段的条件。

当前实施顺序和已完成能力以 `../../../docs/codex/current-state.md` 为准；历史 P1–P3 路线不再作为执行入口：

```text
P1 Platform Backend 最小骨架
→
P2 Runtime + Fake Gateway
→
P3 策略管理最小查询
```
