<script setup lang="ts">
  import { useResearchViewState } from '../composables/researchWorkspace';
  import MacroSeriesChart from '../charts/MacroSeriesChart';

  const period = useResearchViewState('wgc-period', 'Weekly');
</script>
<template>
  <MacroSeriesChart
    :key="period"
    presentation="regional-stack"
    data-domain="commodity"
    :group-id="`wgcEtf${period}`"
  >
    <template #controls>
      <label class="wgc-etf-flow-frequency"
        >频率
        <select v-model="period" aria-label="黄金 ETF 资金流频率"
          ><option value="Weekly">周度</option
          ><option value="Monthly">月度</option></select
        >
      </label>
    </template>
  </MacroSeriesChart>
</template>

<style scoped>
  .wgc-etf-flow-frequency {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding-right: 4px;
    font-size: 12px;
    white-space: nowrap;
  }

  .wgc-etf-flow-frequency select {
    padding: 5px 10px;
    border: 1px solid #dbe4ea;
    border-radius: 7px;
    background: #fff;
    color: inherit;
    font-size: 12px;
    line-height: 18px;
  }
</style>
