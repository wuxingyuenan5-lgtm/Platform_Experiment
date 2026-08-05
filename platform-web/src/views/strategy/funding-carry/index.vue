<template>
  <RestoredProductSurface
    :state="fundingSampleMeta.state"
    :source="fundingSampleMeta.source"
    :as-of="fundingSampleMeta.asOf"
    :actionable="fundingSampleMeta.actionable"
    message="原市场板、图表、详情与订单结构已选择性恢复；真实资金费率 Provider 尚未配置，全部样例不可执行。"
  >
    <main class="funding-page" data-testid="funding-original-structure">
      <header class="funding-toolbar">
        <div>
          <span>FUNDING CARRY</span>
          <h1>资金费率套利</h1>
        </div>
        <nav aria-label="资金费率页面视角">
          <button type="button" :class="{ active: localSection === 'analysis' }" @click="localSection = 'analysis'">分析</button>
          <button type="button" :class="{ active: localSection === 'execution' }" @click="localSection = 'execution'">执行</button>
        </nav>
      </header>

      <template v-if="localSection === 'analysis'">
        <FundingMarketBoard
          :rows="fundingMarketRows"
          :selected-range="selectedRange"
          :selected-symbol="selectedSymbol"
          :selected-resolution="selectedResolution"
          :range-options="fundingRangeOptions"
          @update:selected-range="selectedRange = $event"
          @update:selected-symbol="selectedSymbol = $event"
          @update:selected-resolution="selectedResolution = $event"
        />
        <FundingChartPanel
          :series="fundingChartSeries"
          :exchange="selectedExchange"
          :symbol="selectedSymbol"
          :range="selectedRange"
          :resolution="selectedResolution"
          :start-date="selectedStartDate"
          :end-date="selectedEndDate"
          @update:start-date="selectedStartDate = $event"
          @update:end-date="selectedEndDate = $event"
        />
        <FundingDetailPanel
          :exchange="selectedExchange"
          :symbol="selectedSymbol"
          :selected-range="selectedRange"
          :resolution="selectedResolution"
          :start-date="selectedStartDate"
          :end-date="selectedEndDate"
          :research="fundingResearch"
        />
      </template>

      <template v-else>
        <FundingOrderPanel :data="fundingOrderPreview" />
      </template>
    </main>
  </RestoredProductSurface>
</template>

<script setup lang="ts">
  import { ref, watch } from 'vue';
  import RestoredProductSurface from '@/components/ProductDataState/RestoredProductSurface.vue';
  import {
    fundingChartSeries,
    fundingMarketRows,
    fundingOrderPreview,
    fundingRangeOptions,
    fundingResearch,
    fundingSampleMeta,
    type FundingExchange,
    type FundingRange,
    type FundingSymbol,
  } from '@/data/sample/funding';
  import FundingChartPanel from './components/FundingChartPanel.vue';
  import FundingDetailPanel from './components/FundingDetailPanel.vue';
  import FundingMarketBoard from './components/FundingMarketBoard.vue';
  import FundingOrderPanel from './components/FundingOrderPanel.vue';

  const props = withDefaults(
    defineProps<{
      activeSection?: 'analysis' | 'execution';
      selectedExchange?: FundingExchange;
      selectedSymbol?: FundingSymbol;
      selectedResolution?: string;
    }>(),
    {
      activeSection: 'analysis',
      selectedExchange: 'Bybit',
      selectedSymbol: 'BTC',
      selectedResolution: '30分钟',
    },
  );

  const localSection = ref(props.activeSection);
  const selectedExchange = ref<FundingExchange>(props.selectedExchange);
  const selectedSymbol = ref<string>(props.selectedSymbol);
  const selectedRange = ref<FundingRange>('current');
  const selectedResolution = ref(props.selectedResolution);
  const selectedStartDate = ref('2026-05-28');
  const selectedEndDate = ref('2026-06-24');

  watch(() => props.activeSection, (value) => (localSection.value = value));
  watch(() => props.selectedExchange, (value) => (selectedExchange.value = value));
  watch(() => props.selectedSymbol, (value) => (selectedSymbol.value = value));
  watch(() => props.selectedResolution, (value) => (selectedResolution.value = value));
</script>

<style scoped lang="less">
  .funding-page {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 0 4px 18px;
    color: #1d2b3a;
  }

  .funding-toolbar {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 16px;
    padding: 18px;
    border: 1px solid #e1e7ef;
    border-radius: 14px;
    background: #fff;
  }

  .funding-toolbar span {
    color: #65749a;
    font-size: 11px;
    letter-spacing: 0.16em;
  }

  h1 {
    margin: 4px 0 0;
    font-size: 25px;
  }

  nav {
    display: flex;
    gap: 6px;
    padding: 5px;
    border: 1px solid #e1e7ef;
    border-radius: 11px;
  }

  nav button {
    padding: 8px 14px;
    border: 0;
    border-radius: 8px;
    background: transparent;
    color: #697589;
    cursor: pointer;
  }

  nav button.active {
    background: #edf3f8;
    color: #294a67;
    font-weight: 700;
  }

  @media (max-width: 620px) {
    .funding-toolbar {
      align-items: stretch;
      flex-direction: column;
    }
  }
</style>
