<template
  ><div>
    <p v-if="error">{{ error }}</p>
    <div v-show="!error && rows.length">
      <div class="chart-legend"
        ><label
          >到期日
          <select v-model="expiry"
            ><option value="">全部到期日</option
            ><option v-for="day in expiries" :key="day" :value="day">{{
              day.slice(0, 10)
            }}</option></select
          ></label
        ><span
          >24小时看涨成交 {{ totals.callVolume.toLocaleString() }} BTC · 看跌成交
          {{ totals.putVolume.toLocaleString() }} BTC</span
        ></div
      >
      <h5>按行权价的未平仓量</h5
      ><div
        ref="strikeEl"
        class="option-distribution-chart"
        role="img"
        aria-label="按行权价的看涨和看跌期权未平仓量"
      ></div>
      <div class="option-distribution-metrics"
        ><span
          >看涨持仓 <b>{{ totals.calls.toLocaleString() }} BTC</b></span
        ><span
          >看跌持仓 <b>{{ totals.puts.toLocaleString() }} BTC</b></span
        ><span
          >总持仓 <b>{{ (totals.calls + totals.puts).toLocaleString() }} BTC</b></span
        ><span
          >Put / Call
          <b>{{ totals.calls ? (totals.puts / totals.calls).toFixed(2) : '—' }}</b></span
        ></div
      >
      <h5>按到期日的未平仓量</h5
      ><div
        ref="expiryEl"
        class="option-distribution-chart"
        role="img"
        aria-label="各到期日实值和虚值期权未平仓量"
      ></div>
      <p>Deribit · {{ asOf }} · BTC</p> </div
    ><p v-if="!error && !rows.length">正在读取期权分布…</p>
  </div></template
>
<script setup lang="ts">
  import { computed, onMounted, ref, shallowRef, watch, type Ref } from 'vue';
  import { getCryptoDashboardV1 } from '@/api/hedgeResearch';
  import { useECharts } from '@/hooks/web/useECharts';

  const rows = shallowRef<
    Array<{
      instrument: string;
      expiry: string;
      strike: number;
      side: string;
      openInterest: number;
      volume: number;
      underlyingPrice: number | null;
    }>
  >([]);
  const expiry = ref(''),
    asOf = ref(''),
    error = ref('');
  const strikeEl = ref<HTMLDivElement | null>(null),
    expiryEl = ref<HTMLDivElement | null>(null);
  const strikeChart = useECharts(strikeEl as Ref<HTMLDivElement>, 'light'),
    expiryChart = useECharts(expiryEl as Ref<HTMLDivElement>, 'light');
  const expiries = computed(() => [...new Set(rows.value.map((r) => r.expiry))].sort());
  const selected = computed(() =>
    rows.value.filter((r) => !expiry.value || r.expiry === expiry.value),
  );
  const totals = computed(() =>
    selected.value.reduce(
      (a, r) => {
        a[r.side === 'C' ? 'calls' : 'puts'] += r.openInterest;
        a[r.side === 'C' ? 'callVolume' : 'putVolume'] += r.volume;
        return a;
      },
      { calls: 0, puts: 0, callVolume: 0, putVolume: 0 },
    ),
  );
  function options(
    labels: string[],
    series: Array<{ name: string; data: Array<number | null>; color: string; stack?: string }>,
  ) {
    return {
      animation: false,
      tooltip: { trigger: 'axis', confine: true },
      legend: { data: series.map((s) => s.name), top: 0 },
      grid: { left: 15, right: 15, top: 42, bottom: 60, containLabel: true },
      xAxis: { type: 'category', data: labels, axisLabel: { rotate: 35, hideOverlap: true } },
      yAxis: { type: 'value', name: 'BTC' },
      dataZoom: [
        { type: 'inside', filterMode: 'filter' },
        { type: 'slider', filterMode: 'filter', height: 18, bottom: 0 },
      ],
      series: series.map((s) => ({ ...s, type: 'bar', itemStyle: { color: s.color } })),
    };
  }
  watch(
    [selected, strikeEl, expiryEl],
    () => {
      const strikes = [...new Set(selected.value.map((r) => r.strike))].sort((a, b) => a - b);
      const sum = (list: typeof rows.value) => list.reduce((v, r) => v + r.openInterest, 0);
      strikeChart.setOptions(
        options(
          strikes.map(String),
          ['C', 'P'].map((side, i) => ({
            name: i ? '看跌' : '看涨',
            color: i ? '#e2c82b' : '#4d84ff',
            data: strikes.map((strike) =>
              sum(selected.value.filter((r) => r.strike === strike && r.side === side)),
            ),
          })),
        ) as any,
      );
      const dates = [...new Set(selected.value.map((r) => r.expiry))].sort();
      const groups = [
        ['C', true, '实值看涨', '#79a3ff'],
        ['C', false, '虚值看涨', '#2456d4'],
        ['P', true, '实值看跌', '#ead24a'],
        ['P', false, '虚值看跌', '#a28c00'],
      ] as const;
      expiryChart.setOptions(
        options(
          dates.map((d) => d.slice(0, 10)),
          groups.map(([side, itm, name, color]) => ({
            name,
            color,
            stack: side,
            data: dates.map((day) => {
              const list = selected.value.filter((r) => r.expiry === day && r.side === side);
              if (list.some((r) => r.underlyingPrice == null)) return null;
              return sum(
                list.filter(
                  (r) =>
                    (side === 'C'
                      ? r.strike < Number(r.underlyingPrice)
                      : r.strike > Number(r.underlyingPrice)) === itm,
                ),
              );
            }),
          })),
        ) as any,
      );
    },
    { flush: 'post' },
  );
  onMounted(async () => {
    try {
      const d = await getCryptoDashboardV1();
      rows.value = d.optionDistribution?.rows ?? [];
      asOf.value = d.optionDistribution?.asOf ?? '';
    } catch (e) {
      error.value = e instanceof Error ? e.message : '期权分布不可用';
    }
  });
</script>
<style scoped>
  .option-distribution-chart {
    width: 100%;
    height: 320px;
  }

  .option-distribution-metrics {
    display: flex;
    flex-wrap: wrap;
    gap: 24px;
  }

  .option-distribution-metrics b {
    display: block;
  }

  p {
    color: #64748b;
    font-size: 12px;
  }
</style>
