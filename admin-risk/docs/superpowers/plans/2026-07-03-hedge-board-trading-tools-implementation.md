# Hedge Board Trading Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new `交易工具` child page under `对冲基金看板` that ships a directory-style `加密工具` external-link library while keeping the code split into portable route, page, data, and card components.

**Architecture:** Add one new `hedge-board` child route that points to a dedicated `tradingTools` page instead of extending the existing large `hedgeBoard/index.vue`. Keep the feature isolated in a new folder with one typed data module and two focused presentational components, then validate the integration with TypeScript and a production build.

**Tech Stack:** Vue 3 `script setup`, Vue Router, TypeScript, existing Vben `PageWrapper`, scoped Less/CSS in Vue SFCs, pnpm, `vue-tsc`, Vite build.

---

## File Structure

- Create: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\hedgeBoard\tradingTools\index.vue`
  - Trading tools page entry and layout shell
- Create: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\hedgeBoard\tradingTools\data\cryptoTools.ts`
  - Typed crypto tool catalog grouped by research, trading, fundamentals, and media
- Create: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\hedgeBoard\tradingTools\components\ToolGroupSection.vue`
  - Group title, description, and card grid wrapper
- Create: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\hedgeBoard\tradingTools\components\ToolLinkCard.vue`
  - Reusable external-link card
- Modify: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\router\routes\modules\hedge.ts`
  - Add `trading-tools` route entry under `hedge-board`

## Task 1: Add the route entry for the new page

**Files:**
- Modify: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\router\routes\modules\hedge.ts`
- Verify: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\router\routes\index.ts`

- [ ] **Step 1: Write the route change with the final child definition**

Add a new child route object after the existing hedge board children:

```ts
    {
      path: 'trading-tools',
      name: 'HedgeTradingTools',
      component: () => import('@/views/hedgeBoard/tradingTools/index.vue'),
      meta: {
        title: '交易工具',
        icon: 'ant-design:link-outlined',
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
      },
    },
```

- [ ] **Step 2: Run TypeScript check to verify the new route initially fails if the page file does not exist**

Run: `pnpm type:check`
Expected: FAIL with a module resolution error for `@/views/hedgeBoard/tradingTools/index.vue`

- [ ] **Step 3: Do not change any other hedge board child route behavior**

Keep:

```ts
redirect: '/hedge-board/macro',
```

and leave all existing `macro / gold / crypto / us / a-share / global` route names intact.

- [ ] **Step 4: Commit the isolated route task after the page file exists later**

```bash
git add src/router/routes/modules/hedge.ts
git commit -m "feat: add hedge board trading tools route"
```

## Task 2: Create the typed crypto tool data module

**Files:**
- Create: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\hedgeBoard\tradingTools\data\cryptoTools.ts`

- [ ] **Step 1: Create the type declarations before the dataset**

Start the file with:

```ts
export interface TradingToolLink {
  id: string;
  name: string;
  url: string;
  description: string;
  domain: string;
  tags: string[];
}

export interface TradingToolGroup {
  id: 'research' | 'trading' | 'fundamental' | 'media';
  title: string;
  description: string;
  tools: TradingToolLink[];
}
```

- [ ] **Step 2: Add the grouped export with the final group metadata**

Add:

```ts
export const cryptoToolGroups: TradingToolGroup[] = [
  {
    id: 'research',
    title: '研报类',
    description: '机构研报、链上分析与分析师观点入口。',
    tools: [],
  },
  {
    id: 'trading',
    title: '交易类',
    description: '衍生品、期限结构、溢价、资金费率与热力图工具。',
    tools: [],
  },
  {
    id: 'fundamental',
    title: '基本面类',
    description: '政策、ETF、财库与政府储备跟踪。',
    tools: [],
  },
  {
    id: 'media',
    title: '媒体类',
    description: '资讯流、专题研究与行业新闻入口。',
    tools: [],
  },
];
```

- [ ] **Step 3: Fill the `research` tools with split, portable records**

Add records in this shape:

```ts
{
  id: 'glassnode-newsletter',
  name: 'Glassnode Newsletter',
  url: 'https://insights.glassnode.com/tag/newsletter/',
  description: '链上周报与结构化洞察。',
  domain: 'insights.glassnode.com',
  tags: ['链上', '周报'],
}
```

Include these research IDs:

```ts
'glassnode-newsletter'
'glassnode-market-pulse'
'galaxy-research'
'coinbase-institutional-research'
'a16z-crypto'
'vaneck-digital-assets'
'river-research'
'grayscale-research'
'binance-research'
'ark-articles'
'bitwise-market-insights'
'messari-delphi-report'
'hayes-substack'
'coinshares-insights'
'unbias-analysts'
'market-beggar-x'
```

- [ ] **Step 4: Fill the `trading` tools and split multi-link entries into separate cards**

Use one record per URL, including:

```ts
'coinglass-tv'
'coinglass-open-interest'
'coinglass-cme-cftc'
'coinglass-long-short-ratio'
'coinglass-hyperliquid'
'coinglass-liquidation-heatmap'
'checkonchain-term-structure'
'greeks-live-btc'
'deribit-options-metrics'
'coinglass-fear-greed'
'coinglass-margin-fee'
'coinglass-funding-rate'
'cryptoquant-btc-summary'
'checkonchain-home'
'glassnode-active-addresses'
'coinglass-cgdi'
'coinglass-coinbase-premium'
'coinglass-etf-premium'
'coinglass-heatmap'
'sosovalue-crypto-index'
'cryptobubbles'
'coinmarketcap'
'coinglass-halving-performance'
```

- [ ] **Step 5: Fill the `fundamental` tools with the ETF and treasury split records**

Use one record per URL, including:

```ts
'bitcoin-laws'
'sosovalue-btc-eth-etf'
'coinglass-bitcoin-treasuries'
'sosovalue-bitcoin-treasuries'
'bitcointreasuries-net'
'strategic-eth-reserve'
'coinglass-government-treasuries'
```

- [ ] **Step 6: Fill the `media` tools**

Include:

```ts
'foresight-news'
'jinse'
'sosovalue-research'
'techflow'
'panews'
'the-block'
'blockbeats'
```

- [ ] **Step 7: Export a small page-level descriptor for the page shell**

Append:

```ts
export const cryptoToolPageMeta = {
  title: '加密工具',
  eyebrow: 'Crypto Tooling',
  summary: '把研究、交易、基本面与资讯入口整理到同一页，作为对冲基金看板里的外部工具目录。',
} as const;
```

- [ ] **Step 8: Commit the data module**

```bash
git add src/views/hedgeBoard/tradingTools/data/cryptoTools.ts
git commit -m "feat: add crypto trading tools dataset"
```

## Task 3: Build the reusable external-link card component

**Files:**
- Create: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\hedgeBoard\tradingTools\components\ToolLinkCard.vue`
- Input contract: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\hedgeBoard\tradingTools\data\cryptoTools.ts`

- [ ] **Step 1: Write the card component props and script block**

Use:

```vue
<script setup lang="ts">
import type { TradingToolLink } from '../data/cryptoTools';

defineProps<{
  tool: TradingToolLink;
}>();
</script>
```

- [ ] **Step 2: Write the full clickable card template**

Use:

```vue
<template>
  <a
    class="tool-link-card"
    :href="tool.url"
    target="_blank"
    rel="noreferrer noopener"
  >
    <div class="tool-link-card__head">
      <div>
        <p class="tool-link-card__domain">{{ tool.domain }}</p>
        <h4>{{ tool.name }}</h4>
      </div>
      <span class="tool-link-card__cta">Open</span>
    </div>
    <p class="tool-link-card__desc">{{ tool.description }}</p>
    <ul class="tool-link-card__tags">
      <li v-for="tag in tool.tags" :key="tag">{{ tag }}</li>
    </ul>
  </a>
</template>
```

- [ ] **Step 3: Add self-contained scoped styles that match the hedge board tone**

Implement styles for:

```less
.tool-link-card
.tool-link-card:hover
.tool-link-card__head
.tool-link-card__domain
.tool-link-card__cta
.tool-link-card__desc
.tool-link-card__tags
.tool-link-card__tags li
```

Visual requirements:

- light surface
- thin cool border
- 16px to 18px radius
- subtle shadow on hover
- no dark-theme divergence

- [ ] **Step 4: Commit the card component**

```bash
git add src/views/hedgeBoard/tradingTools/components/ToolLinkCard.vue
git commit -m "feat: add trading tool link card component"
```

## Task 4: Build the grouped section component

**Files:**
- Create: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\hedgeBoard\tradingTools\components\ToolGroupSection.vue`
- Import: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\hedgeBoard\tradingTools\components\ToolLinkCard.vue`
- Input contract: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\hedgeBoard\tradingTools\data\cryptoTools.ts`

- [ ] **Step 1: Write the props and imports**

Use:

```vue
<script setup lang="ts">
import ToolLinkCard from './ToolLinkCard.vue';
import type { TradingToolGroup } from '../data/cryptoTools';

defineProps<{
  group: TradingToolGroup;
}>();
</script>
```

- [ ] **Step 2: Write the section template with a reusable card grid**

Use:

```vue
<template>
  <section class="tool-group-section">
    <div class="tool-group-section__head">
      <div>
        <p class="tool-group-section__eyebrow">{{ group.id.toUpperCase() }}</p>
        <h3>{{ group.title }}</h3>
      </div>
      <p>{{ group.description }}</p>
    </div>

    <div class="tool-group-section__grid">
      <ToolLinkCard
        v-for="tool in group.tools"
        :key="tool.id"
        :tool="tool"
      />
    </div>
  </section>
</template>
```

- [ ] **Step 3: Add scoped layout styles for desktop and mobile**

Implement:

```less
.tool-group-section
.tool-group-section__head
.tool-group-section__eyebrow
.tool-group-section__grid
@media (max-width: 900px)
```

Grid behavior:

- desktop: `repeat(auto-fit, minmax(240px, 1fr))`
- mobile: single column or narrow two-column fallback

- [ ] **Step 4: Commit the group component**

```bash
git add src/views/hedgeBoard/tradingTools/components/ToolGroupSection.vue
git commit -m "feat: add trading tool group section component"
```

## Task 5: Build the trading tools page shell

**Files:**
- Create: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\hedgeBoard\tradingTools\index.vue`
- Import: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\hedgeBoard\tradingTools\data\cryptoTools.ts`
- Import: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\hedgeBoard\tradingTools\components\ToolGroupSection.vue`

- [ ] **Step 1: Create the page script and imports**

Use:

```vue
<script setup lang="ts">
import { computed } from 'vue';
import { PageWrapper } from '@/components/Page';
import ToolGroupSection from './components/ToolGroupSection.vue';
import { cryptoToolGroups, cryptoToolPageMeta } from './data/cryptoTools';

const pageTitle = computed(() => '对冲基金看板 / 交易工具');
</script>
```

- [ ] **Step 2: Create the page template**

Use:

```vue
<template>
  <PageWrapper :title="pageTitle">
    <div class="trading-tools-page">
      <section class="trading-tools-page__hero">
        <div>
          <p class="trading-tools-page__eyebrow">{{ cryptoToolPageMeta.eyebrow }}</p>
          <h2>{{ cryptoToolPageMeta.title }}</h2>
        </div>
        <p class="trading-tools-page__summary">{{ cryptoToolPageMeta.summary }}</p>
      </section>

      <section class="trading-tools-page__catalog">
        <ToolGroupSection
          v-for="group in cryptoToolGroups"
          :key="group.id"
          :group="group"
        />
      </section>
    </div>
  </PageWrapper>
</template>
```

- [ ] **Step 3: Add page-level styles that visually align with hedge board**

Implement:

```less
.trading-tools-page
.trading-tools-page__hero
.trading-tools-page__eyebrow
.trading-tools-page__summary
.trading-tools-page__catalog
```

Visual requirements:

- use pale white/blue surfaces
- use cool grey body text
- maintain generous spacing
- no marketing hero pattern

- [ ] **Step 4: Run TypeScript check to verify the route now resolves**

Run: `pnpm type:check`
Expected: PASS with exit code 0

- [ ] **Step 5: Commit the page shell**

```bash
git add src/views/hedgeBoard/tradingTools/index.vue
git commit -m "feat: add hedge board trading tools page"
```

## Task 6: Verify integration and production readiness

**Files:**
- Verify: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\router\routes\modules\hedge.ts`
- Verify: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\hedgeBoard\tradingTools\index.vue`
- Verify: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\hedgeBoard\tradingTools\components\ToolGroupSection.vue`
- Verify: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\hedgeBoard\tradingTools\components\ToolLinkCard.vue`
- Verify: `C:\Users\jiuxi\Desktop\codex\平台最终版\Variable-Global-main\admin-risk\src\views\hedgeBoard\tradingTools\data\cryptoTools.ts`

- [ ] **Step 1: Run TypeScript verification**

Run: `pnpm type:check`
Expected: PASS with exit code 0

- [ ] **Step 2: Run production build verification**

Run: `pnpm build`
Expected: PASS with exit code 0

- [ ] **Step 3: Manually verify the page in the browser**

Check:

```text
/hedge-board/trading-tools
```

Confirm:

- page title reads `对冲基金看板 / 交易工具`
- four crypto groups render
- cards open in new tab
- desktop grid spacing looks consistent
- narrow layout does not collapse awkwardly

- [ ] **Step 4: Commit the verified feature**

```bash
git add src/router/routes/modules/hedge.ts src/views/hedgeBoard/tradingTools
git commit -m "feat: add hedge board crypto trading tools page"
```
