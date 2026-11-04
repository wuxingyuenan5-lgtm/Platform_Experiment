<template>
  <section class="broad-panel">
    <header
      ><h2>{{
        widgetOnly === 'details'
          ? 'ETF资金统计表'
          : widgetOnly === 'ratio'
          ? '头部ETF市值占比'
          : widgetOnly === 'flow'
          ? 'ETF净申赎'
          : '宽基ETF资金总览'
      }}</h2
      ><select v-model="selected" aria-label="宽基指数"
        ><option v-for="o in data?.options || defaults" :key="o.key" :value="o.key">{{
          o.label
        }}</option></select
      ></header
    >
    <p v-if="error" role="alert">{{ error }}</p
    ><p v-if="loading">正在读取宽基历史…</p>
    <template v-if="data">
      <div v-if="!widgetOnly" class="window-cards"
        ><article v-for="n in [1, 5, 20]" :key="n"
          ><span>{{ n === 1 ? '最新一日' : `近${n}个交易日` }}净申赎</span
          ><strong>{{ amount(summaryFlow(n)) }} 亿元</strong></article
        ></div
      >
      <label v-if="widgetOnly !== 'ratio'" class="frequency"
        >统计频率
        <select v-model="frequency" aria-label="宽基资金统计频率"
          ><option value="daily">日度</option
          ><option value="weekly">周度</option></select
        ></label
      >
      <nav v-if="!widgetOnly" class="flow-views" aria-label="宽基资金展示">
        <button
          v-for="v in flowViews"
          :key="v.key"
          :aria-pressed="flowView === v.key"
          @click="flowView = v.key"
          >{{ v.label }}</button
        >
      </nav>
      <FinancingChart
        v-if="flowView === 'chart' && widgetOnly !== 'ratio'"
        :key="selected + frequency"
        :title="`${label} ETF ${frequency === 'daily' ? '日' : '周'}净申赎（估算）`"
        :rows="rows"
        :lines="lines"
        :note="
          frequency === 'daily'
            ? '已跟踪ETF份额变化×价格估算；黑线为同日指数收盘。缺失不计零。'
            : '按实际指数交易日汇总；缺失不计零。黑线为周末次收盘，未结束周单独标记。'
        "
      />
      <EtfObservationPanel v-if="flowView === 'heatmap'" mode="heatmap" />
      <div class="summary" v-if="latest && flowView !== 'heatmap' && !widgetOnly"
        ><span>{{ latest.date }}</span
        ><strong>合计 {{ amount(latest.total) }} 亿元</strong
        ><span
          >{{ frequency === 'daily' ? '日' : '周' }}成交额
          {{ amount(latest.turnoverYi) }} 亿元</span
        ><span
          >指数{{ frequency === 'daily' ? '日' : '周' }}涨跌
          {{ amount(latest.indexReturnPct) }}%</span
        ><span v-if="latest.partialWeek">本周未结束</span
        ><span>{{ data.members.length }} 只已跟踪ETF</span></div
      >
      <div v-if="flowView === 'details'" aria-label="资金统计明细"
        ><h3>{{ label }} ETF · 资金统计明细</h3
        ><div class="scroll"
          ><table
            ><thead
              ><tr
                ><th>交易日</th><th v-for="m in data.members" :key="m.code">{{ m.name }}</th
                ><th>合计（亿元）</th><th>ETF成交额（估算，亿元）</th><th>指数区间涨跌（%）</th
                ><th>指数收盘</th></tr
              ></thead
            ><tbody
              ><tr v-for="r in [...activeDays].reverse()" :key="r.date"
                ><td>{{ r.date }}</td
                ><td v-for="f in r.funds" :key="f.code">{{ amount(f.value) }}</td
                ><td>{{ amount(r.total) }}</td
                ><td>{{ amount(r.turnoverYi) }}</td
                ><td>{{ amount(r.indexReturnPct) }}</td
                ><td>{{ amount(r.indexClose) }}</td></tr
              ></tbody
            ></table
          ></div
        ></div
      >
      <details v-if="!widgetOnly || widgetOnly === 'ratio'" class="ratio" open
        ><summary>头部ETF市值占比</summary><h3>{{ label }} · 头部ETF市值 / 指数流通市值</h3
        ><p>{{ data.marketCapRatio.reason }}</p>
        <FinancingChart
          v-if="data.marketCapRatio.rows?.length"
          :title="`${label} · 头部ETF市值占比`"
          :rows="data.marketCapRatio.rows"
          :lines="[
            { key: 'ratioPct', name: 'ETF市值 / 指数流通市值', unit: '%', color: '#2563eb' },
          ]"
        />
        <p v-if="data.marketCapRatio.rows?.length"
          >最新 {{ Number(data.marketCapRatio.rows.at(-1)?.ratioPct).toFixed(3) }}% · 已跟踪ETF
          {{ Number(data.marketCapRatio.rows.at(-1)?.etfCapYi).toFixed(2) }} 亿元 / 指数流通市值
          {{ Number(data.marketCapRatio.rows.at(-1)?.indexCapYi).toFixed(2) }} 亿元 ·
          <a href="https://gu.qq.com/sh000300" target="_blank" rel="noreferrer">行情来源 ↗</a></p
        ></details
      >
      <p class="source"
        >来源：<a href="https://wangwang-etf.com/" target="_blank" rel="noreferrer"
          >ETF 跟踪历史 ↗</a
        >
        · {{ data.sources?.market?.fetchedAt?.slice(0, 10) || '—' }}</p
      >
    </template>
  </section>
</template>
<script setup lang="ts">
  import EtfObservationPanel from './EtfObservationPanel.vue';
  import { computed, onBeforeUnmount, ref, watch } from 'vue';
  import { researchRequest } from '@/api/hedgeResearch';
  import FinancingChart, { type FinanceLine, type FinanceRow } from './FinancingChart.vue';

  interface Day {
    date: string;
    indexClose: string | null;
    total: string | null;
    turnoverYi: string | null;
    indexReturnPct: string | null;
    funds: Array<{ code: string; name: string; value: string | null }>;
    partialWeek?: boolean;
  }
  interface Broad {
    options: Array<{ key: string; label: string }>;
    members: Array<{ code: string; name: string }>;
    daily: Day[];
    weekly: Day[];
    marketCapRatio: {
      reason: string;
      rows: Array<FinanceRow & { ratioPct: string; etfCapYi: string; indexCapYi: string }>;
    };
    sources?: Record<string, { fetchedAt?: string }>;
  }
  const props = defineProps<{
    refreshKey?: number;
    widgetOnly?: 'flow' | 'details' | 'ratio';
    initialIndex?: string;
  }>();
  const defaults = [
    { key: 'hs300', label: '沪深300' },
    { key: 'sse50', label: '上证50' },
    { key: 'csi500', label: '中证500' },
    { key: 'csi1000', label: '中证1000' },
    { key: 'chinext', label: '创业板' },
    { key: 'star50', label: '科创50' },
  ];
  const flowViews = [
    { key: 'chart', label: '图表' },
    { key: 'heatmap', label: '宽基月度资金表' },
    { key: 'details', label: '资金统计明细' },
  ] as const;
  const flowView = ref<'chart' | 'heatmap' | 'details'>(
    props.widgetOnly === 'details' ? 'details' : 'chart',
  );
  const frequency = ref<'daily' | 'weekly'>('daily');
  const selected = ref(props.initialIndex || 'hs300'),
    data = ref<Broad>(),
    error = ref(''),
    loading = ref(false);
  let abort: AbortController | undefined;
  watch(
    [selected, () => props.refreshKey],
    async () => {
      abort?.abort();
      const current = new AbortController();
      abort = current;
      loading.value = true;
      data.value = undefined;
      error.value = '';
      try {
        const result = await researchRequest<Broad>({
          method: 'GET',
          url: `/research/a-share/broad-etfs/${selected.value}`,
          signal: current.signal,
        });
        if (!current.signal.aborted) data.value = result;
      } catch {
        if (!current.signal.aborted) error.value = '宽基统计读取失败';
      } finally {
        if (!current.signal.aborted) loading.value = false;
      }
    },
    { immediate: true },
  );
  onBeforeUnmount(() => abort?.abort());
  const label = computed(
    () => data.value?.options.find((o) => o.key === selected.value)?.label || '宽基',
  );
  const activeDays = computed(() => data.value?.[frequency.value] || []);
  function summaryFlow(count: number) {
    const rows = data.value?.daily.slice(-count) || [];
    if (rows.length !== count || rows.some((r) => r.total == null)) return null;
    return rows.reduce((sum, r) => sum + Number(r.total), 0);
  }
  const rows = computed<FinanceRow[]>(
    () =>
      activeDays.value.map((r) => ({
        date: r.date,
        index: r.indexClose,
        total: r.total,
        ...Object.fromEntries(r.funds.map((f) => [f.code, f.value])),
      })) || [],
  );
  const colors = ['#2563eb', '#059669', '#d4a516', '#8b5cf6', '#ed7373', '#18a8c7'];
  const lines = computed<FinanceLine[]>(() => [
    ...(data.value?.members || []).map((m, i) => ({
      key: m.code,
      name: m.name,
      color: colors[i % colors.length],
      unit: '亿元',
      bar: true,
      stack: 'flows',
    })),
    { key: 'index', name: label.value, color: '#171717', unit: '点', right: true },
  ]);
  const latest = computed(() => activeDays.value.at(-1));
  const amount = (v: unknown) =>
    v == null ? '—' : Number(v).toLocaleString('zh-CN', { maximumFractionDigits: 2 });
</script>
<style scoped>
  .flow-views {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin: 12px 0;
  }

  .flow-views button {
    padding: 6px 12px;
    border: 1px solid #dbe4ed;
    border-radius: 6px;
    background: #fff;
    font: inherit;
    cursor: pointer;
  }

  .flow-views button[aria-pressed='true'] {
    border-color: #a5bfff;
    background: #edf3ff;
    color: #2864ec;
  }

  .window-cards {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    margin: 16px 0;
  }

  .window-cards article {
    display: grid;
    gap: 8px;
    padding: 14px;
    border: 1px solid #dce5ed;
    border-radius: 8px;
  }

  .window-cards strong {
    font-size: 20px;
  }

  summary {
    padding: 12px 0;
    font-weight: 600;
    cursor: pointer;
  }

  .frequency {
    display: block;
    margin: 12px 0;
  }

  @media (max-width: 600px) {
    .window-cards {
      grid-template-columns: 1fr;
    }
  }

  .broad-panel {
    margin-bottom: 24px;
    font-family: inherit;
  }

  header,
  .summary {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 16px;
  }

  h2 {
    margin: 0;
    font-size: 17px;
  }

  h3 {
    font-size: 14px;
  }

  select {
    padding: 6px 14px;
    border: 1px solid #d7e3ee;
    border-radius: 7px;
    background: #fff;
    color: #123247;
    font: inherit;
  }

  .summary {
    padding: 10px 16px;
    color: #59718b;
    font-size: 12px;
  }

  .summary strong {
    color: #163b54;
  }

  details,
  .ratio {
    margin-top: 12px;
    padding: 14px;
    border: 1px solid #d7e3ee;
    border-radius: 10px;
  }

  .ratio p,
  .source {
    color: #71869e;
    font-size: 12px;
  }

  .scroll {
    max-height: 360px;
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
    padding: 9px 12px;
    border-bottom: 1px solid #e6edf5;
    text-align: right;
  }

  th:first-child,
  td:first-child {
    text-align: left;
  }

  a {
    color: #467dbb;
  }
</style>
