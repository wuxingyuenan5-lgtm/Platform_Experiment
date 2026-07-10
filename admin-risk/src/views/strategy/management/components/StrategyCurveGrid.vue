<template>
  <section class="curve-grid">
    <StrategyCurveCardChart v-for="item in curves" :key="item.title" :item="item" />
  </section>
</template>

<script setup lang="ts">
  import StrategyCurveCardChart from './StrategyCurveCardChart.vue';
  import type { StrategyCurveCard } from '../types';

  defineProps<{ curves: StrategyCurveCard[] }>();
</script>

<style scoped lang="less">
  .curve-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 16px;
  }
  @media (max-width: 1320px) {
    .curve-grid { grid-template-columns: 1fr; }
  }
</style>
