# EconomicEvent / PnL 最小模型

状态：`active`  
适用分支：`refactor/frontend-architecture-v6`

## 1. 目标

只保留策略收益计算、成本归集、资金费率／库存费记录和对账所需的最小模型。

第一阶段仅包含：

- EconomicEvent。
- PnLResult。
- PnLAttributionItem。

不建设完整财务总账、基金 NAV 和复杂会计科目体系。

## 2. EconomicEvent

EconomicEvent 表示已经发生、会影响策略经济结果的事实。

最小字段：

```text
economicEventId
eventType
accountId
strategyInstanceId
instrumentId
amount
currency
quantity
quantityUnit
occurredAt
receivedAt
source
externalReference
qualityStatus
```

按事件类型允许部分字段为空。

第一阶段事件类型：

```text
trade_fill
commission
trading_fee
funding_settlement
swap_settlement
cash_adjustment
manual_adjustment
```

规则：

- FundingRate Snapshot 不是 EconomicEvent；实际 Funding Settlement 才是。
- Swap 只有实际结算后才形成 EconomicEvent。
- Fill 可以产生交易损益输入，但 Fill 本身仍属于交易领域。
- manual_adjustment 必须记录原因、操作人和审计引用。
- 原始事件不因后续重算而被覆盖。

## 3. PnLResult

PnLResult 表示指定时间区间、策略和计价币种下的收益计算结果。

最小字段：

```text
pnlResultId
strategyInstanceId
from
to
reportingCurrency
totalPnl
status
calculationVersion
dataAsOf
generatedAt
```

规则：

- PnLResult 是派生结果，不是原始事实。
- 相同口径重算时创建新版本或新结果，不覆盖旧结果。
- status 初期只使用 estimated、provisional、verified、superseded、failed。
- PnLResult 不称为正式 Fund NAV。

## 4. PnLAttributionItem

PnLAttributionItem 表示 PnLResult 下的收益归因项。

最小字段：

```text
pnlAttributionItemId
pnlResultId
category
amount
currency
```

第一阶段公共分类：

```text
trading_pnl
funding_pnl
swap_pnl
fees
fx_pnl
other_adjustment
```

策略可以在页面或报表中继续细分，但数据库第一阶段不要求复杂归因树。

例如：

- 资费套利可把现货平台溢价和永续基差合并归入 trading_pnl。
- 黄金跨所价差可以使用 trading_pnl、swap_pnl、fees 和 fx_pnl。
- 海内外黄金价差可以保留已有更细归因，但最终映射到公共分类。

## 5. 最小计算输入

第一阶段 PnL 只依赖：

- Fill。
- Commission／Trading Fee。
- Funding Settlement。
- Swap Settlement。
- 必要的价格和 FX Rate。
- Manual Adjustment，适用时。

缺失关键输入时：

```text
status = failed 或 provisional
```

不得静默按零处理。

## 6. 对账与修正

出现外部费用补录、成交修正或结算变化时：

```text
新增或修正 EconomicEvent
→ 创建新的 PnLResult
→ 旧结果标记 superseded
```

第一阶段不建设复杂 RecalculationRun 对象；通过 calculationVersion、generatedAt 和 superseded 关系满足追溯。

## 7. 暂不建设

第一阶段不建设：

- 完整复式记账。
- Finance Ledger。
- Investor 和 ShareClass NAV。
- 管理费、业绩报酬和申赎会计。
- 复杂会计期间关闭流程。
- 通用可配置归因树引擎。

## 8. 验收标准

- 实际成交、费用、Funding 和 Swap 可以形成可追溯经济事件。
- PnL 可以按 StrategyInstance 和时间区间计算。
- PnLResult 可版本化并可重算。
- 缺失输入不被当作零。
- 策略归因可以保留差异，但共享最小公共分类。
- 策略 PnL 不被称为正式 Fund NAV。
