# 遗留代码与前端技术债务清单

状态：`active`  
适用基线：Platform V5

## 1. 目的

记录 V5 当前已识别的遗留代码、职责混合、大型页面、重复入口和生成文件规则，为后续本地重构提供顺序和安全边界。

本阶段只盘点，不删除、不迁移阶段 7－10 的具体策略页面。

## 2. 处理标签

- `keep`：继续保留。
- `refactor-later`：后续局部重构。
- `replace-first`：必须先完成替代实现。
- `generated`：生成文件，不人工维护。
- `freeze`：当前阶段冻结，不主动调整。
- `delete-after-verification`：确认无引用和无唯一信息后删除。

## 3. 高优先级技术债务

### 3.1 `src/views/risk/detail/index.vue`

标签：`refactor-later`

当前问题：

- 同时展示风险、账户、报表、通知、审计和系统监控。
- 同一页面承担多个模块的数据请求和聚合。
- 使用 `LegacyStrategyCoverage` 作为账户管理区域。
- 风险状态存在中英文混用。

后续处理：

- 保留路由不变。
- 风控页逐步只保留风险事件和必要摘要。
- 账户、报表、审计、监控和通知改为摘要或跳转。
- 不在本轮直接重写页面。

### 3.2 `src/views/hedgeBoard/index.vue`

标签：`refactor-later`

当前问题：

- 单文件同时承担路由状态、页面编排、图表渲染、数据、计算和拖动交互。
- 部分市场快照硬编码。
- 多类研究看板共用一个超大入口文件。

后续处理：

- 先拆图表工具和数据配置。
- 再拆看板页面编排。
- 保持现有六类看板路由和产品结构不变。
- 不在本轮执行拆分。

### 3.3 `src/views/strategy/spread-carry/index.vue`

标签：`refactor-later`

当前问题：

- 同时承载跨所价差和海内外价差的行情分析。
- 页面包含筛选、期限结构、机会分析、主图、实时价差、统计、季节性和热力图。
- 图表配置、业务数据和页面结构耦合。

后续处理：

- 按用户本地计划处理，不在本次分支迁移。
- 未来保留共享骨架，但不合并两个策略的损益和业务口径。

### 3.4 `src/views/strategy/management/index.vue`

标签：`keep` + `refactor-later`

当前状态：

- 已形成策略损益、账户资金、订单信息的稳定入口。
- 入口结构合理。

后续处理：

- 只负责策略和管理视角切换。
- 策略列表后续接入统一策略注册表。
- 具体策略页面迁移由用户本地处理。

## 4. 明确遗留组件

### 4.1 `src/views/strategy/components/LegacyStrategyCoverage.vue`

标签：`replace-first`

已知引用：

- `src/views/account/index.vue`
- `src/views/risk/detail/index.vue`

问题：

- 文件名已明确标记 Legacy。
- 同一组件同时被账户和风控页面使用，业务归属不清。
- 不能因为名称旧就直接删除。

安全处理顺序：

1. 读取组件实际内容。
2. 判断账户页面真正需要的功能。
3. 判断风控页面只需要哪些摘要。
4. 建立新的账户组件或摘要组件。
5. 替换两处引用。
6. 确认无其他引用。
7. 再删除 Legacy 文件。

### 4.2 已删除的 `StrategyDeskTabs.vue`

标签：`已完成清理`

当前统一使用 `CompactSegmentTabs`，无需恢复旧组件。

## 5. 策略共享层

### 5.1 `src/views/strategy/shared/CompactSegmentTabs.vue`

标签：`keep`

用途：

- 交易平台顶部页签。
- 策略管理顶部页签。
- 对冲基金看板顶部页签。

治理要求：

- 保持无具体策略业务含义。
- 不在单个页面复制另一套视觉相同页签。

### 5.2 `src/views/strategy/shared/strategy-theme.less`

标签：`keep`

用途：

- 策略、平台和看板的视觉变量基座。

风险：

- 选择器覆盖范围较大。
- 后续新增通用样式可能影响多个页面。

治理要求：

- 优先新增设计变量，而不是堆叠宽泛选择器。
- 修改前确认影响页面。
- 不为局部问题重写整份主题文件。

### 5.3 `src/views/strategy/shared/strategyRegistry.ts`

标签：`keep`

当前状态：

- 已建立统一策略注册表。
- 尚未接入现有页面。

治理要求：

- 当前不接入阶段 7－10 页面，避免与用户本地修改冲突。
- 后续接入前对照策略能力矩阵。

## 6. Mock 数据

### 6.1 `src/views/strategy/management/mock/*`

标签：`keep`

当前用途：

- 策略损益。
- 账户资金。
- 订单信息。

后续要求：

- 使用统一策略 ID。
- 同一基础信息不在多个文件重复硬编码。
- 保持前端演示数据属性。

### 6.2 `src/views/strategy/funding-carry/mock/data.ts`

标签：`keep` + `refactor-later`

后续由用户本地整理，需与资费套利正式策略文档保持一致。

### 6.3 看板本地数据

标签：`refactor-later`

问题：

- 部分数据在 `hedgeBoard/index.vue` 中硬编码。
- 部分数据位于 `nativeData` 和生成目录。

后续目标：

- 数据配置与图表组件分离。
- 不在本轮处理。

## 7. 生成文件和脚本

### 7.1 `src/views/hedgeBoard/tradingTools/data/marketTools.ts`

标签：`generated`

规则：

- 由 `docs/trading-tools-bookmarks-review.md` 生成。
- 不作为人工维护源。
- 不直接修改工具内容。

### 7.2 `scripts/sync-trading-tools-from-md.cjs`

标签：`keep`

用途：交易工具 Markdown 同步脚本。

### 7.3 `scripts/verify-cross-spread-layout.cjs`

标签：`keep`

用途：保护跨所价差页面已经确认的局部布局规则。

后续建议：

- 按关键页面逐步增加小范围校验。
- 不依赖一次性全仓库修复。

## 8. 路由重复与入口问题

### 8.1 用户管理入口

当前存在：

- `/user/list`
- `/risk/users`

两者指向同一用户页面。

标签：`keep-route` + `review-later`

规则：

- 一级和现有路由不变。
- 业务实现保持单一组件或单一能力。
- 不复制两套用户管理页面。

### 8.2 隐藏菜单支撑路由

包括：

- 数据。
- 账户。
- 财务。
- 报表。
- 监控。
- 审计。
- 用户管理。
- 系统设置。
- 消息通知。

标签：`freeze`

当前阶段：

- 保持路由和显隐状态。
- 只明确职责。
- 不因页面不完整而删除。

## 9. API 占位和历史后端文件

涉及但不限于：

- `src/api/account.ts`
- `src/api/diffStrategy.ts`
- `src/api/execution.ts`
- `src/api/fmonitor.ts`
- `src/api/funding.ts`
- `src/api/future.ts`
- `src/api/monitor.ts`
- `src/api/mt5.ts`
- `src/api/notifications.ts`
- `src/api/pricediff.ts`
- `src/api/quantSystem.ts`
- `src/api/strategy.ts`
- `src/api/risk/*`

标签：`freeze`

原因：

- 用户当前明确不考虑后端和数据实现。
- 部分文件可能属于旧系统接口或未来占位。
- 当前没有足够依据判断删除。

规则：

- 本阶段不清理 API 文件。
- 不让旧 API 类型反向决定新的产品架构。
- 后端设计开始前单独进行接口和使用情况盘点。

## 10. 工程清单文件

### `src/file_structure.txt`

标签：`delete-after-verification`

问题：

- 是某一时点生成的目录快照。
- 很容易随代码变化而过期。
- 不应作为当前工程结构的唯一事实来源。

处理建议：

- 确认没有脚本依赖。
- 如只用于人工查看，后续删除或改为可重复生成脚本。
- 本阶段不删除。

## 11. 当前禁止动作

- 不删除 `LegacyStrategyCoverage.vue`。
- 不大规模移动 `strategy/funding-carry`、`strategy/spread-carry` 和 `strategy/management`。
- 不清理 API 占位文件。
- 不直接编辑 `marketTools.ts`。
- 不重写 `strategy-theme.less`。
- 不改变一级架构和路由。

## 12. 后续本地处理优先级

### P0：先明确替代关系

- `LegacyStrategyCoverage.vue`。
- 风控详情中的跨模块内容。

### P1：大型页面拆分

- `hedgeBoard/index.vue`。
- `strategy/spread-carry/index.vue`。

### P2：统一策略配置

- 注册表接入。
- Mock 使用统一策略 ID。

### P3：支撑模块完善

- 账户、报表、审计、监控等页面根据真实需求逐步补齐。

### P4：后端开始前专项盘点

- API 文件。
- 类型模型。
- 旧服务地址和接口约定。

## 13. 完成标准

- 每个遗留对象都有明确标签和处理顺序。
- 用户本地修改范围与本分支文档治理不冲突。
- 不因清理工作破坏 V5 页面和路由。
- 后续删除动作都有替代实现和引用检查依据。
