<template>
  <section
    class="valuation-research"
    :class="{ 'scenario-only': scenarioContext }"
    :aria-label="scenarioContext ? '盈利 × PE 情景矩阵' : '估值研究'"
  >
    <template v-if="!scenarioContext">
      <header
        ><div
          ><h2>估值研究 <small>新增</small></h2
          ><p>历史位置 · 相对溢价 · 盈利与估值情景</p></div
        >
        <label
          >研究截止日 <input v-model="asOf" type="date" aria-label="研究截止日" :max="latestDate"
        /></label>
      </header>
      <p class="note"
        >各项显示实际观察日；历史为来源最新修订版本，按日期回看不代表当时已知。分位越高表示数值越高，股息率与估值倍数的方向不同。</p
      >
      <div class="controls"
        ><label
          >历史定位指标
          <select v-model="key" aria-label="历史定位指标"
            ><option value="pe">历史 PE</option
            ><option value="pb">PB</option
            ><option value="cape">CAPE</option
            ><option value="dividend">股息率</option></select
          ></label
        ></div
      >
      <div class="scroll"
        ><table
          ><caption>一、历史定位：比较多个窗口，识别结论是否依赖起点</caption>
          <thead
            ><tr
              ><th>指数 / 实际口径</th><th>最新值 / 日期</th
              ><th v-for="y in windows" :key="y">{{ y }}年窗口分位 / 样本</th
              ><th>来源 / 状态</th></tr
            ></thead
          >
          <tbody
            ><tr v-for="row in rows" :key="row.chart.id"
              ><th
                ><button @click="selectedId = row.chart.id">{{ row.chart.name }}</button
                ><small>{{ row.metric?.label || '未接入此指标' }}</small></th
              >
              <td
                >{{ fmt(row.stats[0].value) }} {{ row.metric?.unit
                }}<small>{{ row.stats[0].latest?.date || '—' }}</small></td
              >
              <td v-for="(s, i) in row.stats" :key="i"
                >{{ s.rank == null ? '样本不足' : fmt(s.rank) + '%'
                }}<small>n={{ s.count }} · {{ s.start || '—' }} 起</small></td
              >
              <td
                ><a
                  v-if="row.metric?.sourceUrl"
                  :href="row.metric.sourceUrl"
                  target="_blank"
                  rel="noopener noreferrer"
                  >{{ row.metric.source || '来源' }} ↗</a
                ><small>{{ status(row.metric?.status) }}</small></td
              >
            </tr></tbody
          ></table
        ></div
      >
      <p class="note">分位按窗口内有效样本计算，实际起点和样本数见表格。</p>
      <div class="controls"
        ><label
          >研究指数
          <select v-model="selectedId" aria-label="研究指数"
            ><option v-for="c in charts" :key="c.id" :value="c.id">{{ c.name }}</option></select
          ></label
        ></div
      >
      <article
        ><h3>二、相对估值：{{ selected?.name }} / {{ benchmark?.name }}</h3>
        <div class="controls"
          ><label
            >比较指数
            <select v-model="benchmarkId" aria-label="比较指数"
              ><option v-for="c in comparisonChoices" :key="c.id" :value="c.id"
                >{{ c.name }} · {{ c.count }}个共同有效样本</option
              ></select
            ></label
          >
          <label
            >相对估值窗口
            <select v-model.number="relativeYears" aria-label="相对估值窗口"
              ><option v-for="y in windows" :key="y" :value="y">{{ y }}年</option></select
            ></label
          ></div
        >
        <div class="cards"
          ><div
            >同日{{ key === 'dividend' ? '股息率' : '估值' }}比值<strong
              >{{ fmt(relativeStats.value) }} ×</strong
            ><small>{{ relativeStats.latest?.date || '无同日样本' }}</small></div
          ><div
            >比值历史分位<strong>{{
              relativeStats.rank == null ? '—' : fmt(relativeStats.rank) + '%'
            }}</strong
            ><small
              >n={{ relativeStats.count }} · {{ relativeStats.start || '—' }} —
              {{ relativeStats.end || '—' }}</small
            ></div
          ><div
            >历史比值中位数<strong>{{ fmt(relativeStats.median) }} ×</strong
            ><small>分子、分母均须为正值</small></div
          ></div
        >
        <WidgetErrorBoundary
          v-if="relativeStats.count > 1"
          :key="relativeChartKey"
          widget-title="相对估值历史"
        >
          <SourceSeriesPlot
            :key="relativeChartKey"
            :state-key="relativeChartKey"
            :series="relativeSeries"
            :colors="['#315e91']"
          />
        </WidgetErrorBoundary>
        <p v-else role="status"
          >共同有效观察不足两点，暂不绘制历史曲线。可查看比较指数选项中的共同样本数。</p
        >
        <p class="note"
          >仅匹配两指数同日的原始观察，不前向填充。{{ researchMetric(selected, key)?.label || '—' }}
          /
          {{
            researchMetric(benchmark, key)?.label || '—'
          }}；各指数成分、行业权重和来源算法可能不同，比值不等于可套利价差，也不据此生成买卖信号。</p
        >
      </article>
    </template>
    <article class="scenario">
      <header class="scenario-header">
        <h3>{{ scenarioContext ? '盈利 × PE 情景矩阵' : '三、盈利 × PE 情景矩阵' }}</h3>
        <div class="scenario-anchor">
          <strong>{{ selected?.name }}</strong>
          <span
            >{{ anchor.metric?.label || '历史 PE' }} <b>{{ fmt(anchor.pe) }} 倍</b></span
          >
          <span
            >指数 <b>{{ fmt(anchor.price) }} 点</b></span
          >
          <time v-if="anchor.date" :datetime="anchor.date">{{ anchor.date }}</time>
        </div>
      </header>

      <div class="scenario-layout">
        <section class="scenario-reference" aria-label="历史 PE 参照">
          <div class="scenario-reference-header">
            <label>
              历史 PE 参照
              <select v-model.number="referenceYears" aria-label="历史PE参照窗口">
                <option v-for="y in windows" :key="y" :value="y">{{ y }}年</option>
                <option v-if="scenarioContext" :value="0">全部</option>
              </select>
            </label>
            <span v-if="referenceStats.count" :title="referencePeriod"
              >n={{ referenceStats.count }}</span
            >
          </div>
          <table v-if="referenceStats.rank != null && anchor.pe != null" class="reference-table">
            <thead>
              <tr>
                <th scope="col">分位</th>
                <th scope="col">代入 PE</th>
                <th scope="col" title="盈利不变时的隐含价格涨跌幅">价格变化</th>
                <th scope="col" title="维持基准价格所需的盈利变化">保本盈利变化</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in references" :key="r.label">
                <th scope="row">{{ r.label }}</th>
                <td>
                  <button
                    class="reference-pe"
                    :aria-label="`代入${r.label} PE ${fmt(r.pe)} 倍`"
                    :disabled="r.pe == null || r.pe < 0.1 || r.pe > 500"
                    @click="useReference(r.pe)"
                    >{{ fmt(r.pe) }} 倍</button
                  >
                </td>
                <td>{{ fmt(scenarioReturn(0, r.pe!, anchor.pe)) }}%</td>
                <td>{{ fmt(earningsToOffset(anchor.pe, r.pe)) }}%</td>
              </tr>
            </tbody>
          </table>
          <p v-else class="scenario-message" role="status">暂无有效历史 PE 参照。</p>
        </section>

        <div class="scenario-main">
          <div class="scenario-controls">
            <label>
              盈利变化（%）
              <input
                v-model.number="earnings"
                type="number"
                min="-90"
                max="100"
                step="5"
                aria-label="中性盈利变化"
              />
            </label>
            <label>
              目标 PE（倍）
              <input
                v-model.number="target"
                type="number"
                min="0.1"
                max="500"
                step="0.5"
                aria-label="目标PE"
              />
            </label>
            <button @click="resetScenario">恢复基准</button>
          </div>

          <div v-if="validScenario" class="matrix-scroll">
            <table class="matrix-table" aria-label="盈利与估值敏感性">
              <thead>
                <tr>
                  <th scope="col">盈利变化 / 目标 PE</th>
                  <th v-for="p in targets" :key="p" scope="col">{{ fmt(p) }} 倍</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(e, i) in earningsCases" :key="e">
                  <th scope="row">{{ fmt(e) }}%</th>
                  <td
                    v-for="(p, j) in targets"
                    :key="p"
                    :class="{ 'scenario-center': i === 1 && j === 1 }"
                  >
                    {{ fmt(scenarioReturn(e, p, anchor.pe!)) }}%
                    <span v-if="anchor.price != null" class="matrix-points">
                      {{ fmt(anchor.price * (1 + scenarioReturn(e, p, anchor.pe!)! / 100)) }} 点
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else class="scenario-message" role="status"
            >请输入 −90% 至 100% 的盈利变化和 0.1 至 500 倍的目标 PE，并选择有有效基准 PE
            的指数。</p
          >

          <div v-if="validScenario" class="scenario-results" aria-live="polite">
            <span
              >情景涨跌幅 <b>{{ fmt(centerReturn) }}%</b></span
            >
            <span
              >情景点位 <b>{{ fmt(centerPrice) }}</b></span
            >
            <span>
              保本盈利变化
              <button
                v-if="scenarioContext && breakEven != null && breakEven >= -90 && breakEven <= 100"
                class="reference-pe"
                aria-label="代入保本盈利变化"
                title="代入保本盈利变化"
                @click="applyBreakEven"
                >{{ fmt(breakEven) }}%</button
              >
              <b v-else>{{ fmt(breakEven) }}%</b>
            </span>
            <span
              class="scenario-unit"
              title="目标 PE 按 0.8、1、1.2 倍取值，盈利变化按中值上下各 10 个百分点取值。"
              >价格收益 · 不含分红、费用或汇率</span
            >
          </div>
        </div>
      </div>
    </article>
  </section>
</template>
<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import type { IndexValuationChart } from '@/api/equityObservatory';
  import SourceSeriesPlot from '../charts/SourceSeriesPlot.vue';
  import WidgetErrorBoundary from './WidgetErrorBoundary';
  import type { MacroDashboardSeries } from '@/api/hedgeResearch';
  import { valuationStats } from './indexValuationStats';
  import {
    earningsToOffset,
    researchMetric,
    researchStats,
    relativeValuation,
    scenarioReturn,
    valuationAnchor,
  } from './valuationResearch';

  const props = defineProps<{
    charts: IndexValuationChart[];
    windows: number[];
    scenarioContext?: { indexId?: string; asOf: string; metricId?: string; years: number };
  }>();
  const key = ref('pe'),
    selectedId = ref(''),
    benchmarkId = ref(''),
    asOf = ref('');
  const referenceYears = ref(5);
  const relativeYears = ref(5),
    earnings = ref<number | string>(0),
    target = ref<number | string>(0);
  const latestDate = computed(
    () =>
      props.charts
        .flatMap((c) => c.metrics.flatMap((m) => m.history.map((p) => p.date)))
        .sort()
        .at(-1) || new Date().toLocaleDateString('sv-SE', { timeZone: 'Asia/Shanghai' }),
  );
  watch(
    latestDate,
    (day, old) => {
      if (!asOf.value || asOf.value === old) asOf.value = day;
    },
    { immediate: true },
  );
  const selected = computed(
    () =>
      props.charts.find((c) => c.id === (props.scenarioContext?.indexId ?? selectedId.value)) ||
      props.charts[0],
  );
  const cutoff = computed(() => props.scenarioContext?.asOf || asOf.value || latestDate.value);
  watch(
    () => props.scenarioContext?.years,
    (years) => {
      if (years != null) referenceYears.value = years;
    },
    { immediate: true },
  );
  const benchmark = computed(
    () =>
      props.charts.find((c) => c.id === benchmarkId.value && c.id !== selected.value?.id) ||
      props.charts.find((c) => c.id !== selected.value?.id),
  );
  watch(
    () => selected.value?.id,
    (id) => {
      selectedId.value = id || '';
      benchmarkId.value = benchmark.value?.id || '';
    },
    { immediate: true },
  );
  const rows = computed(() =>
    props.charts.map((chart) => {
      const metric = researchMetric(chart, key.value);
      return {
        chart,
        metric,
        stats: props.windows.map((y) => researchStats(metric, y, asOf.value || latestDate.value)),
      };
    }),
  );
  const relativeRows = computed(() =>
    relativeValuation(
      researchMetric(selected.value, key.value),
      researchMetric(benchmark.value, key.value),
      relativeYears.value,
      asOf.value || latestDate.value,
    ),
  );
  const relativeStats = computed(() =>
    valuationStats(relativeRows.value, relativeYears.value, asOf.value || latestDate.value),
  );
  const comparisonChoices = computed(() =>
    props.charts
      .filter((c) => c.id !== selected.value?.id)
      .map((c) => ({
        id: c.id,
        name: c.name,
        count: relativeValuation(
          researchMetric(selected.value, key.value),
          researchMetric(c, key.value),
          relativeYears.value,
          asOf.value || latestDate.value,
        ).filter((p) => p.value != null).length,
      })),
  );
  const relativeChartKey = computed(
    () =>
      `valuation-relative:${selected.value?.id}:${benchmark.value?.id}:${key.value}:${relativeYears.value}:${asOf.value}`,
  );
  const relativeSeries = computed(
    () =>
      [
        {
          seriesId: 'valuation-relative',
          label: `${selected.value?.name} / ${benchmark.value?.name} · ${
            researchMetric(selected.value, key.value)?.label || key.value
          }`,
          unit: '倍',
          frequency: 'source_observation',
          observations: relativeRows.value,
        },
      ] as MacroDashboardSeries[],
  );
  const anchor = computed(() =>
    valuationAnchor(
      selected.value,
      cutoff.value,
      props.scenarioContext?.metricId === 'official_pe' ? 'official_pe' : 'pe',
    ),
  );
  const referenceStats = computed(() =>
    researchStats(anchor.value.metric, referenceYears.value, cutoff.value),
  );
  const referencePeriod = computed(
    () => `${referenceStats.value.start} 至 ${referenceStats.value.end}`,
  );
  const references = computed(() => [
    { label: '20% 分位', pe: referenceStats.value.p20 },
    { label: '中位数', pe: referenceStats.value.median },
    { label: '80% 分位', pe: referenceStats.value.p80 },
  ]);
  function useReference(pe: number | null) {
    if (pe != null && pe >= 0.1 && pe <= 500) {
      target.value = Number(pe.toFixed(6));
      earnings.value = 0;
    }
  }
  function resetScenario() {
    earnings.value = 0;
    target.value = anchor.value.pe == null ? 0 : Number(anchor.value.pe.toFixed(6));
  }
  watch(
    [
      () => selected.value?.id,
      () => anchor.value.date,
      () => anchor.value.metric?.id,
      () => anchor.value.pe,
    ],
    resetScenario,
    { immediate: true },
  );
  const validScenario = computed(
    () =>
      anchor.value.pe != null &&
      typeof earnings.value === 'number' &&
      Number.isFinite(earnings.value) &&
      earnings.value >= -90 &&
      earnings.value <= 100 &&
      typeof target.value === 'number' &&
      Number.isFinite(target.value) &&
      target.value >= 0.1 &&
      target.value <= 500,
  );
  const targets = computed(() => [0.8, 1, 1.2].map((x) => x * Number(target.value)));
  const earningsCases = computed(() => [-10, 0, 10].map((x) => x + Number(earnings.value)));
  const centerReturn = computed(() =>
    validScenario.value
      ? scenarioReturn(Number(earnings.value), Number(target.value), anchor.value.pe!)
      : null,
  );
  const centerPrice = computed(() =>
    anchor.value.price != null && centerReturn.value != null
      ? anchor.value.price * (1 + centerReturn.value / 100)
      : null,
  );
  const breakEven = computed(() => earningsToOffset(anchor.value.pe, Number(target.value)));
  function applyBreakEven() {
    if (breakEven.value != null && breakEven.value >= -90 && breakEven.value <= 100) {
      earnings.value = Number(breakEven.value.toFixed(6));
    }
  }
  const fmt = (v: unknown) =>
    v == null || !Number.isFinite(Number(v))
      ? '—'
      : Number(v).toLocaleString('zh-CN', { maximumFractionDigits: 2 });
  const status = (s?: string) =>
    ({
      ready: '来源可用',
      stale: '更新滞后',
      error: '更新失败',
      degraded: '数据受限',
      no_data: '暂无数据',
    }[s || 'no_data'] || s);
</script>
<style scoped>
  .valuation-research {
    min-width: 0;
    margin-top: 24px;
    padding: 20px;
    border: 1px solid #ccd9e8;
    border-top: 3px solid #315e91;
    border-radius: 12px;
    background: var(--strategy-surface, #fff);
  }

  .scenario-only {
    margin-top: 0;
    padding: 14px 16px;
    border-top-width: 1px;
  }

  .scenario-only article {
    margin-top: 0;
    padding-top: 0;
    border-top: 0;
  }

  .scenario-center {
    background: #eaf2ff;
    font-weight: 600;
  }

  .scenario-header {
    margin-bottom: 12px;
  }

  .scenario-header h3 {
    margin: 0;
  }

  .scenario-anchor,
  .scenario-controls,
  .scenario-reference-header,
  .scenario-results {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    font-size: 12px;
    gap: 6px 12px;
  }

  .scenario-anchor,
  .scenario-results {
    color: #536981;
  }

  .scenario-anchor strong {
    display: inline;
    margin: 0;
    font-size: 12px;
  }

  .scenario-anchor b,
  .scenario-anchor strong,
  .scenario-results b {
    color: #15334f;
  }

  .scenario-layout {
    display: grid;
    grid-template-columns: minmax(300px, 1fr) minmax(0, 2.4fr);
    gap: 12px;
    align-items: start;
  }

  .scenario-reference,
  .scenario-main {
    min-width: 0;
    border: 1px solid #e0e9f2;
    border-radius: 8px;
  }

  .scenario-reference-header,
  .scenario-controls,
  .scenario-results {
    padding: 7px 10px;
  }

  .scenario-reference-header {
    justify-content: space-between;
    color: #536981;
  }

  .scenario-reference-header label {
    color: #15334f;
    font-weight: 600;
  }

  .scenario-reference-header select {
    font-weight: 400;
  }

  .scenario input,
  .scenario select,
  .scenario button {
    padding: 4px 7px;
    background: var(--strategy-surface, #fff);
  }

  .scenario input[type='number'] {
    width: 96px;
    min-width: 0;
  }

  .scenario table {
    font-variant-numeric: tabular-nums;
  }

  .scenario th,
  .scenario td {
    padding: 7px 9px;
    text-align: center;
  }

  .scenario th:first-child {
    text-align: left;
  }

  .reference-table tbody tr:last-child > * {
    border-bottom: 0;
  }

  .scenario .reference-pe {
    padding: 2px 6px;
    border-color: #d7e4f6;
    background: #f1f6ff;
    color: #1c54a3;
    font-weight: 600;
  }

  .scenario button:enabled:hover {
    border-color: #aac4e6;
    background: #eaf2ff;
  }

  .scenario button:disabled {
    opacity: 0.55;
    cursor: default;
  }

  .matrix-scroll {
    overflow-x: auto;
  }

  .matrix-points {
    margin-left: 5px;
    color: #536981;
    font-size: 11px;
    font-weight: 400;
  }

  .scenario-unit {
    margin-left: auto;
    font-size: 11px;
  }

  .scenario-message {
    margin: 8px 10px;
    color: #536981;
    font-size: 12px;
  }

  @media (max-width: 950px) {
    .scenario-layout {
      grid-template-columns: minmax(0, 1fr);
    }
  }

  @media (max-width: 540px) {
    .scenario-unit {
      margin-left: 0;
    }
  }

  header,
  .controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  h2 {
    margin: 0;
    font-size: 19px;
  }

  h2 small {
    display: inline;
    padding: 3px 8px;
    border-radius: 4px;
    background: #eaf2ff;
    color: #315e91;
    font-size: 11px;
  }

  h3 {
    font-size: 16px;
  }

  header p,
  .note,
  small {
    color: #64748b;
    font-size: 12px;
  }

  .note {
    line-height: 1.8;
  }

  .controls {
    justify-content: flex-start;
    margin: 16px 0;
  }

  label {
    display: inline-flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }

  input,
  select,
  button {
    max-width: 100%;
    padding: 6px 8px;
    border: 1px solid #dbe4ea;
    border-radius: 5px;
    background: transparent;
    font: inherit;
  }

  input[type='number'] {
    width: 100px;
  }

  button {
    cursor: pointer;
  }

  .scroll {
    max-height: 560px;
    overflow: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    white-space: nowrap;
  }

  caption {
    padding: 10px 0;
    color: #475569;
    text-align: left;
  }

  th,
  td {
    padding: 12px;
    border-bottom: 1px solid #e5edf4;
    text-align: right;
  }

  th:first-child {
    text-align: left;
  }

  thead th {
    position: sticky;
    top: 0;
    background: #f3f7fb;
  }

  small {
    display: block;
    margin-top: 5px;
  }

  article {
    margin-top: 22px;
    padding-top: 8px;
    border-top: 1px solid #e5edf4;
  }

  .cards {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }

  .cards > div {
    padding: 14px;
    background: #f6f8fc;
    font-size: 12px;
  }

  strong {
    display: block;
    margin: 8px 0;
    font-size: 23px;
  }

  @media (max-width: 640px) {
    .valuation-research {
      padding: 12px;
    }

    .cards {
      grid-template-columns: 1fr;
    }
  }
</style>
