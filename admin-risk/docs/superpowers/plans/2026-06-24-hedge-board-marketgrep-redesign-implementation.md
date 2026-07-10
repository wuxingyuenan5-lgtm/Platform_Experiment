# Hedge Board MarketGrep Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand `对冲基金看板` into six routed subpages and land a new MarketGrep-style terminal UI for `美股 / A股 / 全球` while preserving the current `宏观 / 黄金 / 加密` research pages.

**Architecture:** Keep `src/views/hedgeBoard/index.vue` as the route entry and conditional page shell. Add one new config-driven terminal component plus one typed mock-data module, then extend router metadata and top navigation so both legacy research modules and new terminal pages live under the same hedge board.

**Tech Stack:** Vue 3, TypeScript, Vue Router, Vben `PageWrapper`, scoped Less

---

### Task 1: Write the redesign spec and execution notes

**Files:**
- Create: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\docs\superpowers\specs\2026-06-24-hedge-board-marketgrep-redesign-design.md`
- Create: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\docs\superpowers\plans\2026-06-24-hedge-board-marketgrep-redesign-implementation.md`

- [ ] Save the confirmed redesign scope, component boundaries, and verification rules.
- [ ] Save this implementation plan before editing production files.

### Task 2: Extend hedge board routing to six market entries

**Files:**
- Modify: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\router\routes\modules\hedge.ts`

- [ ] Add `us`, `a-share`, and `global` children pointing to `@/views/hedgeBoard/index.vue`.
- [ ] Set `hedgeCategory` meta values to `us`, `aShare`, and `global`.
- [ ] Keep existing `macro`, `gold`, and `crypto` children unchanged.

### Task 3: Create typed MarketTerminal mock data

**Files:**
- Create: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\hedgeBoard\nativeData\marketTerminal.ts`

- [ ] Define terminal-only types for hero stats, switcher tabs, sections, cards, tables, and detail rows.
- [ ] Add static configs for `us`, `global`, and `aShare`.
- [ ] Fill each config with front-end-only mock values and sparkline arrays.

### Task 4: Build the new MarketTerminal page component

**Files:**
- Create: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\hedgeBoard\components\MarketTerminalPage.vue`

- [ ] Render the hero header, status chips, summary cards, and section switcher.
- [ ] Render mixed content blocks: metric cards, mover cards, ranking lists, and tables.
- [ ] Add a detail modal that opens from clickable rows/cards and shows mock sparkline + detail fields.
- [ ] Keep styling aligned to the platform’s light research-terminal palette instead of the source site’s dark palette.

### Task 5: Refactor hedge board entry page into a page shell

**Files:**
- Modify: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\hedgeBoard\index.vue`

- [ ] Extend `HedgeCategory` to include `us`, `aShare`, and `global`.
- [ ] Add unified top navigation data for all six subpages.
- [ ] Import `MarketTerminalPage` and `marketTerminalConfigs`.
- [ ] Render `MarketTerminalPage` for `us / aShare / global`.
- [ ] Preserve the existing legacy research-module rendering path for `macro / gold / crypto`.

### Task 6: Adjust legacy hedge board copy to match the new six-page shell

**Files:**
- Modify: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\hedgeBoard\nativeData\dashboardClean.ts`
- Modify: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\hedgeBoard\index.vue`

- [ ] Expand any in-page copy that still says the hedge board has only three modules.
- [ ] Ensure the top banner, nav cards, and labels describe the new six-market structure.

### Task 7: Run verification

**Files:**
- Verify only

- [ ] Run `pnpm vue-tsc --noEmit --skipLibCheck` in `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk`
- [ ] Run `pnpm vite build` in `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk`
- [ ] Fix any type, template, import, or style regressions until both commands pass.
