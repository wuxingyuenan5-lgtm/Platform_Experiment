# Lightweight Optimization Plan

状态：`active`

目标不是重写平台，而是降低日常修改成本、运行成本和 Agent 上下文成本。

## 判断标准

优先做：

- 收敛当前可信入口。
- 拆分高频大页面的自然业务边界。
- 给已踩坑的问题加轻量守卫。
- 把 mock、fixtures、mapper、API client 从 Vue 模板中分离。
- 保持三服务本地入口稳定：Frontend `4373`、Platform Backend `8000`、Execution Runtime `8100`。

避免做：

- 为了“架构好看”引入新框架、新状态层或复杂目录迁移。
- 全项目一次性消灭 `any`、mock、历史代码。
- 批量移动或删除历史文档、截图、生成文件。
- 合并 Platform Backend 和 Execution Runtime。
- 为低频页面建立重型测试体系。

## 当前主要减负点

1. Codex 入口
   - 默认读 `AGENTS.md` 和 `docs/codex/CURRENT_CONTEXT.md`。
   - 长状态只在需要时读 `docs/codex/current-state.md`。
   - 不默认读取 changelog、archive、outputs、生成结构文件、依赖目录和虚拟环境。
   - 小 UI 微调默认不更新 md、不新增守卫、不跑全量前端检查；只有用户明确要求“更新 md / 同类型同步 / 以后按此标准”时才升级为标准类调整。
   - 浏览器验证以一次目标页只读检查为主，不为同一事实反复读取 DOM、截图和 computed style。

2. 前端大页面
   - 页面只做布局编排。
   - 子组件负责 UI。
   - composable 负责状态和 API 调用。
   - mapper 负责 API 数据到 UI row。
   - fixtures 负责 mock/seed 数据。

3. 核心模块守卫
   - 首页：`platform-web/scripts/verify-homepage-layout.cjs`
   - 跨所价差：`platform-web/scripts/verify-cross-spread-layout.cjs`
   - Codex 上下文：`scripts/check-codex-context.py`

## 后续推荐顺序

1. `strategy/spread-carry/index.vue`
   - 继续拆出页面级 layout 和 desk registry。
   - 不改交易 API 行为。
   - 已抽出 `SpreadAnalysisWorkspaceHeader.vue`，父页面不再内联顶部工作区筛选栏。
   - 已抽出 `SpreadAnalysisOverview.vue`，父页面不再内联期限结构和机会分析行数据。
   - 已抽出 `DomesticOverseasSupplement.vue`，父页面不再内联国内外价差补充表。
   - 已抽出 `SpreadStatisticsSection.vue`，父页面不再内联统计图表、KPI 和热力矩阵。

2. `strategy/funding-carry/components/FundingOrderPanel.vue`
   - 拆 order form、order summary、execution feedback。
   - 保留现有视觉风格。
   - 已抽出 `FundingStatusPanel.vue`，主组件不再内联交易规则和执行反馈。
   - 已抽出 `FundingPositionsPanel.vue`，主组件不再内联持仓汇总表和持仓种子数据。
   - 已抽出 `FundingExecutionPanel.vue`，主组件不再内联开仓/平仓表单和执行表格。
   - 已新增 `test:funding-order-layout` 结构守卫。

3. `hedgeBoard/index.vue`
   - 先建立结构守卫，再拆导航、terminal、data panel。
   - 不先动大数据文件。
   - 已新增 `test:hedge-board-layout` 结构守卫，防止回退到旧 dashboard、分散工具数据和继续扩大页面内联代码。
   - 已抽出 `HedgeBoardSubnav.vue`，父页面不再内联研究模块子导航。
   - 已抽出 `HedgeResearchModule.vue`，父页面不再内联研究模块、图表分区和 widget 卡片模板。
   - 视觉标准：研究模块子导航的序号和标题保持同色黑字，字号统一为 `14px`，不使用强调色区分数字。
   - 视觉标准：研究模块 widget 已有外层标题时，`TerminalDetailPanel.vue` 内部不再重复渲染“市场明细”标题，只保留编辑操作区。

4. `hedgeBoard/tradingTools/data/*.ts`
   - 只做索引拆分和 lazy import。
   - 不重写业务数据结构。
   - `tradingTools/data/catalog.ts` 已改成异步目录入口，按当前模块 lazy-load `marketTools.ts`。
   - `hedgeBoard/index.vue` 和 `hedgeBoard/tradingTools/index.vue` 已改为通过 lazy catalog API 获取工具组。

## 验收口径

每次减负改动至少满足：

- 轻量 UI 微调：目标组件改动可解释，必要时完成一次浏览器或定向搜索验证。
- 标准类调整：目标页面可通过现有 type check，相关结构守卫通过，正式 md 标准已更新。
- 架构或高风险调整：相关模块检查、结构守卫和上下文检查通过。
- 没有新增产品页工程解释性文案。
- 没有扩大服务边界。
- 没有批量删除文件。

## 非目标

- 不追求一次性清理全部历史模板。
- 不追求 100% 单元测试覆盖。
- 不把所有文档合并成一份。
- 不把项目迁移成新的 monorepo 结构。
