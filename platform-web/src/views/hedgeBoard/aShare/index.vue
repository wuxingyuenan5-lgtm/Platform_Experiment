<template>
  <PageWrapper title="对冲基金看板">
    <div class="a-share-board">
      <section class="board-toolbar">
        <CompactSegmentTabs
          :items="marketTabs"
          model-value="aShare"
          @update:modelValue="navigateMarket"
        />
        <button
          type="button"
          class="refresh-button"
          :disabled="dashboardLoading"
          @click="loadDashboard(true)"
        >
          {{ dashboardLoading ? '刷新中…' : '刷新数据' }}
        </button>
      </section>

      <AShareLegacyTerminalSection :dashboard="dashboard" />

      <AShareMarketOverviewSection :dashboard="dashboard" />

      <div v-if="dashboardError" class="dashboard-error">{{ dashboardError }}</div>

      <VibeStockPoolSection />
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { useRouter } from 'vue-router';
  import { PageWrapper } from '@/components/Page';
  import CompactSegmentTabs from '@/views/strategy/shared/CompactSegmentTabs.vue';
  import AShareLegacyTerminalSection from './components/AShareLegacyTerminalSection.vue';
  import AShareMarketOverviewSection from './components/AShareMarketOverviewParitySection.vue';
  import VibeStockPoolSection from './components/VibeStockPoolSection.vue';
  import { useAShareResearch } from './useAShareResearch';

  const router = useRouter();
  const marketTabs = [
    { key: 'macro', label: '宏观' },
    { key: 'gold', label: '商品' },
    { key: 'crypto', label: '加密' },
    { key: 'us', label: '美股' },
    { key: 'aShare', label: 'A股' },
    { key: 'global', label: '全球' },
    { key: 'tradingTools', label: '交易工具' },
  ];
  const routeByMarket: Record<string, string> = {
    macro: '/hedge-board/macro',
    gold: '/hedge-board/gold',
    crypto: '/hedge-board/crypto',
    us: '/hedge-board/us',
    aShare: '/hedge-board/a-share',
    global: '/hedge-board/global',
    tradingTools: '/hedge-board/trading-tools/macro',
  };
  const { dashboard, dashboardLoading, dashboardError, loadDashboard } = useAShareResearch();

  function navigateMarket(value: string) {
    const path = routeByMarket[value];
    if (path) void router.push(path);
  }
</script>

<style scoped lang="less">
  @media (max-width: 1150px) {
    .overview-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 680px) {
    .board-toolbar,
    .section-header {
      flex-direction: column;
      align-items: flex-start;
    }

    .overview-grid {
      grid-template-columns: 1fr;
    }
  }

  .a-share-board {
    --strategy-bg: #eef3f8;
    --strategy-surface: #ffffff;
    --strategy-surface-2: #f7f9fc;
    --strategy-border: #d9e3ee;
    --strategy-text-1: #10233d;
    --strategy-text-2: #354d68;
    --strategy-text-3: #60758f;
    --strategy-text-4: #8a9ab0;
    --strategy-accent: #1d4ed8;
    --strategy-accent-soft: #eaf2ff;
    --strategy-accent-strong: #1d4ed8;
    --strategy-accent-ring: rgb(29 78 216 / 16%);
    --strategy-up: #df4b47;
    --strategy-down: #0e9f78;
    --strategy-radius-card: 16px;
    --strategy-radius-control: 8px;
    --strategy-tab-height: 36px;
    --strategy-font-base: 13px;
    --strategy-shadow: 0 16px 34px rgb(26 54 93 / 8%);
    --strategy-shadow-soft: 0 6px 18px rgb(26 54 93 / 5%);

    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 18px;
    min-width: 0;
    max-width: 100%;
    padding-bottom: 32px;
    background: linear-gradient(180deg, rgb(255 255 255 / 72%), transparent 340px),
      var(--strategy-bg);
    color: var(--strategy-text-2);
    font-family: Inter, 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
    font-variant-numeric: tabular-nums;
  }

  .a-share-board > * {
    min-width: 0;
    max-width: 100%;
  }

  // PageWrapper clips horizontal overflow.  Keep the shared terminal within
  // its available viewport; individual data tables manage their own scroll.
  .a-share-board :deep(.market-terminal) {
    width: min(100%, calc(100vw - 32px));
    min-width: 0;
    max-width: 100%;
    overflow: hidden;
  }

  .a-share-board :deep(.market-terminal__overview-strip) {
    grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr);
  }

  .board-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    min-height: 42px;
    padding: 4px 4px 4px 8px;
    border: 1px solid rgb(217 227 238 / 88%);
    border-radius: 12px;
    background: rgb(255 255 255 / 82%);
    box-shadow: 0 3px 12px rgb(26 54 93 / 3%);
  }

  .refresh-button {
    min-height: 36px;
    padding: 0 16px;
    border: 1px solid #1d4ed8;
    border-radius: var(--strategy-radius-control);
    background: #1d4ed8;
    color: #fff;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.02em;
    cursor: pointer;
    transition: background 160ms ease, box-shadow 160ms ease, transform 160ms ease;
  }

  .refresh-button:hover:not(:disabled) {
    background: #1741b4;
    box-shadow: 0 7px 15px rgb(29 78 216 / 18%);
    transform: translateY(-1px);
  }

  .refresh-button:disabled {
    opacity: 0.65;
    cursor: wait;
  }

  .dashboard-error {
    padding: 11px 13px;
    border-radius: 10px;
    background: rgb(239 68 68 / 8%);
    color: #dc2626;
  }

  .overview-card {
    padding: 20px;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-card);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-soft);
  }

  .section-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 15px;
  }

  .section-header p {
    margin: 0 0 3px;
    color: var(--strategy-text-4);
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.12em;
  }

  .section-header h2 {
    margin: 0;
    color: var(--strategy-text-1);
    font-size: 19px;
    letter-spacing: -0.02em;
  }

  .overview-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 11px;
  }

  .overview-grid article {
    min-width: 0;
    padding: 13px;
    border: 1px solid var(--strategy-border);
    border-radius: 11px;
    background: var(--strategy-surface-2);
    transition: border-color 160ms ease, background 160ms ease;
  }

  .overview-grid article:hover {
    border-color: #b9ceea;
    background: #fff;
  }

  .overview-card__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .overview-card__head span {
    color: var(--strategy-text-4);
    font-size: 12px;
  }

  .overview-grid article > strong {
    display: block;
    margin-top: 8px;
    color: var(--strategy-text-1);
  }

  .overview-grid article > em {
    display: block;
    margin-top: 3px;
    color: var(--strategy-text-2);
    font-size: 18px;
    font-style: normal;
    font-variant-numeric: tabular-nums;
  }

  .overview-grid svg {
    width: 100%;
    height: 28px;
    margin-top: 8px;
  }

  .overview-grid polyline {
    stroke-width: 2;
    stroke: #64748b;
    fill: none;
    vector-effect: non-scaling-stroke;
  }

  .overview-grid polyline.is-positive {
    stroke: var(--strategy-up);
  }

  .overview-grid polyline.is-negative {
    stroke: var(--strategy-down);
  }

  .is-positive {
    color: var(--strategy-up) !important;
  }

  .is-negative {
    color: var(--strategy-down) !important;
  }

  // The following cross-component rules establish one dense "trading sheet"
  // treatment for live data, rather than letting every module look unrelated.
  .a-share-board :deep(.market-terminal__overview-panel),
  .a-share-board :deep(.market-terminal__side-panel),
  .a-share-board :deep(.overview-card),
  .a-share-board :deep(.pool-card) {
    border-color: #d7e2ee;
    box-shadow: var(--strategy-shadow-soft);
  }

  .a-share-board :deep(.market-terminal__overview-panel),
  .a-share-board :deep(.overview-card),
  .a-share-board :deep(.pool-card) {
    border-top: 3px solid #1d4ed8;
  }

  .a-share-board :deep(.market-terminal__panel-head),
  .a-share-board :deep(.overview-header),
  .a-share-board :deep(.pool-head) {
    padding-bottom: 11px;
    border-bottom: 1px solid #e5ebf3;
  }

  .a-share-board :deep(.market-terminal__panel-head h3),
  .a-share-board :deep(.overview-header h2),
  .a-share-board :deep(.pool-head h2) {
    color: #10233d;
    font-size: 20px;
    font-weight: 760;
    letter-spacing: -0.025em;
  }

  .a-share-board :deep(.eyebrow),
  .a-share-board :deep(.stock-filter-copy > span),
  .a-share-board :deep(.matrix-kicker) {
    color: #1d4ed8;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.14em;
  }

  .a-share-board :deep(.market-terminal__market-card),
  .a-share-board :deep(.metric-cell),
  .a-share-board :deep(.pool-kpi),
  .a-share-board :deep(.breadth-card),
  .a-share-board :deep(.sub-panel) {
    border-color: #dce5ef;
    background: #f9fbfd;
  }

  .a-share-board :deep(.market-terminal__market-card:hover),
  .a-share-board :deep(.metric-cell:hover),
  .a-share-board :deep(.pool-kpi:hover) {
    border-color: #b7cdea;
    background: #fff;
  }

  .a-share-board :deep(.panel h3),
  .a-share-board :deep(.sub-panel h3),
  .a-share-board :deep(.stock-filter-copy h3) {
    color: #173353;
    font-weight: 750;
    letter-spacing: -0.015em;
  }

  .a-share-board :deep(.metric-cell strong),
  .a-share-board :deep(.pool-kpi strong),
  .a-share-board :deep(.market-terminal__market-head strong) {
    font-weight: 780;
    letter-spacing: -0.025em;
  }

  .a-share-board :deep(.table-shell),
  .a-share-board :deep(.market-terminal__rotation-heatmap) {
    border-color: #d6e1ed;
    border-radius: 10px;
    background: #fff;
  }

  .a-share-board :deep(table thead th) {
    background: #f1f5fa;
    color: #526982;
    font-size: 11px;
    font-weight: 750;
  }

  .a-share-board :deep(table tbody tr:hover td) {
    background: #f3f7fd;
  }

  .a-share-board :deep(input),
  .a-share-board :deep(select) {
    border-color: #ccd9e7;
    border-radius: 7px;
    background: #fff;
    color: #263f5e;
  }

  .a-share-board :deep(button.toolbar),
  .a-share-board :deep(button.meta-action),
  .a-share-board :deep(.hot-history-dates button) {
    border-color: #cad8e8;
    background: #fff;
    color: #294663;
    font-weight: 650;
  }

  .a-share-board :deep(button.toolbar:hover:not(:disabled)),
  .a-share-board :deep(button.meta-action:hover:not(:disabled)) {
    border-color: #82a9db;
    background: #edf5ff;
    color: #1649a5;
  }

  @media (prefers-reduced-motion: reduce) {
    .refresh-button,
    .overview-grid article {
      transition: none;
    }
  }
</style>
