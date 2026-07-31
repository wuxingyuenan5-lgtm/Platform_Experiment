# 跨所价差页组件整理方案

状态：`done`
页面：`src/views/strategy/spread-carry/components/CrossVenueExecutionReplica.vue`

## 目标结构

跨所价差页保留以下产品区域：

- 市场报价
- 价差汇总
- 价差走势图
- 交易规则
- 价差执行指令
- 价差统计分析
- 价差持仓总览
- 执行确认弹窗

不进入产品页的区域：

- 独立 lifecycle 执行区
- 独立 live observability 验收面板
- 工程说明卡片
- 解释性辅助文案

## 组件拆分顺序

第一阶段：拆纯展示组件。状态：`done`

- `CrossVenueMarketQuotes.vue`
- `CrossVenueSpreadSummary.vue`
- `CrossVenueSpreadChart.vue`
- `CrossVenueSpreadAnalysis.vue`
- `CrossVenueTradingRules.vue`

第二阶段：拆数据表和只读账户信息。状态：`done`

- `SpreadPositionOverview.vue`：`done`
- `useCrossSpreadObservability.ts`：`done`
- `useCrossSpreadPositions.ts`：`done`

第三阶段：拆执行链路。状态：`done`

- `SpreadExecutionCommand.vue`：`done`
- `SpreadExecutionConfirmModal.vue`：`done`
- `useCrossSpreadExecution.ts`：`done`
- `useCrossSpreadExitPlans.ts`：`done`

第四阶段：整理公共格式化和 mock 边界。状态：`done`

- `useCrossSpreadFormatting.ts`：`done`
- `crossSpreadFixtures.ts`：`done`
- `mapCrossSpreadPositions.ts`：`done`

## 代码边界

- API 返回值到 UI row 的映射放入 mapper 或 composable，不放在模板组件中。
- mock / seed 数据只允许出现在 fixtures 或 dev-only 区域。
- 交易提交、退出计划、只读观测分别独立 composable。
- 单个 Vue 组件目标控制在 300-500 行；超过后优先继续拆分。

## 每步验收

- `npx pnpm@9.15.9 test:cross-spread-layout`
- `npx pnpm@9.15.9 type:check`
- 不新增产品内解释性文案。
- 不重新挂载 deprecated 面板。
