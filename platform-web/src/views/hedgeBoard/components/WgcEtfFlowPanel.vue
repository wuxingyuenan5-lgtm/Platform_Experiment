<script setup lang="ts">
  import { useResearchViewState } from '../composables/researchWorkspace';
  import MacroSeriesChart from '../charts/MacroSeriesChart';

  const period = useResearchViewState('wgc-period', 'Weekly');
</script>
<template>
  <div>
    <label style="padding: 8px; font-size: 12px"
      >频率
      <select v-model="period" aria-label="黄金 ETF 资金流频率"
        ><option value="Weekly">周度</option
        ><option value="Monthly">月度</option></select
      >
    </label>
    <MacroSeriesChart
      :key="period"
      presentation="regional-stack"
      data-domain="commodity"
      :group-id="`wgcEtf${period}`"
    />
  </div>
</template>
