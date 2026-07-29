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

      <nav class="research-subnav" aria-label="A股研究模块导航">
        <button
          v-for="(item, index) in sectionNav"
          :key="item.id"
          type="button"
          @click="jumpTo(item.id)"
        >
          <span>{{ String(index + 1).padStart(2, '0') }}</span
          ><strong>{{ item.label }}</strong>
        </button>
      </nav>

      <div v-if="dashboardError" class="dashboard-error">{{ dashboardError }}</div>

      <section id="a-share-overview" class="overview-card">
        <header class="section-header">
          <div><p>MARKET OVERVIEW</p><h2>大盘表现</h2></div>
          <ResearchSourceState v-if="dashboard?.marketDetail" :meta="dashboard.marketDetail.meta" />
        </header>
        <div class="overview-grid">
          <article v-for="row in overviewRows" :key="row.code">
            <div class="overview-card__head"
              ><span>{{ row.code }}</span
              ><b :class="toneClass(row.return1dPct)">{{ formatPct(row.return1dPct) }}</b></div
            >
            <strong>{{ row.name }}</strong>
            <em>{{ formatNumber(row.close) }}</em>
            <svg viewBox="0 0 100 28" preserveAspectRatio="none">
              <polyline :points="sparkPoints(row.spark)" :class="toneClass(row.return1dPct)" />
            </svg>
          </article>
        </div>
      </section>

      <AShareBreadthSection :module="dashboard?.breadth" />
      <AShareMarketDetailSection :module="dashboard?.marketDetail" />
      <ShenwanIndustrySection
        v-model:threshold-mode="thresholdMode"
        v-model:custom-threshold-yi="customThresholdYi"
        :module="dashboard?.shenwan"
        @apply-threshold="applyThresholdMode"
        @copy="copyThresholdSummary"
        @export="exportThresholdCsv"
      />
      <ShortTermEmotionSection :module="dashboard?.emotion" />
      <AShareWatchlistSection
        :groups="watchlistGroups"
        @add="addToWatchlist"
        @remove="removeFromWatchlist"
        @move="moveWatchlistItem"
        @set-group="setWatchlistGroup"
        @query="queryStockAndJump"
      />
      <StockSnapshotSection
        v-model:code="stockCode"
        :snapshot="stockSnapshot"
        :loading="stockLoading"
        :error="stockError"
        @query="queryStock"
        @add-watchlist="addToWatchlist"
      />
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { computed, nextTick } from 'vue';
  import { useRouter } from 'vue-router';
  import { PageWrapper } from '@/components/Page';
  import CompactSegmentTabs from '@/views/strategy/shared/CompactSegmentTabs.vue';
  import ResearchSourceState from '../research/components/ResearchSourceState.vue';
  import AShareBreadthSection from './components/AShareBreadthSection.vue';
  import AShareMarketDetailSection from './components/AShareMarketDetailSection.vue';
  import AShareWatchlistSection from './components/AShareWatchlistSection.vue';
  import ShenwanIndustrySection from './components/ShenwanIndustrySection.vue';
  import ShortTermEmotionSection from './components/ShortTermEmotionSection.vue';
  import StockSnapshotSection from './components/StockSnapshotSection.vue';
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
  const sectionNav = [
    { id: 'a-share-overview', label: '大盘表现' },
    { id: 'a-share-breadth', label: '大盘广度' },
    { id: 'a-share-market-detail', label: '市场明细' },
    { id: 'a-share-shenwan', label: '申万板块' },
    { id: 'a-share-emotion', label: '短线情绪' },
    { id: 'a-share-watchlist', label: '自选股' },
    { id: 'a-share-stock-snapshot', label: '一键个股数据' },
  ];

  const {
    dashboard,
    dashboardLoading,
    dashboardError,
    thresholdMode,
    customThresholdYi,
    stockCode,
    stockSnapshot,
    stockLoading,
    stockError,
    watchlistGroups,
    loadDashboard,
    queryStock,
    addToWatchlist,
    removeFromWatchlist,
    moveWatchlistItem,
    setWatchlistGroup,
    applyThresholdMode,
    exportThresholdCsv,
    copyThresholdSummary,
  } = useAShareResearch();

  const overviewRows = computed(() => dashboard.value?.marketDetail.data?.slice(0, 8) || []);

  function navigateMarket(value: string) {
    const path = routeByMarket[value];
    if (path) void router.push(path);
  }

  function jumpTo(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  async function queryStockAndJump(code: string) {
    await queryStock(code);
    await nextTick();
    jumpTo('a-share-stock-snapshot');
  }

  function numeric(value: string | number | null | undefined) {
    const result = Number(value);
    return Number.isFinite(result) ? result : null;
  }

  function formatNumber(value: string | number | null | undefined) {
    const result = numeric(value);
    return result == null ? '—' : result.toLocaleString('zh-CN', { maximumFractionDigits: 2 });
  }

  function formatPct(value: string | number | null | undefined) {
    const result = numeric(value);
    return result == null ? '—' : `${result > 0 ? '+' : ''}${result.toFixed(2)}%`;
  }

  function toneClass(value: string | number | null | undefined) {
    const result = numeric(value);
    return result == null ? '' : result > 0 ? 'is-positive' : result < 0 ? 'is-negative' : '';
  }

  function sparkPoints(values: Array<string | number>) {
    const series = values.map(Number).filter(Number.isFinite);
    if (!series.length) return '';
    const min = Math.min(...series);
    const range = Math.max(...series) - min || 1;
    return series
      .map(
        (value, index) =>
          `${((index / Math.max(series.length - 1, 1)) * 100).toFixed(2)},${(
            26 -
            ((value - min) / range) * 22
          ).toFixed(2)}`,
      )
      .join(' ');
  }
</script>

<style scoped lang="less">
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
    --strategy-accent-ring: rgba(67, 56, 202, 0.18);
    --strategy-up: #ef4444;
    --strategy-down: #10b981;
    --strategy-radius-card: 14px;
    --strategy-radius-control: 9px;
    --strategy-tab-height: 34px;
    --strategy-font-base: 13px;
    --strategy-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    --strategy-shadow-soft: 0 4px 16px rgba(15, 23, 42, 0.045);
    display: grid;
    gap: 14px;
    min-width: 0;
    padding-bottom: 32px;
    background: var(--strategy-bg);
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
  .research-subnav {
    position: sticky;
    top: 0;
    z-index: 5;
    display: flex;
    gap: 8px;
    overflow-x: auto;
    padding: 8px 0;
    background: var(--strategy-bg);
  }
  .research-subnav button {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    min-width: max-content;
    padding: 9px 12px;
    border: 1px solid var(--strategy-border);
    border-radius: 999px;
    background: var(--strategy-surface);
    color: #111827;
    cursor: pointer;
    box-shadow: var(--strategy-shadow-soft);
  }
  .research-subnav span,
  .research-subnav strong {
    color: #111827;
    font-size: 14px;
    font-weight: 800;
  }
  .dashboard-error {
    padding: 11px 13px;
    border-radius: 10px;
    background: rgba(239, 68, 68, 0.08);
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
    fill: none;
    stroke: #64748b;
    stroke-width: 2;
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
  @media (max-width: 1150px) {
    .overview-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
  @media (max-width: 680px) {
    .board-toolbar,
    .section-header {
      align-items: flex-start;
      flex-direction: column;
    }
    .overview-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
