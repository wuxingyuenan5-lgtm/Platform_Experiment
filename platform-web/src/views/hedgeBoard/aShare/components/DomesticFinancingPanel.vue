<template>
  <section class="domestic-financing" :aria-label="mode === 'margin' ? '两融变化' : '衍生品'">
    <p v-if="error" role="alert"
      >{{ error }} <button type="button" @click="load(true)">重试</button></p
    >
    <p v-if="loading" role="status">正在读取本地历史…</p>
    <template v-if="data">
      <template v-if="mode === 'margin'">
        <FinancingChart
          class="margin-balance-chart"
          title="两融余额变化"
          :rows="marginRows"
          :lines="marginLines"
          :initial-range="365"
          allow-table
          :note="
            marginPeriod === 'day'
              ? undefined
              : '取每期最近一个有融资余额的交易日。融资余额变动为相邻两期余额之差，成交额占比和沪深300取同日值。'
          "
        >
          <template #range-controls>
            <label class="margin-level">
              级别选择
              <select v-model="marginPeriod" aria-label="级别选择">
                <option v-for="(label, period) in marginPeriods" :key="period" :value="period">
                  {{ label }}度
                </option>
              </select>
            </label>
          </template>
        </FinancingChart>
        <p v-if="!hideMarginSource" class="source"
          >来源：<a href="https://data.eastmoney.com/rzrq/" target="_blank" rel="noreferrer"
            >沪深两融汇总 ↗</a
          >
          · {{ marginRows.at(-1)?.date || '—' }}
          <template v-if="data.marginIndex?.sourceUrl">
            ·
            <a :href="data.marginIndex.sourceUrl" target="_blank" rel="noreferrer">沪深300收盘 ↗</a>
          </template></p
        >
      </template>
      <template v-else>
        <div class="basis-summary" aria-label="股指期货近月基差摘要">
          <button
            v-for="item in basisSummary"
            :key="item.family"
            type="button"
            :aria-pressed="family === item.family"
            @click="
              family = item.family;
              contract = 'near';
            "
          >
            <span>{{ item.family }} · {{ item.label }}</span
            ><strong>{{ format(item.value) }} <small>点</small></strong
            ><span>{{ item.date || '暂无数据' }} · 近月基差</span>
          </button>
        </div>
        <div class="derivative-grid">
          <ChartExpand title="股指期货基差">
            <article class="derivative-card">
              <header><h3>股指期货基差</h3></header>
              <div class="controls">
                <label
                  >品种
                  <select v-model="family" aria-label="股指期货品种"
                    ><option value="IF">IF · 沪深300</option
                    ><option value="IH">IH · 上证50</option
                    ><option value="IC">IC · 中证500</option
                    ><option value="IM">IM · 中证1000</option></select
                  ></label
                ><label
                  >合约
                  <select v-model="contract" aria-label="基差合约"
                    ><option value="near">近月（逐日最近挂牌合约）</option
                    ><option v-for="c in contracts" :key="c" :value="c">{{ c }}</option></select
                  ></label
                ><label
                  >单位
                  <select v-model="basisMetric" aria-label="基差单位"
                    ><option value="basis">基差（点）</option
                    ><option value="basisPct">基差率（%）</option></select
                  ></label
                ></div
              >
              <FinancingChart
                :title="`${family} 股指基差`"
                :rows="basisRows"
                :lines="basisLines"
                embedded
                allow-table
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
            </article></ChartExpand
          >
          <ChartExpand title="国内股票期权 IV"><DomesticOptionIvPanel /></ChartExpand>
        </div>
      </template>
    </template>
    <section v-if="mode === 'derivatives'" class="futures-section" aria-label="股指期货席位持仓">
      <h3>股指期货席位持仓</h3>
      <VisibleChart :height="680"
        ><NationalEtfPanel view="futures" :refresh-key="refreshKey"
      /></VisibleChart>
    </section>
  </section>
</template>
<script setup lang="ts">
  import { computed, defineAsyncComponent, ref, watch } from 'vue';
  import Decimal from 'decimal.js';
  import DomesticOptionIvPanel from './DomesticOptionIvPanel.vue';
  import { useDomesticFinancing, type Basis } from './useDomesticFinancing';
  import VisibleChart from '../../components/VisibleChart';
  import ChartExpand from '../../components/ChartExpand.vue';
  import FinancingChart, { type FinanceLine, type FinanceRow } from './FinancingChart.vue';

  const NationalEtfPanel = defineAsyncComponent(() => import('./NationalEtfPanel.vue'));

  const props = withDefaults(
      defineProps<{
        refreshKey?: number;
        mode?: 'margin' | 'derivatives';
        hideMarginSource?: boolean;
      }>(),
      { mode: 'margin' },
    ),
    emit = defineEmits<{ (event: 'ready'): void }>();
  const { data, error, loading, load } = useDomesticFinancing();
  const family = ref('IF'),
    contract = ref('near'),
    basisMetric = ref('basis');
  watch(
    () => props.refreshKey,
    async (_, previous) => {
      await load(previous !== undefined);
      emit('ready');
    },
    { immediate: true },
  );
  const format = (value: unknown) =>
    value == null || value === '' || !Number.isFinite(Number(value))
      ? '—'
      : Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 2 });
  const basisSummary = computed(() =>
    [
      ['IF', '沪深300'],
      ['IH', '上证50'],
      ['IC', '中证500'],
      ['IM', '中证1000'],
    ].map(([code, label]) => {
      const rows = (data.value?.basis || []).filter((row) => row.family === code);
      const date = rows.reduce((last, row) => (row.date > last ? row.date : last), '');
      const row = rows
        .filter((item) => item.date === date)
        .sort((a, b) => a.contract.localeCompare(b.contract))[0];
      return { family: code, label, date, value: row?.basis };
    }),
  );
  const marginPeriods = { day: '日', week: '周', month: '月' } as const;
  const marginPeriod = ref<keyof typeof marginPeriods>('day');
  const financingBalance = 'cn_margin_financing_balance';
  const financingChange = 'cn_margin_financing_change';
  const dailyMarginRows = computed<FinanceRow[]>(() => {
    const rows = new Map<string, FinanceRow>();
    for (const s of data.value?.margin || [])
      for (const o of s.observations) {
        if (!rows.has(o.date)) rows.set(o.date, { date: o.date });
        rows.get(o.date)![s.seriesId] = o.value;
      }
    const closes = new Map(data.value?.marginIndex?.rows.map((row) => [row.date, row.close]));
    return [...rows.values()]
      .sort((a, b) => a.date.localeCompare(b.date))
      .map((row) => ({ ...row, hs300: closes.get(row.date) ?? null }));
  });
  const marginRows = computed(() => {
    const period = marginPeriod.value;
    if (period === 'day') return dailyMarginRows.value;

    const endpoints = new Map<number, FinanceRow>();
    for (const row of dailyMarginRows.value) {
      if (row[financingBalance] == null || row[financingBalance] === '') continue;
      const day = new Date(row.date + 'T00:00:00Z');
      // The Unix epoch starts on Thursday. Shift three days to bucket Monday–Sunday.
      const key =
        period === 'month'
          ? day.getUTCFullYear() * 12 + day.getUTCMonth()
          : Math.floor((day.getTime() / 86_400_000 + 3) / 7);
      endpoints.set(key, row);
    }
    return [...endpoints].map(([key, row]) => {
      const previous = endpoints.get(key - 1);
      return {
        ...row,
        [financingChange]: previous
          ? new Decimal(String(row[financingBalance]))
              .minus(String(previous[financingBalance]))
              .toString()
          : null,
      };
    });
  });
  const marginLines = computed<FinanceLine[]>(() => [
    {
      key: 'cn_margin_total_balance',
      name: '两融总余额',
      color: '#171717',
      unit: '亿元',
      defaultSelected: false,
    },
    { key: financingBalance, name: '融资余额', color: '#171717', unit: '亿元' },
    {
      key: 'cn_margin_short_balance',
      name: '融券余额',
      color: '#d3a21e',
      unit: '亿元',
      defaultSelected: false,
    },
    {
      key: financingChange,
      name: `融资余额${marginPeriods[marginPeriod.value]}变化`,
      color: '#35a47b',
      unit: '亿元',
      right: true,
      bar: true,
    },
    {
      key: 'cn_margin_buy_share',
      name: '融资融券成交额占比',
      defaultSelected: false,
      color: '#7c3aed',
      unit: '%',
      axis: 2,
    },
    {
      key: 'hs300',
      name: '沪深300',
      color: '#d97706',
      unit: '点',
      axis: 3,
      hideAxis: true,
      width: 2.2,
      lineType: 'solid',
    },
  ]);
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
</script>
<style scoped>
  .margin-balance-chart :deep(.data-scroll) {
    width: max-content;
    max-width: 100%;
  }

  .margin-balance-chart :deep(.data-scroll table) {
    width: max-content;
    min-width: 0;
  }

  .margin-balance-chart :deep(.data-scroll th),
  .margin-balance-chart :deep(.data-scroll td) {
    box-sizing: border-box;
    min-width: 130px;
    padding: 9px 16px;
  }

  .margin-balance-chart :deep(.data-scroll th:first-child) {
    min-width: 110px;
  }

  .margin-balance-chart :deep(.table-pages) {
    justify-content: flex-start;
  }

  .domestic-financing {
    min-width: 0;
    color: var(--strategy-text-2);
    font-family: inherit;
  }

  h3 {
    margin: 0;
    font-size: 15px;
  }

  header {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
    padding-right: 38px;
  }

  select,
  button {
    max-width: 100%;
    padding: 6px 10px;
    border: 1px solid #d7e3ee;
    border-radius: 7px;
    background: #fff;
    color: #294d68;
    font: inherit;
  }

  button {
    cursor: pointer;
  }

  .margin-level {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    white-space: nowrap;
  }

  button:focus-visible,
  select:focus-visible {
    outline: 2px solid var(--strategy-accent);
    outline-offset: 2px;
  }

  .controls {
    display: flex;
    flex-wrap: wrap;
    gap: 10px 14px;
    align-items: center;
    margin: 16px 0;
    font-size: 12px;
  }

  .controls label {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
    min-width: 0;
  }

  .derivative-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
    align-items: stretch;
  }

  .derivative-card {
    height: 100%;
    padding: 18px;
    border: 1px solid var(--strategy-border);
    border-radius: 14px;
    background: var(--strategy-surface);
  }

  .derivative-grid :deep(.chart-expand__surface:not(:modal)) {
    height: 100%;
  }

  .derivative-grid :deep(.financing-chart.is-embedded) {
    margin: 0;
    padding: 0;
  }

  .derivative-grid :deep(.plot) {
    height: 340px;
  }

  .source {
    color: #71869e;
    font-size: 12px;
    line-height: 1.7;
    overflow-wrap: anywhere;
  }

  .basis-summary {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin: 16px 0;
  }

  .basis-summary button {
    display: flex;
    flex-direction: column;
    padding: 14px;
    border-color: var(--strategy-border);
    background: var(--strategy-surface);
    text-align: left;
    gap: 8px;
  }

  .basis-summary span {
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  .basis-summary strong {
    font-size: 21px;
    font-variant-numeric: tabular-nums;
  }

  .basis-summary small {
    font-size: 12px;
    font-weight: 400;
  }

  .basis-summary button[aria-pressed='true'] {
    border-color: var(--strategy-accent);
    background: var(--strategy-accent-soft);
  }

  .futures-section {
    margin-top: 24px;
  }

  .futures-section h3 {
    margin-bottom: 14px;
  }

  @media (max-width: 1250px) {
    .derivative-grid {
      grid-template-columns: minmax(0, 1fr);
    }
  }

  @media (max-width: 650px) {
    .basis-summary {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .derivative-card {
      padding: 14px;
    }
  }

  a {
    color: #467dbb;
  }
</style>
