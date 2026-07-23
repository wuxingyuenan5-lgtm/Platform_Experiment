# Platform V6 查询与后端读模型规范

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：后端架构

## 1. 文档定位

本文档定义权威领域对象、后端 Read Model、API DTO 和前端 View Model 之间的边界。

复杂页面可以读取聚合结果，但聚合查询不得形成第二套订单、账户、持仓、损益或风险权威。

## 2. 分层关系

```text
Domain Facts / Authoritative State
                ↓ projection / aggregation
Backend Read Model
                ↓ API mapping
API DTO
                ↓ frontend adapter
Frontend Domain Model / View Model
```

### Domain Facts

由主责领域维护的权威事实，例如：

- Order 和 Fill。
- MT5 Deal 和账户历史摘要。
- Account 和 BalanceSnapshot。
- Position。
- PnLResult。
- StrategyNavSnapshot。
- RiskDecision。
- ReconciliationResult。

### Backend Read Model

为稳定查询场景形成的只读投影或聚合，例如：

- 交易执行工作台摘要。
- 策略管理损益总览。
- 多账户资金对照。
- 当前未完成执行批次列表。
- 风险和数据质量综合摘要。

### API DTO

面向具体 API 版本的传输结构。

### Frontend View Model

面向页面展示、格式化和交互的结构。

## 3. 权威对象查询与页面查询

### 3.1 权威对象查询

用于读取单一对象或明确集合，例如：

- `GET /orders/{orderId}`
- `GET /execution-batches/{id}`
- `GET /accounts/{accountId}/balances/latest`
- `GET /positions?accountId=...`

响应应尽量接近稳定领域语义，并包含版本和更新时间。

### 3.2 页面 Read Model 查询

用于一次性满足页面决策需求，例如交易执行页可以组合：

- StrategyInstance。
- QuoteSnapshot。
- BalanceSnapshot 和 MarginSnapshot。
- RiskDecision。
- TradingPermissionState。
- 当前 ExecutionBatch。

建议使用明确页面用例名称，而不是返回任意拼接对象，例如：

```text
GET /api/v1/trading-workspaces/{strategyInstanceId}
GET /api/v1/strategy-management/{strategyId}/pnl-overview
GET /api/v1/strategy-management/{strategyId}/capital-overview
```

页面 Read Model 是查询契约，不是新的业务聚合根。

## 4. Read Model 所有权

- 原始字段和业务规则仍由主责领域拥有。
- Platform API／BFF 或专门查询层可以组合多个领域结果。
- Read Model 可以存储为投影以提高查询效率。
- Read Model 不得成为命令写入入口。
- Read Model 不得直接修改领域对象。
- Read Model 失效时可以从权威事实重建。

## 5. 数据新鲜度

Read Model 必须表达：

- `generatedAt`
- `dataTime`
- `sourceVersions` 或来源更新时间
- DataQualityStatus
- 是否估算
- 是否包含部分数据

不同来源更新时间不一致时，应明确展示或标记 partial／delayed，不得伪装成同一时点快照。

## 6. 一致性要求

### 强一致需求

适用于：

- 提交命令前读取的关键权限、风险和账户校验。
- 订单和 ExecutionBatch 单对象状态确认。
- 高风险配置保存前版本检查。

这些场景应直接读取权威服务或具备明确一致性保证的读模型。

### 最终一致需求

适用于：

- 策略损益总览。
- 历史报表摘要。
- 多模块首页摘要。
- 研究看板聚合。

最终一致读模型必须显示更新时间和质量状态。

## 7. 缓存与失效

可以缓存：

- 策略定义和标的基础信息。
- 历史统计和报表读模型。
- 非交易关键页面摘要。

交易关键读模型在以下事件后应主动失效或刷新：

- TradeCommandAccepted。
- ExecutionBatchStatusChanged。
- Order 或 Fill 更新。
- MT5 Deal 更新。
- BalanceSnapshotUpdated。
- PositionUpdated。
- StrategyNavSnapshotUpdated。
- RiskDecisionChanged。
- Gateway 状态变化。
- 权限、TradingMode 或账户绑定变化。

缓存不得成为交易事实的唯一来源。

## 8. 写后读

提交命令后：

1. 命令响应返回 commandId 和目标对象 ID，适用时。
2. 前端进入已受理或待确认状态。
3. 通过对象查询或实时事件获取后续状态。
4. 页面 Read Model 在必要时失效并重新查询。

不得仅修改前端表格行来模拟权威写入完成。

## 9. 分页、排序和快照一致性

- 订单和成交列表使用稳定排序字段。
- 游标分页优先基于稳定 ID、事件时间或序列。
- 同一次分页查询应尽量保持查询快照或明确数据可能变化。
- `total` 计算成本过高时可以省略，但契约需明确。
- 实时新增数据不应导致用户在翻页时无提示丢失或重复记录。

## 10. Read Model 版本

Read Model 应记录：

- 模型版本。
- 生成逻辑版本，适用时。
- 来源领域版本或截止时间。

结构发生破坏性变化时，通过 API 版本或新查询模型迁移，不在同一字段中改变含义。

## 11. 错误与降级

聚合查询中部分来源失败时，应区分：

- 整体不可用。
- 部分数据可用。
- 使用上一次成功快照。
- 数据过期。
- 来源冲突。

前端不应因为一个非关键摘要失败而丢失全部页面，也不能在关键交易校验数据失败时继续开放操作。

## 12. 禁止事项

- 不让 BFF 重新实现损益、风险和订单规则。
- 不将页面卡片一一建成后端领域对象。
- 不把 Read Model 当作普通更新接口。
- 不在读模型中无痕修正权威事实。
- 不用一个“万能 dashboard 接口”承载所有页面且无法版本管理。
- 不让前端直接拼接多个相互矛盾的权威结果完成交易判断。
- 不让前端把 Funding Rate、MT5 Order 或 Mock 数据加工成正式收益、成交或净值。

## 13. 验收标准

- 权威对象、后端 Read Model、API DTO 和前端 View Model 明确分开。
- 页面聚合不形成第二套数据权威。
- 交易关键查询具有明确一致性和新鲜度。
- Read Model 可以失效、重建和版本化。
- 写入后通过权威对象或事件恢复页面状态。
- 部分失败和数据过期可以明确表达。
- 策略管理读模型能区分真实 API 模拟/测试/Demo、Fake、Simulation 和未来 Live 的来源状态。
