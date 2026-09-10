<template>
  <div class="index-overview">
    <ResearchSourceState v-if="dashboard?.marketDetail" :meta="dashboard.marketDetail.meta" />
    <MarketTerminalPage
      :dashboard="dashboard"
      :config="config"
      :market-tabs="tabs"
      :readonly-details="true"
      detail-section-id="a-share-market-detail"
      @index-chart="openChart"
    />
    <Modal
      v-model:open="chartOpen"
      :title="`${chartName} · 指数日线`"
      :footer="null"
      width="min(1050px, calc(100vw - 32px))"
      :get-container="false"
    >
      <p v-if="loading" role="status">正在读取历史日线…</p>
      <p v-else-if="error" role="alert">{{ error }}</p>
      <VibeTimeChart
        v-else-if="history.length"
        :title="chartName"
        y-label="指数收盘"
        :dates="history.map((row) => row.observedAt)"
        :series="[
          {
            name: '收盘',
            type: 'line',
            color: '#1d4ed8',
            values: history.map((row) => Number(row.close)),
          },
        ]"
      />
      <p v-else>暂无已入库的指数日线。</p>
    </Modal>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { Modal } from 'ant-design-vue';
  import { researchRequest, type AShareDashboardResponse } from '@/api/hedgeResearch';
  import MarketTerminalPage from '../../components/MarketTerminalPage.vue';
  import ResearchSourceState from '../../research/components/ResearchSourceState.vue';
  import VibeTimeChart from './VibeTimeChart.vue';
  import {
    marketTerminalConfigs,
    type TerminalMarketId,
    type MarketTerminalPageConfig,
  } from '../../nativeData/marketTerminal';

  const props = defineProps<{ dashboard: AShareDashboardResponse | null }>();
  const base = marketTerminalConfigs.aShare;
  const tabs: Array<{ id: TerminalMarketId; label: string; path: string }> = [
    { id: 'aShare', label: 'A股', path: '/hedge-board/a-share' },
  ];
  const pct = (value: unknown) =>
    value == null ? '—' : `${Number(value) > 0 ? '+' : ''}${Number(value).toFixed(2)}%`;
  const config = computed<MarketTerminalPageConfig>(() => {
    const snapshots = props.dashboard?.marketDetail.data || [];
    const benchmark = snapshots.find((row) => row.code === '000300');
    const breadth = props.dashboard?.breadth.data;
    return {
      ...base,
      updatedAt: props.dashboard?.generatedAt || '',
      overviewChip: `沪深300 距52周高点：${pct(benchmark?.distance52wHighPct)}`,
      breadthCards: (base.breadthCards || []).map((row) => ({
        ...row,
        value: '—',
        tag: '暂无数据',
        delta: '',
      })),
      volatilityCards: (base.volatilityCards || []).map((row) =>
        row.id === 'a-advdec'
          ? {
              ...row,
              value: breadth && breadth.down > 0 ? (breadth.up / breadth.down).toFixed(2) : '—',
              badge: breadth?.breadthState || '暂无数据',
              ranges: '',
            }
          : { ...row, value: '—', badge: '暂无数据', ranges: '' },
      ),
      detailGroups: base.detailGroups.map((group) => ({
        ...group,
        rows: group.rows.map((row) => {
          const quote = snapshots.find((item) => item.code === row.symbol);
          return {
            ...row,
            spark: quote?.spark.map(Number) || [],
            price: quote?.close == null ? '—' : String(quote.close),
            d1: pct(quote?.return1dPct),
            ytd: pct(quote?.returnYtdPct),
            qtd: pct(quote?.returnQtdPct),
            w1: pct(quote?.return1wPct),
            m1: pct(quote?.return1mPct),
            y1: pct(quote?.return1yPct),
            high: pct(quote?.distance52wHighPct),
            d10: '—',
            d20: '—',
            d50: '—',
            d200: '—',
            x2050: '—',
            x50200: '—',
          };
        }),
      })),
    };
  });
  const chartOpen = ref(false),
    loading = ref(false),
    error = ref(''),
    chartName = ref('');
  const history = ref<Array<{ observedAt: string; close: string | number }>>([]);
  let requestId = 0;
  async function openChart(code: string, name: string) {
    const current = ++requestId;
    chartName.value = name;
    chartOpen.value = true;
    loading.value = true;
    error.value = '';
    history.value = [];
    try {
      const result = await researchRequest<{ data: typeof history.value }>({
        url: `/research/a-share/indices/${encodeURIComponent(code)}/history`,
      });
      if (current === requestId) history.value = result.data;
    } catch (cause) {
      if (current === requestId)
        error.value = cause instanceof Error ? cause.message : '日线暂不可用';
    } finally {
      if (current === requestId) loading.value = false;
    }
  }
</script>

<style scoped>
  .index-overview {
    display: grid;
    gap: 8px;
    min-width: 0;
  }
</style>
