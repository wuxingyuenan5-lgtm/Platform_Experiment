# Platform 0.10.x 前端数据适配与 View Model 规范

状态：`active`  
适用分支：`refactor/frontend-architecture-v6`  
架构层级：前端架构

## 1. 文档定位

本文档定义前端如何接收 Mock、旧接口和未来正式后端数据，并转换为稳定领域对象和页面 View Model。

目标是让页面组件不直接依赖具体接口字段，也不把格式化后的字符串当作业务数据。

## 2. 分层结构

```text
Mock DTO / API DTO / Import DTO
              ↓ Adapter
        Domain Model
              ↓ Selector / Mapper
          View Model
              ↓
        Vue Component
```

### DTO

DTO 描述某一数据来源的传输格式，可以随接口、供应商或版本变化。

### Domain Model

Domain Model 表达稳定业务语义，例如 Order、Fill、Deal、ExecutionBatch、Position、PnLResult 和 StrategyNavSnapshot。

### View Model

View Model 只服务于页面展示，例如：

- 已格式化金额。
- 状态标签文案。
- 图表序列。
- 表格列值。
- 操作是否可用及禁用原因。

## 3. Repository Interface

页面和 composable 不直接调用具体 axios 方法或读取 Mock 文件，应依赖稳定 Repository 接口。

示例：

```ts
interface StrategyManagementRepository {
  getPnl(query: PnlQuery): Promise<PnlResult>;
  getCapital(query: CapitalQuery): Promise<CapitalSnapshot>;
  getOrders(query: OrderQuery): Promise<PageResult<Order>>;
}
```

实现可以包括：

- `MockStrategyManagementRepository`
- `ApiStrategyManagementRepository`
- `ImportedStrategyManagementRepository`

切换实现不应要求重写页面组件。

## 4. Adapter 职责

Adapter 负责：

- 字段名称转换。
- 外部 symbol 映射为 `instrumentId`。
- 外部账户标识映射为 `accountId`。
- 时间格式和时区转换。
- 状态码映射。
- 数值、精度和币种转换。
- 缺失字段和兼容版本处理。
- 数据质量状态生成。

Adapter 不负责：

- 页面布局。
- 业务规则补造。
- 通过猜测生成真实订单状态。
- 为缺失数据虚构零值。
- 修改后端最终事实。

## 5. 数值模型

业务数据不得长期保存为带单位字符串。

推荐结构：

```ts
interface MoneyValue {
  amount: string;
  currency: string;
}

interface QuantityValue {
  amount: string;
  unit: string;
}

interface RatioValue {
  value: string;
  scale: 'decimal' | 'percent';
}
```

金融金额和高精度数量优先使用字符串传输，并在计算层使用 Decimal 类库；避免直接依赖 JavaScript 浮点数完成正式损益和数量计算。

## 6. 状态模型

状态必须由明确字段提供，不通过显示文本推断。

错误示例：

```ts
const negative = row.pnl.startsWith('-');
const warning = row.status.includes('高');
```

正确方向：

```ts
interface PnlViewModel {
  formattedValue: string;
  direction: 'positive' | 'negative' | 'neutral';
}

interface StatusViewModel {
  code: string;
  label: string;
  severity: 'neutral' | 'info' | 'success' | 'warning' | 'danger';
}
```

## 7. 时间模型

至少区分：

- `occurredAt`：业务事件实际发生时间。
- `sourceTime`：外部数据源时间。
- `receivedAt`：平台接收时间。
- `calculatedAt`：指标计算时间。
- `updatedAt`：记录更新时间。

View Model 负责按用户时区格式化，但 Domain Model 保留标准时间字段。

## 8. 数据质量

所有重要数据查询应能够表达：

- `fresh`
- `delayed`
- `stale`
- `missing`
- `partial`
- `conflicted`
- `unverified`

View Model 应展示：

- 更新时间。
- 数据来源。
- 质量状态。
- 是否为估算值。
- 是否允许继续操作。

## 9. 查询状态

业务数据和请求状态分开：

```ts
interface QueryState<T> {
  data?: T;
  loading: boolean;
  error?: AppError;
  lastUpdated?: string;
}
```

不得在业务对象内部塞入页面 loading、弹窗开关和分页状态。

## 10. 缓存原则

- 行情和实时状态缓存时间短，并显示新鲜度。
- 策略定义和标的基础信息可以较长时间缓存。
- 账户、持仓、订单和风险状态在执行操作后应主动失效或重新查询。
- 浏览器缓存不得成为最终权威。
- 用户退出、权限变化或环境变化时清理敏感缓存。

## 11. Mock 迁移原则

Mock 数据必须：

- 使用稳定领域 ID。
- 尽量符合未来接口契约。
- 明确标识 `demo` 或 `mock` 来源。
- 同时覆盖成功、空数据、延迟、失败和部分数据场景。
- 不在组件中直接定义大块业务数据。

接入正式 API 时：

1. 保留 Repository 接口。
2. 新增 API DTO 和 Adapter。
3. 切换 Repository 实现。
4. 通过契约测试验证 Mock 和 API 语义一致。

Mock 不得伪装成真实成交、真实资金费入账、MT5 Deal 或正式净值。V1 中，资费套利和跨所价差的真实 API 模拟/测试/Demo 数据必须通过 API Adapter 进入页面，并保留 source、tradingMode、qualityStatus 和 isEstimated。
5. 页面不直接感知数据来源变化。

## 12. View Model 组织

View Model 应按页面用例组织，不按后端接口一一复制。

例如策略损益页可以组合：

- PnLResult。
- Account 摘要。
- DataQualityState。
- RiskSnapshot。

但组合逻辑应位于 selector、mapper 或 composable，不放入基础 UI 组件。

## 13. 错误处理

Adapter 错误至少区分：

- 字段缺失。
- 状态码未知。
- 数值解析失败。
- 时间解析失败。
- ID 映射失败。
- 版本不兼容。

不得静默吞掉错误并显示看似正常的零值。

## 14. 验收标准

- 页面不直接依赖完整 API 响应。
- Mock 和 API 通过同一 Repository 接口接入。
- View Model 可以格式化展示净值、收益和成交，但不得在前端生成正式 PnLResult、FundingSettlement 或 StrategyNavSnapshot。
- 金额、数量、比例和状态不是纯展示字符串。
- View Model 与 Domain Model 明确分离。
- 数据质量、更新时间和来源可展示。
- 接口变化主要影响 DTO 和 Adapter，而不是全部页面组件。
