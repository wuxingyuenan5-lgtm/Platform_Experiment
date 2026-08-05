# Platform 0.10.x 前端状态归属规范

状态：`active`  
产品基线：Platform V5  
架构版本：Platform V6  
适用分支：`refactor/frontend-architecture-v6`  
文档层级：前端架构

## 1. 文档定位

本文档定义浏览器前端中的路由状态、页面状态、模块状态、全局状态和服务端数据状态如何归属。

前端状态用于组织页面交互，不是订单、账户、持仓、损益、风险、审批和交易能力的最终权威。

## 2. 状态分类

### 2.1 路由状态

适用于：

- 刷新后应保留。
- 可以通过链接打开。
- 影响页面主视图或主要业务上下文。
- 浏览器前进和后退应恢复。

典型内容：

- 当前策略。
- 当前行情分析／交易执行视角。
- 当前策略损益／账户资金／订单信息视角。
- 当前看板分类。
- 当前新闻日历分类。

规则：

- 优先使用 path、route meta 或 query。
- 参数具有默认值、类型检查和非法值回退。
- 页面不同时维护另一份不同步的主状态。
- URL 不保存敏感数据、完整交易参数和权限结果。

### 2.2 页面本地状态

适用于当前页面生命周期内的交互：

- 图表显示项。
- 展开和折叠。
- 当前分页和临时筛选。
- 输入中的交易参数。
- 弹窗和确认框。
- 未提交表单修改。

规则：

- 使用 `ref`、`reactive` 或页面级 composable。
- 页面卸载后不需要保留的状态不进入全局 Store。
- 复杂页面状态抽到模块内 composable。
- 未提交交易参数离开页面时按需求提示确认。

### 2.3 模块共享状态

适用于同一模块多个页面或业务区块共享：

- 当前策略上下文。
- 当前账户组合。
- 当前 ExecutionBatch 摘要。
- 模块级筛选条件。
- 模块内临时选择和草稿。

规则：

- 优先使用模块内 composable 或 provider／inject。
- 只有确实跨路由并需要保留时才建立模块级 Pinia Store。
- 模块 Store 不承载其他模块的业务对象。
- ExecutionBatch 只保存展示和恢复所需引用，权威状态来自后端 Query 或 Event。

### 2.4 全局状态

仅适用于全平台共同依赖：

- 当前登录用户。
- 能力权限和数据范围。
- DeploymentEnvironment。
- TradingMode。
- TradingPermissionState 及原因摘要。
- 全局交易阻断摘要。
- 全局通知状态。
- 用户界面偏好。
- 会话过期和实时连接摘要。

规则：

- DeploymentEnvironment、TradingMode 和 TradingPermissionState 使用独立字段。
- 全局 Store 数量保持克制。
- 页面筛选、图表开关和普通分页不进入全局 Store。
- 全局状态具有初始化、清理、过期和持久化规则。
- 权限和安全状态不能只依赖浏览器持久化值。

### 2.5 服务端数据状态

服务端数据包括：

- Execution Market Data 和 Research Data。
- Account、BalanceSnapshot 和 MarginSnapshot。
- Position 和 ExposureSnapshot。
- TradeCommand、ExecutionBatch、Order、Fill、Deal 和 StrategyNavSnapshot。
- PnLResult 和策略经济账本摘要。
- RiskDecision 和 GlobalTradingBlock。
- ApprovalRequest 和 ApprovalGrant。
- DataQualityState 和 ReconciliationResult。

每类服务端数据区分：

- 数据主体。
- loading 和 refreshing。
- error。
- lastUpdated 和 dataTime。
- 数据来源和质量。
- 是否估算或部分数据。

规则：

- 服务端数据通过 Repository／Adapter 获取。
- 不把 Mock 数据本身复制进全局 Store。
- 实时事件更新后仍可通过 Query 恢复权威状态。
- 页面卸载不代表服务端业务状态被清除。

## 3. 界面状态、请求状态和业务状态分离

同一页面中区分：

- 业务数据：Order、Fill、Deal、Position、PnL、StrategyNavSnapshot、Account、Risk、Approval。
- 请求状态：加载、刷新、错误和更新时间。
- 界面状态：页签、筛选、折叠和选中项。
- 命令受理状态：received、validating、accepted、rejected、result_unknown。
- 执行状态：ExecutionBatchStatus。
- 订单状态：OrderStatus。
- 配平和暴露：ExecutionBalanceStatus、ExposureStatus。

不得使用一个大型 reactive 对象同时承载全部状态。

## 4. 模块规则

### 4.1 交易平台

- `strategy` 和 `view`：路由状态。
- 交易所、标的和时间粒度：页面或模块状态；需要分享时再进入 query。
- 未提交参数：页面本地状态。
- 当前 ExecutionBatch 引用：模块共享状态；权威状态来自服务端。
- Order、Fill、Deal、StrategyNavSnapshot、配平、暴露和风险：服务端数据状态。
- DeploymentEnvironment、TradingMode 和 TradingPermissionState：全局受信任上下文。

切换策略时：

- 返回目标策略行情分析。
- 清理不兼容执行参数。
- 保留兼容公共分析条件。

### 4.2 策略管理

- `strategy` 和 `view`：路由状态。
- 切换策略时保留当前管理视角。
- 日期、订单状态和分页：页面本地状态；需要链接复现时可以进入 query。
- 策略基础信息：从注册表或后端 StrategyDefinition 读取。
- PnL、StrategyNavSnapshot、Account、Order、Fill、Deal 和 Reconciliation：服务端数据状态。

### 4.3 对冲基金看板

- `category`：路由状态。
- 图表时间区间和显示项：页面本地状态。
- Research Data 和行情：服务端数据状态。
- 收藏工具：用户偏好状态。

### 4.4 风险管理

- 当前子板块：路由状态。
- 风险规则编辑草稿：页面本地状态。
- RiskStatus、GlobalTradingBlock、Approval 和服务健康：服务端数据；必要摘要进入全局状态。
- User、Account、Audit 和 Notification 不应塞入一个 Risk Store。

## 5. 持久化规则

允许持久化：

- 用户界面偏好。
- 最近使用且不敏感的筛选。
- 合法可验证的最近页面上下文。

不得只依赖前端持久化：

- 权限和数据范围。
- DeploymentEnvironment、TradingMode 和 TradingPermissionState。
- TradeCommand、ExecutionBatch、Order、Fill、Deal 和 StrategyNavSnapshot 状态。
- Account 余额和 Position。
- Risk 阻断和 ApprovalGrant。

所有持久化值具有版本和非法值回退策略。

## 6. 状态失效和清理

以下变化需要清理或重新获取相关状态：

- 用户退出或会话过期。
- 权限或数据范围变化。
- DeploymentEnvironment 变化。
- TradingMode 变化。
- StrategyAccountBinding 变化。
- Gateway 或交易服务恢复。
- 从断线状态恢复实时连接。

清理页面缓存不能代替后端撤单、终止或风险处置。

## 7. 禁止事项

- 不因多个组件使用就立即放入 Pinia。
- 不在路由和本地状态中保存同一个主字段。
- 不把 Mock 数据本身存入全局 Store。
- 不使用全局事件总线代替清晰数据流。
- 不把后端 DTO 原样作为长期领域状态。
- 不把按钮禁用视为最终权限控制。
- 不把 WebSocket 最后一条事件视为不可恢复的唯一事实。
- 不使用一个 `environment` 字段混合部署环境和交易模式。

## 8. 唯一来源

- 路由、权限和运行上下文：`frontend/routing-permission-and-environment.md`。
- 状态枚举：`domain/status-enums-and-lifecycles.md`。
- 数据适配：`frontend/data-adapter-and-view-model.md`。
- 实时恢复：`integration/realtime-events-and-recovery.md`。

## 9. 验收标准

- 刷新和浏览器导航可以恢复主要视图。
- 临时交互状态在页面离开后正确清理。
- 全局 Store 中不存在普通分页和图表开关。
- DeploymentEnvironment、TradingMode 和 TradingPermissionState 独立管理。
- 同一前端主状态只有一个权威来源。
- 服务端业务事实可以通过 Query 恢复。
- 命令、执行批次、订单、配平和暴露状态分别表达。
