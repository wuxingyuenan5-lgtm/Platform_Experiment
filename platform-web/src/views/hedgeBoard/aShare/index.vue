<template>
  <PageWrapper title="对冲基金看板" content-class="a-share-page-content">
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
            :disabled="dashboardLoading || pageLoading || producing"
            @click="refreshAll"
          >
            {{ dashboardLoading || pageLoading ? '读取中…' : '刷新当前页' }}
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
      <div v-if="productionMessage" role="status">{{ productionMessage }}</div>
      <div class="research-workspace" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
        <ResearchSidebar
          :items="pages"
          :active="activePage"
          :collapsed="sidebarCollapsed"
          @toggle="sidebarCollapsed = !sidebarCollapsed"
        />
        <main
          ref="viewport"
          class="research-viewport"
          tabindex="0"
          :aria-label="pageTitle"
          @scroll.passive="saveScroll"
        >
          <div class="research-page" :key="`${account}:${activePage}`">
            <div v-if="needsDashboard && dashboardError" class="dashboard-error" role="alert">
              {{ dashboardError }}<button type="button" @click="refreshAll">重试</button>
            </div>
            <p v-if="needsDashboard && !dashboard && dashboardLoading" role="status"
              >正在读取{{ pageTitle }}…</p
            >
            <template v-if="activePage === 'overview'">
              <AShareLegacyTerminalSection :dashboard="dashboard" />
              <AShareMarketOverviewSection
                :dashboard="dashboard"
                :refresh-key="refreshKey"
                @query="selectedCode = $event"
                @ready="restoreScroll"
              />
            </template>
            <template v-else-if="activePage === 'crowding'">
              <EquityObservatoryPanel
                market="cn"
                view="crowding"
                :refresh-key="refreshKey"
                @ready="restoreScroll"
              />
              <AShareMarketOverviewSection
                mode="crowding"
                :dashboard="dashboard"
                :refresh-key="refreshKey"
                @ready="restoreScroll"
              />
            </template>
            <VibeStockPoolSection
              v-else-if="activePage === 'stocks'"
              :refresh-key="refreshKey"
              @query="selectedCode = $event"
              @ready="restoreScroll"
            />
            <EtfTrackingPanel
              v-else-if="activePage === 'etf'"
              :refresh-key="refreshKey"
              @ready="restoreScroll"
            />
            <EquityObservatoryPanel
              v-else
              market="cn"
              :view="activePage"
              :refresh-key="refreshKey"
              @ready="restoreScroll"
            />
          </div>
        </main>
      </div>
      <StockResearchDrawer :code="selectedCode" @close="selectedCode = ''" />
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { computed, ref, watch, nextTick, defineAsyncComponent } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { PageWrapper } from '@/components/Page';
  import { hasPermission } from '@/access/userAccess';
  import { useUserStore } from '@/store/modules/user';
  import { refreshAShareResearch } from '@/api/hedgeResearch';
  import ResearchSidebar from '../components/ResearchSidebar.vue';
  import { provideResearchWorkspace } from '../composables/researchWorkspace';
  import CompactSegmentTabs from '@/views/strategy/shared/CompactSegmentTabs.vue';
  import StockResearchDrawer from './components/StockResearchDrawer.vue';
  import { useAShareResearch } from './useAShareResearch';

  const AShareLegacyTerminalSection = defineAsyncComponent(
    () => import('./components/AShareLegacyTerminalSection.vue'),
  );
  const AShareMarketOverviewSection = defineAsyncComponent(
    () => import('./components/AShareMarketOverviewParitySection.vue'),
  );
  const VibeStockPoolSection = defineAsyncComponent(
    () => import('./components/VibeStockPoolSection.vue'),
  );
  const EquityObservatoryPanel = defineAsyncComponent(
    () => import('../components/EquityObservatoryPanel.vue'),
  );
  const EtfTrackingPanel = defineAsyncComponent(() => import('./components/EtfTrackingPanel.vue'));

  const router = useRouter();
  const route = useRoute();
  const sidebarCollapsed = ref(false);
  const pages = [
    { key: 'overview', label: '市场总览', short: '总览' },
    { key: 'themes', label: '主题与行业', short: '主题' },
    { key: 'valuation', label: '估值', short: '估值' },
    { key: 'crowding', label: '拥挤度', short: '拥挤' },
    { key: 'etf', label: 'ETF跟踪', short: 'ETF' },
    { key: 'stocks', label: '股票池', short: '股票' },
    { key: 'hk', label: '港股观察', short: '港股' },
  ];
  const activePage = computed(
    () => pages.find((p) => p.key === route.query.view)?.key || 'overview',
  );
  const pageTitle = computed(() => pages.find((p) => p.key === activePage.value)!.label);
  const needsDashboard = computed(() => ['overview', 'crowding'].includes(activePage.value));
  const workspace = provideResearchWorkspace(() => activePage.value);
  const viewport = ref<HTMLElement>();
  const positions = new Map<string, number>();
  const pageLoading = ref(true);
  let restoring = true;
  function saveScroll() {
    if (!restoring && viewport.value) positions.set(activePage.value, viewport.value.scrollTop);
  }
  async function restoreScroll() {
    pageLoading.value = false;
    if (!restoring) return;
    await nextTick();
    requestAnimationFrame(() => {
      if (viewport.value) viewport.value.scrollTop = positions.get(activePage.value) || 0;
      restoring = false;
    });
  }
  watch(
    activePage,
    () => {
      restoring = true;
      pageLoading.value = true;
      selectedCode.value = '';
      if (viewport.value) viewport.value.scrollTop = 0;
    },
    { flush: 'sync' },
  );
  const user = useUserStore();
  const account = computed(() => String(user.getUserInfo.userId || 'anonymous'));
  watch(account, () => {
    workspace.states.clear();
    workspace.snapshots.clear();
    positions.clear();
  });
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
  const { dashboard, dashboardLoading, dashboardError, loadDashboard, ensureDashboard } =
    useAShareResearch(needsDashboard);
  watch(activePage, () => void ensureDashboard());
  watch(
    [dashboardLoading, activePage],
    () => {
      if (activePage.value === 'overview' && !dashboardLoading.value) void restoreScroll();
    },
    { flush: 'post' },
  );
  async function refreshAll() {
    pageLoading.value = true;
    refreshKey.value += 1;
    workspace.snapshots.clear();
    if (needsDashboard.value) await loadDashboard();
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

  .research-workspace {
    display: grid;
    grid-template-columns: 150px minmax(0, 1fr);
    gap: 16px;
    min-width: 0;
  }

  .research-workspace.sidebar-collapsed {
    grid-template-columns: 76px minmax(0, 1fr);
  }

  .research-viewport {
    min-width: 0;
    height: calc(100dvh - 270px);
    min-height: 420px;
    overflow: auto;
    scrollbar-gutter: stable;
    overscroll-behavior: contain;
  }

  .research-page {
    min-width: 0;
    padding: 0 4px 24px;
  }

  .research-page > :deep(:first-child) {
    margin-top: 0;
  }

  @media (max-width: 900px) {
    .research-workspace,
    .research-workspace.sidebar-collapsed {
      grid-template-columns: minmax(0, 1fr);
      gap: 10px;
    }

    .research-viewport {
      height: calc(100dvh - 320px);
    }
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
