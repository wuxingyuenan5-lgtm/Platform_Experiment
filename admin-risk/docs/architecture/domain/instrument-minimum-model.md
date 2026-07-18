# Instrument 最小领域模型

状态：`active`  
架构版本：Platform V6+  
适用分支：`refactor/frontend-architecture-v6`

## 1. 目的

本文只定义初期行情展示、交易下单、单位换算和外部标的映射所需的最小 Instrument 模型。

不建设完整证券主数据平台。

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

这些能力只有在真实业务需要时再扩展。

## 9. 核心原则

- 页面 symbol 不是 InstrumentId。
- TradingView symbol 不是交易 symbol 的唯一来源。
- MT5 symbol 可能按 Broker 和账户变化。
- ContractSpecification 可以按 Venue 或 Account 覆盖。
- 不因未来扩展需要提前增加大量字段。
