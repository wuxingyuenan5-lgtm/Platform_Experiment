<script setup lang="ts">
  import { ref } from 'vue';
  import MacroSeriesChart from '../charts/MacroSeriesChart';

  const view = ref('global');
</script>
<template
  ><div
    ><div class="chart-legend"
      ><button :aria-pressed="view === 'global'" @click="view = 'global'">全球季度购金</button
      ><button :aria-pressed="view === 'country'" @click="view = 'country'">分国家</button></div
    ><MacroSeriesChart
      v-if="view === 'global'"
      data-domain="commodity"
      group-id="wgcCentralPurchases"
      :bar-series-ids="['wgc_central_bank_quarterly_purchases']"
      :years="20" /><MacroSeriesChart
      v-else
      data-domain="commodity"
      group-id="wgcPurchases"
      presentation="distribution" /></div
></template>
