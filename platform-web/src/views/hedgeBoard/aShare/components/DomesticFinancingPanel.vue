<template>
  <section class="domestic-financing">
    <h2>两融与国内衍生品</h2><p v-if="error" role="alert">{{ error }}</p
    ><p v-if="loading">正在读取本地历史…</p>
    <template v-if="data">
      <FinancingChart
        title="A股两融余额与融资余额变化"
        :rows="marginRows"
        :lines="marginLines"
        note="两市融资余额、融券余额和两融总余额；右轴为融资余额日变化，并非融资买入额。"
      />
      <p class="source"
        >来源：<a href="https://data.eastmoney.com/rzrq/" target="_blank" rel="noreferrer"
          >沪深两融汇总 ↗</a
        >
        · {{ marginRows.at(-1)?.date || '—' }}</p
      >
      <header
        ><h3>股指期货基差</h3
        ><select v-model="family" aria-label="股指期货品种"
          ><option value="IF">IF · 沪深300</option
          ><option value="IH">IH · 上证50</option
          ><option value="IC">IC · 中证500</option
          ><option value="IM">IM · 中证1000</option></select
        ><select v-model="contract" aria-label="基差合约"
          ><option value="near">近月（逐日最近挂牌合约）</option
          ><option v-for="c in contracts" :key="c" :value="c">{{ c }}</option></select
        ><select v-model="basisMetric" aria-label="基差单位"
          ><option value="basis">基差（点）</option
          ><option value="basisPct">基差率（%）</option></select
        ></header
      >
      <FinancingChart
        :title="`${family} 股指基差`"
        :rows="basisRows"
        :lines="basisLines"
        note="基差=期货收盘−同日现货指数收盘；正值为升水。近月随挂牌合约换月，悬浮可见实际合约；缺少同日现货时不计算。"
      />
      <p class="source"
        >来源：<a href="http://www.cffex.com.cn/rtj/" target="_blank" rel="noreferrer"
          >中金所日行情 ↗</a
        >
        · 同日指数收盘 · {{ basisRows.at(-1)?.date || '—'
        }}<span v-if="data.futuresSource.status !== 'ready'">
          · 部分日期采集未完成，保留已核验历史</span
        ></p
      >
      <header
        ><h3>国内股票期权 IV</h3
        ><select v-model="underlying" aria-label="期权标的"
          ><option value="510050">50ETF</option
          ><option value="510300">沪深300ETF</option
          ><option value="510500">中证500ETF</option
          ><option value="588000">科创50ETF（588000）</option
          ><option value="588080">科创50ETF（588080）</option></select
        ><select v-model="ivMonth" aria-label="期权月份"
          ><option value="near">近月</option
          ><option v-for="m in ivMonths" :key="m" :value="m">{{ m }}</option></select
        ></header
      >
      <FinancingChart
        title="ETF期权隐含波动率"
        :rows="ivRows"
        :lines="[{ key: 'iv', name: 'IV', color: '#2563eb', unit: '%' }]"
        note="上交所ETF期权IV：认购、认沽分别取最接近50 Delta的标准合约后平均。ETF代理口径，非股指期权IV。"
      />
      <p class="source"
        >来源：<a
          href="https://www.sse.com.cn/assortment/options/risk/"
          target="_blank"
          rel="noreferrer"
          >上交所期权风险指标 ↗</a
        >
        · {{ ivRows.at(-1)?.date || '—' }}</p
      >
      <h3>中国杠杆交易与风险偏好</h3>
      <MacroSeriesChart group-id="cnRiskLeverage" :years="1" />
    </template>
  </section>
</template>
<script setup lang="ts">
  import { computed, onBeforeUnmount, ref, watch } from 'vue';
  import { researchRequest, type MacroDashboardSeries } from '@/api/hedgeResearch';
  import MacroSeriesChart from '../../charts/MacroSeriesChart';
  import FinancingChart, { type FinanceLine, type FinanceRow } from './FinancingChart.vue';

  interface Basis extends FinanceRow {
    family: string;
    contract: string;
    close: string;
    spot: string;
    basis: string;
    basisPct: string;
  }
  interface Iv {
    date: string;
    underlying: string;
    month: string;
    value: string;
    contracts: string[];
  }
  interface Data {
    margin: MacroDashboardSeries[];
    basis: Basis[];
    iv: { rows?: Iv[] };
    goldIv: MacroDashboardSeries[];
    futuresSource: { status?: string };
  }
  const props = defineProps<{ refreshKey?: number }>(),
    emit = defineEmits<{ (event: 'ready'): void }>();
  const data = ref<Data>(),
    error = ref(''),
    loading = ref(false),
    family = ref('IF'),
    contract = ref('near'),
    basisMetric = ref('basis'),
    underlying = ref('510300'),
    ivMonth = ref('near');
  let abort: AbortController | undefined;
  watch(
    () => props.refreshKey,
    async () => {
      abort?.abort();
      const current = new AbortController();
      abort = current;
      loading.value = true;
      error.value = '';
      try {
        const result = await researchRequest<Data>({
          method: 'GET',
          url: '/research/a-share/financing',
          signal: current.signal,
        });
        if (!current.signal.aborted) {
          data.value = result;
        }
      } catch {
        if (!current.signal.aborted) error.value = '两融与衍生品读取失败，请刷新重试';
      } finally {
        if (!current.signal.aborted) {
          loading.value = false;
          emit('ready');
        }
      }
    },
    { immediate: true },
  );
  onBeforeUnmount(() => abort?.abort());
  const marginRows = computed<FinanceRow[]>(() => {
    const rows = new Map<string, FinanceRow>();
    for (const s of data.value?.margin || [])
      for (const o of s.observations) {
        if (!rows.has(o.date)) rows.set(o.date, { date: o.date });
        rows.get(o.date)![s.seriesId] = o.value;
      }
    return [...rows.values()].sort((a, b) => a.date.localeCompare(b.date));
  });
  const marginLines: FinanceLine[] = [
    { key: 'cn_margin_total_balance', name: '两融总余额', color: '#171717', unit: '亿元' },
    { key: 'cn_margin_financing_balance', name: '融资余额', color: '#2563eb', unit: '亿元' },
    { key: 'cn_margin_short_balance', name: '融券余额', color: '#d3a21e', unit: '亿元' },
    {
      key: 'cn_margin_financing_change',
      name: '融资余额日变化',
      color: '#35a47b',
      unit: '亿元',
      right: true,
      bar: true,
    },
  ];
  const contracts = computed(() =>
    [...new Set(data.value?.basis.filter((r) => r.family === family.value).map((r) => r.contract))]
      .sort()
      .reverse(),
  );
  watch(family, () => (contract.value = 'near'));
  const basisRows = computed<FinanceRow[]>(() => {
    const selected =
      data.value?.basis.filter(
        (r) =>
          r.family === family.value && (contract.value === 'near' || r.contract === contract.value),
      ) || [];
    const days = new Map<string, Basis>();
    for (const r of selected) {
      if (!days.has(r.date) || r.contract < days.get(r.date)!.contract) days.set(r.date, r);
    }
    return [...days.values()].sort((a, b) => a.date.localeCompare(b.date));
  });
  const basisLines = computed<FinanceLine[]>(() => [
    {
      key: basisMetric.value,
      name: basisMetric.value === 'basis' ? '基差' : '基差率',
      color: '#2563eb',
      unit: basisMetric.value === 'basis' ? '点' : '%',
      bar: true,
    },
    { key: 'spot', name: '现货指数', color: '#171717', unit: '点', right: true },
  ]);
  const ivMonths = computed(() =>
    [
      ...new Set(
        data.value?.iv.rows?.filter((r) => r.underlying === underlying.value).map((r) => r.month),
      ),
    ].sort(),
  );
  watch(underlying, () => (ivMonth.value = 'near'));
  const ivRows = computed<FinanceRow[]>(() => {
    const rows =
      data.value?.iv.rows?.filter(
        (r) =>
          r.underlying === underlying.value &&
          (ivMonth.value === 'near' || r.month === ivMonth.value),
      ) || [];
    const days = new Map<string, Iv>();
    for (const r of rows)
      if (!days.has(r.date) || r.month < days.get(r.date)!.month) days.set(r.date, r);
    return [...days.values()]
      .sort((a, b) => a.date.localeCompare(b.date))
      .map((r) => ({ date: r.date, iv: r.value, contract: r.contracts.join(' / ') }));
  });
</script>
<style scoped>
  .domestic-financing {
    color: #123247;
    font-family: inherit;
  }

  h2 {
    margin: 0 0 18px;
    font-size: 18px;
  }

  h3 {
    margin: 0;
    font-size: 15px;
  }

  header {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    margin-top: 25px;
    gap: 12px;
  }

  select {
    padding: 5px 12px;
    border: 1px solid #d7e3ee;
    border-radius: 7px;
    background: #fff;
    color: #294d68;
    font: inherit;
  }

  .source {
    color: #71869e;
    font-size: 12px;
  }

  a {
    color: #467dbb;
  }
</style>
