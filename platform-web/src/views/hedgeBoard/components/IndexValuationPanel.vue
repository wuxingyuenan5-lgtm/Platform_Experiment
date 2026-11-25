<template>
  <IndexValuationGroupTable
    v-if="alwaysExpanded"
    :group="coreGroup"
    :charts="chartsById"
    :as-of="asOf || lastObservation"
    :selected-id="selected?.id"
    @select="chooseMetric"
  />
  <component
    :is="alwaysExpanded ? ChartExpand : 'div'"
    :title="alwaysExpanded ? '指数估值走势' : undefined"
  >
    <section class="index-valuation" :class="{ 'index-valuation--trend': alwaysExpanded }">
      <header
        ><h2>{{ alwaysExpanded ? '指数估值走势' : '指数估值' }}</h2
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
            v-for="n in rangeOptions"
            :key="n"
            :aria-pressed="years === n"
            @click="years = n"
            >{{ n ? `${n}年` : '全部' }}</button
          >
          <label v-if="alwaysExpanded">
            级别选择
            <select v-model="chartCadence" aria-label="级别选择">
              <option value="observation" :disabled="monthlySeries">日度</option>
              <option value="week" :disabled="monthlySeries">周度</option>
              <option value="month">月度</option>
            </select>
          </label>
          <label v-else
            >图表采样
            <select v-model="cadence" aria-label="估值图表采样">
              <option value="observation">原始观察</option
              ><option value="week">每周末次观察</option
              ><option value="month">每月末次观察</option>
            </select>
          </label>
          <label v-if="!alwaysExpanded"
            >观察日
            <input v-model="asOf" type="date" aria-label="估值观察日期" :max="lastObservation"
          /></label> </div
      ></header>
      <template v-if="!alwaysExpanded">
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
              >20%分位值 {{ format(statistics.p20) }} · 80%分位值
              {{ format(statistics.p80) }}</small
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
        <p v-if="metric?.status === 'error'" role="status"
          >该来源本轮更新失败，保留上次有效历史。</p
        >
      </template>
      <div :class="{ 'valuation-trend-grid': alwaysExpanded }">
        <div class="valuation-chart">
          <WidgetErrorBoundary
            :key="`${selected?.id}:${metric?.id}:${years}:${chartCadence}:${asOf}`"
            widget-title="估值走势图"
          >
            <FinancingChart
              v-if="alwaysExpanded && plotSeries.length"
              class="valuation-trend-plot"
              title="指数估值走势"
              :rows="standardRows"
              :lines="standardLines"
              :range-days="0"
              embedded
              hide-ranges
              independent-dates
              allow-table
            />
            <SourceSeriesPlot
              v-else-if="plotSeries.length"
              :key="`${selected?.id}:${metric?.id}:${years}:${cadence}:${asOf}`"
              :state-key="`index-valuation:${selected?.id}:${metric?.id}:${years}:${cadence}:${asOf}`"
              :series="plotSeries"
              :colors="['#3366a3', '#111111']"
              :pick-date="charts.some((c) => c.id === '000300')"
              @pick="asOf = $event"
            />
          </WidgetErrorBoundary>
          <p v-if="!alwaysExpanded && metric && !metric.history.length" role="status">
            该指标暂无已接通数据。
          </p>
          <a
            v-if="!alwaysExpanded && metric?.sourceUrl"
            :href="metric.sourceUrl"
            target="_blank"
            rel="noopener noreferrer"
            >{{ metric.source }} ↗</a
          >
        </div>
        <aside v-if="alwaysExpanded" class="valuation-statistics" aria-label="估值统计">
          <div class="statistics-heading">
            <h3>估值统计</h3>
            <span>{{ years ? `近${years}年` : '全部历史' }}</span>
          </div>
          <dl class="statistics-primary">
            <div>
              <dt :title="metric?.source">当前值</dt>
              <dd>
                <strong>{{ format(statistics.value) }}</strong>
                <small v-if="statistics.value != null">{{ metric?.unit }}</small>
                <time v-if="latest" :datetime="latest.date">{{ latest.date }}</time>
              </dd>
            </div>
            <div>
              <dt>历史分位</dt>
              <dd>
                <strong>{{ statistics.rank == null ? '—' : format(statistics.rank) + '%' }}</strong>
                <div
                  v-if="statistics.rank != null"
                  class="percentile-track"
                  aria-label="历史分位位置"
                >
                  <span :style="{ left: statistics.rank + '%' }"></span>
                </div>
              </dd>
            </div>
          </dl>
          <dl class="statistics-quantiles">
            <div v-for="[label, value] in quantiles" :key="label">
              <dt>{{ label }}</dt
              ><dd>{{ format(value) }}</dd>
            </div>
          </dl>
          <dl class="statistics-context">
            <div
              ><dt>较历史中位数</dt><dd>{{ vsMedian }}</dd></div
            >
            <div>
              <dt>历史均值</dt>
              <dd
                >{{ format(statistics.mean) }} {{ statistics.mean != null ? metric?.unit : '' }}</dd
              >
            </div>
            <div>
              <dt>历史标准差</dt>
              <dd>
                {{ format(statistics.standardDeviation) }}
                {{
                  statistics.standardDeviation != null
                    ? metric?.unit === '%'
                      ? '个百分点'
                      : metric?.unit
                    : ''
                }}
              </dd>
            </div>
            <div>
              <dt>距历史均值</dt>
              <dd>{{ signedStandardScore }}</dd>
            </div>
            <div>
              <dt>有效样本</dt>
              <dd
                >{{ statistics.count.toLocaleString('zh-CN')
                }}{{ monthlySeries ? ' 个月' : ' 个' }}</dd
              >
            </div>
          </dl>
          <p v-if="statistics.start" class="statistics-coverage"
            >{{ statistics.start }} 至 {{ statistics.end }}</p
          >
          <p
            v-if="metric?.status === 'stale' || metric?.status === 'error'"
            class="statistics-coverage"
            role="status"
            >数据待更新</p
          >
        </aside>
      </div>
      <details v-if="!alwaysExpanded" class="index-comparison" :open="initialComparisonOpen">
        <summary>指数估值比较</summary>
        <div class="comparison-toolbar">
          <input v-model="query" aria-label="搜索估值指数" placeholder="名称 / 代码" />
          <label>
            排序
            <select v-model="sortMetric" aria-label="估值比较排序">
              <option v-for="column in comparisonColumns" :key="column.id" :value="column.id"
                >{{ column.label }}分位</option
              >
            </select>
          </label>
          <button :aria-pressed="ascending" @click="ascending = !ascending">{{
            ascending ? '从低到高' : '从高到低'
          }}</button>
        </div>
        <div class="comparison-scroll">
          <table>
            <thead>
              <tr>
                <th>指数</th>
                <th v-for="column in comparisonColumns" :key="column.id"
                  >{{ column.label }} / 历史分位</th
                >
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in comparisonRows"
                :key="item.chart.id"
                :class="{ selected: item.chart.id === selected?.id }"
              >
                <th>
                  <button @click="indexId = item.chart.id"
                    >{{ item.chart.name }}<small>{{ item.chart.id }}</small></button
                  >
                </th>
                <td v-for="cell in item.cells" :key="cell.id">
                  <button
                    :disabled="!cell.stat.latest"
                    @click="chooseMetric(item.chart.id, cell.metricId)"
                  >
                    <strong>{{ format(cell.stat.value) }}{{ cell.unit }}</strong>
                    <span :class="rankClass(cell.stat.rank)">{{
                      cell.stat.rank == null ? '—' : format(cell.stat.rank) + '%'
                    }}</span>
                    <small>{{ cell.stat.latest?.date || '—' }} · n={{ cell.stat.count }}</small>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </details>
    </section>
  </component>
  <VisibleChart v-if="alwaysExpanded">
    <section class="valuation-below-book" aria-label="破净比例">
      <MarketContextPanel
        section="breadth"
        breadth-part="belowBook"
        :below-book-ranges="rangeOptions"
        :refresh-key="refreshKey"
      />
    </section>
  </VisibleChart>
  <VisibleChart v-if="alwaysExpanded">
    <MarketContextPanel section="macroValue" :refresh-key="refreshKey" />
  </VisibleChart>
  <VisibleChart v-if="alwaysExpanded" class="valuation-context">
    <MarketContextPanel section="risk" :refresh-key="refreshKey" />
  </VisibleChart>
  <ValuationResearchPanel
    :charts="allCharts"
    :windows="historyWindows"
    :scenario-context="
      alwaysExpanded
        ? {
            indexId: selected?.id,
            asOf: asOf || lastObservation,
            metricId: metric?.id,
            years,
          }
        : undefined
    "
  />
  <template v-if="alwaysExpanded && !hideStyleGroups">
    <IndexValuationGroupTable
      v-for="group in otherGroups"
      :key="group.name"
      :group="group"
      :charts="chartsById"
      :as-of="asOf || lastObservation"
      :selected-id="selected?.id"
      @select="chooseMetric"
    />
  </template>
</template>
<script setup lang="ts">
  import {
    inject,
    computed,
    defineAsyncComponent,
    nextTick,
    onBeforeUnmount,
    ref,
    shallowRef,
    watch,
  } from 'vue';
  import { getMarketContext, type MarketMonitor, type MonitorRow } from '@/api/cnMarketMonitor';
  import SourceSeriesPlot from '../charts/SourceSeriesPlot.vue';
  import FinancingChart, {
    type FinanceLine,
    type FinanceRow,
  } from '../aShare/components/FinancingChart.vue';
  import ValuationResearchPanel from './ValuationResearchPanel.vue';
  import IndexValuationGroupTable from './IndexValuationGroupTable.vue';
  import ChartExpand from './ChartExpand.vue';
  import VisibleChart from './VisibleChart';
  import { observationGroups } from './indexValuationSnapshot';
  import WidgetErrorBoundary from './WidgetErrorBoundary';
  import type { IndexValuationChart } from '@/api/equityObservatory';
  import type { MacroDashboardSeries } from '@/api/hedgeResearch';
  import {
    DEFAULT_RESEARCH_HISTORY_YEARS,
    RESEARCH_HISTORY_YEARS,
    valuationStats,
    valuationWindow,
    valuationSample,
    type ValuationCadence,
  } from './indexValuationStats';

  const alwaysExpanded = inject('themeResearchAlwaysExpanded', false);
  const [coreGroup, ...otherGroups] = observationGroups;
  const props = defineProps<{
    charts: IndexValuationChart[];
    hideStyleGroups?: boolean;
    selection?: { index: string; metric?: string };
    initialComparisonOpen?: boolean;
    refreshKey?: number;
  }>();
  const MarketContextPanel = defineAsyncComponent(
    () => import('../aShare/components/MarketContextPanel.vue'),
  );
  const historyWindows = computed(() =>
    alwaysExpanded || props.charts.some((chart) => chart.id === '000300')
      ? RESEARCH_HISTORY_YEARS.filter((years) => years !== 0)
      : [3, 5, 10],
  );
  const rangeOptions = computed(() => [...historyWindows.value, 0]);
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
  const valuationLabels: Record<string, string> = {
    pe: 'PE TTM',
    official_pe: 'PE TTM（指数官方口径）',
    peLyr: 'PE LYR',
    pb: 'PB MRQ',
    ps: 'PS TTM',
    pcf: 'PCF TTM',
    dividend: '股息率 TTM',
  };
  const allCharts = computed<IndexValuationChart[]>(() =>
    props.charts.map((chart) => {
      const baseMetrics = alwaysExpanded
        ? chart.metrics.map((metric) => ({
            ...metric,
            label: valuationLabels[metric.id] || metric.label,
          }))
        : chart.metrics;
      const source = distribution.value?.sources['pe_' + chart.id];
      if (!source) return { ...chart, metrics: baseMetrics };
      const rows = (source.data || []) as MonitorRow[];
      const prices = rows.map((r) => ({ date: r.date, value: r.close ?? null }));
      const metrics = peFields.map(([field, label]) => ({
        id: 'public_' + field,
        label: alwaysExpanded ? label : label + ' · 公开观察',
        unit: '倍',
        history: rows.map((r) => ({ date: r.date, value: r[field] ?? null })),
        prices,
        source: '乐咕乐股',
        sourceUrl: source.sourceUrl,
        status: source.status,
        description:
          '总市值法为总市值除以利润合计；等权平均和中位数按来源剔除亏损、暂停上市及PE大于300的公司。公开历史以月频观察为主，不插值；分位按所选窗口的有效观察本地计算，与来源日频全历史分位不同。',
      }));
      return { ...chart, metrics: [...baseMetrics, ...metrics] };
    }),
  );
  const indexId = ref(''),
    metricId = ref(''),
    years = ref<number>(alwaysExpanded ? DEFAULT_RESEARCH_HISTORY_YEARS : 5);
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
  const monthlySeries = computed(() => alwaysExpanded && metric.value?.rankFrequency === 'month');
  const chartCadence = computed<ValuationCadence>({
    get: () => (monthlySeries.value ? 'month' : cadence.value),
    set: (level) => (cadence.value = level),
  });
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
      metric.value?.rankFrequency,
    ),
  );
  const latest = computed(() => statistics.value.latest);
  const quantiles = computed(() => {
    const { min, p20, median, p80, max } = statistics.value;
    return [
      ['最低', min],
      ['20%分位', p20],
      ['中位数', median],
      ['80%分位', p80],
      ['最高', max],
    ] as const;
  });
  const vsMedian = computed(() => {
    const { value, median } = statistics.value;
    if (
      value == null ||
      (metric.value?.id === 'dividend' ? value < 0 : value <= 0) ||
      median == null ||
      median <= 0
    )
      return '—';
    return (value / median - 1).toLocaleString('zh-CN', {
      style: 'percent',
      signDisplay: 'exceptZero',
      maximumFractionDigits: 2,
    });
  });
  const signedStandardScore = computed(() => {
    const score = statistics.value.standardScore;
    if (score == null) return '—';
    return (
      score.toLocaleString('zh-CN', { signDisplay: 'exceptZero', maximumFractionDigits: 2 }) + ' σ'
    );
  });
  const lastPrice = computed(() =>
    (metric.value?.prices || selected.value?.prices || [])
      .filter((p) => p.date <= (asOf.value || lastObservation.value))
      .at(-1),
  );
  const chartsById = computed(() => new Map(allCharts.value.map((chart) => [chart.id, chart])));
  const comparisonColumns = computed(() => [
    { id: 'pe', label: 'PE TTM' },
    ...(props.charts.some((c) => c.metrics.some((m) => m.id === 'peLyr'))
      ? [{ id: 'peLyr', label: 'PE LYR' }]
      : []),
    { id: 'pb', label: 'PB' },
    { id: 'dividend', label: '股息率' },
  ]);
  const comparisonRows = computed(() => {
    if (alwaysExpanded) return [];
    return allCharts.value
      .filter((chart) => (chart.name + chart.id).toLowerCase().includes(query.value.toLowerCase()))
      .map((chart) => ({
        chart,
        cells: comparisonColumns.value.map((column) => {
          const metric = chart.metrics.find(
            (item) => item.id === column.id || (column.id === 'pe' && item.id === 'pe-trailing'),
          );
          return {
            id: column.id,
            metricId: metric?.id || column.id,
            unit: metric?.unit || '',
            stat: valuationStats(
              metric?.history || [],
              years.value,
              asOf.value || lastObservation.value,
              column.id === 'dividend',
            ),
          };
        }),
      }))
      .sort((a, b) => {
        const x = a.cells.find((cell) => cell.id === sortMetric.value)?.stat.rank;
        const y = b.cells.find((cell) => cell.id === sortMetric.value)?.stat.rank;
        return x == null
          ? y == null
            ? 0
            : 1
          : y == null
          ? -1
          : (ascending.value ? 1 : -1) * (x - y);
      });
  });
  const rankClass = (v: number | null) =>
    v == null ? '' : v < 20 ? 'rank-low' : v > 80 ? 'rank-high' : '';
  async function chooseMetric(index: string, id?: string) {
    indexId.value = index;
    if (id) {
      await nextTick();
      metricId.value = id;
    }
  }
  watch(
    () => props.selection,
    (selection) => {
      if (selection) void chooseMetric(selection.index, selection.metric);
    },
    { immediate: true },
  );
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
          chartCadence.value,
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
  const standardLines = computed<FinanceLine[]>(() =>
    plotSeries.value
      .filter((series) => series.observations.some((row) => row.value != null))
      .map((series) => ({
        key: series.seriesId,
        name: series.seriesId === 'index_price' ? `${series.label}收盘` : series.label,
        unit: series.unit || '',
        color: series.seriesId === 'index_price' ? '#c2852b' : '#3366a3',
        right: series.seriesId === 'index_price',
      })),
  );
  const standardRows = computed<FinanceRow[]>(() => {
    const rows = new Map<string, FinanceRow>();
    for (const series of plotSeries.value) {
      if (!standardLines.value.some((line) => line.key === series.seriesId)) continue;
      for (const point of series.observations) {
        const row = rows.get(point.date) || { date: point.date };
        row[series.seriesId] = point.value;
        rows.set(point.date, row);
      }
    }
    return [...rows.values()].sort((a, b) => a.date.localeCompare(b.date));
  });
</script>
<style scoped>
  .valuation-below-book {
    min-width: 0;
    padding: 14px;
    border: 1px solid var(--strategy-border, #d9e3ee);
    border-radius: 12px;
    background: var(--strategy-surface, #fff);
  }

  .valuation-context + .valuation-research {
    margin-top: 8px;
  }

  .index-valuation {
    min-width: 0;
    padding: 18px;
    border: 1px solid var(--strategy-border, #dbe4ea);
    border-radius: 12px;
    background: var(--strategy-surface, #fff);
  }

  .index-valuation--trend {
    border-radius: 14px;
    border-color: #d7e3ee;
    background: linear-gradient(#fff, #f4f9fc);
  }

  .index-valuation--trend > header {
    padding-right: 42px;
  }

  .valuation-trend-plot {
    --valuation-data-height: 326px;

    min-width: 0;
  }

  .chart-expand :deep(.chart-expand__surface:modal .valuation-trend-plot) {
    --valuation-data-height: calc(max(360px, 100dvh - 220px) - 54px);
  }

  .valuation-trend-plot :deep(.financing-chart > header) {
    justify-content: flex-end;
    padding-right: 0;
  }

  .valuation-trend-plot :deep(.data-scroll) {
    width: 100%;
    height: var(--valuation-data-height);
    overflow: auto;
  }

  .valuation-trend-plot :deep(.data-scroll thead) {
    position: sticky;
    z-index: 1;
    top: 0;
  }

  .valuation-trend-grid {
    display: grid;
    grid-template-columns: minmax(0, 5fr) minmax(260px, 2fr);
    align-items: start;
    gap: 18px;
  }

  .valuation-trend-grid .valuation-chart,
  .valuation-trend-plot :deep(.financing-chart) {
    margin: 0;
  }

  .valuation-statistics {
    min-width: 0;
    padding: 14px;
    border: 1px solid #dbe5ed;
    border-radius: 10px;
    background: #fff;
    font-variant-numeric: tabular-nums;
  }

  .statistics-heading,
  .statistics-context > div {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 8px;
  }

  .statistics-heading h3 {
    margin: 0;
    font-size: 15px;
  }

  .valuation-statistics dl,
  .valuation-statistics dd {
    margin: 0;
  }

  .statistics-heading span,
  .valuation-statistics dt,
  .valuation-statistics time,
  .statistics-coverage {
    color: #526880;
    font-size: 12px;
  }

  .valuation-statistics .statistics-primary,
  .valuation-statistics .statistics-quantiles {
    display: grid;
    gap: 8px;
    margin: 12px 0;
  }

  .statistics-primary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .statistics-primary > div {
    padding: 9px 10px;
    border-radius: 7px;
    background: #f1f5f9;
  }

  .statistics-primary strong {
    font-size: 20px;
  }

  .statistics-primary small {
    margin-left: 4px;
  }

  .statistics-primary time {
    display: block;
  }

  .valuation-statistics .percentile-track {
    height: 5px;
    margin: 6px 3px;
  }

  .valuation-statistics .percentile-track > span {
    top: -2px;
    height: 9px;
  }

  .statistics-quantiles {
    grid-template-columns: repeat(5, minmax(0, 1fr));
    text-align: center;
  }

  .statistics-quantiles dd,
  .statistics-context dd {
    font-weight: 600;
  }

  .statistics-context {
    display: grid;
    padding-top: 8px;
    border-top: 1px solid #e7edf3;
    gap: 4px;
  }

  .statistics-coverage {
    margin: 6px 0 0;
  }

  header {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: flex-start;
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

  .valuation-chart {
    min-width: 0;
    margin-top: 14px;
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

  @media (max-width: 980px) {
    .valuation-trend-grid {
      grid-template-columns: minmax(0, 1fr);
    }
  }

  @media (max-width: 640px) {
    .valuation-summary {
      grid-template-columns: 1fr;
    }

    .valuation-controls label {
      max-width: 100%;
    }

    .index-valuation--trend > header {
      padding-right: 0;
    }

    .index-valuation--trend h2 {
      padding-right: 38px;
    }

    .index-valuation--trend .valuation-controls label {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      white-space: nowrap;
    }

    .index-valuation--trend .valuation-controls select {
      min-width: 0;
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
