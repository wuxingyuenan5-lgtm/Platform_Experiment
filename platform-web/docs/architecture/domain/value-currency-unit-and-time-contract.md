# Platform V6+ 数值、币种、单位与时间统一契约

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6+  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：公共领域与跨系统数据契约

配套文档：

- `domain-overview.md`
- `unified-domain-model.md`
- `status-enums-and-lifecycles.md`
- `../integration/api-contract-and-versioning.md`
- `../integration/runtime-command-event-contract.md`
- `../backend/storage-ledger-and-audit.md`
- `../../../../docs/technical/DATA_MODEL.md`

## 1. 文档定位

本文是 Platform Backend、Execution Runtime、API、数据库、数据导入、计算、报表和前端适配共同遵守的数值与时间语义唯一来源。

本文定义：

- Decimal 传输和计算规则。
- Money、Price、Quantity、Rate、Ratio 和 Percentage 的区别。
- Currency、Asset、Unit 和 ContractSpecification 的关系。
- 舍入、精度、最小变动单位和展示格式。
- FX 折算和计价币种。
- Instant、Local Date、businessDate、tradingDay、settlementDate 和 valuationDate。
- 外部时间、接收时间、处理时间和数据截止时间。

本文不决定具体 Decimal 库、数据库字段类型或时区库，但实现必须满足本文语义。

## 2. 核心原则

1. 正式金融数值不得依赖二进制浮点精度。
2. 数值与币种、资产或单位不可分离。
3. 存储值、计算值和展示值分开。
4. 舍入只在明确业务边界发生，不在中间计算中任意发生。
5. 百分比、比率和费率必须区分倍率语义。
6. 时间点、自然日期和业务日期必须分开。
7. 所有带时间的数据必须能回答“哪个时区、哪个日历、哪个截止时间”。
8. 缺失值、零值和不可用值不得混用。
9. 外部原始值保留，标准化过程可追溯。
10. API、Event、导入和报表使用同一基础语义。

## 3. Decimal 表达

### 3.1 跨系统传输

正式金额、价格、数量和费率通过十进制字符串传输：

```json
{
  "amount": "1250000.25",
  "price": "102212.00",
  "quantity": "0.5000",
  "rate": "0.000125"
}
```

禁止：

```json
{
  "amount": 1250000.25,
  "quantity": 0.1
}
```

原因是 JSON Number、JavaScript Number 和部分语言默认浮点不能保证金融精度。

### 3.2 标准格式

- 使用普通十进制字符串。
- 不含千位分隔符。
- 不含币种符号。
- 不含百分号。
- 不使用科学计数法，除非专项契约明确允许。
- 负号仅出现在字符串首位。
- `0`、`0.0` 和 `0.0000` 数值相等，但原始 scale 可以按业务需要保留。

### 3.3 领域内计算

领域层使用任意精度 Decimal 或等效类型。

不得在以下对象中使用 float／double 作为权威值：

- Order quantity 和 price。
- Fill quantity、price 和 fee。
- Balance、Margin 和 Position。
- EconomicEvent 和 LedgerEntry。
- PnL、NAV、Risk Limit 和 Exposure。
- FundingRate、FX Rate 和合约乘数。

## 4. 标准值对象

### 4.1 Money

Money 表示某种 Currency 下的货币金额：

```text
Money
- amount: Decimal
- currency: CurrencyCode
```

示例：

```json
{
  "amount": "1250000.25",
  "currency": "USD"
}
```

Money 不表达资产数量，例如 `0.5 BTC` 是 Quantity，不是 Money。

### 4.2 Price

Price 表示每单位基础资产对应的计价价值：

```text
Price
- value: Decimal
- quoteCurrency / quoteAsset
- priceUnit
```

示例：

```json
{
  "value": "102212.00",
  "quoteAsset": "USDT",
  "priceUnit": "USDT_PER_BTC"
}
```

Price 必须能结合 Instrument 和 ContractSpecification 解释经济含义。

### 4.3 Quantity

Quantity 表示资产、合约、手数或其他业务单位数量：

```text
Quantity
- value: Decimal
- unit: UnitCode
```

示例：

```json
{ "value": "0.5000", "unit": "BTC" }
{ "value": "5", "unit": "LOT" }
{ "value": "10", "unit": "CONTRACT" }
{ "value": "5000", "unit": "GRAM" }
```

`5 LOT` 不能在没有 ContractSpecification 时自动解释为资产数量。

### 4.4 Rate

Rate 是无量纲或具有明确周期语义的十进制率：

```text
Rate
- value: Decimal
- rateType
- period / basis，适用时
```

示例：

```json
{
  "value": "0.000125",
  "rateType": "funding_rate",
  "period": "8H"
}
```

`0.000125` 表示十进制率，即 `0.0125%`，不是 `0.000125%`。

### 4.5 Ratio

Ratio 表示两个量的比例，不自动乘以 100：

```json
{
  "value": "1.025",
  "numerator": "XAUTUSDT_PRICE",
  "denominator": "XAUUSD_PRICE"
}
```

### 4.6 Percentage

Percentage 只用于明确的百分数展示或传输场景：

```text
Percentage.value = 1.25
```

表示 `1.25%`。

领域计算优先使用 Rate；Percentage 通常由 Adapter 或 View Model 转换。

### 4.7 BasisPoint

需要明确基点时：

```text
1 bp = 0.0001 Rate = 0.01%
```

禁止将 bp 数值与 Rate 数值直接相加。

## 5. Currency 与 Asset

### 5.1 CurrencyCode

法币优先使用 ISO 4217 代码，例如：

- USD。
- CNY。
- JPY。
- EUR。

数字资产使用平台稳定 AssetCode，例如：

- BTC。
- ETH。
- USDT。
- USDC。

稳定 AssetId 与显示 Code 分开；Code 改名或映射变化不得改变历史身份。

### 5.2 Reporting Currency

至少区分：

- Instrument Quote Currency。
- Account Currency。
- Settlement Currency。
- Strategy Reporting Currency。
- Portfolio Reporting Currency。
- Fund Reporting Currency。

不得把“页面当前显示币种”当作原始事实币种。

### 5.3 Stablecoin

USDT、USDC 等不自动等同于 USD。

如需按 1:1 展示或计算，必须具有：

- 明确估值政策。
- FX／Conversion Rate 来源。
- dataAsOf。
- 数据质量。
- 是否使用固定值或市场值。

V1 默认以 USDT 作为策略运行净值和主要绩效展示币种。跨所价差在 Crypto/MT5 Demo 或测试链路中可以临时按 USD/USDT = 1 展示，但必须标记为 `estimated` 或 `provisional`，并记录使用固定值、dataAsOf 和质量状态；该口径不能直接用于正式 Live、客户展示或 Fund NAV。

## 6. FX Rate

标准结构：

```text
FxRate
- baseCurrency
- quoteCurrency
- rate
- source
- observedAt
- dataAsOf
- qualityStatus
```

定义：

```text
1 baseCurrency = rate quoteCurrency
```

例如：

```json
{
  "baseCurrency": "USD",
  "quoteCurrency": "CNY",
  "rate": "7.1800"
}
```

表示 `1 USD = 7.1800 CNY`。

折算必须记录：

- 原始金额和币种。
- 目标币种。
- 使用的 FxRateId 或版本。
- 汇率时间。
- 舍入结果。

不得只保存折算后金额。

## 7. Unit 与合约规格

### 7.1 UnitCode

候选标准单位包括：

- `UNIT`。
- `CONTRACT`。
- `LOT`。
- `SHARE`。
- `COIN`。
- `GRAM`。
- `KILOGRAM`。
- `TROY_OUNCE`。
- `USD_NOTIONAL`。
- `CNY_NOTIONAL`。

数字资产可使用具体 AssetCode 作为数量单位。

### 7.2 ContractSpecification

合约换算必须依赖版本化 ContractSpecification：

- contractMultiplier。
- contractSize。
- quantityUnit。
- priceUnit。
- tickSize。
- tickValue。
- lotSize。
- minQuantity。
- quantityStep。
- minNotional。
- settlementCurrency。
- effectiveFrom／effectiveTo。

### 7.3 不同市场示例

沪金：

```text
Quantity = 5 CONTRACT
Contract Size = 1000 GRAM / CONTRACT
Underlying Quantity = 5000 GRAM
```

MT5 CFD：

```text
Quantity = 5 LOT
Contract Size = Broker-specific units / LOT
```

Crypto Spot：

```text
Quantity = 0.5 BTC
```

Crypto Perpetual：

可能按 coin、contract 或 quote notional 表达，必须由具体合约规格决定。

## 8. 精度和舍入

### 8.1 精度来源

精度来源包括：

- Currency minor unit。
- Instrument tickSize。
- quantityStep。
- ContractSpecification。
- 外部场所规则。
- PnL／NAV／报表政策。

前端小数位不是领域精度来源。

### 8.2 舍入边界

允许舍入的典型边界：

- 生成外部订单参数前。
- 费用和结算规则要求时。
- EconomicEvent 正式记账时。
- 报表和展示输出时。

中间计算保持足够精度。

### 8.3 舍入模式

每类正式计算明确舍入模式，例如：

- HALF_EVEN。
- HALF_UP。
- FLOOR。
- CEILING。
- TRUNCATE。

订单数量经常需要按 quantityStep 向下取整，但不得把该规则泛化到所有金额计算。

### 8.4 原始值与标准值

外部返回数值可同时保存：

- rawValue。
- normalizedValue。
- normalizationRuleVersion。

标准化不得丢失必要证据。

## 9. 缺失、零和不可用

必须区分：

- `null`：当前不存在或未提供。
- `0`：已确认数值为零。
- `unavailable`：来源当前不可用。
- `not_applicable`：该字段不适用。
- `unverified`：值存在但未核对。

不得：

- 用 `0` 代替缺失费用。
- 用 `--` 进入领域和 API。
- 用空字符串表示未知币种。
- 用 NaN 或 Infinity 持久化正式结果。

## 10. 时间基础类型

### 10.1 Instant

Instant 表示全球唯一时间点，使用 ISO 8601／RFC 3339 并包含时区偏移，跨系统传输优先 UTC：

```text
2026-07-18T08:30:15.123Z
```

### 10.2 LocalDate

自然日期：

```text
2026-07-18
```

LocalDate 不含时区和时间点，必须结合业务日历理解。

### 10.3 LocalTime 和 ZonedDateTime

交易时段、日界线和计划任务需要保存：

- localTime。
- timeZoneId，使用 IANA 标识，例如 `Asia/Tokyo`。
- calendarId 或 sessionId，适用时。

不要只保存 `UTC+8`，因为固定偏移不能完整表达夏令时和历史规则。

## 11. 标准时间字段

### 11.1 occurredAt

业务事实实际发生时间。

### 11.2 externalTime

外部交易所、Broker、MT5 或供应商提供的时间。

### 11.3 receivedAt

Platform 或 Runtime 首次接收到数据的时间。

### 11.4 processedAt

完成标准化或领域处理的时间。

### 11.5 publishedAt

事件发布到通道的时间。

### 11.6 createdAt 和 updatedAt

平台记录创建和最后更新时间，不替代业务发生时间。

### 11.7 dataAsOf

某项快照、计算或报表所覆盖数据的截止时间。

### 11.8 generatedAt

派生结果或报表的生成时间。

## 12. 业务日期

### 12.1 businessDate

对象归属的业务日期，由具体领域、时区和日界线决定。

例如短线交易员使用自定义日界线时，凌晨成交可以归属于前一个 businessDate。

### 12.2 tradingDay

交易场所或交易日历定义的交易日。

夜盘跨越自然日时，tradingDay 可能与 occurredAt 的 LocalDate 不同。

### 12.3 settlementDate

资金、成交或合约完成结算的业务日期。

### 12.4 valuationDate

估值和绩效计算归属日期。

### 12.5 accountingDate

未来财务账本或基金会计使用的会计日期；当前 Strategy Economic Ledger 不应擅自将 businessDate 等同 accountingDate。

## 13. 日历和交易时段

平台应维护稳定：

- CalendarId。
- TradingSessionId。
- TimeZoneId。
- Open／Close 时间。
- Holiday。
- Half Day。
- Maintenance Window。
- Settlement Cutoff。
- Business Day Convention。

不同 Venue、Broker 和策略可以使用不同日历。

策略不得在代码中仅凭服务器本地日期推导交易日。

## 14. MT5 时间

MT5 需要区分：

- Terminal／Broker server time。
- UTC。
- 本地操作系统时间。
- 策略 businessDate。

Broker Server Time 及其 UTC 偏移可能变化。Runtime 应记录转换规则和观测时间，不能长期硬编码一个固定偏移。

Swap／库存费归属至少保留：

- 外部 Deal 时间。
- Broker business date，若可获得。
- 平台 receivedAt。
- Settlement businessDate。

跨所价差 V1 使用 MT5 Demo/Worker 时，Deal 时间、Broker server time、平台 receivedAt 和 Strategy businessDate 必须同时可追溯。页面不能只按浏览器本地日期归属成交和库存费。

## 15. Crypto 时间

Crypto 24／7 交易不代表所有经济事件没有业务边界。

需要区分：

- 交易所事件时间。
- Funding interval start／end。
- Funding settlement time。
- UTC 日界线。
- 策略自定义 businessDate。

FundingRate Snapshot 和 FundingSettlement 使用不同时间语义。

## 16. CTP 与国内期货时间

需要区分：

- ActionDay。
- TradingDay。
- Exchange time。
- 夜盘自然日期。
- 结算日期。

Adapter 必须保留外部原始字段，并映射为平台 occurredAt、tradingDay 和 settlementDate。

CTP、国内期货平今/平昨、夜盘结算和人民币正式 FX PnL 不进入 V1 完整闭环验收。海内外价差 V1 只保留分析、模拟、字段和管理入口；这些时间口径作为后续扩展标准保留。

## 17. 固定时间净值快照

V1 策略净值按固定时间生成 StrategyNavSnapshot，默认计价 USDT。

最低要求：

- snapshotTime：本次快照时间点。
- valuationDate：快照归属日期。
- dataAsOf：纳入计算的数据截止时间。
- generatedAt：计算完成时间。
- equity：账户权益或策略归属权益。
- capitalBase：策略净值基准资金。
- nav：`equity / capitalBase`。
- status：见 StrategyNavSnapshotStatus。
- source 和 qualityStatus。

StrategyNavSnapshot 是策略运行观察指标，不是正式 Fund NAV。数据未接入或未核对时，不得用前端估算替代正式快照。

## 18. 时间同步和可信度

Platform Backend、Runtime 和 Worker 节点需要时间同步。

至少监控：

- 与可信时间源的偏差。
- Runtime／Worker 节点偏差。
- 外部时间与 receivedAt 延迟。
- 事件乱序和未来时间戳。

时间偏差超过阈值时，可以降级行情质量或阻断时间敏感交易。

## 19. API 和 Event 规则

- 时间点使用带偏移 ISO 8601。
- 自然日期使用 `YYYY-MM-DD`。
- 时区使用 IANA Time Zone ID。
- Decimal 使用字符串。
- Currency、Unit 和 RateType 使用稳定代码。
- API 不传格式化金额。
- Event 保留 occurredAt、receivedAt 和 publishedAt。
- 派生结果保留 dataAsOf 和 generatedAt。
- StrategyNavSnapshot 同时保留 snapshotTime、valuationDate、dataAsOf 和 generatedAt。
- 未知新 Unit、Currency 或 RateType 由消费者降级处理，不得自动解释。

## 20. 前端规则

前端负责：

- 按用户区域格式化。
- 千分位和小数位展示。
- 百分号和币种符号。
- 时区转换和时区提示。
- 原始币种与折算币种提示。

前端不负责：

- 用格式化字符串参与计算。
- 自行决定订单精度。
- 自行推导 businessDate 和 tradingDay。
- 无来源地将 USDT 当 USD。
- 在缺少 FX Rate 时展示伪精确折算结果。
- 用浏览器时间自行生成正式净值快照。

## 21. 数据库和导入规则

数据库实现需要：

- Decimal／Numeric 或等效精确类型。
- 数值与 Currency／Unit 字段共同约束。
- 时间点保存 UTC Instant，并按需保存外部时区语义。
- businessDate 等单独保存为 Date。
- 导入保留 rawValue、rawTime 和 sourceTimeZone。
- 数据修正不覆盖原始导入事实。

CSV／Excel 导入不得依赖本地千位符、小数点和日期格式猜测；格式必须在 ImportDefinition 中声明。

## 22. 核心不变量

1. Money 必须包含 Currency。
2. Quantity 必须包含 Unit。
3. Price 必须能结合 Instrument 和 PriceUnit 解释。
4. Rate 使用十进制倍率，不默认使用百分数。
5. Stablecoin 不自动等于法币。
6. 外汇方向必须明确 base 和 quote。
7. 中间计算不任意舍入。
8. 缺失不等于零。
9. occurredAt 不等于 receivedAt。
10. businessDate 不等于自然日期。
11. tradingDay 不等于 settlementDate。
12. dataAsOf 不等于 generatedAt。
13. 展示字符串不进入领域计算。
14. 外部原始数值和时间可追溯。
15. StrategyNavSnapshot 的 snapshotTime、valuationDate、dataAsOf 和 generatedAt 不得混用。

## 23. 验收标准

- API 和 Runtime 契约不使用浮点承载正式金融值。
- Money、Price、Quantity 和 Rate 具有明确结构和语义。
- 合约数量可通过版本化 ContractSpecification 换算。
- FX 折算可追溯原始金额、汇率和时间。
- 零、缺失和不适用可以区分。
- 交易、结算和估值业务日期可以区分。
- MT5、Crypto 和 CTP 时间可以映射且保留原始语义。
- 前端只负责格式化，不重新定义精度和业务日。
- V1 固定时间策略净值快照具备 USDT 计价、数据截止时间、生成时间和质量状态。
- USD/USDT 临时 1:1 口径只用于标记清楚的 Demo/Test/Simulation，不作为正式 Live 或客户展示口径。
