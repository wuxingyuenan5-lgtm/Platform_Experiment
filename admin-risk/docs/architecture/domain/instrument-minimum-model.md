# Instrument 最小领域模型

状态：`active`  
架构版本：Platform V6+  
适用分支：`refactor/frontend-architecture-v6`

## 1. 目的

本文只定义初期行情展示、交易下单、单位换算和外部标的映射所需的最小 Instrument 模型。

不建设完整证券主数据平台。

V1 优先服务资费套利和跨所价差闭环。首批 Instrument 不追求覆盖全市场，只覆盖首个 Crypto Venue、首个 MT5 Demo Broker/Account，以及两个策略必须交易和观察的标的。

## 2. 只保留三个对象

```text
Instrument
InstrumentMapping
ContractSpecification
```

## 3. Instrument

表示平台内部稳定标的。

初期字段：

```ts
interface Instrument {
  instrumentId: string;
  code: string;
  name: string;
  productType: string;
  baseAsset?: string;
  quoteAsset?: string;
  settlementAsset?: string;
  status: 'active' | 'inactive';
}
```

说明：

- `instrumentId` 是平台稳定 ID。
- `code` 是内部简短代码，不等于交易所 symbol。
- `productType` 初期支持 spot、perpetual、future、cfd、index、fx、metal_spot 等实际需要类型。
- 页面显示名称可以由 View Model 处理。

## 4. InstrumentMapping

表示平台 Instrument 与外部系统 symbol 的对应关系。

初期字段：

```ts
interface InstrumentMapping {
  mappingId: string;
  instrumentId: string;
  externalSystem: string;
  venueId?: string;
  externalSymbol: string;
  accountId?: string;
  validFrom?: string;
  validTo?: string;
  status: 'active' | 'inactive';
}
```

用途示例：

```text
平台黄金现货
→ TradingView: OANDA:XAUUSD
→ MT5 Broker A: XAUUSD.a
→ MT5 Broker B: GOLD

平台 BTC 永续
→ Binance: BTCUSDT
→ Bybit: BTCUSDT
→ OKX: BTC-USDT-SWAP
```

同一 Instrument 可以有多个 Mapping。

V1 必须在开工前确定：

- 首个 Crypto Venue 的 spot、perpetual、funding 和账户 symbol 规则。
- 跨所价差的 Crypto 黄金标的，例如 XAUTUSDT.P 或交易所实际 symbol。
- 首个 MT5 Demo Broker/Account 的黄金 symbol，例如 XAUUSD、XAUUSD.a 或 GOLD。
- 每个 Mapping 是否按 accountId 区分。

不得把 TradingView symbol 当作下单 symbol 使用。

## 5. ContractSpecification

表示下单数量、价格步长和名义价值换算规则。

初期字段：

```ts
interface ContractSpecification {
  specificationId: string;
  instrumentId: string;
  venueId?: string;
  accountId?: string;
  quantityUnit: string;
  contractSize: string;
  contractSizeUnit: string;
  priceTick: string;
  quantityStep: string;
  minQuantity?: string;
  minNotional?: string;
  marginCurrency?: string;
  settlementCurrency?: string;
  validFrom: string;
  validTo?: string;
}
```

数值使用 Decimal 字符串。

## 6. 初期换算规则

统一使用：

```text
底层数量
= 下单数量
× contractSize
```

例如：

```text
沪金 5 CONTRACT
× 1000 GRAM / CONTRACT
= 5000 GRAM
```

MT5 LOT 必须使用具体 Broker／Account 的 ContractSpecification，不使用平台全局固定值。

跨所价差 V1 必须分别保存 Crypto 黄金合约规格和 MT5 黄金合约规格。XAUTUSDT.P、XAUUSD、XAUUSD.a、GOLD 等显示接近的 symbol，不代表合约乘数、最小手数、tick、保证金、库存费和交易时段一致。

## 7. 初期校验

下单前至少校验：

- Instrument 是否 active。
- 是否存在目标外部系统的有效 Mapping。
- 是否存在有效 ContractSpecification。
- 数量是否符合 quantityStep 和 minQuantity。
- 价格是否符合 priceTick。
- 名义价值是否满足 minNotional，适用时。

## 8. 暂不实现

当前不建设：

- 完整 ISIN、CUSIP、SEDOL 等全球证券编码体系。
- 公司行动和证券生命周期全模型。
- 复杂期权 Greeks 和波动率曲面主数据。
- 自动连续合约拼接规则。
- 全市场交易日历平台。
- 多级标的继承体系。
- CTP 国内期货合约、平今/平昨、换月和结算级主数据闭环。

这些能力只有在真实业务需要时再扩展。

## 9. 核心原则

- 页面 symbol 不是 InstrumentId。
- TradingView symbol 不是交易 symbol 的唯一来源。
- MT5 symbol 可能按 Broker 和账户变化。
- ContractSpecification 可以按 Venue 或 Account 覆盖。
- 不因未来扩展需要提前增加大量字段。
- V1 如果未确定首个 Crypto Venue 和首个 MT5 Demo Broker/Account，不应先开发多交易所、多券商的复杂映射体系。
