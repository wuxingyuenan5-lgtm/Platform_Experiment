<template>
  <section class="detail-panel">
    <div class="compact-shell">
      <section class="chart-grid">
        <article class="chart-card">
          <div class="chart-toolbar">
            <h3>期现价差</h3>
            <div class="chart-controls">
              <label
                >标的<select
                  :value="symbol"
                  @change="emit('update:symbol', ($event.target as HTMLSelectElement).value)"
                >
                  <option v-for="item in symbolOptions" :key="item" :value="item">{{
                    item
                  }}</option>
                </select></label
              >
              <div class="range-tabs" aria-label="价差窗口">
                <button
                  v-for="days in rangeOptions"
                  :key="days"
                  type="button"
                  :class="{ active: days === rangeDays }"
                  @click="emit('update:range-days', days)"
                  >近 {{ days }} 日</button
                >
              </div>
              <label
                >级别<select
                  :value="resolution"
                  @change="
                    emit(
                      'update:resolution',
                      ($event.target as HTMLSelectElement).value as BasisResolution,
                    )
                  "
                >
                  <option v-for="item in resolutionOptions" :key="item.value" :value="item.value">{{
                    item.label
                  }}</option>
                </select></label
              >
            </div>
          </div>
          <p v-if="!rows.length" role="status">所选窗口暂无有效高精度价差；缺口不补零。</p>
          <div ref="basisChartRef" class="borrow-chart"></div>
        </article>
        <article class="chart-card">
          <div class="chart-toolbar"><h3>借贷费率</h3><span>公开 VIP 0 · USDT · 1H</span></div>
          <p v-if="!borrowRows.length" role="status"
            >所选窗口暂无借贷费率观测；账户实际费率未知。</p
          >
          <div ref="borrowChartRef" class="borrow-chart"></div>
        </article>
      </section>
      <section class="table-grid">
        <article class="table-card">
          <div class="table-head"><h3>期现价差表</h3></div>
          <div class="table-scroll"
            ><table class="data-table"
              ><thead
                ><tr
                  ><th>时间</th><th>中间价差</th><th>买价差</th><th>卖价差</th><th>有效毫秒</th></tr
                ></thead
              >
              <tbody
                ><tr v-for="row in rows.slice(-100)" :key="row.timeMs"
                  ><td>{{ formatTime(row.timeMs) }}</td
                  ><td>{{ row.ohlc?.midSpread?.close ?? '未知' }}</td
                  ><td>{{ row.ohlc?.buySpread?.close ?? '未知' }}</td
                  ><td>{{ row.ohlc?.sellSpread?.close ?? '未知' }}</td
                  ><td>{{ row.validDurationMs }}</td></tr
                >
                <tr v-if="!rows.length"><td colspan="5">暂无已采集样本</td></tr></tbody
              ></table
            ></div
          >
        </article>
        <article class="table-card">
          <div class="table-head"><h3>借贷费率表</h3></div>
          <div class="table-scroll"
            ><table class="data-table"
              ><thead
                ><tr
                  ><th>观测时间</th><th>每小时利率（小数）</th><th>净 Carry</th
                  ><th>来源口径</th></tr
                ></thead
              >
              <tbody
                ><tr v-for="row in borrowRows" :key="row.at"
                  ><td>{{ new Date(row.at).toLocaleString() }}</td
                  ><td>{{ row.rate }}</td
                  ><td>成本覆盖不足</td><td>Bybit 公开 VIP 0；非账户费率</td></tr
                >
                <tr v-if="!borrowRows.length"><td colspan="4">暂无观测，不推定为零</td></tr></tbody
              ></table
            ></div
          >
        </article>
      </section>
    </div>
  </section>
</template>
<script setup lang="ts">
  import { onMounted, ref, watch, type Ref } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';

  type BasisResolution = '15m' | '1h' | '8h' | '1d';
  const rangeOptions = [1, 7, 30] as const;
  const resolutionOptions = [
    { value: '15m' as const, label: '15min' },
    { value: '1h' as const, label: '1H' },
    { value: '8h' as const, label: '8H' },
    { value: '1d' as const, label: '日' },
  ];
  const props = withDefaults(
    defineProps<{
      rows: Array<{
        timeMs?: string;
        validDurationMs?: number;
        ohlc?: Record<string, { close: string }>;
      }>;
      borrowRows?: Array<{ at: string; rate: string }>;
      symbol?: string;
      symbolOptions?: string[];
      rangeDays?: 1 | 7 | 30;
      resolution?: BasisResolution;
    }>(),
    {
      borrowRows: () => [],
      symbol: 'BTC',
      symbolOptions: () => ['BTC'],
      rangeDays: 1,
      resolution: '15m',
    },
  );
  const emit = defineEmits<{
    (e: 'update:symbol', value: string): void;
    (e: 'update:range-days', value: 1 | 7 | 30): void;
    (e: 'update:resolution', value: BasisResolution): void;
  }>();
  const basisChartRef = ref<HTMLDivElement>();
  const borrowChartRef = ref<HTMLDivElement>();
  const basisChart = useECharts(basisChartRef as Ref<HTMLDivElement>);
  const borrowChart = useECharts(borrowChartRef as Ref<HTMLDivElement>);
  function formatTime(value?: string) {
    return value ? new Date(Number(value)).toLocaleString() : '未知';
  }
  function render() {
    const common = {
      tooltip: {
        trigger: 'axis' as const,
        formatter: (items: any) => {
          const rows = Array.isArray(items) ? items : [items];
          return rows
            .map(
              (item) => `${item.seriesName}: ${item.data?.exactPrice ?? item.value?.[1] ?? '未知'}`,
            )
            .join('<br/>');
        },
      },
      grid: { left: 60, right: 20, top: 36, bottom: 68 },
      xAxis: { type: 'time' as const },
      yAxis: { type: 'value' as const, scale: true },
      dataZoom: [{ type: 'inside' as const }, { type: 'slider' as const, height: 16, bottom: 8 }],
    };
    const previousLegend = (basisChart.getInstance()?.getOption()?.legend as any)?.[0]?.selected;
    void basisChart.setOptions({
      ...common,
      color: ['#d79a1e', '#cf3f4f', '#2db87c'],
      legend: {
        data: ['中间价差', '买价差', '卖价差'],
        selected: previousLegend || { 中间价差: true, 买价差: false, 卖价差: false },
      },
      series: ['midSpread', 'buySpread', 'sellSpread'].map((key, i) => ({
        name: ['中间价差', '买价差', '卖价差'][i],
        type: 'line' as const,
        showSymbol: false,
        connectNulls: false,
        data: props.rows.flatMap((r) => {
          const value = r.ohlc?.[key]?.close;
          return value == null ? [] : [{ value: [Number(r.timeMs), value], exactPrice: value }];
        }),
      })),
    });
    void borrowChart.setOptions({
      ...common,
      color: ['#f2c94c'],
      series: [
        {
          name: '每小时利率（%）',
          type: 'line',
          showSymbol: true,
          connectNulls: false,
          data: props.borrowRows.map((r) => [Date.parse(r.at), Number(r.rate) * 100]),
        },
      ],
    });
  }
  watch(() => [props.rows, props.borrowRows], render, { deep: true });
  onMounted(render);
</script>
<style scoped lang="less">
  .table-scroll {
    max-height: 380px;
    overflow: auto;
  }

  .detail-panel {
    padding: var(--strategy-space-5);
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-panel);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-card);
  }

  .chart-toolbar h3,
  .table-head h3 {
    margin: 0;
    color: var(--strategy-text-1);
    font-family: var(--strategy-font-sans);
    font-size: 16px;
    font-weight: 800;
  }

  .compact-shell {
    display: flex;
    flex-direction: column;
    gap: 16px;
    margin-top: 18px;
  }

  .chart-card,
  .table-card {
    padding: var(--strategy-space-4);
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-panel);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-soft);
  }

  .chart-grid,
  .table-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
  }

  .chart-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }

  .chart-controls {
    display: flex;
    flex-wrap: wrap;
    align-items: end;
    justify-content: flex-end;
    gap: 8px;
  }

  .chart-controls label {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  .chart-controls select {
    min-height: 30px;
    padding: 4px 8px;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
  }

  .range-tabs {
    display: inline-flex;
    gap: 4px;
  }

  .range-tabs button {
    padding: 6px 8px;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
    cursor: pointer;
  }

  .range-tabs button.active {
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
  }

  .borrow-chart {
    height: 360px;
    margin-top: 14px;
  }

  .data-table {
    width: 100%;
    margin-top: 12px;
    border-collapse: collapse;
  }

  .data-table th,
  .data-table td {
    padding: 12px 10px;
    border-bottom: 1px solid var(--strategy-border-soft);
    font-size: var(--strategy-font-sm);
    text-align: left;
  }

  .data-table th {
    background: var(--strategy-table-head-bg);
    color: var(--strategy-text-3);
    font-weight: 700;
  }

  .tone-positive {
    color: #16a34a;
  }

  .tone-negative {
    color: #dc2626;
  }

  @media (max-width: 1180px) {
    .chart-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 960px) {
    .table-grid {
      grid-template-columns: 1fr;
    }

    .chart-toolbar {
      flex-direction: column;
      align-items: flex-start;
    }

    .chart-controls {
      justify-content: flex-start;
    }
  }
</style>
