<template>
  <FinancingChart
    :title="indexed ? '主题ETF份额走势（首日=100）' : '主题ETF份额走势'"
    :rows="chartData.rows"
    :lines="chartData.lines"
    :range-days="range"
    :axis-names="[indexed ? '首日=100' : '亿份', '']"
    allow-table
    @range="$emit('range', $event)"
  />
</template>
<script setup lang="ts">
  import { computed } from 'vue';
  import FinancingChart from './FinancingChart.vue';
  import { themeChartData, type ThemeFund } from './themeEtfAnalysis';

  const props = defineProps<{ funds: ThemeFund[]; range: number; indexed: boolean }>();
  defineEmits<{ range: [days: number] }>();
  const chartData = computed(() => themeChartData(props.funds, props.range, props.indexed));
</script>
