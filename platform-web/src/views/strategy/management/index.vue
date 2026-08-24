<template>
  <div class="strategy-management-page" data-testid="strategy-management-original-structure">
    <section class="strategy-top-toolbar">
      <div class="strategy-top-toolbar__left">
        <CompactSegmentTabs :items="deskTabs" v-model="activeDesk" />
      </div>

      <div class="strategy-top-toolbar__meta">
        <CompactSegmentTabs :items="sectionTabs" v-model="activeSection" />
      </div>
    </section>

    <template v-if="activeSection === 'pnl'">
      <StrategyPnlPanel :active-desk="activeDesk" :live-profile="activePnlProfile" />
    </template>

    <template v-else-if="activeSection === 'capital'">
      <StrategyKpiGrid :items="capitalProfile.overview" />

      <StrategyCapitalFinanceBoard
        :risk-cards="capitalProfile.riskCards"
        :structure-cards="capitalProfile.structureCards"
      />

      <StrategyCapitalRulePanel
        v-if="capitalProfile.specialRulePanel"
        :panel="capitalProfile.specialRulePanel"
      />

      <StrategyCapitalRiskOverview
        v-if="capitalProfile.riskOverview"
        :overview="capitalProfile.riskOverview"
      />

      <StrategyRuntimePanel :cards="capitalProfile.comparisonCards" />

      <StrategyCapitalNetValueBoard :curve="capitalProfile.curve" />

      <StrategyCurveGrid
        v-if="capitalProfile.metricCurves?.length"
        :curves="capitalProfile.metricCurves"
      />
    </template>

    <template v-else>
      <section class="records-only-grid">
        <StrategyRecordsPanel
          :tabs="orderProfile.tabs"
          :tables="orderProfile.tables"
          v-model:activeTab="activeRecordTab"
        />
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref, watch } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import type { StrategyManagementOverviewResult } from '@/api/platform/trading.types';
  import CompactSegmentTabs from '../shared/CompactSegmentTabs.vue';
  import { useCrossSpreadFinance } from './composables/useCrossSpreadFinance';
  import { useCrossSpreadRecords } from './composables/useCrossSpreadRecords';
  import { useStrategyAccountSnapshots } from './composables/useStrategyAccountSnapshots';
  import { useStrategyManagementOverview } from './composables/useStrategyManagementOverview';
  import StrategyKpiGrid from './components/StrategyKpiGrid.vue';
  import StrategyRuntimePanel from './components/StrategyRuntimePanel.vue';
  import StrategyCurveGrid from './components/StrategyCurveGrid.vue';
  import StrategyRecordsPanel from './components/StrategyRecordsPanel.vue';
  import StrategyCapitalFinanceBoard from './components/StrategyCapitalFinanceBoard.vue';
  import StrategyCapitalNetValueBoard from './components/StrategyCapitalNetValueBoard.vue';
  import StrategyCapitalRulePanel from './components/StrategyCapitalRulePanel.vue';
  import StrategyCapitalRiskOverview from './components/StrategyCapitalRiskOverview.vue';
  import StrategyPnlPanel from './components/StrategyPnlPanel.vue';
  import type {
    StrategyCapitalProfile,
    StrategyDeskKey,
    StrategyOrderProfile,
    StrategyPnlProfile,
  } from '@/data/sample/strategy';

  const route = useRoute();
  const router = useRouter();
  const activeDesk = ref<StrategyDeskKey>('funding');
  const activeRecordTab = ref('positions');
  const activeSection = ref<'pnl' | 'capital' | 'orders'>('pnl');

  const sectionTabs = [
    { key: 'pnl', label: '策略损益' },
    { key: 'capital', label: '账户资金' },
    { key: 'orders', label: '订单信息' },
  ];

  const {
    tabs: liveCrossSpreadTabs,
    tables: liveCrossSpreadTables,
    refresh: refreshCrossSpreadRecords,
  } = useCrossSpreadRecords();

  const {
    pnlProfile,
    refresh: refreshCrossSpreadFinance,
    liveCapitalProfile,
  } = useCrossSpreadFinance();
  const {
    byDesk: strategyOverviewByDesk,
    items: strategyOverview,
    refresh: refreshStrategyOverview,
  } = useStrategyManagementOverview();

  const {
    capitalProfiles: accountCapitalProfiles,
    isAccountStrategy,
    orderProfiles: accountOrderProfiles,
    pnlProfiles: accountPnlProfiles,
    refresh: refreshAccountSnapshots,
  } = useStrategyAccountSnapshots();

  function isDeskKey(value: unknown): value is StrategyDeskKey {
    return (
      value === 'funding' ||
      value === 'crossSpread' ||
      value === 'domesticOverseas' ||
      value === 'dip' ||
      value === 'shortLineTraderL' ||
      value === 'shortLineTraderW'
    );
  }

  function normalizeSection(value: unknown): 'pnl' | 'capital' | 'orders' {
    return value === 'capital' || value === 'orders' ? value : 'pnl';
  }

  function statusLabel(value: string | null | undefined): string {
    if (!value) return '--';
    const labels: Record<string, string> = {
      active: '运行中',
      paused: '已暂停',
      simulation: '模拟',
      read_only: '只读',
      trade_and_read: '可交易',
      unavailable: '不可用',
      partial: '部分可用',
      complete: '完整',
      unbound: '未绑定',
    };
    return labels[value] ?? value;
  }

  function overviewHeadline(overview: StrategyManagementOverviewResult | null): string {
    if (!overview) return '管理总览待加载';
    if (overview.v1Scope === 'read_only') return '只读策略：不开放交易写入';
    if (overview.executionReadiness?.blockers?.length) {
      return overview.executionReadiness.blockers.join('；');
    }
    return `实例状态：${statusLabel(overview.operatingStatus)}`;
  }

  function placeholderPnlProfile(
    overview: StrategyManagementOverviewResult | null,
    desk: StrategyDeskKey,
  ): StrategyPnlProfile {
    const title = `${overview?.strategyName || desk}损益总览`;
    const note = overviewHeadline(overview);
    const account = overview?.primaryAccountCode || '--';
    return {
      title,
      totalFund: '--',
      period: note,
      xLabels: [],
      dailyReturns: [],
      netValues: [],
      metrics: [
        {
          label: '策略状态',
          value: statusLabel(overview?.operatingStatus),
          ratio: note,
          tone: 'neutral',
        },
        {
          label: '运行模式',
          value: statusLabel(overview?.tradingMode),
          ratio: `Scope: ${overview?.v1Scope || '--'}`,
          tone: 'neutral',
        },
        {
          label: '账户能力',
          value: statusLabel(overview?.activeCapability),
          ratio: account,
          tone: 'neutral',
        },
        {
          label: '数据状态',
          value: statusLabel(overview?.dataQualityState),
          ratio: statusLabel(overview?.primaryAccountDataQualityState),
          tone: 'neutral',
        },
      ],
      attributions: [
        {
          label: '主账户',
          value: account,
          ratio: statusLabel(overview?.primaryAccountStatus),
          tone: 'neutral',
        },
        {
          label: '账户能力',
          value: statusLabel(overview?.activeCapability),
          ratio: note,
          tone: 'neutral',
        },
        {
          label: '绑定数量',
          value: String(overview?.bindingCount ?? 0),
          ratio: overview?.instanceName || '--',
          tone: 'neutral',
        },
      ],
      breakdownSeries: [{ name: '损益曲线待接入', color: '#3498db', data: [] }],
      legSnapshots: [
        {
          title: overview?.strategyName || desk,
          venue: overview?.category || '--',
          symbol: '--',
          rows: [
            { label: '策略实例', value: overview?.instanceName || '--' },
            { label: '运行状态', value: statusLabel(overview?.operatingStatus) },
            { label: '账户能力', value: statusLabel(overview?.activeCapability) },
            { label: '说明', value: note },
          ],
        },
      ],
      detailCurves: [{ title: '数据接通状态', value: note, tone: 'neutral', data: [] }],
    };
  }

  function placeholderCapitalProfile(
    overview: StrategyManagementOverviewResult | null,
    desk: StrategyDeskKey,
  ): StrategyCapitalProfile {
    const note = overviewHeadline(overview);
    return {
      overview: [
        { label: '策略状态', value: statusLabel(overview?.operatingStatus), note, tone: 'neutral' },
        {
          label: 'Scope',
          value: overview?.v1Scope || '--',
          note: overview?.instanceName || '--',
          tone: 'neutral',
        },
        {
          label: '账户能力',
          value: statusLabel(overview?.activeCapability),
          note: overview?.primaryAccountCode || '--',
          tone: 'neutral',
        },
        {
          label: '数据状态',
          value: statusLabel(overview?.dataQualityState),
          note: statusLabel(overview?.primaryAccountDataQualityState),
          tone: 'neutral',
        },
      ],
      riskCards: [
        {
          label: '执行就绪',
          value: overview?.executionReadiness
            ? overview.executionReadiness.runnable
              ? '可运行'
              : '受限'
            : '不适用',
          note,
          tone: 'neutral',
        },
        {
          label: '主账户状态',
          value: statusLabel(overview?.primaryAccountStatus),
          note: overview?.primaryAccountCode || '--',
          tone: 'neutral',
        },
      ],
      structureCards: [
        {
          label: '策略',
          value: overview?.strategyName || desk,
          note: overview?.category || '--',
          tone: 'neutral',
        },
        {
          label: '实例',
          value: overview?.instanceName || '--',
          note: overview?.strategyInstanceId || '--',
          tone: 'neutral',
        },
      ],
      comparisonCards: [],
      metricCurves: [],
      curve: {
        title: `${overview?.strategyName || desk}账户净值`,
        subtitle: note,
        metricOptions: [{ key: 'equity', label: '账户净值' }],
        periodOptions: [{ key: 'all', label: '全部' }],
        defaultMetric: 'equity',
        defaultPeriod: 'all',
        xLabels: [],
        netValueData: [],
        drawdownData: [],
        summaries: [
          { label: '主账户', value: overview?.primaryAccountCode || '--', tone: 'neutral' },
          { label: '绑定数量', value: String(overview?.bindingCount ?? 0), tone: 'neutral' },
        ],
      },
    };
  }

  function emptyTable(message: string) {
    return {
      columns: [{ key: 'message', label: '说明' }],
      rows: [{ message }],
    };
  }

  function placeholderOrderProfile(
    overview: StrategyManagementOverviewResult | null,
    desk: StrategyDeskKey,
  ): StrategyOrderProfile {
    const note = overviewHeadline(overview);
    return {
      label: `${overview?.strategyName || desk}订单信息`,
      tabs: [
        { key: 'positions', label: '当前持仓' },
        { key: 'orders', label: '历史订单' },
        { key: 'fills', label: '成交记录' },
      ],
      tables: {
        positions: emptyTable(note),
        orders: emptyTable(note),
        fills: emptyTable(note),
      },
    };
  }

  const deskTabs = computed(() =>
    strategyOverview.value.map((item) => ({
      key: item.deskKey as StrategyDeskKey,
      label: item.strategyName,
    })),
  );

  const activeOverview = computed(() => strategyOverviewByDesk.value[activeDesk.value] || null);

  const activePnlProfile = computed(() => {
    if (activeDesk.value === 'crossSpread') return pnlProfile.value;
    if (isAccountStrategy(activeDesk.value)) return accountPnlProfiles.value[activeDesk.value];
    return placeholderPnlProfile(activeOverview.value, activeDesk.value);
  });

  const orderProfile = computed(() => {
    if (activeDesk.value === 'crossSpread') {
      return {
        label: `${activeOverview.value?.strategyName || '跨所价差'}订单信息`,
        tabs: liveCrossSpreadTabs,
        tables: liveCrossSpreadTables.value,
      };
    }
    if (isAccountStrategy(activeDesk.value)) {
      return accountOrderProfiles.value[activeDesk.value];
    }
    return placeholderOrderProfile(activeOverview.value, activeDesk.value);
  });

  const capitalProfile = computed(() => {
    if (activeDesk.value === 'crossSpread') return liveCapitalProfile.value;
    return isAccountStrategy(activeDesk.value)
      ? accountCapitalProfiles.value[activeDesk.value]
      : placeholderCapitalProfile(activeOverview.value, activeDesk.value);
  });

  onMounted(() => {
    void refreshStrategyOverview();
    void refreshCrossSpreadRecords();
    void refreshCrossSpreadFinance();
    void refreshAccountSnapshots();
  });

  watch(
    () => route.query.section,
    (section) => {
      activeSection.value = normalizeSection(section);
    },
    { immediate: true },
  );

  watch(
    () => [route.query.desk, strategyOverview.value] as const,
    ([requestedDesk, items]) => {
      const available = items.map((item) => item.deskKey).filter(isDeskKey);
      if (!available.length) return;
      const nextDesk =
        isDeskKey(requestedDesk) && available.includes(requestedDesk)
          ? requestedDesk
          : available[0];
      if (activeDesk.value !== nextDesk) activeDesk.value = nextDesk;
    },
    { immediate: true, deep: true },
  );

  watch(
    () => [activeDesk.value, activeSection.value] as const,
    ([desk, section]) => {
      if (!deskTabs.value.some((item) => item.key === desk)) return;
      if (route.query.desk === desk && route.query.section === section) return;
      void router.replace({
        query: {
          ...route.query,
          desk,
          section,
        },
      });
    },
  );

  watch(
    () => activeDesk.value,
    () => {
      if (activeDesk.value === 'crossSpread') {
        void refreshCrossSpreadRecords();
        void refreshCrossSpreadFinance();
      }
      if (isAccountStrategy(activeDesk.value)) {
        void refreshAccountSnapshots(activeDesk.value);
      }
    },
    { immediate: true },
  );

  watch(
    () => orderProfile.value.tabs.map((tab) => tab.key),
    (keys) => {
      if (!keys.includes(activeRecordTab.value)) {
        activeRecordTab.value = keys[0] || 'positions';
      }
    },
    { immediate: true },
  );
</script>

<style lang="less">
  @import '../shared/strategy-theme.less';
</style>

<style scoped lang="less">
  .strategy-management-page {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 6px 4px 0;
    background: var(--strategy-bg);
    color: var(--strategy-text-1);
  }

  .records-only-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 16px;
  }
</style>
