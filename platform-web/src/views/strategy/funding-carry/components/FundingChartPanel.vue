<template>
  <section class="funding-chart-panel" data-testid="funding-chart-panel">
    <header>
      <div><span>资金费率路径</span><h2>{{ exchange }} · {{ symbol }}</h2></div>
      <div class="date-filters">
        <input type="date" :value="startDate" @input="$emit('update:startDate', valueOf($event))" />
        <span>至</span>
        <input type="date" :value="endDate" @input="$emit('update:endDate', valueOf($event))" />
      </div>
    </header>
    <div class="chart" role="img" :aria-label="`${symbol} 资金费率样例图表`">
      <svg v-for="(seriesItem, index) in series" :key="seriesItem.label" viewBox="0 0 640 180" preserveAspectRatio="none">
        <polyline :points="toPoints(seriesItem.values)" fill="none" :class="`series-${index}`" stroke-width="3" />
      </svg>
    </div>
    <footer>
      <span v-for="(seriesItem, index) in series" :key="seriesItem.label"><i :class="`series-${index}`"></i>{{ seriesItem.label }}</span>
      <em>{{ range }} · {{ resolution }} · 非实时</em>
    </footer>
  </section>
</template>

<script setup lang="ts">
  defineProps<{
    series: Array<{ label: string; values: number[] }>;
    exchange: string;
    symbol: string;
    range: string;
    resolution: string;
    startDate: string;
    endDate: string;
  }>();

  defineEmits<{
    (event: 'update:startDate', value: string): void;
    (event: 'update:endDate', value: string): void;
  }>();

  function valueOf(event: Event) {
    return (event.target as HTMLInputElement).value;
  }

  function toPoints(values: number[]): string {
    const max = Math.max(...values);
    const min = Math.min(...values);
    const range = Math.max(max - min, 1);
    return values.map((value, index) => `${((index / Math.max(values.length - 1, 1)) * 640).toFixed(1)},${(160 - ((value - min) / range) * 130).toFixed(1)}`).join(' ');
  }
</script>

<style scoped lang="less">
  .funding-chart-panel { display: grid; gap: 14px; padding: 18px; border: 1px solid #e1e7ef; border-radius: 14px; background: #fff; }
  header, footer { display: flex; align-items: center; justify-content: space-between; gap: 14px; }
  header > div:first-child { display: grid; gap: 4px; }
  header span, footer { color: #738094; font-size: 12px; }
  h2 { margin: 0; font-size: 18px; }
  .date-filters { display: flex; align-items: center; gap: 7px; }
  input { height: 34px; padding: 0 8px; border: 1px solid #dce3eb; border-radius: 8px; }
  .chart { position: relative; height: 220px; border-radius: 12px; background: linear-gradient(to bottom, transparent 24%, #edf1f5 25%, transparent 26%) 0 0 / 100% 55px, #fafbfd; }
  svg { position: absolute; inset: 18px 12px; width: calc(100% - 24px); height: calc(100% - 36px); }
  polyline.series-0, i.series-0 { stroke: #4878bd; background: #4878bd; }
  polyline.series-1, i.series-1 { stroke: #2f9d76; background: #2f9d76; }
  polyline.series-2, i.series-2 { stroke: #c88a35; background: #c88a35; }
  footer { flex-wrap: wrap; }
  footer span { display: inline-flex; align-items: center; gap: 5px; }
  footer i { width: 10px; height: 3px; }
  footer em { margin-left: auto; font-style: normal; }
  @media (max-width: 680px) { header { flex-direction: column; align-items: stretch; } .date-filters { flex-wrap: wrap; } }
</style>
