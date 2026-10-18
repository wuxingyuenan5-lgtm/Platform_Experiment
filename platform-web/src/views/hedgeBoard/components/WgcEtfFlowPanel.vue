<script setup lang="ts">
  import { ref } from 'vue';
  import MacroSeriesChart from '../charts/MacroSeriesChart';

  const period = ref('Weekly');
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
    <p style="padding: 0 8px; color: #64748b; font-size: 12px"
      >WGC 实物支持黄金 ETF 资金流；全球值为北美、欧洲、亚洲及其他地区合计。正值为净流入。</p
    >
  </div>
</template>
