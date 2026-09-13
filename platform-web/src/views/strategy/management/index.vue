<template>
  <div class="strategy-management-page" data-testid="strategy-management-original-structure">
    <section v-if="monitorWarning" class="strategy-sync-alert" role="alert">
      <strong>后台监控告警</strong><span>{{ monitorWarning }}</span>
    </section>
    <section v-if="overviewLoading" class="strategy-overview-state" data-testid="overview-loading">
      <p>策略管理总览加载中</p>
    </section>

    <section v-else-if="overviewError" class="strategy-overview-state" data-testid="overview-error">
      <p>{{ overviewError }}</p>
      <button type="button" class="state-refresh-btn" @click="refreshManagementOverview">
        重新刷新
      </button>
    </section>

    <section v-else-if="overviewEmpty" class="strategy-overview-state" data-testid="overview-empty">
      <p>暂无策略</p>
      <button type="button" class="state-refresh-btn" @click="refreshManagementOverview">
        重新刷新
      </button>
    </section>

    <template v-else>
      <section class="strategy-top-toolbar">
        <div class="strategy-top-toolbar__left">
          <CompactSegmentTabs :items="deskTabs" v-model="activeDesk" />
        </div>

        <div class="strategy-top-toolbar__meta">
          <CompactSegmentTabs :items="sectionTabs" v-model="activeSection" />
        </div>
      </section>

      <section v-if="activeSyncAlert" class="strategy-sync-alert" role="alert">
        <strong>账户数据同步中断</strong>
        <span
          >{{ activeSyncAlert.label }}：{{ activeSyncAlert.value }}；后台定时重试同步。{{
            activeSyncAlert.note
          }}</span
        >
        <button type="button" @click="refreshVisibleAccount">刷新状态</button>
      </section>

      <template v-if="activeSection === 'pnl'">
        <StrategyPnlPanel
          view="overview"
          :active-desk="activeDesk"
          :live-profile="activePnlProfile"
        />
      </template>

      <template v-else-if="activeSection === 'capital'">
        <StrategyKpiGrid :items="capitalProfile.overview" />

        <StrategyCapitalFinanceBoard
          :risk-cards="capitalProfile.riskCards"
          :structure-cards="capitalProfile.structureCards"
        >
          <template #position-distribution>
            <StrategyPnlPanel
              view="daily-position"
              :active-desk="activeDesk"
              :live-profile="activePnlProfile"
              distribution-only
            />
          </template>
        </StrategyCapitalFinanceBoard>

        <StrategyPnlPanel
          view="daily-position"
          :active-desk="activeDesk"
          :live-profile="activePnlProfile"
          hide-distribution
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
        <p v-if="fundingGroupsError && activeDesk === 'funding'" role="alert">{{
          fundingGroupsError
        }}</p>
        <section v-if="visibleAbnormalOrders.length" class="strategy-abnormal-card">
          <h3>{{ activeDesk === 'funding' ? '资费' : '跨所价差' }}异常订单</h3>
          <article v-for="row in visibleAbnormalOrders" :key="row.id">
            <strong>{{ row.label }}</strong
            ><p>{{ row.detail }}</p>
          </article>
          <router-link
            :to="{ path: '/strategy/platform', query: { desk: activeDesk, section: 'execution' } }"
            >前往处理异常平仓</router-link
          >
        </section>
        <section class="records-only-grid">
          <StrategyRecordsPanel
            :key="activeDesk"
            :loading="
              activeDesk === 'crossSpread'
                ? crossRecordsLoading
                : isAccountStrategy(activeDesk)
                ? accountRecordsLoading[activeDesk]
                : false
            "
            :error="
              activeDesk === 'crossSpread'
                ? crossRecordsError
                : isAccountStrategy(activeDesk)
                ? accountRecordsErrors[activeDesk]
                : undefined
            "
            :tabs="orderProfile.tabs"
            :tables="orderProfile.tables"
            v-model:activeTab="activeRecordTab"
          />
        </section>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
  import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { createStrategyClient } from '@/api/platform/strategyClient';
  import {
    getFundingPositionGroups,
    type FundingPositionGroup,
  } from '@/api/platform/fundingWorkspace';
  import type { StrategyManagementOverviewResult } from '@/api/platform/trading.types';
  import CompactSegmentTabs from '../shared/CompactSegmentTabs.vue';
  import { useCrossSpreadFinance } from './composables/useCrossSpreadFinance';
  import { useCrossSpreadRecords } from './composables/useCrossSpreadRecords';
  import {
    normalizeManagementSection,
    resolveManagementDesk,
  } from './composables/strategyManagementOverviewState';
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
  import { strategyRegistryMap } from '../shared/strategyRegistry';

  const route = useRoute();
  const router = useRouter();
  const activeRecordTab = ref('positions');

  const sectionTabs = [
    { key: 'capital', label: '账户资金' },
    { key: 'pnl', label: '策略损益' },
    { key: 'orders', label: '订单信息' },
  ];

  const {
    loading: crossRecordsLoading,
    error: crossRecordsError,
    abnormalOrders: crossAbnormalOrders,
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
    empty: overviewEmpty,
    error: overviewError,
    items: strategyOverview,
    loading: overviewLoading,
    refresh: refreshStrategyOverview,
  } = useStrategyManagementOverview();

  const activeDesk = computed<StrategyDeskKey>({
    get: () => {
      const desk = resolveManagementDesk(route.query.desk, strategyOverview.value);
      return isDeskKey(desk) ? desk : 'funding';
    },
    set: (desk) => {
      void router.replace({ query: { ...route.query, desk, section: activeSection.value } });
    },
  });
  const activeSection = computed<'pnl' | 'capital' | 'orders'>({
    get: () => normalizeManagementSection(route.query.section),
    set: (section) => {
      void router.replace({ query: { ...route.query, desk: activeDesk.value, section } });
    },
  });

  const {
    loading: accountRecordsLoading,
    errors: accountRecordsErrors,
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

  async function refreshManagementOverview() {
    await refreshStrategyOverview();
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
        { key: 'activity', label: '开平记录' },
        { key: 'fills', label: '逐笔成交' },
        { key: 'orders', label: '委托明细' },
      ],
      tables: {
        positions: emptyTable(note),
        activity: emptyTable(note),
        orders: emptyTable(note),
        fills: emptyTable(note),
      },
    };
  }

  const deskTabs = computed(() =>
    strategyOverview.value.map((item) => ({
      key: item.deskKey as StrategyDeskKey,
      label: strategyRegistryMap[item.deskKey as StrategyDeskKey]?.name || item.strategyName,
    })),
  );

  const activeOverview = computed(() => strategyOverviewByDesk.value[activeDesk.value] || null);

  const activePnlProfile = computed(() => {
    if (activeDesk.value === 'crossSpread') return pnlProfile.value;
    if (isAccountStrategy(activeDesk.value)) return accountPnlProfiles.value[activeDesk.value];
    return placeholderPnlProfile(activeOverview.value, activeDesk.value);
  });

  const fundingGroups = ref<FundingPositionGroup[]>([]);
  const fundingGroupsError = ref('');
  async function refreshFundingGroups() {
    try {
      fundingGroups.value = await getFundingPositionGroups('active');
      fundingGroupsError.value = '';
    } catch {
      fundingGroupsError.value = '资费组合状态暂不可用，请刷新核对。';
    }
  }
  const visibleAbnormalOrders = computed(() => {
    if (activeDesk.value === 'crossSpread')
      return crossAbnormalOrders.value.map((row) => ({
        id: row.batchId,
        label: row.label,
        detail: `Bybit 剩余 ${row.bybitRemainingQuantity ?? '待核对'} XAUT；MT5 剩余 ${
          row.mt5RemainingQuantity ?? '待核对'
        } 手。${row.reason || ''}`,
      }));
    if (activeDesk.value === 'funding')
      return fundingGroups.value
        .filter((row) => row.isAbnormal)
        .map((row) => ({
          id: row.instructionId,
          label: `${row.perpetualSymbol} · ${row.instructionId}`,
          detail: row.abnormalReason || '请核对两腿成交',
        }));
    return [];
  });

  const orderProfile = computed(() => {
    if (activeDesk.value === 'crossSpread') {
      return {
        label: `${activeOverview.value?.strategyName || '跨所价差'}订单信息`,
        abnormalOrders: crossAbnormalOrders,
        tabs: liveCrossSpreadTabs,
        tables: liveCrossSpreadTables.value,
      };
    }
    if (activeDesk.value === 'funding') {
      const profile = accountOrderProfiles.value.funding;
      return {
        ...profile,
        tables: {
          ...profile.tables,
          positions: {
            columns: [
              { key: 'instructionId', label: '组合' },
              { key: 'symbol', label: '标的' },
              { key: 'perpetualQuantity', label: '永续空仓（剩余）' },
              { key: 'spotQuantity', label: '现货持有（扣费后剩余）' },
              { key: 'spotFill', label: '现货累计成交' },
              { key: 'spotFee', label: '现货扣币手续费' },
              { key: 'status', label: '状态' },
            ],
            rows: fundingGroups.value
              .filter((row) => !row.isAbnormal && row.lifecycleState === 'active')
              .map((row) => ({
                instructionId: row.instructionId,
                symbol: row.perpetualSymbol,
                perpetualQuantity: row.remainingPerpetualQuantity,
                spotQuantity: row.remainingSpotHolding ?? '--',
                spotFill: row.cumulativeSpotFill,
                spotFee: row.spotFeeResidualQuantity ?? '--',
                status: row.status === 'completed' ? '双腿已成交' : row.status,
              })),
          },
        },
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

  const activeSyncAlert = computed(() =>
    capitalProfile.value.riskCards.find(
      (card) => card.label.endsWith('数据状态') && card.tone === 'negative',
    ),
  );

  const monitorWarning = ref('');
  const monitorClient = createStrategyClient(5000);
  let monitorReadPending = false;
  async function refreshMonitorHealth() {
    if (monitorReadPending) return;
    monitorReadPending = true;
    try {
      const { data } = await monitorClient.get('/system/monitor-health');
      const warnings: string[] = [];
      if (['stalled', 'degraded'].includes(data.accountSync?.status))
        warnings.push('账户后台同步异常，保留最后成功数据');
      if (['stalled', 'degraded', 'starting'].includes(data.crossExit?.status))
        warnings.push('止盈止损监控尚未完成有效评估，请核对退出计划');
      if (data.crossExit?.status === 'disabled') warnings.push('自动止盈止损后台监控进程未启用');
      else if (data.crossExitExecutionEnabled === false)
        warnings.push('止盈止损监控运行中；实盘执行闸门关闭，仅监控不下单');
      if (
        ['blocked', 'stalled', 'unavailable', 'degraded', 'recovering'].includes(
          data.watchdog?.status,
        )
      )
        warnings.push(
          data.watchdog.status === 'recovering' ? '后台服务正在恢复' : '服务看护异常或需要人工处理',
        );
      monitorWarning.value = warnings.join('；');
    } catch {
      monitorWarning.value = '无法读取后台健康状态，请勿将旧数据视为实时数据';
    } finally {
      monitorReadPending = false;
    }
  }

  let monitorTimer: ReturnType<typeof setInterval> | null = null;
  function refreshVisibleAccount() {
    if (document.visibilityState !== 'visible') return;
    void refreshMonitorHealth();
    void refreshStrategyOverview();
    if (activeDesk.value === 'crossSpread') {
      void refreshCrossSpreadFinance(activeSection.value === 'pnl' ? 'pnl' : 'capital');
      if (activeSection.value === 'orders') void refreshCrossSpreadRecords();
    } else if (isAccountStrategy(activeDesk.value)) {
      void refreshAccountSnapshots(activeDesk.value);
      if (activeDesk.value === 'funding') void refreshFundingGroups();
    }
  }
  onMounted(() => {
    void refreshMonitorHealth();
    void refreshManagementOverview();
    monitorTimer = setInterval(refreshVisibleAccount, 30_000);
    document.addEventListener('visibilitychange', refreshVisibleAccount);
  });
  onBeforeUnmount(() => {
    if (monitorTimer) clearInterval(monitorTimer);
    document.removeEventListener('visibilitychange', refreshVisibleAccount);
  });

  watch(
    () => [activeDesk.value, activeSection.value] as const,
    ([desk, section], previous) => {
      const previousDesk = previous?.[0];
      const previousSection = previous?.[1];
      if (desk === 'crossSpread') {
        if (desk !== previousDesk) {
          void refreshCrossSpreadFinance(section === 'pnl' ? 'pnl' : 'capital');
        } else if (section === 'pnl' && previousSection !== 'pnl') {
          void refreshCrossSpreadFinance('pnl');
        }
        if (section === 'orders' && (desk !== previousDesk || section !== previousSection)) {
          void refreshCrossSpreadRecords();
        }
      }
      if (isAccountStrategy(desk) && desk !== previousDesk) {
        void refreshAccountSnapshots(desk);
        if (desk === 'funding') void refreshFundingGroups();
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

  .strategy-overview-state {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 20px;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-panel);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-card);
    gap: 12px;
  }

  .strategy-overview-state p {
    margin: 0;
    color: var(--strategy-text-2);
    font-size: 14px;
    font-weight: 600;
  }

  .strategy-sync-alert {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 16px;
    border: 1px solid #efb4b4;
    border-radius: 12px;
    background: #fff5f5;
    color: #a83232;
    font-size: 13px;
  }

  .strategy-sync-alert span {
    flex: 1;
  }

  .strategy-sync-alert button {
    padding: 6px 12px;
    border: 1px solid #df8d8d;
    border-radius: 8px;
    background: #fff;
    color: #a83232;
    font-weight: 700;
    cursor: pointer;
  }

  .strategy-abnormal-card {
    padding: 20px;
    margin-bottom: 16px;
    border: 1px solid #e9bcb6;
    border-radius: 14px;
    background: #fffaf8;
    overflow-wrap: anywhere;
  }

  .state-refresh-btn {
    min-width: 88px;
    padding: 8px 12px;
    border: 1px solid var(--strategy-border-strong);
    border-radius: 10px;
    background: var(--strategy-surface-muted);
    color: var(--strategy-text-1);
    font-weight: 700;
  }
</style>
