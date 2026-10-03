<template>
  <section class="basis-panel">
    <div class="basis-panel__head">
      <div>
        <h3>期现价差</h3>
        <p>合约mid - 现货mid</p>
      </div>
      <div class="basis-panel__ranges" role="group" aria-label="期现价差时间范围">
        <a
          class="basis-panel__template-link"
          href="https://cn.tradingview.com/chart/fLzPjgRY/"
          target="_blank"
          rel="noopener noreferrer"
        >
          tradingview模板
        </a>
        <button
          v-for="range in ranges"
          :key="range.label"
          type="button"
          :class="{ active: selectedRange === range.label }"
          @click="selectedRange = range.label"
        >
          {{ range.label }}
        </button>
      </div>
    </div>
    <p v-if="loading" class="basis-panel__status" role="status">正在读取期现价差…</p>
    <p v-else-if="error" class="basis-panel__status basis-panel__status--error" role="alert">
      {{ error }}
    </p>
    <div ref="chartRef" class="basis-panel__chart"></div>
  </section>
</template>

<script setup lang="ts">
  import { ref, watch, type Ref } from 'vue';
  import { useKeepAliveActive } from '@/hooks/web/useKeepAliveActive';
  import { useECharts } from '@/hooks/web/useECharts';
  import { researchSeries, type ResearchResponse } from '@/api/platform/strategyResearch';

  const symbols = ['XAUT', 'BTC', 'ETH', 'CRCL', 'MSTR'] as const;
  const chartRef = ref<HTMLDivElement>();
  const chart = useECharts(chartRef as Ref<HTMLDivElement>);
  const pageActive = useKeepAliveActive();
  const rowsBySymbol = ref<Record<string, Array<Record<string, any>>>>({});
  const loading = ref(false);
  const error = ref('');
  const ranges = [
    { label: '近24小时', hours: 24 },
    { label: '近7日', hours: 24 * 7 },
    { label: '近30日', hours: 24 * 30 },
  ] as const;
  const selectedRange = ref<(typeof ranges)[number]['label']>('近24小时');
  let timer: ReturnType<typeof setInterval> | undefined;

  function rowsFrom(response: ResearchResponse) {
    return (response.data?.rows || []) as Array<Record<string, any>>;
  }

  function rowsBySymbolFrom(response: ResearchResponse) {
    const seriesBySymbol = (response.data as Record<string, any> | undefined)?.seriesBySymbol;
    if (seriesBySymbol && typeof seriesBySymbol === 'object') {
      return seriesBySymbol as Record<string, Array<Record<string, any>>>;
    }
    return { BTC: rowsFrom(response) };
  }

  async function load() {
    loading.value = true;
    error.value = '';
    const end = new Date();
    const range = ranges.find((item) => item.label === selectedRange.value) ?? ranges[0];
    const start = new Date(end.getTime() - range.hours * 60 * 60 * 1000);
    try {
      const response = await researchSeries(
        'funding-btc',
        start.toISOString(),
        end.toISOString(),
        'valid',
        '15m',
        'ALL',
      );
      rowsBySymbol.value = rowsBySymbolFrom(response);
    } catch {
      rowsBySymbol.value = {};
    }
    if (!Object.keys(rowsBySymbol.value).length) error.value = '期现价差暂不可用，请稍后刷新。';
    loading.value = false;
  }

  function render() {
    const selected = (chart.getInstance()?.getOption()?.legend as any)?.[0]?.selected;
    const series = symbols
      .map((symbol) => ({
        name: symbol,
        type: 'line' as const,
        showSymbol: false,
        connectNulls: false,
        data: (rowsBySymbol.value[symbol] || []).map((row) => [
          Number(row.timeMs),
          row.ohlc?.midSpread?.close ?? null,
        ]),
      }))
      .filter((item) => item.data.length);
    void chart.setOptions({
      color: ['#d79a1e', '#3478d4', '#22a06b', '#cf4b5f', '#8b5fbf'],
      tooltip: { trigger: 'axis' },
      legend: { data: Array.from(symbols), selected },
      grid: { left: 58, right: 24, top: 40, bottom: 48 },
      xAxis: { type: 'time' },
      yAxis: { type: 'value', name: 'USDT', scale: true },
      dataZoom: [{ type: 'inside' }, { type: 'slider', height: 16, bottom: 8 }],
      series,
    });
  }

  watch(rowsBySymbol, render, { deep: true });
  watch(selectedRange, () => {
    if (pageActive.value) void load();
  });
  watch(pageActive, (active) => {
    if (active) {
      void load();
      timer = setInterval(() => void load(), 60_000);
    } else if (timer) {
      clearInterval(timer);
      timer = undefined;
    }
  });
</script>

<style scoped lang="less">
  .basis-panel {
    display: grid;
    gap: 10px;
    padding: var(--strategy-space-4);
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-panel);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-soft);
  }

  .basis-panel__head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
  }

  .basis-panel h3 {
    margin: 0;
    color: var(--strategy-text-1);
    font-family: var(--strategy-font-sans);
    font-size: 17px;
    font-weight: 800;
  }

  .basis-panel__head p,
  .basis-panel__head > span,
  .basis-panel__status {
    margin: 4px 0 0;
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  .basis-panel__ranges {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 6px;
  }

  .basis-panel__ranges button {
    padding: 5px 10px;
    border: 1px solid var(--strategy-border);
    border-radius: 8px;
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
    font-size: 12px;
    cursor: pointer;
  }

  .basis-panel__template-link {
    display: inline-flex;
    align-items: center;
    padding: 5px 10px;
    border: 1px solid var(--strategy-border);
    border-radius: 8px;
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
    font-size: 12px;
    line-height: 1.4;
    text-decoration: none;
  }

  .basis-panel__template-link:hover,
  .basis-panel__template-link:focus-visible {
    border-color: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
  }

  .basis-panel__ranges button.active {
    border-color: var(--strategy-accent-soft);
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
    font-weight: 700;
  }

  .basis-panel__status--error {
    color: var(--strategy-danger);
  }

  .basis-panel__chart {
    min-height: 300px;
  }

  @media (max-width: 700px) {
    .basis-panel__head {
      flex-direction: column;
      gap: 4px;
    }

    .basis-panel__ranges {
      justify-content: flex-start;
    }
  }
</style>
