# Platform V6 前端策略注册表规范

状态：`active`  
适用分支：`refactor/frontend-architecture-v6`  
架构层级：前端架构

## 1. 文档定位

前端策略注册表统一管理策略 ID、名称、分类、页面能力和基础结构属性，避免交易平台、策略管理、Mock 数据和路由分别维护不同策略清单。

注册表是前端静态能力声明的唯一代码来源，不是未来后端策略运行实例、账户状态、参数版本或风险规则的最终权威。

前端总览参见 `frontend/frontend-overview.md`，公共 Strategy 模型参见 `domain-model-boundaries.md`。

## 2. 当前位置

```text
src/views/strategy/shared/strategyRegistry.ts
```

在目录架构整体重构前，不为注册表单独进行大规模代码迁移。

## 3. 稳定策略 ID

```ts
export type StrategyId =
  | 'funding'
  | 'crossSpread'
  | 'domesticOverseas'
  | 'dip'
  | 'shortLineTraderL'
  | 'shortLineTraderW';
```

不得继续保留 `spread` 等已经废弃或与正式策略身份重复的 ID。

## 4. 注册表结构

```ts
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
    v1ExecutionScope?: 'complete' | 'simulation_only' | 'none';
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

## 5. 当前注册内容

| 策略 ID | 正式名称 | 类型 | 交易平台 | 策略管理 | 腿结构 | 账户结构 |
|---|---|---|---:|---:|---|---|
| `funding` | 资费套利 | 套利 | 是 | 是 | 双腿 | 双账户 |
| `crossSpread` | 跨所价差 | 套利 | 是 | 是 | 双腿 | 双账户 |
| `domesticOverseas` | 海内外价差 | 套利 | 是 | 是 | 双腿 | 双账户 |
| `dip` | 抄底 | 方向性 | 否 | 是 | 单腿 | 单账户 |
| `shortLineTraderL` | 短线交易员 L | 日内 | 否 | 是 | 单腿 | 单账户 |
| `shortLineTraderW` | 短线交易员 W | 日内 | 否 | 是 | 单腿 | 单账户 |

结构属性以当前已确认业务为准。V1 执行范围另行区分：`funding` 和 `crossSpread` 为 `complete`；`domesticOverseas` 为 `simulation_only`；`dip`、`shortLineTraderL`、`shortLineTraderW` 为 `none`。若后续确认策略存在多账户、多腿或新的执行能力，应同时更新策略文档、能力矩阵和注册表。

## 6. 模块使用规则

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

页面不得自行维护另一份完整策略主清单。

## 7. 与公共 Strategy 领域模型的关系

前端注册表对应 StrategyDefinition 的静态子集，主要用于：

- 稳定策略 ID。
- 默认名称和简称。
- 页面排序。
- 前端页面能力。
- 基础腿和账户结构。

后端未来负责：

- StrategyVersion。
- StrategyInstance。
- 运行环境和运行状态。
- 账户绑定。
- 参数版本。
- 权限和风险配置。

前端不得通过注册表推断策略当前是否运行、是否允许交易或实际绑定了哪些账户。

注册表中的 `platform.enabled = true` 只代表交易平台存在入口，不代表 V1 可提交真实执行命令。真实交易能力由后端 TradingPermissionState、GatewayCapability、StrategyInstance、账户绑定、风控和审批共同决定。

## 8. 注册表与策略配置的边界

注册表不负责：

- 指标和图表数据。
- 损益科目和计算公式。
- 交易参数默认值。
- 订单、成交和持仓。
- 账户余额和保证金。
- 风险阈值。
- 页面 CSS。
- 后端接口地址。

策略特有业务规则由 `docs/strategies/*.md` 定义；页面配置和数据通过对应模块的配置、Repository 和 Adapter 提供。

## 9. Mock 和接口使用规则

- Mock 数据对象使用 `StrategyId` 作为键。
- API Adapter 将后端策略 ID 映射为稳定 `StrategyId`。
- 路由参数只接受合法 `StrategyId`。
- 不以 Mock 数据是否存在决定策略是否展示。
- 不在不同文件使用不同 ID 表示同一策略。

当后端返回未识别策略时，前端应进入明确的兼容或不支持状态，不自行创建临时策略名称。

## 10. 接入顺序

1. 交易平台页签改为读取 `platformStrategies`。
2. 策略管理页签改为读取 `managementStrategies`。
3. 统一 Mock 和页面类型使用 `StrategyId`。
4. 删除 `spread` 等废弃 ID。
5. 统一路由参数校验和非法值回退。
6. 建立后端策略定义 Adapter。
7. 删除所有重复策略主清单。

接入过程应保持现有可见策略范围和页面行为，不一次性重写策略页面、Mock、路由和目录结构。

## 11. 禁止事项

- 不在 `platform/index.vue` 单独维护完整策略名称清单。
- 不在策略管理 Mock 中维护策略主顺序。
- 不在注册表中放入大块页面配置和业务数据。
- 不把注册表当作真实策略运行状态。
- 不因为策略未进入交易平台，就从策略管理删除。
- 不让后端显示名称变化破坏稳定策略 ID。

## 12. 验收标准

- 前端只有一套稳定策略 ID 定义。
- 交易平台和策略管理均从注册表筛选策略。
- Mock、路由和页面类型使用统一 `StrategyId`。
- 注册表不包含动态账户、订单、持仓、损益和风险数据。
- 后端策略主数据接入后，页面不需要重新定义策略身份。
