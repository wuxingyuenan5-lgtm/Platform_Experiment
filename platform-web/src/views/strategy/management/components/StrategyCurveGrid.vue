<template>
  <section class="curve-grid">
    <StrategyCurveCardChart v-for="item in curves" :key="item.title" :item="item" />
  </section>
</template>

<script setup lang="ts">
  import StrategyCurveCardChart from './StrategyCurveCardChart.vue';
  import type { StrategyCurveCard } from '@/data/sample/strategy';

  defineProps<{ curves: StrategyCurveCard[] }>();
</script>

<style scoped lang="less">
  .curve-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
    gap: var(--strategy-space-2);
    align-items: stretch;
  }
  @media (max-width: 1320px) {
    .curve-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
