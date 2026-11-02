<template>
  <section class="monitor" aria-label="市场监测">
    <header
      ><div><h2>市场监测</h2><p>股息 · 仓位 · 风格 · 盈利 · 交易热度</p></div></header
    >
    <nav aria-label="监测分类"
      ><button
        v-for="t in tabs"
        :key="t.key"
        :aria-pressed="tab === t.key"
        :class="{ active: tab === t.key }"
        @click="tab = t.key"
        >{{ t.name }}</button
      ></nav
    >
    <p v-if="loading && !contextSection && tab !== 'style'" role="status">正在读取市场监测…</p>
    <p v-if="error && !contextSection && tab !== 'style'" role="alert"
      >{{ error }} <button @click="load">重试</button></p
    >
    <MarketContextPanel v-if="contextSection" :section="contextSection" :refresh-key="refreshKey" />
    <template v-if="tab !== 'style' && !contextSection && data">
      <div class="source"
        ><span>{{ sourceDate }}</span
        ><a :href="source?.sourceUrl" target="_blank" rel="noopener noreferrer">来源 ↗</a></div
      >
      <p v-if="source?.status === 'error'" class="notice">来源本轮更新失败，保留上次有效数据。</p>
    </template>
    <template v-if="tab === 'dividend'">
      <div class="cards"
        ><button
          v-for="r in items('dividend')"
          :key="r.code"
          :class="{ active: dividend === r.code }"
          @click="dividend = r.code"
          ><span>{{ r.name }}</span
          ><strong>{{ fmt(last(r.history)?.value) }}%</strong
          ><small>{{ last(r.history)?.date }}</small></button
        ></div
      >
      <FinancingChart
        v-if="selectedDividend"
        :key="dividend"
        :title="`${selectedDividend.name} · 股息率`"
        :rows="selectedDividend.history || []"
        :lines="dividendLines"
      />
      <p v-if="dividendWarnings.length" class="notice"
        >来源异常待复核：{{
          dividendWarnings.join('、')
        }}
        出现单日大幅变化并于次日恢复；图中保留原值。</p
      >
      <p class="definition">板块整体股息率；具体宽基指数股息率可在“估值”中切换查看。</p>
    </template>
    <template v-else-if="tab === 'fund'">
      <div class="controls"
        ><label
          >基金类型
          <select v-model="fund"
            ><option value="stock">股票型</option
            ><option value="pingheng">平衡混合型</option
            ><option value="linghuo">灵活配置型</option></select
          ></label
        ><a href="#/hedge-board/a-share?view=funds">查看公募定期披露持仓 ↗</a></div
      >
      <p class="definition"
        >估算股票仓位，与基金定期报告披露仓位分开展示。来源页面标注停止更新，以下以实际观测日期为准。</p
      >
      <FinancingChart
        v-if="rows('fund_' + fund).length"
        :key="fund"
        :title="`${fundNames[fund]} · 估算仓位`"
        :rows="rows('fund_' + fund)"
        :lines="[
          { key: 'value', name: '估算股票仓位', color: '#2864ec', unit: '%' },
          { key: 'close', name: '沪深300', color: '#171717', unit: '点', right: true },
        ]"
      />
    </template>
    <template v-else-if="tab === 'style'">
      <p v-if="styleError" role="alert"
        >{{ styleError }} <button @click="loadStyles">重试</button></p
      >
      <EquityStylePanel
        v-if="themes"
        market="cn"
        :data="themes.styles"
        :benchmark="themes.benchmark?.name || '沪深300'"
      />
      <p v-else-if="!styleError" role="status">正在读取风格数据…</p>
    </template>
    <template v-else-if="tab === 'growth'">
      <div class="controls"
        ><label
          >景气指标
          <select v-model="metric"
            ><option v-for="(name, key) in metrics" :key="key" :value="key">{{
              name
            }}</option></select
          ></label
        ><label>行业筛选 <input v-model="query" placeholder="输入行业名称" /></label
      ></div>
      <FinancingChart
        v-if="rows('growth').length"
        :key="metric"
        :title="`全A · ${metrics[metric]}中位数`"
        :rows="rows('growth')"
        :lines="[{ key: metric, name: metrics[metric], color: '#2864ec', unit: '%' }]"
      />
      <div class="table-scroll"
        ><table
          ><thead
            ><tr
              ><th>申万一级行业</th><th>{{ growthItems[0]?.date || '本期' }}</th
              ><th>{{ growthItems[0]?.previousDate || '上期' }}</th
              ><th><button @click="growthSort = !growthSort">同比变化（pp） ↕</button></th></tr
            ></thead
          ><tbody
            ><tr v-for="r in growthItems" :key="r.code"
              ><th>{{ r.name }}</th
              ><td :class="tone(r.value)">{{ fmt(r.value) }}%</td><td>{{ fmt(r.previous) }}%</td
              ><td :class="tone(r.change)">{{ fmt(r.change) }}</td></tr
            ></tbody
          ></table
        ></div
      >
      <p class="definition"
        >财报同比增速的中位数；变化列为本期与上期同比增速之差（百分点），不代表单季环比增速。</p
      >
    </template>
    <template v-else-if="tab === 'crowding'">
      <div class="controls"
        ><label
          >行业
          <select v-model="industry"
            ><option v-for="r in items('industry')" :key="r.code" :value="r.code">{{
              r.name
            }}</option></select
          ></label
        ><label
          >观察维度
          <select v-model="heatMetric"
            ><option value="turnover">等权换手率分位</option
            ><option value="amount">成交额占比分位</option></select
          ></label
        ></div
      >
      <FinancingChart
        v-if="selectedIndustry"
        :key="industry"
        :title="`${selectedIndustry.name} · 交易拥挤度`"
        :rows="selectedIndustry.history || []"
        :lines="[
          { key: 'turnover', name: '等权换手率分位', color: '#2864ec', unit: '%' },
          { key: 'amount', name: '成交额占比分位', color: '#e6aa20', unit: '%' },
        ]"
      />
      <div class="table-scroll"
        ><table class="heatmap"
          ><thead
            ><tr
              ><th>行业 / 日期</th><th v-for="d in heatDates" :key="d">{{ d.slice(5) }}</th></tr
            ></thead
          ><tbody
            ><tr v-for="r in items('industry')" :key="r.code"
              ><th
                ><button @click="industry = r.code">{{ r.name }}</button></th
              ><td v-for="d in heatDates" :key="d" :style="heatStyle(heatValue(r, d))">{{
                fmt(heatValue(r, d), 0)
              }}</td></tr
            ></tbody
          ></table
        ></div
      >
      <details
        ><summary>全A交易集中度历史</summary
        ><p class="definition"
          >公开来源最近有效值：{{ lastValidCongestion?.date || '—' }}；其后缺值保留为空。</p
        ><FinancingChart
          v-if="rows('congestion').length"
          title="全A · 交易集中度"
          :rows="rows('congestion')"
          :lines="[
            { key: 'value', name: '成交额集中度', color: '#2864ec', unit: '%' },
            { key: 'close', name: '上证指数', color: '#171717', unit: '点', right: true },
          ]"
      /></details>
    </template>
    <p v-if="data && tab !== 'style' && !contextSection && !source?.data?.length" class="notice"
      >当前来源暂无有效数据，其他分类可继续查看。</p
    >
  </section>
</template>
<script setup lang="ts">
  import { computed, onBeforeUnmount, ref, watch } from 'vue';
  import {
    getMarketMonitor,
    type MarketMonitor,
    type MonitorItem,
    type MonitorRow,
    type MonitorValue,
    MarketContextSection,
  } from '@/api/cnMarketMonitor';
  import { getEquityObservatory, type EquityThemes } from '@/api/equityObservatory';
  import FinancingChart from './FinancingChart.vue';
  import EquityStylePanel from '../../components/EquityStylePanel.vue';
  import MarketContextPanel from './MarketContextPanel.vue';

  const props = defineProps<{ refreshKey?: number }>();
  const emit = defineEmits<{ (e: 'ready'): void }>();
  const tabs = [
    { key: 'dividend', name: '股息率' },
    { key: 'fund', name: '基金仓位' },
    { key: 'style', name: '风格跟踪' },
    { key: 'growth', name: '行业景气度' },
    { key: 'crowding', name: '交易拥挤度' },
    { key: 'risk', name: '股债性价比' },
    { key: 'breadth', name: '市场宽度' },
    { key: 'macroValue', name: '总市值与GDP' },
  ];
  const tab = ref('dividend'),
    dividend = ref('shangzheng'),
    fund = ref('stock'),
    industry = ref('801080.SI');
  const contextSection = computed(() =>
    ['risk', 'breadth', 'macroValue'].includes(tab.value)
      ? (tab.value as MarketContextSection)
      : null,
  );
  const metrics: Record<string, string> = {
    netProfitYoy: '净利润同比',
    orYoy: '营业收入同比',
    opYoy: '营业利润同比',
    trYoy: '营业总收入同比',
    ebtYoy: '利润总额同比',
    roeYoy: 'ROE同比增长率',
  };
  const fundNames: Record<string, string> = {
    stock: '股票型基金',
    pingheng: '平衡混合型基金',
    linghuo: '灵活配置型基金',
  };
  const metric = ref('netProfitYoy'),
    query = ref(''),
    growthSort = ref(true),
    heatMetric = ref('turnover');
  const data = ref<MarketMonitor>(),
    themes = ref<EquityThemes>(),
    error = ref(''),
    styleError = ref(''),
    loading = ref(false);
  let controller: AbortController | undefined;
  let styleController: AbortController | undefined;
  const rows = (key: string) => (data.value?.sources[key]?.data || []) as MonitorRow[];
  const items = (key: string) => (data.value?.sources[key]?.data || []) as MonitorItem[];
  const last = (history?: MonitorRow[]) => history?.at(-1);
  const selectedDividend = computed(() => items('dividend').find((r) => r.code === dividend.value));
  const dividendLines = computed(() => [
    { key: 'value', name: '股息率 TTM', color: '#2864ec', unit: '%' },
    ...(selectedDividend.value?.history?.some((r) => r.close != null)
      ? [{ key: 'close', name: '指数收盘', color: '#171717', unit: '点', right: true }]
      : []),
  ]);
  const dividendWarnings = computed(() => {
    const history = selectedDividend.value?.history || [];
    return history
      .filter((r, i) => {
        if (
          !i ||
          i === history.length - 1 ||
          [history[i - 1].value, r.value, history[i + 1].value].some((v) => v == null)
        )
          return false;
        const previous = Number(history[i - 1].value),
          current = Number(r.value),
          next = Number(history[i + 1].value);
        return (
          previous > 0 &&
          next > 0 &&
          Math.abs(current / previous - 1) > 0.35 &&
          Math.abs(next / previous - 1) < 0.1
        );
      })
      .map((r) => r.date);
  });
  const selectedIndustry = computed(() => items('industry').find((r) => r.code === industry.value));
  const growthItems = computed(() =>
    items('growth_' + metric.value)
      .filter((r) => r.name.includes(query.value))
      .slice()
      .sort((a, b) => {
        if (a.change == null) return b.change == null ? 0 : 1;
        if (b.change == null) return -1;
        return (Number(b.change) - Number(a.change)) * (growthSort.value ? 1 : -1);
      }),
  );
  const source = computed(
    () =>
      data.value?.sources[
        tab.value === 'fund'
          ? 'fund_' + fund.value
          : tab.value === 'growth'
          ? 'growth_' + metric.value
          : tab.value === 'crowding'
          ? 'industry'
          : tab.value
      ],
  );
  const sourceDate = computed(() =>
    tab.value === 'dividend'
      ? last(selectedDividend.value?.history)?.date
      : tab.value === 'crowding'
      ? last(selectedIndustry.value?.history)?.date
      : tab.value === 'growth'
      ? growthItems.value[0]?.date
      : last(rows('fund_' + fund.value))?.date,
  );
  const lastValidCongestion = computed(() =>
    rows('congestion')
      .filter((r) => r.value != null)
      .at(-1),
  );
  const heatDates = computed(
    () => selectedIndustry.value?.history?.slice(-10).map((r) => r.date) || [],
  );
  const heatValue = (r: MonitorItem, d: string) =>
    r.history?.find((p) => p.date === d)?.[heatMetric.value];
  const fmt = (v: MonitorValue | undefined, digits = 2) =>
    v == null || v === '' || !Number.isFinite(Number(v)) ? '—' : Number(v).toFixed(digits);
  const tone = (v: MonitorValue | undefined) =>
    v == null ? '' : Number(v) > 0 ? 'positive' : Number(v) < 0 ? 'negative' : '';
  const heatStyle = (v: MonitorValue | undefined) =>
    v == null
      ? {}
      : {
          background:
            Number(v) >= 50
              ? `rgba(220,60,70,${0.06 + Number(v) / 500})`
              : `rgba(0,150,100,${0.06 + (100 - Number(v)) / 500})`,
        };
  async function load() {
    controller?.abort();
    const current = new AbortController();
    controller = current;
    loading.value = true;
    error.value = '';
    try {
      const result = await getMarketMonitor(current.signal);
      if (!current.signal.aborted) data.value = result;
    } catch {
      if (!current.signal.aborted) error.value = '市场监测读取失败';
    } finally {
      if (!current.signal.aborted) {
        loading.value = false;
        emit('ready');
      }
    }
  }
  async function loadStyles() {
    styleController?.abort();
    const current = new AbortController();
    styleController = current;
    styleError.value = '';
    try {
      const result = await getEquityObservatory('cn', current.signal);
      if (!current.signal.aborted) themes.value = result.themes || undefined;
    } catch {
      if (!current.signal.aborted) styleError.value = '风格数据读取失败';
    }
  }
  watch(
    () => props.refreshKey,
    () => {
      load();
      if (tab.value === 'style') loadStyles();
    },
    { immediate: true },
  );
  watch(tab, (value) => {
    if (value === 'style' && !themes.value) loadStyles();
  });
  onBeforeUnmount(() => {
    controller?.abort();
    styleController?.abort();
  });
</script>
<style scoped>
  .monitor {
    min-width: 0;
    color: #17324d;
  }

  h2 {
    margin: 0;
    font-size: 20px;
  }

  header p,
  .definition,
  .source {
    color: #71869d;
    font-size: 12px;
  }

  nav,
  .controls,
  .source {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    margin: 16px 0;
    gap: 12px;
  }

  button,
  select,
  input {
    padding: 6px 12px;
    border: 1px solid #dce5ef;
    border-radius: 6px;
    background: white;
    color: inherit;
    font: inherit;
  }

  button {
    cursor: pointer;
  }

  button.active,
  button[aria-pressed='true'] {
    border-color: #a7c0ff;
    background: #edf3ff;
    color: #2864ec;
  }

  a {
    color: #2864ec;
  }

  .cards {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin: 16px 0;
  }

  .cards button {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
    padding: 16px;
  }

  strong {
    font-size: 23px;
  }

  small {
    color: #71869d;
    font-size: 11px;
  }

  .table-scroll {
    max-height: 620px;
    margin: 16px 0;
    overflow: auto;
    border: 1px solid #dce5ef;
    border-radius: 10px;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    white-space: nowrap;
  }

  th,
  td {
    padding: 10px 14px;
    border-bottom: 1px solid #edf1f5;
    text-align: right;
  }

  th:first-child {
    text-align: left;
  }

  thead {
    position: sticky;
    z-index: 1;
    top: 0;
    background: #f4f7fb;
  }

  th button {
    padding: 0;
    border: 0;
    background: transparent;
  }

  .positive {
    color: #d84f5a;
  }

  .negative {
    color: #00976f;
  }

  .heatmap td {
    text-align: center;
  }

  .notice {
    color: #967025;
  }

  details {
    margin: 16px 0;
    padding: 16px;
    border: 1px solid #dce5ef;
    border-radius: 10px;
  }

  summary {
    cursor: pointer;
  }

  @media (max-width: 700px) {
    .cards {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    nav {
      gap: 6px;
    }

    nav button {
      padding: 6px 8px;
    }
  }
</style>
