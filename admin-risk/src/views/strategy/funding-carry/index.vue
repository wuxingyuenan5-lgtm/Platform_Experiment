<template>
  <div class="funding-page">
    <template v-if="activeSection === 'analysis'">
      <FundingMarketBoard
        :data="fundingMarketBoard"
        :exchange="selectedExchange"
        :selected-range="selectedRange"
        :selected-symbol="selectedSymbol"
        :selected-resolution="selectedResolution"
        :range-options="rangeOptions"
        @update:selected-range="selectedRange = $event"
        @update:selected-symbol="handleChartSymbolUpdate"
        @update:selected-resolution="selectedResolution = $event"
      />

      <FundingChartPanel
        :data="fundingChartPanel"
        :exchange="selectedExchange"
        :symbol="selectedSymbol"
        :range="selectedRange"
        :resolution="selectedResolution"
        :start-date="selectedStartDate"
        :end-date="selectedEndDate"
        @update:exchange="handleExchangeUpdate"
        @update:symbol="handleChartSymbolUpdate"
        @update:range="selectedRange = $event"
        @update:resolution="selectedResolution = $event"
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
        :research="currentResearch"
      />
    </template>

    <template v-else>
      <FundingPlatformTradingPanel :exchange="selectedExchange" :symbol="selectedSymbol" />
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
  import FundingPlatformTradingPanel from './components/FundingPlatformTradingPanel.vue';
  import {
    defaultSymbol,
    fundingChartPanel,
    fundingCarryProfiles,
    fundingMarketBoard,
    fundingOrderPanel,
    fundingRangeLabels,
  } from './mock/data';
  import type { FundingExchange, FundingMarketRange, FundingSymbol } from './types';

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
  const selectedRange = ref<FundingMarketRange>('current');
  const selectedResolution = ref<string>(props.selectedResolution);
  const selectedStartDate = ref('2026-05-28');
  const selectedEndDate = ref('2026-06-24');

  const profile = computed(() => fundingCarryProfiles[selectedExchange.value] ?? fundingCarryProfiles.Bybit);
  const currentResearch = computed(() => profile.value.research[selectedSymbol.value] ?? profile.value.research[defaultSymbol]);

  const rangeOptions = computed(() =>
    (Object.keys(fundingRangeLabels) as FundingMarketRange[]).map((value) => ({
      value,
      label: fundingRangeLabels[value],
    })),
  );

  const profileOrderPanel = computed(() => ({
    ...fundingOrderPanel,
    strategyLabel: `${selectedExchange.value} ${selectedSymbol.value}资金费率套利`,
  }));

  function handleChartSymbolUpdate(value: string) {
    selectedSymbol.value = value as FundingSymbol;
  }

  function handleExchangeUpdate(value: FundingExchange) {
    selectedExchange.value = value;
  }

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
