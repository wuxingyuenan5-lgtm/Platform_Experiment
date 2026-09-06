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
          @click="loadDashboard"
        >
          {{ dashboardLoading ? '刷新中…' : '刷新数据' }}
        </button>
      </section>

      <AShareLegacyTerminalSection />

      <AShareMarketOverviewSection :dashboard="dashboard" />

      <div v-if="dashboardError" class="dashboard-error">{{ dashboardError }}</div>

      <VibeStockPoolSection />
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { onActivated, onMounted } from 'vue';
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

  function resetPageScroll() {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
  }

  onMounted(resetPageScroll);
  onActivated(resetPageScroll);

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
    --strategy-bg: #f4f6f8;
    --strategy-surface: #fff;
    --strategy-surface-2: #f8fafc;
    --strategy-border: #e2e8f0;
    --strategy-text-1: #111827;
    --strategy-text-2: #334155;
    --strategy-text-3: #64748b;
    --strategy-text-4: #94a3b8;
    --strategy-accent-soft: #eef2ff;
    --strategy-accent-strong: #4338ca;
    --strategy-accent-ring: rgb(67 56 202 / 18%);
    --strategy-up: #ef4444;
    --strategy-down: #10b981;
    --strategy-radius-card: 14px;
    --strategy-radius-control: 9px;
    --strategy-tab-height: 34px;
    --strategy-font-base: 13px;
    --strategy-shadow: 0 8px 24px rgb(15 23 42 / 6%);
    --strategy-shadow-soft: 0 4px 16px rgb(15 23 42 / 4.5%);

    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 14px;
    min-width: 0;
    max-width: 100%;
    padding-bottom: 32px;
    background: var(--strategy-bg);
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
  }

  .refresh-button {
    min-height: 36px;
    padding: 0 13px;
    border: 1px solid var(--strategy-border);
    border-radius: 9px;
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
    cursor: pointer;
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
    padding: 18px;
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
    font-size: 18px;
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
</style>
