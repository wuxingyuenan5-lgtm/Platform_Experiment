<template>
  <div v-if="broad" class="etf-daily-flow">
    <ChartExpand :title="title">
      <section class="flow-card" aria-label="宽基ETF资金图表与数据表">
        <header
          ><h3>{{ title }}</h3
          ><nav aria-label="资金展示方式">
            <button
              v-for="item in ['图表', '数据表']"
              :key="item"
              :aria-pressed="view === item"
              @click="view = item"
              >{{ item }}</button
            >
          </nav></header
        >
        <div class="controls">
          <label
            >级别选择
            <select v-model="level" aria-label="级别选择"
              ><option value="daily">日度</option
              ><option value="weekly">周度</option
              ><option value="monthly">月度</option></select
            ></label
          >
          <nav aria-label="宽基资金范围选择"
            ><button
              v-for="item in ranges"
              :key="item.days"
              :aria-pressed="range === item.days"
              @click="range = item.days"
              >{{ item.label }}</button
            ></nav
          >
          <fieldset
            ><legend>指数价格走势</legend
            ><label v-for="item in indexChoices" :key="item.key"
              ><input v-model="selected" type="checkbox" :value="item.key" />{{ item.label }}</label
            ></fieldset
          >
          <label class="offset-control" title="正数后移，负数前移；按当前级别的期间数平移指数价格。"
            >指数偏移
            <input
              :value="indexOffset"
              type="number"
              step="1"
              :min="-maxIndexOffset"
              :max="maxIndexOffset"
              :disabled="!selected.length"
              aria-label="指数时间偏移"
              @change="changeOffset"
            />{{ offsetUnit(level) }}
            <span>正数后移，负数前移</span>
          </label>
        </div>
        <p class="scope-note">
          统计范围：{{ broad.cats.length }}类宽基ETF<span v-if="coverage"
            >（{{ coverage.date }}：{{ coverage.covered }} /
            {{ coverage.expected }}只数据完整）</span
          >。
        </p>
        <p v-if="missing" class="notice"
          >所选范围有 {{ missing }} 个期间数据不完整，缺失值及其后的累计值留空。</p
        >
        <div v-show="view === '图表'" ref="plot" class="plot" role="img" :aria-label="title"></div>
        <template v-if="view === '数据表'">
          <div class="table-scroll"
            ><table
              ><thead
                ><tr
                  ><th>交易日／期末</th
                  ><th v-for="category in broad.cats" :key="category">{{ category }}</th
                  ><th>合计</th><th>累计净流入</th
                  ><th v-for="item in selectedIndices" :key="item.key"
                    >{{ item.label }}收盘{{ offsetDescription(effectiveOffset, level) }}</th
                  ></tr
                ></thead
              >
              <tbody
                ><tr v-for="row in tableRows" :key="row.date"
                  ><td :title="`${row.from} 至 ${row.date}`">{{ row.date }}</td
                  ><td
                    v-for="category in broad.cats"
                    :key="category"
                    :style="cellStyle(row.values[category], category)"
                    >{{ format(row.values[category]) }}</td
                  ><td>{{ format(row.total) }}</td
                  ><td>{{ format(row.cumulative) }}</td
                  ><td
                    v-for="item in selectedIndices"
                    :key="item.key"
                    :title="row.priceDate ? `原日期 ${row.priceDate}` : row.date"
                    >{{ format(row.prices[item.key]) }}</td
                  ></tr
                ></tbody
              >
            </table></div
          >
          <div class="pagination"
            ><span>金额：亿元 · 指数：点 · {{ displayPeriods.length }} 个期间</span
            ><button :disabled="page === 1" @click="page--">上一页</button
            ><span>{{ page }} / {{ pages }}</span
            ><button :disabled="page >= pages" @click="page++">下一页</button></div
          >
        </template>
      </section>
    </ChartExpand>
    <FinancingChart
      v-if="!flowOnly"
      title="宽基ETF日度成交额与沪深300"
      :rows="amountRows"
      :lines="amountLines"
      :initial-range="1095"
      note="按当日已上市成员汇总；不完整日期按已取得数据统计，悬停查看覆盖情况。"
    />
  </div>
</template>

<script setup lang="ts">
  import { computed, nextTick, ref, watch, type Ref } from 'vue';
  import type { EChartsOption } from 'echarts';
  import { useECharts } from '@/hooks/web/useECharts';
  import ChartExpand from '../../components/ChartExpand.vue';
  import FinancingChart, { type FinanceLine, type FinanceRow } from './FinancingChart.vue';
  import {
    flowPeriods,
    flowChartOption,
    indexChoices,
    maxIndexOffset,
    offsetDescription,
    offsetFlowPeriods,
    offsetUnit,
    numeric,
    type BroadFlowInput,
    type FlowLevel,
    type IndexPrices,
  } from './etfFlowAnalysis';

  const props = defineProps<{ reference?: Record<string, any>; flowOnly?: boolean }>();
  const broad = computed(() => props.reference?.broadData as BroadFlowInput | undefined);
  const coverage = computed(() => {
    const date = broad.value?.dates.at(-1);
    const groups = date && props.reference?.nativeCoverage?.broad?.[date];
    if (!groups || !broad.value?.cats.every((category) => groups[category])) return null;
    return {
      date,
      expected: broad.value.cats.reduce((sum, category) => sum + groups[category].expected, 0),
      covered: broad.value.cats.reduce((sum, category) => sum + groups[category].covered, 0),
    };
  });
  const indices = computed(() => (props.reference?.indexPrices || {}) as IndexPrices);
  const level = ref<FlowLevel>('daily'),
    range = ref(365),
    view = ref('图表');
  const selected = ref(['hs300']);
  const indexOffset = ref(0);
  const effectiveOffset = computed(() => (selected.value.length ? indexOffset.value : 0));
  function changeOffset(event: Event) {
    const input = event.target as HTMLInputElement;
    if (!input.reportValidity()) return;
    indexOffset.value = input.value === '' ? 0 : input.valueAsNumber;
    input.value = String(indexOffset.value);
  }
  const ranges = [
    { days: 90, label: '3个月' },
    { days: 365, label: '1年' },
    { days: 1095, label: '3年' },
    { days: 0, label: '全部' },
  ];
  const title = computed(
    () =>
      `宽基ETF${{ daily: '日度', weekly: '周度', monthly: '月度' }[level.value]}净流入与累计净流入`,
  );
  const selectedIndices = computed(() =>
    indexChoices.filter((item) => selected.value.includes(item.key)),
  );
  const periods = computed(() =>
    broad.value ? flowPeriods(broad.value, indices.value, level.value, range.value) : [],
  );
  const missing = computed(() => periods.value.filter((r) => r.total == null).length);
  const displayPeriods = computed(() =>
    offsetFlowPeriods(periods.value, effectiveOffset.value, level.value),
  );
  const plot = ref<HTMLDivElement | null>(null);
  const chart = useECharts(plot as Ref<HTMLDivElement>, 'light');
  watch(
    [periods, selected, effectiveOffset, view, plot],
    async () => {
      await nextTick();
      if (!plot.value || !broad.value) return;
      chart.setOptions(
        flowChartOption(
          periods.value,
          broad.value,
          selected.value,
          level.value,
          effectiveOffset.value,
        ) as EChartsOption,
        true,
      );
    },
    { deep: false, immediate: true },
  );
  const page = ref(1),
    pageSize = 25;
  const pages = computed(() => Math.max(1, Math.ceil(displayPeriods.value.length / pageSize)));
  watch([level, range, effectiveOffset], () => (page.value = 1));
  const tableRows = computed(() =>
    [...displayPeriods.value].reverse().slice((page.value - 1) * pageSize, page.value * pageSize),
  );
  const maxima = computed(() =>
    Object.fromEntries(
      (broad.value?.cats || []).map((c) => [
        c,
        Math.max(1, ...periods.value.map((r) => Math.abs(r.values[c] || 0))),
      ]),
    ),
  );
  function cellStyle(value: number | null, category: string) {
    if (!value) return {};
    return {
      backgroundColor: `rgba(${value > 0 ? '217,54,48' : '10,160,110'},${
        0.06 + 0.45 * Math.min(1, Math.abs(value) / maxima.value[category])
      })`,
    };
  }
  const format = (value: unknown) =>
    numeric(value) == null
      ? '—'
      : Number(value).toLocaleString('zh-CN', {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        });
  const amountRows = computed<FinanceRow[]>(() => {
    const daily = props.reference?.broadDailyData;
    if (!daily) return [];
    const prices = new Map((indices.value.hs300?.rows || []).map((r) => [r.date, r.close]));
    return daily.dates.map((date: string, i: number) => ({
      date,
      amount: daily.amount[i],
      hs300: prices.get(date) ?? null,
      qualityNote: daily.qualityNote?.[i] || '',
    }));
  });
  const amountLines: FinanceLine[] = [
    {
      key: 'amount',
      name: '宽基ETF日度成交额合计',
      color: '#637cd0',
      unit: '亿元',
      bar: true,
      stack: 'amount',
    },
    { key: 'hs300', name: '沪深300', color: '#d18a30', unit: '点', right: true },
  ];
</script>

<style scoped>
  .etf-daily-flow {
    min-width: 0;
  }

  .flow-card {
    min-width: 0;
    padding: 16px;
    border: 1px solid #d7e3ee;
    border-radius: 10px;
    background: #fff;
  }

  header,
  .controls,
  nav,
  fieldset,
  .pagination {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }

  header {
    justify-content: space-between;
    margin-bottom: 12px;
    padding-right: 34px;
  }

  h3 {
    margin: 0;
    font-size: 15px;
  }

  button,
  select,
  input[type='number'] {
    padding: 5px 10px;
    border: 1px solid #dbe4ee;
    border-radius: 6px;
    background: #fff;
    color: #40546b;
    font: inherit;
    font-size: 12px;
    cursor: pointer;
  }

  button[aria-pressed='true'] {
    border-color: #a5bfff;
    background: #edf3ff;
    color: #2864ec;
  }

  button:disabled {
    opacity: 0.45;
    cursor: default;
  }

  .controls {
    margin-bottom: 12px;
    font-size: 12px;
    gap: 12px;
  }

  .scope-note {
    margin: 0 0 12px;
    color: #65758a;
    font-size: 12px;
  }

  .offset-control {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  .offset-control input {
    width: 76px;
  }

  .offset-control span {
    color: #65758a;
  }

  fieldset {
    margin: 0;
    padding: 0;
    border: 0;
  }

  legend {
    width: auto;
    margin: 0 8px 0 0;
    float: left;
    font-size: 12px;
  }

  fieldset label {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }

  .plot {
    min-width: 0;
    height: 460px;
  }

  .table-scroll {
    overflow: auto;
  }

  table {
    width: 100%;
    min-width: 1100px;
    border-collapse: collapse;
    font-size: 12px;
    font-variant-numeric: tabular-nums;
  }

  th,
  td {
    padding: 8px;
    border-bottom: 1px solid #e3eaf1;
    text-align: right;
    white-space: nowrap;
  }

  th:first-child,
  td:first-child {
    position: sticky;
    left: 0;
    background: #fff;
    text-align: left;
  }

  th {
    background: #f4f7fb;
  }

  .pagination {
    justify-content: flex-end;
    margin-top: 10px;
    font-size: 12px;
  }

  .notice {
    color: #65758a;
    font-size: 12px;
  }

  @media (max-width: 600px) {
    .flow-card {
      padding: 10px;
    }

    .plot {
      height: 420px;
    }
  }
</style>
