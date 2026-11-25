<script setup lang="ts">
  import { ref } from 'vue';
  import MacroSeriesChart from '../charts/MacroSeriesChart';

  const view = ref('global');
</script>
<template>
  <MacroSeriesChart
    :key="view"
    data-domain="commodity"
    :group-id="view === 'global' ? 'wgcCentralPurchases' : 'wgcPurchases'"
    :presentation="view === 'global' ? 'time' : 'distribution'"
    :bar-series-ids="view === 'global' ? ['wgc_central_bank_quarterly_purchases'] : []"
    :years="20"
  >
    <template #controls>
      <button type="button" :aria-pressed="view === 'global'" @click="view = 'global'"
        >全球季度购金</button
      >
      <button type="button" :aria-pressed="view === 'country'" @click="view = 'country'"
        >分国家</button
      >
    </template>
  </MacroSeriesChart>
</template>
