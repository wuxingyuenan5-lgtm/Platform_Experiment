<template>
  <RestoredProductSurface
    :state="strategySampleMeta.state"
    :source="strategySampleMeta.source"
    :as-of="strategySampleMeta.asOf"
    :actionable="strategySampleMeta.actionable"
    message="原策略管理组件体系已选择性恢复；跨所价差继续读取真实观测接口，其他数据为不可执行样例。"
  >
    <main class="strategy-management-page" data-testid="strategy-management-original-structure">
      <section class="strategy-top-toolbar">
        <div>
          <span class="toolbar-label">策略 Desk</span>
          <CompactSegmentTabs v-model="activeDesk" :items="deskTabs" />
        </div>
        <div>
          <span class="toolbar-label">管理视角</span>
          <CompactSegmentTabs v-model="activeSection" :items="sectionTabs" />
        </div>
      </section>

      <aside v-if="activeDesk === 'crossSpread'" class="live-read-status" aria-live="polite">
        <strong>跨所价差真实读取</strong>
        <span v-if="liveLoading">正在读取 CrossSpreadObservability…</span>
        <span v-else-if="liveError">实时读取失败：{{ liveError }}；未使用假 API 值替代。</span>
        <span v-else-if="liveAsOf">观测接口可用，数据时间：{{ liveAsOf }}</span>
        <span v-else>尚未获得实时观测结果。</span>
      </aside>

      <template v-if="activeSection === 'pnl'">
        <StrategyPnlPanel :title="strategyDeskLabels[activeDesk]" :items="profile.pnl" />
      </template>

      <template v-else-if="activeSection === 'capital'">
        <StrategyKpiGrid :items="profile.overview" />
        <StrategyCapitalFinanceBoard
          :risk-cards="profile.riskCards"
          :structure-cards="profile.structureCards"
        />
        <section class="capital-lower-grid">
          <StrategyCapitalRulePanel :panel="profile.rulePanel" />
          <StrategyCapitalRiskOverview :overview="profile.riskOverview" />
          <StrategyRuntimePanel :cards="profile.runtimeCards" />
        </section>
        <StrategyCapitalNetValueBoard :curve="profile.curve" />
        <StrategyCurveGrid :curves="profile.metricCurves" />
      </template>

      <template v-else>
        <StrategyRecordsPanel
          v-model:active-tab="activeRecordTab"
          :tabs="recordTabs"
          :tables="profile.records"
        />
      </template>

      <footer class="write-boundary">
        <div>
          <strong>示例策略不可启停、部署或下单</strong>
          <span>Platform 与 Runtime Live Write 均保持关闭。</span>
        </div>
        <div v-if="canWrite" class="write-actions">
          <button type="button" disabled data-write-action="true">启停策略</button>
          <button type="button" disabled data-write-action="true">部署策略</button>
        </div>
        <strong v-else class="readonly">当前账号为只读权限</strong>
      </footer>
    </main>
  </RestoredProductSurface>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref, watch } from 'vue';
  import { getCrossSpreadObservability } from '@/api/platform/crossSpreadObservability';
  import { hasPermission } from '@/access/userAccess';
  import RestoredProductSurface from '@/components/ProductDataState/RestoredProductSurface.vue';
  import {
    strategyDeskLabels,
    strategyDeskOrder,
    strategyProfiles,
    strategySampleMeta,
    type StrategyDeskKey,
  } from '@/data/sample/strategy';
  import { useUserStore } from '@/store/modules/user';
  import CompactSegmentTabs from '../shared/CompactSegmentTabs.vue';
  import StrategyCapitalFinanceBoard from './components/StrategyCapitalFinanceBoard.vue';
  import StrategyCapitalNetValueBoard from './components/StrategyCapitalNetValueBoard.vue';
  import StrategyCapitalRiskOverview from './components/StrategyCapitalRiskOverview.vue';
  import StrategyCapitalRulePanel from './components/StrategyCapitalRulePanel.vue';
  import StrategyCurveGrid from './components/StrategyCurveGrid.vue';
  import StrategyKpiGrid from './components/StrategyKpiGrid.vue';
  import StrategyPnlPanel from './components/StrategyPnlPanel.vue';
  import StrategyRecordsPanel from './components/StrategyRecordsPanel.vue';
  import StrategyRuntimePanel from './components/StrategyRuntimePanel.vue';

  type SectionKey = 'pnl' | 'capital' | 'orders';

  const userStore = useUserStore();
  const activeDesk = ref<StrategyDeskKey>('funding');
  const activeSection = ref<SectionKey>('pnl');
  const activeRecordTab = ref('positions');
  const liveLoading = ref(false);
  const liveError = ref('');
  const liveAsOf = ref('');

  const deskTabs = strategyDeskOrder.map((key) => ({
    key,
    label: strategyDeskLabels[key],
  }));
  const sectionTabs = [
    { key: 'pnl', label: '策略损益' },
    { key: 'capital', label: '账户资金' },
    { key: 'orders', label: '订单信息' },
  ];
  const recordTabs = [
    { key: 'positions', label: '持仓' },
    { key: 'orders', label: '订单' },
  ];

  const profile = computed(() => strategyProfiles[activeDesk.value]);
  const canWrite = computed(() =>
    hasPermission(userStore.getAuthentication?.permissions || [], 'strategy.write'),
  );

  watch(activeDesk, () => {
    activeSection.value = 'pnl';
    activeRecordTab.value = 'positions';
    void loadCrossSpreadObservation();
  });

  onMounted(() => void loadCrossSpreadObservation());

  async function loadCrossSpreadObservation() {
    if (activeDesk.value !== 'crossSpread') return;
    liveLoading.value = true;
    liveError.value = '';
    liveAsOf.value = '';
    try {
      const result = await getCrossSpreadObservability(24, 50, 'fast');
      liveAsOf.value = result.asOf || '接口未返回时间';
    } catch (error) {
      liveError.value = error instanceof Error ? error.message : '跨所价差观测接口不可用';
    } finally {
      liveLoading.value = false;
    }
  }
</script>

<style scoped lang="less">
  .strategy-management-page {
    --strategy-border: #e4e9ef;
    --strategy-radius-card: 14px;
    --strategy-radius-control: 9px;
    --strategy-surface: #fff;
    --strategy-shadow: 0 8px 24px rgba(23, 35, 57, 0.05);
    --strategy-text-1: #1d2b3a;
    --strategy-text-3: #778396;
    --strategy-accent-soft: #edf3f8;
    --strategy-accent-strong: #294a67;
    --strategy-accent-ring: rgba(61, 101, 137, 0.18);
    --strategy-tab-height: 34px;
    --strategy-font-base: 13px;

    display: grid;
    gap: 14px;
    color: var(--strategy-text-1);
  }

  .strategy-top-toolbar {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 18px;
    padding: 16px 18px;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-card);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow);
  }

  .strategy-top-toolbar > div {
    display: grid;
    gap: 7px;
  }

  .toolbar-label {
    color: var(--strategy-text-3);
    font-size: 11px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .live-read-status {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 11px 14px;
    border: 1px solid #cbdce9;
    border-radius: 11px;
    background: #f5f9fc;
    color: #426078;
  }

  .capital-lower-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }

  .write-boundary {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 15px 18px;
    border: 1px solid #eadcae;
    border-radius: var(--strategy-radius-card);
    background: #fffaf0;
  }

  .write-boundary > div:first-child {
    display: grid;
    gap: 4px;
  }

  .write-boundary span {
    color: #786638;
    font-size: 12px;
  }

  .write-actions {
    display: flex;
    gap: 8px;
  }

  .write-actions button {
    padding: 8px 12px;
    border: 0;
    border-radius: 8px;
    background: #e5e8ec;
    color: #77808d;
  }

  .readonly {
    color: #786638;
    font-size: 12px;
  }

  @media (max-width: 1024px) {
    .capital-lower-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 760px) {
    .strategy-top-toolbar,
    .write-boundary {
      flex-direction: column;
      align-items: stretch;
    }

    .live-read-status {
      align-items: flex-start;
      flex-direction: column;
    }
  }
</style>
