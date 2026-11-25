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
      <ResearchWorkspace
        ref="workspace"
        :pages="pages"
        :active="activePage"
        label="A股研究"
        content-key="a-share-pages"
      >
        <KeepAlive :key="account" :max="3">
          <ASharePageContent
            :key="activePage"
            :page="activePage"
            :title="pageTitle"
            :dashboard="dashboard"
            :dashboard-error="dashboardError"
            :dashboard-loading="dashboardLoading"
            :refresh-key="refreshKey"
            @ready="onPageReady"
            @query="selectedCode = $event"
            @refresh="refreshAll"
          />
        </KeepAlive>
      </ResearchWorkspace>
      <StockResearchDrawer :code="selectedCode" @close="closeStock" />
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import ASharePageContent from './ASharePageContent.vue';
  import { PageWrapper } from '@/components/Page';
  import { hasPermission } from '@/access/userAccess';
  import { useUserStore } from '@/store/modules/user';
  import { refreshAShareResearch } from '@/api/hedgeResearch';
  import ResearchWorkspace from '../components/ResearchWorkspace.vue';
  import CompactSegmentTabs from '@/views/strategy/shared/CompactSegmentTabs.vue';
  import StockResearchDrawer from './components/StockResearchDrawer.vue';
  import { useAShareResearch } from './useAShareResearch';
  import { provideDomesticFinancing } from './components/useDomesticFinancing';

  const domesticFinancing = provideDomesticFinancing();

  const router = useRouter();
  const route = useRoute();
  const pages = [
    { key: 'overview', label: '市场总览', short: '总览' },
    { key: 'themes', label: '主题研究', short: '主题' },
    { key: 'capital', label: '资金面', short: '资金' },
    { key: 'derivatives', label: '衍生品', short: '衍生品' },
    { key: 'timing-radar', label: '择时雷达', short: '择时' },
    { key: 'stocks', label: '股票池', short: '股票' },
    { key: 'hk', label: '港股观察', short: '港股' },
  ];
  watch(
    () => [route.query.view, route.query.section],
    ([view, section]) => {
      if (view === 'capital' && section === 'derivatives')
        void router.replace({ query: { ...route.query, view: 'derivatives', section: undefined } });
      else if (view === 'capital' && section === 'liquidity')
        void router.replace({
          path: '/hedge-board/macro',
          query: { view: 'macro-details', section: 'macro-liquidity', subsection: 'cn' },
        });
      else if (view === 'valuation' || view === 'crowding')
        void router.replace({ query: { ...route.query, view: 'themes', section: view } });
      else if (view === 'etf')
        void router.replace({ query: { ...route.query, view: 'capital', section: 'etf' } });
      else if (view === 'financing')
        void router.replace({ query: { ...route.query, view: 'capital', section: 'margin' } });
      else if (view === 'funds')
        void router.replace({ query: { ...route.query, view: 'capital', section: 'funds' } });
    },
    { immediate: true },
  );
  const activePage = computed(() =>
    ['etf', 'financing', 'funds'].includes(String(route.query.view))
      ? 'capital'
      : ['valuation', 'crowding'].includes(String(route.query.view))
      ? 'themes'
      : pages.find((p) => p.key === route.query.view)?.key || 'overview',
  );
  const needsDashboard = computed(() => activePage.value === 'overview');
  const pageTitle = computed(() => pages.find((p) => p.key === activePage.value)!.label);
  const workspace = ref<InstanceType<typeof ResearchWorkspace>>();
  const readTimes = new Map<string, number>();
  const pageLoading = ref(true);
  function onPageReady(page: string, readAt: number) {
    if (page === activePage.value) {
      readTimes.set(page, readAt);
      pageLoading.value = false;
      workspace.value?.restoreScroll(page);
    }
  }
  watch(
    activePage,
    (page) => {
      pageLoading.value = true;
      selectedCode.value = '';
      if (readTimes.has(page) && Date.now() - readTimes.get(page)! >= 60_000) refreshKey.value++;
    },
    { flush: 'sync' },
  );
  const user = useUserStore();
  const account = computed(() => String(user.getUserInfo.userId || 'anonymous'));
  watch(account, () => {
    domesticFinancing.reset();
    readTimes.clear();
  });
  const canProduce = computed(() =>
    hasPermission(user.getAuthentication?.permissions || [], 'research.write'),
  );
  const refreshKey = ref(0);
  const selectedCode = ref('');
  watch(
    () => [activePage.value, route.query.stock],
    ([page, code]) => {
      if (page === 'stocks' && typeof code === 'string' && /^\d{5,6}$/.test(code))
        selectedCode.value = code;
      else selectedCode.value = '';
    },
    { immediate: true },
  );
  function closeStock() {
    selectedCode.value = '';
    if (route.query.stock) void router.replace({ query: { ...route.query, stock: undefined } });
  }
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
      if (activePage.value === 'overview' && !dashboardLoading.value) {
        pageLoading.value = false;
        workspace.value?.restoreScroll(activePage.value);
      }
    },
    { flush: 'post' },
  );
  async function refreshAll() {
    pageLoading.value = true;
    refreshKey.value += 1;
    workspace.value?.clearSnapshots();
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
  @import '../hedgeBoardTheme.less';

  // The legacy desktop shell has a 1280px minimum; this page owns a responsive layout.
  #app:has(.a-share-board) {
    min-width: 0;
  }
</style>

<style scoped lang="less" src="./aSharePage.less"></style>
