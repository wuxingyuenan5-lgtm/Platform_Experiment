<template>
  <section class="index-valuation">
    <header
      ><h2>指数估值</h2
      ><div class="valuation-controls">
        <label
          >标的
          <select v-model="indexId" aria-label="标的"
            ><option v-for="item in allCharts" :key="item.id" :value="item.id">{{
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
        <label
          >图表采样
          <select v-model="cadence" aria-label="估值图表采样">
            <option value="observation">原始观察</option
            ><option value="week">每周末次观察</option
            ><option value="month">每月末次观察</option>
          </select>
        </label>
        <label
          >观察日
          <input v-model="asOf" type="date" aria-label="估值观察日期" :max="lastObservation"
        /></label> </div
    ></header>
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
      <div
        ><span>{{ years ? `近${years}年` : '全部历史' }} · {{ metric?.label }}分位</span
        ><strong>{{ statistics.rank == null ? '—' : format(statistics.rank) + '%' }}</strong
        ><small
          >{{ statistics.count }}个有效样本 · {{ statistics.start || '—' }} —
          {{ statistics.end || '—' }}</small
        ></div
      >
      <div
        ><span>历史区间 · 最低 / 中位 / 最高</span
        ><strong
          >{{ format(statistics.min) }} / {{ format(statistics.median) }} /
          {{ format(statistics.max) }}</strong
        ><small
          >20%分位值 {{ format(statistics.p20) }} · 80%分位值 {{ format(statistics.p80) }}</small
        ></div
      >
    </div>
    <div v-if="statistics.rank != null" class="percentile-track" aria-label="历史分位位置"
      ><span :style="{ left: statistics.rank + '%' }"></span
    ></div>
    <p v-if="distributionError" role="alert"
      >{{ distributionError }} <button @click="loadDistribution">重试</button></p
    >
    <p v-if="metric?.description" class="valuation-definition">{{ metric.description }}</p>
    <p v-if="metric?.status === 'error'" role="status">该来源本轮更新失败，保留上次有效历史。</p>
    <WidgetErrorBoundary
      :key="`${selected?.id}:${metric?.id}:${years}:${cadence}:${asOf}`"
      widget-title="估值走势图"
    >
      <SourceSeriesPlot
        v-if="plotSeries.length"
        :key="`${selected?.id}:${metric?.id}:${years}:${cadence}:${asOf}`"
        :state-key="`index-valuation:${selected?.id}:${metric?.id}:${years}:${cadence}:${asOf}`"
        :series="plotSeries"
        :colors="['#3366a3', '#111111']"
      />
    </WidgetErrorBoundary>
    <p v-if="metric && !metric.history.length" role="status">该指标暂无已接通数据。</p>
    <a v-if="metric?.sourceUrl" :href="metric.sourceUrl" target="_blank" rel="noopener noreferrer"
      >{{ metric.source }} ↗</a
    >
    <details class="index-comparison"
      ><summary>指数估值比较</summary
      ><div class="comparison-toolbar"
        ><input v-model="query" aria-label="搜索估值指数" placeholder="名称 / 代码" /><label
          >排序
          <select v-model="sortMetric" aria-label="估值比较排序"
            ><option v-for="column in comparisonColumns" :key="column.id" :value="column.id"
              >{{ column.label }}分位</option
            ></select
          ></label
        ><button :aria-pressed="ascending" @click="ascending = !ascending">{{
          ascending ? '从低到高' : '从高到低'
        }}</button></div
      ><div class="comparison-scroll"
        ><table
          ><thead
            ><tr
              ><th>指数</th
              ><th v-for="column in comparisonColumns" :key="column.id"
                >{{ column.label }} / 历史分位</th
              ></tr
            ></thead
          ><tbody
            ><tr
              v-for="item in comparisonRows"
              :key="item.chart.id"
              :class="{ selected: item.chart.id === selected?.id }"
              ><th
                ><button @click="indexId = item.chart.id"
                  >{{ item.chart.name }}<small>{{ item.chart.id }}</small></button
                ></th
              ><td v-for="cell in item.cells" :key="cell.id"
                ><button
                  :disabled="!cell.stat.latest"
                  @click="chooseMetric(item.chart.id, cell.metricId)"
                  ><strong>{{ format(cell.stat.value) }}{{ cell.unit }}</strong
                  ><span :class="rankClass(cell.stat.rank)">{{
                    cell.stat.rank == null ? '—' : format(cell.stat.rank) + '%'
                  }}</span
                  ><small
                    >{{ cell.stat.latest?.date || '—' }} · n={{ cell.stat.count }}</small
                  ></button
                ></td
              ></tr
            ></tbody
          ></table
        ></div
      ></details
    >
  </section>
</template>
<script setup lang="ts">
  import { computed, nextTick, onBeforeUnmount, ref, shallowRef, watch } from 'vue';
  import { getMarketContext, type MarketMonitor, type MonitorRow } from '@/api/cnMarketMonitor';
  import SourceSeriesPlot from '../charts/SourceSeriesPlot.vue';
  import WidgetErrorBoundary from './WidgetErrorBoundary';
  import type { IndexValuationChart } from '@/api/equityObservatory';
  import type { MacroDashboardSeries } from '@/api/hedgeResearch';
  import {
    valuationStats,
    valuationWindow,
    valuationSample,
    type ValuationCadence,
  } from './indexValuationStats';

  const props = defineProps<{ charts: IndexValuationChart[] }>();
  const distribution = shallowRef<MarketMonitor>();
  const distributionError = ref('');
  const cadence = ref<ValuationCadence>('observation');
  let distributionRequest: AbortController | undefined;
  async function loadDistribution() {
    distributionRequest?.abort();
    const request = new AbortController();
    distributionRequest = request;
    distributionError.value = '';
    try {
      const result = await getMarketContext('valuation', request.signal);
      if (!request.signal.aborted) distribution.value = result;
    } catch {
      if (!request.signal.aborted)
        distributionError.value = '公开PE统计暂不可用，原有估值继续展示。';
    }
  }
  watch(
    () => props.charts.some((c) => c.id === '000300'),
    (ready) => {
      if (ready) loadDistribution();
    },
    { immediate: true },
  );
  onBeforeUnmount(() => distributionRequest?.abort());
  const peFields = [
    ['addTtmPe', '总市值法 PE TTM'],
    ['addLyrPe', '总市值法 PE LYR'],
    ['ttmPe', '等权平均 PE TTM'],
    ['lyrPe', '等权平均 PE LYR'],
    ['middleTtmPe', '中位数 PE TTM'],
    ['middleLyrPe', '中位数 PE LYR'],
  ];
  const allCharts = computed<IndexValuationChart[]>(() =>
    props.charts.map((chart) => {
      const source = distribution.value?.sources['pe_' + chart.id];
      if (!source) return chart;
      const rows = (source.data || []) as MonitorRow[];
      const prices = rows.map((r) => ({ date: r.date, value: r.close ?? null }));
      const metrics = peFields.map(([field, label]) => ({
        id: 'public_' + field,
        label: label + ' · 公开观察',
        unit: '倍',
        history: rows.map((r) => ({ date: r.date, value: r[field] ?? null })),
        prices,
        source: '乐咕乐股',
        sourceUrl: source.sourceUrl,
        status: source.status,
        description:
          '总市值法为总市值除以利润合计；等权平均和中位数按来源剔除亏损、暂停上市及PE大于300的公司。公开历史以月频观察为主，不插值；分位按所选窗口的有效观察本地计算，与来源日频全历史分位不同。',
      }));
      return { ...chart, metrics: [...chart.metrics, ...metrics] };
    }),
  );
  const indexId = ref(''),
    metricId = ref(''),
    years = ref(5);
  const asOf = ref(''),
    query = ref(''),
    sortMetric = ref('pe'),
    ascending = ref(true);
  const lastObservation = computed(
    () =>
      allCharts.value
        .flatMap((c) => c.metrics.flatMap((m) => m.history.map((p) => p.date)))
        .sort()
        .at(-1) || new Date().toISOString().slice(0, 10),
  );
  watch(
    lastObservation,
    (day, previous) => {
      if (!asOf.value || asOf.value === previous) asOf.value = day;
    },
    { immediate: true },
  );
  const selected = computed(
    () => allCharts.value.find((c) => c.id === indexId.value) || allCharts.value[0],
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
  const statistics = computed(() =>
    valuationStats(
      metric.value?.history || [],
      years.value,
      asOf.value || lastObservation.value,
      metric.value?.id === 'dividend',
    ),
  );
  const latest = computed(() => statistics.value.latest);
  const lastPrice = computed(() =>
    (metric.value?.prices || selected.value?.prices || [])
      .filter((p) => p.date <= (asOf.value || lastObservation.value))
      .at(-1),
  );
  const comparisonColumns = computed(() => [
    { id: 'pe', label: 'PE TTM' },
    ...(props.charts.some((c) => c.metrics.some((m) => m.id === 'peLyr'))
      ? [{ id: 'peLyr', label: 'PE LYR' }]
      : []),
    { id: 'pb', label: 'PB' },
    { id: 'dividend', label: '股息率' },
  ]);
  const comparisonRows = computed(() =>
    allCharts.value
      .filter((c) => (c.name + c.id).toLowerCase().includes(query.value.toLowerCase()))
      .map((chart) => ({
        chart,
        cells: comparisonColumns.value.map((col) => {
          const m = chart.metrics.find(
            (m) => m.id === col.id || (col.id === 'pe' && m.id === 'pe-trailing'),
          );
          return {
            id: col.id,
            metricId: m?.id || col.id,
            unit: m?.unit || '',
            stat: valuationStats(
              m?.history || [],
              years.value,
              asOf.value || lastObservation.value,
              col.id === 'dividend',
            ),
          };
        }),
      }))
      .sort((a, b) => {
        const x = a.cells.find((c) => c.id === sortMetric.value)?.stat.rank,
          y = b.cells.find((c) => c.id === sortMetric.value)?.stat.rank;
        return x == null
          ? y == null
            ? 0
            : 1
          : y == null
          ? -1
          : (ascending.value ? 1 : -1) * (x - y);
      }),
  );
  const rankClass = (v: number | null) =>
    v == null ? '' : v < 20 ? 'rank-low' : v > 80 ? 'rank-high' : '';
  async function chooseMetric(index: string, id: string) {
    indexId.value = index;
    await nextTick();
    metricId.value = id;
  }
  const format = (v: unknown) =>
    v == null ? '—' : Number(v).toLocaleString('en-US', { maximumFractionDigits: 2 });
  const plotSeries = computed(() => {
    if (!selected.value || !metric.value) return [];
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
        observations: valuationSample(
          valuationWindow(history, years.value, asOf.value || lastObservation.value),
          cadence.value,
        ),
        frequency: 'source_observation',
      } as MacroDashboardSeries);
    const m = make('valuation', metric.value.label, metric.value.unit, metric.value.history);
    const p = make(
      'index_price',
      selected.value.name,
      '点',
      metric.value.prices || selected.value.prices,
    );
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

  .percentile-track {
    position: relative;
    height: 7px;
    margin: 18px 8px 22px;
    border-radius: 8px;
    background: linear-gradient(to right, #ccece0 0% 20%, #dfe9f6 20% 80%, #f6d8d5 80%);
  }

  .percentile-track > span {
    position: absolute;
    top: -4px;
    width: 3px;
    height: 15px;
    transform: translateX(-50%);
    background: #294b6e;
  }

  .index-comparison {
    margin-top: 20px;
    padding-top: 14px;
    border-top: 1px solid #e1e8f0;
  }

  summary {
    font-weight: 600;
    cursor: pointer;
  }

  .comparison-toolbar {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    align-items: center;
    margin: 14px 0;
  }

  input {
    max-width: 100%;
    padding: 5px 8px;
    border: 1px solid #dbe4ea;
    border-radius: 6px;
    background: transparent;
    font: inherit;
  }

  .comparison-scroll {
    max-height: 530px;
    overflow: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    white-space: nowrap;
  }

  th,
  td {
    padding: 10px;
    border-bottom: 1px solid #e5edf4;
    text-align: right;
  }

  th:first-child {
    text-align: left;
  }

  thead th {
    position: sticky;
    z-index: 1;
    top: 0;
    background: #f3f7fb;
  }

  td button,
  th button {
    display: inline-grid;
    border: 0;
    text-align: inherit;
    gap: 4px;
  }

  td small,
  th small {
    color: #7c8c9d;
    font-size: 10px;
  }

  td span {
    color: #667e97;
  }

  .rank-low {
    color: #07986d;
  }

  .rank-high {
    color: #cc4b46;
  }

  tr.selected {
    background: #f0f5ff;
  }

  @media (max-width: 640px) {
    .valuation-summary {
      grid-template-columns: 1fr;
    }

    .valuation-controls label {
      max-width: 100%;
    }
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
