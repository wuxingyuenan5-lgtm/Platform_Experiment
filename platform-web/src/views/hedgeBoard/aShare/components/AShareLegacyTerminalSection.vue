<template>
  <div class="index-overview">
    <ResearchSourceState
      v-if="view !== 'overview' && dashboard?.marketDetail"
      :meta="dashboard.marketDetail.meta"
    />
    <MarketTerminalPage
      :dashboard="dashboard"
      :view="view"
      :config="config"
      :market-tabs="tabs"
      detail-section-id="a-share-market-detail"
    >
      <template v-if="$slots.breadth" #breadth><slot name="breadth"></slot></template>
      <template v-if="view === 'overview'" #option-iv
        ><DomesticOptionIvCard :refresh-key="refreshKey"
      /></template>
      <template v-if="view === 'overview'" #info-extra
        ><ChinaTreasuryInfoCards :refresh-key="refreshKey"
      /></template>
    </MarketTerminalPage>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue';
  import ChinaTreasuryInfoCards from './ChinaTreasuryInfoCards.vue';
  import DomesticOptionIvCard from './DomesticOptionIvCard.vue';
  import { type AShareDashboardResponse } from '@/api/hedgeResearch';
  import MarketTerminalPage from '../../components/MarketTerminalPage.vue';
  import ResearchSourceState from '../../research/components/ResearchSourceState.vue';
  import {
    marketTerminalConfigs,
    type TerminalMarketId,
    type MarketTerminalPageConfig,
  } from '../../nativeData/marketTerminal';

  const props = defineProps<{
    dashboard: AShareDashboardResponse | null;
    view?: 'overview' | 'details';
    refreshKey?: number;
  }>();
  const base = marketTerminalConfigs.aShare;
  const tabs: Array<{ id: TerminalMarketId; label: string; path: string }> = [
    { id: 'aShare', label: 'A股', path: '/hedge-board/a-share' },
  ];
  const pct = (value: unknown) =>
    value == null ? '—' : `${Number(value) > 0 ? '+' : ''}${Number(value).toFixed(2)}%`;
  const config = computed<MarketTerminalPageConfig>(() => {
    const snapshots = props.dashboard?.marketDetail.data || [];
    const benchmark = snapshots.find((row) => row.code === '000300');
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
      volatilityCards: (base.volatilityCards || [])
        .filter((row) => ['a-vix50', 'a-style'].includes(row.id))
        .map((row) => ({ ...row, value: '—', badge: '暂无数据', ranges: '' })),
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
</script>

<style scoped>
  .index-overview {
    display: grid;
    gap: 8px;
    min-width: 0;
  }
</style>
