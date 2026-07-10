# Platform Structure Tightening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tighten the funding and spread trading platform pages into denser two-section workspaces and move chart legend controls into the chart body.

**Architecture:** Keep the existing module boundaries, but compress page structure around a shared control bar pattern. Reuse current mock-driven components and only reshape the orchestration layer plus chart option placement.

**Tech Stack:** Vue 3, TypeScript, Vben Admin, ECharts, Less

---

### Task 1: Funding trading platform restructure

**Files:**
- Modify: `src/views/strategy/funding-carry/index.vue`
- Modify: `src/views/strategy/funding-carry/components/FundingChartPanel.vue`

- [ ] Merge “市场总览/图表研究” into “行情分析”
- [ ] Replace exchange button tabs with labeled select controls
- [ ] Default exchange to Bybit
- [ ] Keep “交易执行” as second section

### Task 2: Spread trading platform restructure

**Files:**
- Modify: `src/views/strategy/spread-carry/index.vue`

- [ ] Merge “结构总览/历史图表/机会分析” into “行情分析”
- [ ] Add a dedicated “交易执行” section for `XAUTUSDT.P - XAUUSD`
- [ ] Keep chart filters compact and aligned with the funding page

### Task 3: Strategy overview chart legend placement

**Files:**
- Modify: `src/views/strategy/management/components/StrategyOverviewBoard.vue`

- [ ] Move chart legend inside the chart body near the center-top
- [ ] Preserve series toggling behavior for 日度收益 / 净值曲线

### Task 4: Validation

**Files:**
- No code target; run verification only

- [ ] Run local SFC/TS verification for modified Vue files
- [ ] Run `npm run build`
