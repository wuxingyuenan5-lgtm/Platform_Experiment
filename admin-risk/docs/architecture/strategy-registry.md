# 统一策略注册表规范

状态：`active`  
适用基线：Platform V5

## 1. 目标

统一管理策略 ID、名称、分类、页面能力和结构属性，避免交易平台、策略管理、Mock 数据和未来接口分别维护不同的策略清单。

统一注册表不会要求交易平台和策略管理展示完全相同的策略。它只负责提供唯一策略定义，各模块再根据能力字段筛选。

## 2. 建议位置

现阶段建议放置于：

```text
src/views/strategy/shared/strategyRegistry.ts
```

在目录架构整体重构前，不建议为此单独大规模移动现有代码。

## 3. 数据结构

```ts
export type StrategyId =
  | 'funding'
  | 'crossSpread'
  | 'domesticOverseas'
  | 'dip'
  | 'shortLineTraderL'
  | 'shortLineTraderW';

export type StrategyCategory = 'arbitrage' | 'directional' | 'intraday';
export type StrategyLegModel = 'single' | 'dual' | 'multi';
export type StrategyAccountModel = 'single' | 'dual' | 'multi';

export interface StrategyManifest {
  id: StrategyId;
  name: string;
  shortName: string;
  category: StrategyCategory;
  order: number;

  platform: {
    enabled: boolean;
    analysis: boolean;
    execution: boolean;
  };

  management: {
    enabled: boolean;
    pnl: boolean;
    capital: boolean;
    orders: boolean;
  };

  structure: {
    legModel: StrategyLegModel;
    accountModel: StrategyAccountModel;
  };
}
```

## 4. 当前注册内容

```ts
export const strategyRegistry: StrategyManifest[] = [
  {
    id: 'funding',
    name: '资费套利',
    shortName: '资费',
    category: 'arbitrage',
    order: 10,
    platform: { enabled: true, analysis: true, execution: true },
    management: { enabled: true, pnl: true, capital: true, orders: true },
    structure: { legModel: 'dual', accountModel: 'dual' },
  },
  {
    id: 'crossSpread',
    name: '跨所价差',
    shortName: '跨所价差',
    category: 'arbitrage',
    order: 20,
    platform: { enabled: true, analysis: true, execution: true },
    management: { enabled: true, pnl: true, capital: true, orders: true },
    structure: { legModel: 'dual', accountModel: 'dual' },
  },
  {
    id: 'domesticOverseas',
    name: '海内外价差',
    shortName: '海内外价差',
    category: 'arbitrage',
    order: 30,
    platform: { enabled: true, analysis: true, execution: true },
    management: { enabled: true, pnl: true, capital: true, orders: true },
    structure: { legModel: 'dual', accountModel: 'dual' },
  },
  {
    id: 'dip',
    name: '抄底',
    shortName: '抄底',
    category: 'directional',
    order: 40,
    platform: { enabled: false, analysis: false, execution: false },
    management: { enabled: true, pnl: true, capital: true, orders: true },
    structure: { legModel: 'single', accountModel: 'single' },
  },
  {
    id: 'shortLineTraderL',
    name: '短线交易员 L',
    shortName: '短线 L',
    category: 'intraday',
    order: 50,
    platform: { enabled: false, analysis: false, execution: false },
    management: { enabled: true, pnl: true, capital: true, orders: true },
    structure: { legModel: 'single', accountModel: 'single' },
  },
  {
    id: 'shortLineTraderW',
    name: '短线交易员 W',
    shortName: '短线 W',
    category: 'intraday',
    order: 60,
    platform: { enabled: false, analysis: false, execution: false },
    management: { enabled: true, pnl: true, capital: true, orders: true },
    structure: { legModel: 'single', accountModel: 'single' },
  },
];
```

结构属性以当前 V5 的前端表达为起点。若后续确认某一策略存在多账户或多腿结构，应修改注册表和对应策略文档，不在页面中单独覆盖。

## 5. 模块使用规则

交易平台策略列表：

```ts
export const platformStrategies = strategyRegistry
  .filter((strategy) => strategy.platform.enabled)
  .sort((left, right) => left.order - right.order);
```

策略管理策略列表：

```ts
export const managementStrategies = strategyRegistry
  .filter((strategy) => strategy.management.enabled)
  .sort((left, right) => left.order - right.order);
```

## 6. 禁止事项

- 不在 `platform/index.vue` 单独维护另一套完整策略名称清单。
- 不在 `management/mock/orders.ts` 维护策略主清单。
- 不以 Mock 数据是否存在决定策略是否展示。
- 不使用不同 ID 表示同一策略。
- 不因为策略未进入交易平台，就从策略管理中删除。
- 不在注册表内放大量图表数据、订单数据或页面样式。

## 7. 注册表与策略配置的边界

注册表只负责平台级元数据：

- 策略 ID。
- 正式名称。
- 分类和排序。
- 模块能力。
- 腿和账户的基础模型。

各策略的指标、表格、损益科目、交易参数和图表配置，仍由对应策略文件维护。

## 8. 实施顺序

1. 新增注册表，不删除现有策略列表。
2. 让交易平台页签改为读取 `platformStrategies`。
3. 让策略管理页签改为读取 `managementStrategies`。
4. 统一 Mock 数据对象的键类型。
5. 验证路由、页签顺序和页面切换。
6. 再删除旧的重复策略主清单。

该改造不应改变 V5 当前可见策略范围和页面行为。
