<template>
  <header class="spread-analysis-header" data-testid="spread-analysis-workspace-header">
    <div>
      <span>SPREAD RESEARCH</span>
      <h1>跨所价差研究</h1>
    </div>
    <div class="filters">
      <select :value="selectedVenue" @change="$emit('update:selectedVenue', valueOf($event))">
        <option>Bybit</option><option>Binance</option><option>OKX</option>
      </select>
      <input :value="leftLegSymbol" aria-label="左腿标的" @input="$emit('update:leftLegSymbol', valueOf($event))" />
      <input :value="rightLegSymbol" aria-label="右腿标的" @input="$emit('update:rightLegSymbol', valueOf($event))" />
      <select :value="selectedResolution" @change="$emit('update:selectedResolution', valueOf($event))">
        <option>15分钟</option><option>30分钟</option><option>1小时</option><option>4小时</option><option>日线</option>
      </select>
    </div>
  </header>
</template>

<script setup lang="ts">
  defineProps<{ selectedVenue: string; leftLegSymbol: string; rightLegSymbol: string; selectedResolution: string }>();
  defineEmits<{
    (event: 'update:selectedVenue', value: string): void;
    (event: 'update:leftLegSymbol', value: string): void;
    (event: 'update:rightLegSymbol', value: string): void;
    (event: 'update:selectedResolution', value: string): void;
  }>();
  function valueOf(event: Event) { return (event.target as HTMLInputElement | HTMLSelectElement).value; }
</script>

<style scoped lang="less">
  .spread-analysis-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; padding: 18px; border: 1px solid #e1e7ef; border-radius: 14px; background: #fff; }
  header > div:first-child { display: grid; gap: 4px; }
  span { color: #63739b; font-size: 11px; letter-spacing: .16em; }
  h1 { margin: 0; font-size: 24px; }
  .filters { display: flex; flex-wrap: wrap; gap: 8px; }
  select, input { height: 36px; padding: 0 10px; border: 1px solid #dce3eb; border-radius: 8px; background: #fff; }
  input { width: 135px; }
  @media (max-width: 900px) { .spread-analysis-header { flex-direction: column; align-items: stretch; } }
</style>
