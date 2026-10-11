<script setup lang="ts">
  import { useDashboardRefresh } from '../useDashboardRefresh';

  import { computed, ref, shallowRef, watch, type Ref } from 'vue';
  import type { EChartsOption } from 'echarts';
  import { useECharts } from '@/hooks/web/useECharts';
  import { getCryptoDashboardV1, type OptionExposureSnapshot } from '@/api/hedgeResearch';

  const props = defineProps<{ market: 'deribit' | 'ibit' }>();
  const snapshot = shallowRef<OptionExposureSnapshot | null>(null);
  const error = ref(false);
  const expiry = ref('all');
  const near = ref(true);
  const table = ref(false);
  const chartRef = ref<HTMLDivElement | null>(null);
  const chart = useECharts(chartRef as Ref<HTMLDivElement>, 'light');
  const expiries = computed(() =>
    [...new Set(snapshot.value?.legs.map((x) => x.expiry) ?? [])].sort(),
  );
  const rows = computed(() => {
    const grouped = new Map<number, { strike: number; call: number; put: number }>();
    const spot = Number(snapshot.value?.underlyingPrice);
    for (const leg of snapshot.value?.legs ?? []) {
      const strike = Number(leg.strike);
      if (expiry.value !== 'all' && leg.expiry !== expiry.value) continue;
      if (near.value && (strike < spot * 0.7 || strike > spot * 1.3)) continue;
      const row = grouped.get(strike) ?? { strike, call: 0, put: 0 };
      row[leg.side] += Number(leg.exposureUsd);
      grouped.set(strike, row);
    }
    return [...grouped.values()].sort((a, b) => a.strike - b.strike);
  });
  const number = (value: number) => value.toLocaleString('en-US', { maximumFractionDigits: 2 });
  const coverage = computed(() =>
    snapshot.value
      ? (
          (100 * Number(snapshot.value.includedOpenInterest)) /
          Number(snapshot.value.totalOpenInterest)
        ).toFixed(2)
      : '—',
  );
  const timestamp = (value: string | null) => (value ? value.replace('T', ' ') : '未提供');
  watch([rows, chartRef], () => {
    chart.setOptions({
      animation: false,
      color: ['#168b77', '#cf596a', '#285ac7'],
      legend: { top: 0, data: ['Call', 'Put（负号）', '净代理值'] },
      grid: { left: 60, right: 18, top: 55, bottom: 80, containLabel: true },
      tooltip: {
        trigger: 'axis',
        confine: true,
        valueFormatter: (value: any) => `${number(Number(value))} USD`,
      },
      xAxis: {
        type: 'category',
        name: '行权价 USD',
        nameLocation: 'middle',
        nameGap: 28,
        data: rows.value.map((r) => String(r.strike)),
        axisLabel: { fontSize: 12, hideOverlap: true },
      },
      yAxis: {
        type: 'value',
        name: 'USD / 1% 变动',
        axisLabel: {
          fontSize: 12,
          formatter: (v: number) =>
            Math.abs(v) >= 1e6
              ? `${number(v / 1e6)}M`
              : Math.abs(v) >= 1e3
              ? `${number(v / 1e3)}K`
              : String(v),
        },
      },
      dataZoom: [{ type: 'slider', bottom: 8, height: 20, showDetail: false }],
      series: [
        { name: 'Call', type: 'bar', stack: 'exposure', data: rows.value.map((r) => r.call) },
        {
          name: 'Put（负号）',
          type: 'bar',
          stack: 'exposure',
          data: rows.value.map((r) => -r.put),
        },
        {
          name: '净代理值',
          type: 'line',
          showSymbol: false,
          data: rows.value.map((r) => r.call - r.put),
        },
      ],
    } as EChartsOption);
  });
  useDashboardRefresh(async () => {
    try {
      snapshot.value = (await getCryptoDashboardV1()).optionExposure?.[props.market] ?? null;
      error.value = !snapshot.value?.legs.length;
    } catch {
      snapshot.value = null;
      error.value = true;
    }
  });
</script>

<template>
  <div v-if="!snapshot" class="local-empty">{{
    error ? '期权敞口数据暂不可用。' : '正在加载数据…'
  }}</div>
  <div class="gex-panel">
    <template v-if="snapshot">
      <div class="gex-controls">
        <label
          >到期日
          <select v-model="expiry" aria-label="GEX 到期日"
            ><option value="all">全部到期日</option
            ><option v-for="date in expiries" :key="date" :value="date">{{
              date.slice(0, 10)
            }}</option></select
          ></label
        >
        <button :aria-pressed="near" @click="near = !near">{{
          near ? '近价 ±30%' : '全部行权价'
        }}</button>
        <button :aria-pressed="table" @click="table = !table">{{
          table ? '查看图表' : '查看数据'
        }}</button>
      </div>
      <p class="gex-meta"
        >{{ snapshot.status === 'stale' || snapshot.status === 'degraded' ? '待更新 · ' : '' }}OI
        覆盖 {{ coverage }}% · 纳入 {{ snapshot.legs.length }} /
        {{ snapshot.totalContracts }} 个合约 · 排除 {{ snapshot.excludedContracts }} 个</p
      >
      <p v-if="market === 'deribit'" class="gex-meta"
        >行情 {{ timestamp(snapshot.asOf) }} · 参考远期中位数 ${{
          number(Number(snapshot.underlyingPrice))
        }}</p
      >
      <p v-else class="gex-meta"
        >标的最近成交 {{ timestamp(snapshot.underlyingLastTradeAt) }} · ${{
          number(Number(snapshot.underlyingPrice))
        }}
        · 延迟行情</p
      >
    </template>
    <div
      v-show="snapshot && !table"
      ref="chartRef"
      class="gex-chart"
      role="img"
      :aria-label="`${market} 按行权价的 Gamma 敞口估算`"
    ></div>
    <template v-if="snapshot">
      <div v-if="table" class="gex-table"
        ><table
          ><thead
            ><tr
              ><th>行权价</th><th>Call USD</th><th>Put USD（负号）</th><th>净代理值 USD</th></tr
            ></thead
          ><tbody
            ><tr v-for="row in rows" :key="row.strike"
              ><td>{{ number(row.strike) }}</td
              ><td>{{ number(row.call) }}</td
              ><td>{{ number(-row.put) }}</td
              ><td>{{ number(row.call - row.put) }}</td></tr
            ></tbody
          ></table
        ></div
      >
      <p v-if="!rows.length" class="gex-meta">此筛选范围内没有合约。</p>
      <p class="gex-definition"
        >Call 取正、Put 取负的 OI 敞口代理，不代表交易商实际持仓。单位为标的价格变动 1% 对应的美元
        Delta 变化。</p
      >
      <p class="gex-definition">{{
        market === 'deribit'
          ? 'Gamma 由 Deribit 远期价格、标记隐波与剩余期限估算；假设各期限远期同步变动 1%，OI 已以 BTC 计量。'
          : '使用 Cboe 公布的 Gamma，标准合约乘数 100 股。源站未提供完整报价时间与 OI 日期；正 OI 但隐波缺失的合约已排除。'
      }}</p>
      <p class="gex-meta"
        ><a :href="snapshot.sourceUrl" target="_blank" rel="noopener noreferrer">{{
          snapshot.source
        }}</a>
        · 采集 {{ timestamp(snapshot.collectedAt) }}</p
      >
    </template>
  </div>
</template>

<style scoped>
  .gex-panel {
    min-width: 0;
    padding: 0 20px 18px;
  }

  .gex-controls {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
  }

  button,
  select {
    padding: 5px 8px;
    border: 1px solid #dbe4ea;
    border-radius: 7px;
    background: white;
    font-size: 12px;
    cursor: pointer;
  }

  .gex-meta,
  .gex-definition {
    margin: 8px 0;
    color: #64748b;
    font-size: 12px;
    line-height: 1.7;
    overflow-wrap: anywhere;
  }

  .gex-definition {
    color: #475569;
  }

  .gex-chart {
    width: 100%;
    min-width: 0;
    height: auto;
    min-height: 280px;
    max-height: 420px;
    aspect-ratio: 1.8;
  }

  .gex-table {
    max-height: 340px;
    overflow: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-variant-numeric: tabular-nums;
  }

  th,
  td {
    padding: 7px;
    border-bottom: 1px solid #edf1f5;
    font-size: 12px;
    text-align: right;
    white-space: nowrap;
  }

  th {
    position: sticky;
    top: 0;
    background: #f8fafc;
  }

  button:focus-visible,
  select:focus-visible {
    outline: 2px solid #165dff;
    outline-offset: 2px;
  }
</style>
