<script setup lang="ts">
  import { ref } from 'vue';
  import MacroSeriesChart from '../charts/MacroSeriesChart';

  const view = ref('composition');
</script>
<template
  ><div
    ><div class="chart-legend"
      ><button :aria-pressed="view === 'composition'" @click="view = 'composition'"
        >主要 8 种稳定币</button
      ><button :aria-pressed="view === 'total'" @click="view = 'total'">总市值</button
      ><a
        href="https://www.coinglass.com/zh/pro/stablecoin"
        target="_blank"
        rel="noopener noreferrer"
        >参考网页 ↗</a
      ></div
    ><MacroSeriesChart
      :key="view"
      data-domain="crypto"
      :group-id="view === 'total' ? 'stablecoins' : 'stablecoinComposition'"
      :years="10" /></div
></template>
