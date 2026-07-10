# Funding Carry Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `admin-risk` 的 `strategy` 菜单下新增一个模块化的“资金费率套利”研究页面，并以 mock 数据完成首版展示。

**Architecture:** 采用 `route + page shell + typed mock data + leaf components` 的结构。页面总装配只管理状态与数据分发，具体展示拆到独立组件，确保后续可以单独替换摘要卡、币种列表、结构图区和单币深度模块。

**Tech Stack:** Vue 3、TypeScript、Ant Design Vue、Vben PageWrapper、scoped less

---

### Task 1: 接入路由入口

**Files:**
- Modify: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\router\routes\modules\strategy.ts`

- [ ] 新增 `资金费率套利` 子路由，保持现有 `strategy` 结构不变
- [ ] 路由组件指向 `@/views/strategy/funding-carry/index.vue`

### Task 2: 建立类型与 mock 数据层

**Files:**
- Create: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\strategy\funding-carry\types.ts`
- Create: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\strategy\funding-carry\mock\data.ts`

- [ ] 定义交易所、币种、视角、摘要卡、拆解表、研究卡片的类型
- [ ] 写入 3 个交易所 × 6 个币种的标准化 mock 数据
- [ ] 提供默认交易所与默认币种常量

### Task 3: 建立叶子组件

**Files:**
- Create: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\strategy\funding-carry\components\FundingDeskTabs.vue`
- Create: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\strategy\funding-carry\components\FundingSymbolList.vue`
- Create: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\strategy\funding-carry\components\FundingSummaryCards.vue`
- Create: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\strategy\funding-carry\components\FundingStructureHero.vue`
- Create: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\strategy\funding-carry\components\FundingDetailPanel.vue`

- [ ] 组件保持单一职责
- [ ] 组件通过 props / emits 通信
- [ ] 组件内部不直接依赖全局 mock 数据

### Task 4: 组装页面主文件

**Files:**
- Create: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\strategy\funding-carry\index.vue`

- [ ] 用 `PageWrapper` 承载页面
- [ ] 管理当前交易所、币种、研究视角状态
- [ ] 按页面骨架组装 5 个子模块
- [ ] 保持风格与平台首页一致，不混入旧版深色终端视觉

### Task 5: 验证

**Files:**
- Verify only

- [ ] 运行 `pnpm vue-tsc --noEmit --skipLibCheck`
- [ ] 如果通过，再运行 `pnpm vite build` 或至少执行 `pnpm vite build --mode test` 中的等价检查
- [ ] 根据报错修正 import、类型、模板绑定与样式问题
