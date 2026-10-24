<template>
  <section class="index-valuation">
    <header
      ><h2>指数估值</h2
      ><div class="valuation-controls">
        <label
          >标的
          <select v-model="indexId" aria-label="标的"
            ><option v-for="item in charts" :key="item.id" :value="item.id">{{
              item.name
            }}</option></select
          ></label
        >
        <label
          >指标
          <select v-model="metricId" aria-label="指标"
            ><option v-for="item in selected?.metrics || []" :key="item.id" :value="item.id"
              >{{ item.label }}{{ item.history.length ? '' : ' · 暂无数据' }}</option
            ></select
          ></label
        >
        <button
          v-for="n in [3, 5, 10, 0]"
          :key="n"
          :aria-pressed="years === n"
          @click="years = n"
          >{{ n ? `${n}年` : '全部' }}</button
        >
      </div></header
    >
    <div class="valuation-summary">
      <div
        ><span>{{ metric?.label }}</span
        ><strong>{{ format(latest?.value) }} {{ metric?.unit }}</strong
        ><small>{{ latest?.date || '暂无已接通数据' }}</small></div
      >
      <div
        ><span>{{ selected?.name }} · 指数收盘</span
        ><strong>{{ format(lastPrice?.value) }} 点</strong
        ><small>{{ lastPrice?.date || '暂无已接通数据' }}</small></div
      >
    </div>
    <SourceSeriesPlot
      v-if="plotSeries.length"
      :key="`${selected?.id}:${metric?.id}:${years}`"
      :series="plotSeries"
      :colors="['#3366a3', '#111111']"
    />
    <p v-if="metric && !metric.history.length" role="status">该指标暂无已接通数据。</p>
    <a v-if="metric?.sourceUrl" :href="metric.sourceUrl" target="_blank" rel="noopener noreferrer"
      >{{ metric.source }} ↗</a
    >
  </section>
</template>
<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import SourceSeriesPlot from '../charts/SourceSeriesPlot.vue';
  import type { IndexValuationChart } from '@/api/equityObservatory';
  import type { MacroDashboardSeries } from '@/api/hedgeResearch';

  const props = defineProps<{ charts: IndexValuationChart[] }>();
  const indexId = ref(''),
    metricId = ref(''),
    years = ref(5);
  const selected = computed(
    () => props.charts.find((c) => c.id === indexId.value) || props.charts[0],
  );
  const metric = computed(
    () =>
      selected.value?.metrics.find((m) => m.id === metricId.value) || selected.value?.metrics[0],
  );
  watch(
    () => selected.value?.id,
    () => {
      metricId.value = selected.value?.metrics[0]?.id || '';
    },
    { immediate: true },
  );
  watch(
    () => props.charts,
    () => {
      if (!indexId.value) indexId.value = props.charts[0]?.id || '';
    },
    { immediate: true },
  );
  const latest = computed(() => metric.value?.history.at(-1));
  const lastPrice = computed(() => selected.value?.prices.at(-1));
  const format = (v: unknown) =>
    v == null ? '—' : Number(v).toLocaleString('en-US', { maximumFractionDigits: 2 });
  const plotSeries = computed(() => {
    if (!selected.value || !metric.value) return [];
    const cutoff = years.value ? Date.now() - years.value * 366 * 86400000 : -Infinity;
    const make = (
      id: string,
      label: string,
      unit: string,
      history: Array<{ date: string; value: string | number | null }>,
    ) =>
      ({
        seriesId: id,
        label,
        unit,
        observations: history.filter((r) => Date.parse(r.date) >= cutoff),
        frequency: 'source_observation',
      } as MacroDashboardSeries);
    const m = make('valuation', metric.value.label, metric.value.unit, metric.value.history);
    const p = make('index_price', selected.value.name, '点', selected.value.prices);
    // Keep a stable palette even when the valuation source has no observations.
    return [m, p];
  });
</script>
<style scoped>
  .index-valuation {
    padding: 18px;
    border: 1px solid var(--strategy-border, #dbe4ea);
    border-radius: 12px;
    background: var(--strategy-surface, #fff);
  }

  header {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 18px;
    gap: 16px;
  }

  h2 {
    margin: 0;
    font-size: 18px;
  }

  .valuation-controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }

  button,
  select {
    padding: 5px 8px;
    border: 1px solid #dbe4ea;
    border-radius: 6px;
    background: transparent;
    font: inherit;
  }

  button[aria-pressed='true'] {
    background: #eaf2ff;
    color: #165dff;
  }

  .valuation-summary {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .valuation-summary > div {
    display: grid;
    padding: 12px;
    border-radius: 8px;
    background: var(--strategy-surface-muted, #f6f8fc);
    gap: 6px;
  }

  .valuation-summary span,
  .valuation-summary small {
    color: #64748b;
    font-size: 12px;
  }

  .valuation-summary strong {
    font-size: 19px;
  }

  a {
    font-size: 12px;
  }
</style>
