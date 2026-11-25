<template>
  <section class="timing-radar" aria-label="择时雷达">
    <header class="timing-header">
      <div
        ><h2>择时雷达</h2
        ><span>{{ observationDate || '—' }} · {{ coverage }}/21 项有分数</span></div
      >
      <div class="timing-controls" aria-label="数据视图">
        <button :aria-pressed="mode === 'market'" @click="mode = 'market'">平台计算</button>
        <button :aria-pressed="mode === 'report'" @click="mode = 'report'">研报周度对照</button>
      </div>
    </header>
    <p v-if="error" class="timing-card" role="alert"
      >{{ error }} <button @click="load">重试</button></p
    >
    <p v-if="loading && !payload" class="timing-card" role="status">正在读取择时数据…</p>
    <template v-if="payload">
      <div class="timing-summary">
        <article class="timing-card score-card">
          <h3>综合择时分数</h3>
          <strong :data-tone="tone(overall)">{{ score(overall) }}</strong>
          <span v-if="overall === null">待 21 项同日分数齐全</span>
          <span v-else
            >较上周 {{ signed(overallPrevious === null ? null : overall - overallPrevious) }}</span
          >
        </article>
        <article class="timing-card">
          <h3>六维雷达</h3>
          <div class="timing-summary-chart"
            ><TimingRadarChart :option="radarOption" label="六维择时雷达图"
          /></div>
          <div class="dimension-counts">
            <span v-for="(item, i) in dimensionCurrent" :key="i"
              >{{ payload.dimensions[i] }} {{ item.count }}/{{ item.total }}</span
            >
          </div>
        </article>
        <article class="timing-card">
          <h3>四类分数对比</h3>
          <div class="timing-summary-chart"
            ><TimingRadarChart :option="classOption" label="四类择时分数周度对比"
          /></div>
          <div class="dimension-counts">
            <span v-for="(item, i) in groupCurrent" :key="i"
              >{{ payload.classes[i] }} {{ item.count }}/{{ item.total }}</span
            >
          </div>
        </article>
      </div>
      <section class="timing-card">
        <header class="timing-card-header">
          <h3>21 项因子评分</h3>
          <span v-if="mode === 'report'">国盛证券 · {{ payload.report.published }} 周报</span>
          <label v-else
            >观察日
            <input
              type="date"
              :min="payload.dates[0]"
              :max="payload.dates.at(-1)"
              :value="observationDate"
              @change="pickDate"
          /></label>
        </header>
        <div class="timing-table-scroll">
          <table class="timing-table">
            <thead
              ><tr
                ><th>维度</th><th>因子</th><th>分类</th><th v-if="mode === 'market'">原始读数</th
                ><th>上周 {{ previousDate }}</th
                ><th>当前 {{ observationDate }}</th
                ><th>变化</th></tr
              ></thead
            >
            <tbody>
              <tr
                v-for="(factor, i) in payload.factors"
                :key="factor.key"
                :class="{
                  selected: factor.key === selectedKey,
                  divider: i === 0 || payload.factors[i - 1].dimension !== factor.dimension,
                }"
              >
                <td>{{
                  i === 0 || payload.factors[i - 1].dimension !== factor.dimension
                    ? payload.dimensions[factor.dimension]
                    : ''
                }}</td>
                <th scope="row"
                  ><button
                    :aria-pressed="factor.key === selectedKey"
                    @click="openFactor(factor.key)"
                    >{{ factor.name }}</button
                  ></th
                >
                <td>{{ payload.classes[factor.group] }}</td>
                <td v-if="mode === 'market'">{{
                  reading(factor.values[dayIndex], factor.unit)
                }}</td>
                <td :data-tone="tone(previous[i])">{{ score(previous[i]) }}</td>
                <td :data-tone="tone(current[i])"
                  ><b>{{ score(current[i]) }}</b></td
                >
                <td :data-tone="tone(delta(i))">{{ signed(delta(i)) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
      <section v-if="selected" ref="analysis" class="timing-card analysis-card">
        <header class="timing-card-header">
          <h3>因子时序</h3>
          <div class="timing-controls">
            <label
              >因子
              <select v-model="selectedKey">
                <optgroup v-for="(dimension, i) in payload.dimensions" :key="i" :label="dimension">
                  <option
                    v-for="factor in payload.factors.filter((f) => f.dimension === i)"
                    :key="factor.key"
                    :value="factor.key"
                    >{{ factor.name }}</option
                  >
                </optgroup>
              </select>
            </label>
            <label
              >对照
              <select v-model="benchmark" aria-label="对照标的">
                <option v-for="(name, key) in benchmarks" :key="key" :value="key">{{
                  name
                }}</option>
              </select>
            </label>
          </div>
          <div class="timing-controls" aria-label="时序时间范围">
            <button
              v-for="item in ranges"
              :key="item.value"
              :aria-pressed="range === item.value"
              @click="range = item.value"
              >{{ item.label }}</button
            >
            <button :aria-pressed="showData" @click="showData = !showData">{{
              showData ? '查看图表' : '查看数据'
            }}</button>
            <button class="fullscreen-button" aria-label="切换图表全屏" @click="toggleFullscreen"
              >⛶</button
            >
          </div>
        </header>
        <p class="factor-method"
          >{{ selected.method }} <span>研报第 {{ selected.pages }} 页</span></p
        >
        <p v-if="!selected.values.some((value) => value !== null)" class="factor-missing"
          >待接入 {{ selected.inputs }}</p
        >
        <p v-else-if="selected.scores[dayIndex] == null" class="factor-missing"
          >所选观察日无因子分数，见历史有效区间。</p
        >
        <div v-if="!showData" class="timing-history" :key="selected.key">
          <TimingRadarChart
            :option="trendOption"
            :label="`${selected.name}、${benchmarks[benchmark]}及择时分数历史`"
          />
        </div>
        <div v-else class="timing-history timing-table-scroll">
          <table class="timing-table"
            ><thead
              ><tr
                ><th>日期</th><th>{{ selected.name }}</th
                ><th>择时分数</th><th>{{ benchmarks[benchmark] }}</th></tr
              ></thead
            >
            <tbody
              ><tr v-for="i in tableIndices" :key="i">
                <td>{{ payload.dates[i] }}</td
                ><td>{{ reading(selected.values[i], selected.unit) }}</td>
                <td :data-tone="tone(selected.scores[i])">{{ score(selected.scores[i]) }}</td
                ><td>{{ score(payload.benchmarks[benchmark][i]) }}</td>
              </tr></tbody
            >
          </table>
        </div>
      </section>
    </template>
  </section>
</template>

<script setup lang="ts">
  import { computed, nextTick, onBeforeUnmount, ref, shallowRef, watch } from 'vue';
  import type { EChartsOption } from 'echarts';
  import { researchRequest } from '@/api/hedgeResearch';
  import TimingRadarChart from './TimingRadarChart.vue';

  type Value = number | null;
  type Benchmark = 'benchmark' | 'price' | 'allShare' | 'etf50';
  interface Factor {
    key: string;
    name: string;
    dimension: number;
    group: number;
    unit: string;
    method: string;
    inputs: string;
    pages: string;
    values: Value[];
    scores: Value[];
  }
  interface RadarData {
    dimensions: string[];
    classes: string[];
    dates: string[];
    benchmarks: Record<Benchmark, Value[]>;
    factors: Factor[];
    report: {
      date: string;
      previousDate: string;
      published: string;
      current: number[];
      previous: number[];
    };
  }
  const props = defineProps<{ refreshKey: number }>();
  const emit = defineEmits<{ ready: [] }>();
  const payload = shallowRef<RadarData>();
  const error = ref('');
  const loading = ref(false);
  const mode = ref<'market' | 'report'>('market');
  const selectedKey = ref('priceTrend');
  const chosenDate = ref('');
  const showData = ref(false);
  const range = ref(10);
  const analysis = ref<HTMLElement>();
  const benchmark = ref<Benchmark>('benchmark');
  const benchmarks: Record<Benchmark, string> = {
    benchmark: '中证800全收益',
    price: '中证800价格',
    allShare: '中证全指',
    etf50: '上证50ETF',
  };
  const ranges = [3, 5, 10, 15, 0].map((value) => ({
    value,
    label: value ? `${value}年` : '全部',
  }));
  let request: AbortController | undefined;
  async function load() {
    request?.abort();
    const currentRequest = new AbortController();
    request = currentRequest;
    loading.value = true;
    error.value = '';
    try {
      payload.value = await researchRequest<RadarData>({
        url: '/research/a-share/timing-radar',
        signal: request.signal,
      });
    } catch {
      if (!currentRequest.signal.aborted) error.value = '择时数据读取失败';
    } finally {
      if (request === currentRequest && !currentRequest.signal.aborted) {
        loading.value = false;
        await nextTick();
        emit('ready');
      }
    }
  }
  watch(() => props.refreshKey, load, { immediate: true });
  onBeforeUnmount(() => request?.abort());

  const selected = computed(() =>
    payload.value?.factors.find((factor) => factor.key === selectedKey.value),
  );
  const dayIndex = computed(() => {
    const dates = payload.value?.dates || [];
    return chosenDate.value
      ? dates.findLastIndex((day) => day <= chosenDate.value)
      : dates.length - 1;
  });
  const marketDate = computed(() => payload.value?.dates[dayIndex.value] || '');
  const priorIndex = computed(() => {
    if (!marketDate.value) return -1;
    const date = new Date(`${marketDate.value}T00:00:00Z`);
    date.setUTCDate(date.getUTCDate() - ((date.getUTCDay() + 6) % 7) - 1);
    return payload.value!.dates.findLastIndex((day) => day <= date.toISOString().slice(0, 10));
  });
  const observationDate = computed(() =>
    mode.value === 'report' ? payload.value?.report.date : marketDate.value,
  );
  const previousDate = computed(() =>
    mode.value === 'report'
      ? payload.value?.report.previousDate
      : payload.value?.dates[priorIndex.value],
  );
  const current = computed(() =>
    mode.value === 'report'
      ? payload.value?.report.current || []
      : payload.value?.factors.map((factor) => factor.scores[dayIndex.value] ?? null) || [],
  );
  const previous = computed(() =>
    mode.value === 'report'
      ? payload.value?.report.previous || []
      : payload.value?.factors.map((factor) => factor.scores[priorIndex.value] ?? null) || [],
  );
  const coverage = computed(() => current.value.filter((value) => value !== null).length);
  const mean = (values: number[]) => values.reduce((sum, item) => sum + item, 0) / values.length;
  function aggregates(values: Value[], key: 'dimension' | 'group', count: number) {
    return Array.from({ length: count }, (_, n) => {
      const indices =
        payload.value?.factors.flatMap((factor, i) => (factor[key] === n ? [i] : [])) || [];
      const items = indices.map((i) => values[i]).filter((value): value is number => value != null);
      return {
        value: items.length ? mean(items) : null,
        count: items.length,
        total: indices.length,
      };
    });
  }
  const dimensionCurrent = computed(() => aggregates(current.value, 'dimension', 6));
  const dimensionPrior = computed(() => aggregates(previous.value, 'dimension', 6));
  const groupCurrent = computed(() => aggregates(current.value, 'group', 4));
  const groupPrevious = computed(() => aggregates(previous.value, 'group', 4));
  function total(groups: ReturnType<typeof aggregates>) {
    if (groups.some((x) => x.value === null || x.count !== x.total)) return null;
    return mean(groups.map((x) => x.value!));
  }
  const overall = computed(() => total(groupCurrent.value));
  const overallPrevious = computed(() => total(groupPrevious.value));
  function delta(index: number) {
    const a = current.value[index],
      b = previous.value[index];
    return a == null || b == null ? null : a - b;
  }
  const score = (value: Value | undefined) => (value == null ? '—' : value.toFixed(2));
  const signed = (value: Value) =>
    value == null ? '—' : `${value >= 0.005 ? '+' : ''}${score(value)}`;
  const reading = (value: Value | undefined, unit: string) =>
    value == null ? '—' : `${score(value)} ${unit}`;
  const tone = (value: Value | undefined) =>
    value == null ? '' : value > 0.005 ? 'positive' : value < -0.005 ? 'negative' : '';
  function pickDate(event: Event) {
    chosenDate.value = (event.target as HTMLInputElement).value;
  }
  function openFactor(key: string) {
    selectedKey.value = key;
    analysis.value?.scrollIntoView({ block: 'start', behavior: 'smooth' });
  }
  async function toggleFullscreen() {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await analysis.value?.requestFullscreen();
  }

  const palette = ['#3c6cce', '#b08648', '#9ba9bc'];
  const legend = { top: 1, textStyle: { color: '#6b809a' } };
  const radarOption = computed<EChartsOption>(() => ({
    color: palette,
    legend,
    tooltip: {},
    radar: {
      indicator: (payload.value?.dimensions || []).map((name) => ({ name, min: -1, max: 1 })),
      radius: '63%',
      center: ['50%', '58%'],
      splitNumber: 4,
    },
    series: [
      {
        type: 'radar',
        areaStyle: { opacity: 0.1 },
        data: [
          { name: '当前', value: dimensionCurrent.value.map((item) => item.value ?? '-') },
          { name: '上周', value: dimensionPrior.value.map((item) => item.value ?? '-') },
          {
            name: '中性',
            value: [0, 0, 0, 0, 0, 0],
            symbol: 'none',
            lineStyle: { type: 'dotted' },
            areaStyle: { opacity: 0 },
          },
        ],
      },
    ],
  }));
  const classOption = computed<EChartsOption>(() => ({
    color: palette,
    legend,
    tooltip: { trigger: 'axis' },
    grid: { left: 39, right: 12, top: 42, bottom: 45 },
    xAxis: { type: 'category', data: payload.value?.classes, axisLabel: { interval: 0 } },
    yAxis: { type: 'value', min: -1, max: 1, interval: 0.5 },
    series: [
      { type: 'bar', name: '当前', data: groupCurrent.value.map((item) => item.value ?? '-') },
      { type: 'bar', name: '上周', data: groupPrevious.value.map((item) => item.value ?? '-') },
    ],
  }));
  const rangeStart = computed(() => {
    if (!range.value || !marketDate.value) return 0;
    const start = new Date(`${marketDate.value}T00:00:00Z`);
    start.setUTCFullYear(start.getUTCFullYear() - range.value);
    return Math.max(
      0,
      payload.value!.dates.findIndex((day) => day >= start.toISOString().slice(0, 10)),
    );
  });
  const tableIndices = computed(() =>
    Array.from(
      { length: Math.max(0, dayIndex.value - rangeStart.value + 1) },
      (_, i) => dayIndex.value - i,
    ),
  );
  const trendOption = computed<EChartsOption>(() => {
    const data = payload.value,
      factor = selected.value;
    if (!data || !factor) return {};
    const end = dayIndex.value + 1;
    const anchor = data.benchmarks[benchmark.value]
      .slice(0, end)
      .filter((point): point is number => point !== null);
    const min = Math.min(...anchor),
      max = Math.max(...anchor);
    const benchmarkLine = data.benchmarks[benchmark.value]
      .slice(0, end)
      .map((point) =>
        point == null || !anchor.length
          ? '-'
          : max === min
          ? 0
          : ((point - min) / (max - min)) * 2 - 1,
      );
    return {
      color: ['#a0b2c5', '#214a7b', '#c88a37'],
      legend,
      tooltip: {
        trigger: 'axis',
        valueFormatter: (value) => (typeof value === 'number' ? value.toFixed(2) : String(value)),
      },
      grid: { left: 53, right: 72, top: 57, bottom: 72 },
      xAxis: { type: 'category', data: data.dates.slice(0, end), boundaryGap: false },
      yAxis: [
        { type: 'value', min: -1, max: 1, name: '分数／归一化' },
        { type: 'value', scale: true, name: factor.unit, splitLine: { show: false } },
      ],
      dataZoom: [
        {
          type: 'slider',
          startValue: data.dates[rangeStart.value],
          endValue: data.dates[end - 1],
          bottom: 12,
          height: 24,
        },
        { type: 'inside', zoomOnMouseWheel: 'ctrl' },
      ],
      series: [
        {
          type: 'line',
          name: '择时分数',
          data: factor.scores.slice(0, end).map((v) => v ?? '-'),
          step: 'end',
          showSymbol: false,
          lineStyle: { width: 1 },
          areaStyle: { opacity: 0.22 },
        },
        {
          type: 'line',
          name: benchmarks[benchmark.value],
          data: benchmarkLine,
          showSymbol: false,
          lineStyle: { width: 1.3 },
        },
        {
          type: 'line',
          name: factor.name,
          data: factor.values.slice(0, end).map((v) => v ?? '-'),
          yAxisIndex: 1,
          showSymbol: factor.values.filter((value) => value !== null).length < 10,
          lineStyle: { width: 1.3 },
        },
      ],
    };
  });
</script>

<style scoped lang="less">
  .timing-radar {
    display: grid;
    gap: 12px;
    color: var(--strategy-text, #17324c);
  }

  .timing-header,
  .timing-card-header,
  .timing-controls,
  .dimension-counts {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }

  .timing-header,
  .timing-card-header {
    justify-content: space-between;
  }

  .timing-header h2,
  .timing-card h3 {
    margin: 0;
    font-weight: 650;
  }

  .timing-header h2 {
    font-size: 21px;
  }

  .timing-header span,
  .timing-card-header span,
  .dimension-counts,
  .factor-method span,
  .score-card span {
    color: var(--strategy-muted, #637b94);
    font-size: 12px;
  }

  .timing-card {
    min-width: 0;
    padding: 14px;
    border: 1px solid var(--strategy-border, #d9e4ef);
    border-radius: 10px;
    background: var(--strategy-panel, #fff);
  }

  .timing-summary {
    display: grid;
    grid-template-columns: minmax(150px, 0.55fr) repeat(2, minmax(0, 1.25fr));
    gap: 12px;
  }

  .score-card {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    justify-content: center;
    gap: 8px;
  }

  .score-card strong {
    font-size: 38px;
    font-variant-numeric: tabular-nums;
  }

  .timing-summary-chart {
    height: 246px;
    margin-top: 6px;
  }

  .dimension-counts {
    justify-content: center;
    gap: 5px 11px;
  }

  .timing-controls {
    gap: 5px;
  }

  .timing-controls label {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }

  button,
  select,
  input {
    padding: 4px 8px;
    border: 1px solid var(--strategy-border, #d9e4ef);
    border-radius: 5px;
    background: var(--strategy-panel, #fff);
    color: inherit;
  }

  button[aria-pressed='true'] {
    background: #e8f0ff;
    color: #2756a8;
  }

  .timing-table-scroll {
    max-width: 100%;
    margin-top: 8px;
    overflow: auto;
  }

  .timing-table {
    width: 100%;
    min-width: 650px;
    border-collapse: collapse;
    font-size: 13px;
    font-variant-numeric: tabular-nums;
  }

  .timing-table :is(th, td) {
    padding: 5px 9px;
    border-bottom: 1px solid var(--strategy-border, #e0e9f3);
    text-align: right;
    white-space: nowrap;
  }

  .timing-table :is(th, td):nth-child(-n + 3) {
    text-align: left;
  }

  .timing-table thead {
    position: sticky;
    z-index: 1;
    top: 0;
    background: var(--strategy-panel-alt, #edf3f9);
  }

  .timing-table button {
    padding: 2px 6px;
    border-color: transparent;
    background: transparent;
  }

  .timing-table button:hover {
    text-decoration: underline;
  }

  .timing-table .divider > * {
    border-top: 1px solid var(--strategy-border, #c9d9e8);
  }

  .timing-table .selected {
    background: var(--strategy-panel-alt, #edf3f9);
  }

  [data-tone='positive'] {
    color: #bb384a;
  }

  [data-tone='negative'] {
    color: #087a68;
  }

  .factor-method,
  .factor-missing {
    margin: 8px 0 0;
    font-size: 13px;
  }

  .factor-method span {
    margin-left: 8px;
  }

  .factor-missing {
    color: var(--strategy-muted, #637b94);
  }

  .timing-history {
    min-width: 0;
    height: 400px;
    margin-top: 8px;
  }

  .analysis-card:fullscreen {
    display: flex;
    flex-direction: column;
    padding: 22px;
  }

  .analysis-card:fullscreen .timing-history {
    flex: 1;
    min-height: 0;
  }

  @media (max-width: 1000px) {
    .timing-summary {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .score-card {
      grid-column: 1 / -1;
    }
  }

  @media (max-width: 650px) {
    .timing-summary {
      grid-template-columns: minmax(0, 1fr);
    }
  }
</style>
