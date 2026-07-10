<template>
  <div class="funding-page">
    <template v-if="activeSection === 'analysis'">
      <FundingMarketBoard
        :data="fundingMarketBoard"
        :selected-range="selectedRange"
        :selected-symbol="selectedMarketSymbol"
        :selected-resolution="selectedResolution"
        :range-options="rangeOptions"
        @update:selected-range="selectedRange = $event"
        @update:selected-symbol="selectedMarketSymbol = $event"
        @update:selected-resolution="selectedResolution = $event"
      />

      <FundingChartPanel :data="fundingChartPanel" :symbol="selectedSymbol" />

      <FundingDetailPanel
        :exchange="selectedExchange"
        :symbol="selectedSymbol"
        :active-view="selectedView"
        :view-label="viewLabel"
        :research="currentResearch"
        :views="viewOptions"
        @change-view="selectedView = $event"
      />
    </template>

    <template v-else>
      <FundingOrderPanel :data="profileOrderPanel" />
    </template>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import FundingChartPanel from './components/FundingChartPanel.vue';
  import FundingDetailPanel from './components/FundingDetailPanel.vue';
  import FundingMarketBoard from './components/FundingMarketBoard.vue';
  import FundingOrderPanel from './components/FundingOrderPanel.vue';
  import {
    defaultSymbol,
    fundingChartPanel,
    fundingCarryProfiles,
    fundingMarketBoard,
    fundingOrderPanel,
    fundingRangeLabels,
    fundingViewLabels,
  } from './mock/data';
  import type { FundingExchange, FundingMarketRange, FundingSymbol, FundingViewMode } from './types';

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

  const selectedExchange = ref<FundingExchange>(props.selectedExchange);
  const selectedSymbol = ref<FundingSymbol>(props.selectedSymbol);
  const selectedView = ref<FundingViewMode>('funding');
  const selectedRange = ref<FundingMarketRange>('current');
  const selectedMarketSymbol = ref<string>(props.selectedSymbol);
  const selectedResolution = ref<string>(props.selectedResolution);

  const profile = computed(() => fundingCarryProfiles[selectedExchange.value] ?? fundingCarryProfiles.Bybit);
  const viewLabel = computed(() => fundingViewLabels[selectedView.value]);
  const currentResearch = computed(() => profile.value.research[selectedSymbol.value] ?? profile.value.research[defaultSymbol]);

  const rangeOptions = computed(() =>
    (Object.keys(fundingRangeLabels) as FundingMarketRange[]).map((value) => ({
      value,
      label: fundingRangeLabels[value],
    })),
  );

  const viewOptions = computed(() =>
    (['funding'] as FundingViewMode[]).map((value) => ({
      value,
      label: fundingViewLabels[value],
    })),
  );

  const profileOrderPanel = computed(() => ({
    ...fundingOrderPanel,
    strategyLabel: `${selectedExchange.value} 路 ${selectedSymbol.value} 单交易所资金费率套利`,
  }));

  watch(
    () => props.selectedExchange,
    (value) => {
      selectedExchange.value = value;
    },
    { immediate: true },
  );

  watch(
    () => props.selectedSymbol,
    (value) => {
      selectedSymbol.value = value;
      selectedMarketSymbol.value = value;
    },
    { immediate: true },
  );

  watch(
    () => props.selectedResolution,
    (value) => {
      selectedResolution.value = value;
    },
    { immediate: true },
  );

  watch(
    profile,
    (nextProfile) => {
      const nextSymbols = nextProfile.snapshots.map((item) => item.symbol);
      if (!nextSymbols.includes(selectedSymbol.value)) {
        selectedSymbol.value = nextSymbols[0] ?? defaultSymbol;
      }
    },
    { immediate: true },
  );
</script>

<style lang="less">
  @import '../shared/strategy-theme.less';
</style>

<style scoped lang="less">
  .funding-page {
    display: flex;
    flex-direction: column;
    gap: 18px;
    padding: 0 4px 18px;
    background: var(--strategy-bg);
    color: var(--strategy-text-1);
  }
</style>
