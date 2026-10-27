<template>
  <section class="broad-panel">
    <header
      ><h2>宽基 ETF · 周频资金</h2
      ><select v-model="selected" aria-label="宽基指数"
        ><option v-for="o in data?.options || defaults" :key="o.key" :value="o.key">{{
          o.label
        }}</option></select
      ></header
    >
    <p v-if="error" role="alert">{{ error }}</p
    ><p v-if="loading">正在读取宽基历史…</p>
    <template v-if="data">
      <FinancingChart
        :title="`${label} ETF 周净申赎（估算）`"
        :rows="rows"
        :lines="lines"
        note="已跟踪ETF的份额变化×价格估算，按自然周汇总；黑线为指数收盘。缺失交易日不按零计入。"
      />
      <div class="summary" v-if="latest"
        ><span>{{ latest.date }}{{ latest.partialWeek ? ' · 本周截至当日' : '' }}</span
        ><strong>合计 {{ amount(latest.total) }} 亿元</strong
        ><span>周成交额 {{ amount(latest.turnoverYi) }} 亿元</span
        ><span>指数周涨跌 {{ amount(latest.indexReturnPct) }}%</span
        ><span>{{ data.members.length }} 只已跟踪ETF</span></div
      >
      <details
        ><summary>周频统计明细</summary
        ><div class="scroll"
          ><table
            ><thead
              ><tr
                ><th>周末交易日</th><th>交易日数</th
                ><th v-for="m in data.members" :key="m.code">{{ m.name }}</th
                ><th>合计（亿元）</th><th>ETF周成交额（估算，亿元）</th><th>指数周涨跌（%）</th
                ><th>指数收盘</th></tr
              ></thead
            ><tbody
              ><tr v-for="r in [...data.weekly].reverse()" :key="r.date"
                ><td>{{ r.date }}{{ r.partialWeek ? '（本周）' : '' }}</td
                ><td>{{ r.sessions }}</td
                ><td v-for="f in r.funds" :key="f.code">{{ amount(f.value) }}</td
                ><td>{{ amount(r.total) }}</td
                ><td>{{ amount(r.turnoverYi) }}</td
                ><td>{{ amount(r.indexReturnPct) }}</td
                ><td>{{ amount(r.indexClose) }}</td></tr
              ></tbody
            ></table
          ></div
        ></details
      >
      <div class="ratio"
        ><h3>{{ label }} · 头部ETF市值 / 指数流通市值</h3><p>{{ data.marketCapRatio.reason }}</p>
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
        ></div
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
  import { computed, onBeforeUnmount, ref, watch } from 'vue';
  import { researchRequest } from '@/api/hedgeResearch';
  import FinancingChart, { type FinanceLine, type FinanceRow } from './FinancingChart.vue';

  interface Week {
    date: string;
    sessions: number;
    indexClose: string | null;
    total: string | null;
    turnoverYi: string | null;
    indexReturnPct: string | null;
    partialWeek: boolean;
    funds: Array<{ code: string; name: string; value: string | null }>;
  }
  interface Broad {
    options: Array<{ key: string; label: string }>;
    members: Array<{ code: string; name: string }>;
    weekly: Week[];
    marketCapRatio: {
      reason: string;
      rows: Array<FinanceRow & { ratioPct: string; etfCapYi: string; indexCapYi: string }>;
    };
    sources?: Record<string, { fetchedAt?: string }>;
  }
  const props = defineProps<{ refreshKey?: number }>();
  const defaults = [
    { key: 'hs300', label: '沪深300' },
    { key: 'sse50', label: '上证50' },
    { key: 'csi500', label: '中证500' },
    { key: 'csi1000', label: '中证1000' },
    { key: 'chinext', label: '创业板' },
    { key: 'star50', label: '科创50' },
  ];
  const selected = ref('hs300'),
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
  const rows = computed<FinanceRow[]>(
    () =>
      data.value?.weekly.map((r) => ({
        date: r.date,
        index: r.indexClose,
        total: r.total,
        partialWeek: r.partialWeek,
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
  const latest = computed(() => data.value?.weekly.at(-1));
  const amount = (v: unknown) =>
    v == null ? '—' : Number(v).toLocaleString('zh-CN', { maximumFractionDigits: 2 });
</script>
<style scoped>
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
