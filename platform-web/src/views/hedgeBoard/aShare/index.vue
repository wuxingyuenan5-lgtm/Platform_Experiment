<template>
  <PageWrapper title="对冲基金看板">
    <div class="a-share-board">
      <section class="board-toolbar strategy-top-toolbar">
        <CompactSegmentTabs
          :items="marketTabs"
          model-value="aShare"
          @update:modelValue="navigateMarket"
        />
        <div class="board-actions">
          <button
            type="button"
            class="refresh-button"
            :disabled="dashboardLoading || producing"
            @click="refreshAll"
          >
            {{ dashboardLoading ? '刷新中…' : '刷新看板' }}
          </button>
          <button
            v-if="canProduce"
            type="button"
            class="refresh-button refresh-button--primary"
            :disabled="producing"
            @click="produce"
          >
            {{ producing ? '正在更新收盘数据…' : '更新收盘数据' }}
          </button>
        </div>
      </section>
      <HedgeBoardSubnav
        :sections="[
          { id: 'a-share-index-overview', title: '大盘指数' },
          { id: 'a-share-market-overview', title: '情绪与资金' },
          { id: 'cn-equity-themes', title: '主题产业链' },
          { id: 'cn-equity-valuation', title: '估值分布' },
          { id: 'cn-equity-structure', title: '拥挤与参与' },
          { id: 'cn-equity-hk', title: '港股观察' },
          { id: 'a-share-watchlist-pool', title: '股票池' },
        ]"
        module-label="A股"
        unified
        :resolve-title="(_id, title) => title"
        @jump="scrollTo"
      />
      <div v-if="productionMessage" role="status">{{ productionMessage }}</div>
      <div v-if="dashboardError" class="dashboard-error" role="alert"
        >{{ dashboardError }}<button type="button" @click="refreshAll">重试</button></div
      >
      <div id="a-share-index-overview"><AShareLegacyTerminalSection :dashboard="dashboard" /></div>
      <AShareMarketOverviewSection
        :dashboard="dashboard"
        :refresh-key="refreshKey"
        @query="selectedCode = $event"
      />
      <VibeStockPoolSection :refresh-key="refreshKey" @query="selectedCode = $event" />
      <EquityObservatoryPanel market="cn" :refresh-key="refreshKey" />
      <StockResearchDrawer :code="selectedCode" @close="selectedCode = ''" />
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { useRouter } from 'vue-router';
  import { PageWrapper } from '@/components/Page';
  import { hasPermission } from '@/access/userAccess';
  import { useUserStore } from '@/store/modules/user';
  import { refreshAShareResearch } from '@/api/hedgeResearch';
  import HedgeBoardSubnav from '../components/HedgeBoardSubnav.vue';
  import CompactSegmentTabs from '@/views/strategy/shared/CompactSegmentTabs.vue';
  import AShareLegacyTerminalSection from './components/AShareLegacyTerminalSection.vue';
  import AShareMarketOverviewSection from './components/AShareMarketOverviewParitySection.vue';
  import VibeStockPoolSection from './components/VibeStockPoolSection.vue';
  import StockResearchDrawer from './components/StockResearchDrawer.vue';
  import EquityObservatoryPanel from '../components/EquityObservatoryPanel.vue';
  import { useAShareResearch } from './useAShareResearch';

  const router = useRouter();
  const user = useUserStore();
  const canProduce = computed(() =>
    hasPermission(user.getAuthentication?.permissions || [], 'research.write'),
  );
  const refreshKey = ref(0);
  const selectedCode = ref('');
  const producing = ref(false);
  const productionMessage = ref('');
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
  async function refreshAll() {
    refreshKey.value += 1;
    await loadDashboard();
  }
  async function produce() {
    if (producing.value || !canProduce.value) return;
    producing.value = true;
    productionMessage.value = '正在采集行情与日线，通常需要数分钟';
    try {
      const { data } = await refreshAShareResearch();
      productionMessage.value =
        data.status === 'ready'
          ? '收盘数据已更新'
          : data.status === 'busy'
          ? '已有更新任务正在进行，请稍后刷新看板'
          : '部分数据已更新，未完成的内容保留上次有效数据';
      await refreshAll();
    } catch (error) {
      productionMessage.value = error instanceof Error ? error.message : '更新失败，请稍后重试';
    } finally {
      producing.value = false;
    }
  }
  function navigateMarket(value: string) {
    const path = routeByMarket[value];
    if (path) void router.push(path);
  }
  function scrollTo(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
</script>

<style lang="less">
  // The legacy desktop shell has a 1280px minimum; this page owns a responsive layout.
  #app:has(.a-share-board) {
    min-width: 0;
  }
</style>

<style scoped lang="less">
  .a-share-board {
    --strategy-bg: #fbfcfe;
    --strategy-surface: #fff;
    --strategy-surface-2: #f7f9fc;
    --strategy-border: #d9e3ee;
    --strategy-text-1: #10233d;
    --strategy-text-2: #354d68;
    --strategy-text-3: #60758f;
    --strategy-text-4: #7b8da4;
    --strategy-accent: #1d4ed8;
    --strategy-accent-soft: #eaf2ff;
    --strategy-accent-strong: #1d4ed8;
    --strategy-accent-ring: rgb(29 78 216 / 16%);
    --strategy-up: #df4b47;
    --strategy-down: #0e9f78;
    --strategy-radius-card: 14px;
    --strategy-radius-control: 8px;
    --strategy-tab-height: 36px;
    --strategy-font-base: 13px;
    --strategy-shadow: 0 12px 28px rgb(26 54 93 / 6%);
    --strategy-shadow-soft: 0 3px 12px rgb(26 54 93 / 4%);

    display: grid;
    grid-template-columns: minmax(0, 1fr);
    min-width: 0;
    padding: 4px 0 32px;
    background: transparent;
    color: var(--strategy-text-2);
    gap: 18px;
    font-variant-numeric: tabular-nums;
  }

  .board-toolbar,
  .board-actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
  }

  .board-toolbar {
    --strategy-accent: #da5b5b;
    --strategy-accent-soft: #fbf2f2;
    --strategy-accent-strong: #c94848;
    --strategy-accent-ring: rgb(201 72 72 / 14%);
    --strategy-border: #e5ebf3;
    --strategy-radius-card: 16px;
    --strategy-radius-control: 10px;
    --strategy-tab-height: 34px;
    --strategy-font-base: 14px;
    --strategy-text-3: #485667;
    --strategy-shadow: 0 10px 24px rgb(17 34 68 / 4.5%);

    justify-content: space-between;
    padding: 10px 12px;
    border: 1px solid #e5ebf3;
    border-radius: 20px;
    background: #fff;
    box-shadow: 0 8px 24px rgb(15 23 42 / 4%);
  }

  .refresh-button {
    min-height: 36px;
    padding: 7px 14px;
    border: 1px solid var(--strategy-border);
    border-radius: 8px;
    background: white;
    color: var(--strategy-text-2);
    cursor: pointer;
  }

  .refresh-button--primary {
    border-color: var(--strategy-accent-ring);
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent);
  }

  .refresh-button:disabled {
    opacity: 0.6;
    cursor: wait;
  }

  .refresh-button:focus-visible {
    outline: 2px solid var(--strategy-accent);
    outline-offset: 3px;
  }

  .dashboard-error {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding: 12px 16px;
    border: 1px solid #f5d6b5;
    border-radius: 8px;
    background: #fff8ed;
    color: #8f5517;
  }

  .dashboard-error button {
    border: 0;
    background: transparent;
    color: inherit;
    cursor: pointer;
  }

  #a-share-index-overview,
  :deep(#a-share-market-overview),
  :deep(#a-share-watchlist-pool) {
    scroll-margin-top: 80px;
  }

  @media (max-width: 680px) {
    .board-actions {
      width: 100%;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    :deep(*) {
      scroll-behavior: auto;
    }
  }
</style>
