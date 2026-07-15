<template>
  <section class="funding-terminal">
    <div class="terminal-toolbar">
      <div class="toolbar-left">
        <button
          v-for="item in viewTabs"
          :key="item.key"
          type="button"
          :class="{ 'is-active': activeView === item.key }"
          @click="activeView = item.key"
        >
          {{ item.label }}
        </button>
      </div>

      <div class="toolbar-right">
        <label>
          <span>交易所</span>
          <select v-model="selectedExchange">
            <option v-for="item in exchanges" :key="item" :value="item">{{ item }}</option>
          </select>
        </label>
        <label>
          <span>排序</span>
          <select v-model="selectedSort">
            <option value="carry">净 carry</option>
            <option value="funding">费率</option>
            <option value="liquidity">流动性</option>
          </select>
        </label>
      </div>
    </div>

    <div class="terminal-body">
      <article class="terminal-panel terminal-panel--table">
        <header>
          <div>
            <p class="panel-eyebrow">Funding Opportunity Board</p>
            <h3>{{ activeViewLabel }}</h3>
          </div>
          <span class="panel-meta">{{ selectedExchange }} · 6 symbols</span>
        </header>

        <div class="table-shell">
          <table>
            <thead>
              <tr>
                <th>币种</th>
                <th>费率</th>
                <th>净 carry</th>
                <th>借贷</th>
                <th>流动性</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in filteredRows"
                :key="item.symbol"
                :class="{ 'is-selected': item.symbol === selectedSymbol }"
                @click="selectedSymbol = item.symbol"
              >
                <td>{{ item.symbol }}</td>
                <td :class="toneClass(item.funding)">{{ formatRate(item.funding) }}</td>
                <td :class="toneClass(item.carry)">{{ formatRate(item.carry) }}</td>
                <td :class="toneClass(-item.borrow)">{{ item.borrow.toFixed(2) }}%</td>
                <td>{{ item.liquidity }}</td>
                <td>
                  <span class="status-chip" :class="`is-${item.statusTone}`">{{ item.status }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </article>

      <article class="terminal-panel terminal-panel--detail">
        <header>
          <div>
            <p class="panel-eyebrow">Position Snapshot</p>
            <h3>{{ selectedRow.symbol }} 当前持仓与费率执行</h3>
          </div>
        </header>

        <div class="legend-switches legend-switches--center">
          <button
            v-for="legend in legends"
            :key="legend.key"
            type="button"
            :class="{ 'is-active': visibleSeries.includes(legend.key) }"
            @click="toggleSeries(legend.key)"
          >
            {{ legend.label }}
          </button>
        </div>

        <div class="detail-kpis">
          <div v-for="item in selectedRow.kpis" :key="item.label" class="kpi-card">
            <span>{{ item.label }}</span>
            <strong :class="item.tone ? `is-${item.tone}` : ''">{{ item.value }}</strong>
          </div>
        </div>

        <div ref="chartRef" class="detail-chart"></div>

        <div class="position-table">
          <table>
            <thead>
              <tr>
                <th>币种</th>
                <th>数量</th>
                <th>现货价值</th>
                <th>未实现盈亏</th>
                <th>现货数量</th>
                <th>永续 bid</th>
                <th>费率年化</th>
                <th>参考序列</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="position in selectedRow.positions" :key="position.symbol">
                <td>{{ position.symbol }}</td>
                <td>{{ position.qty }}</td>
                <td>{{ position.spotValue }}</td>
                <td :class="position.pnl.startsWith('-') ? 'is-negative' : 'is-positive'">
                  {{ position.pnl }}
                </td>
                <td>{{ position.spotQty }}</td>
                <td>{{ position.perpBid }}</td>
                <td class="is-positive">{{ position.annualized }}</td>
                <td>{{ position.queue }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
  import type { Ref } from 'vue';
  import { computed, nextTick, onMounted, ref, watch } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';

  type ViewKey = 'watch' | 'positions' | 'queue';
  type SortKey = 'carry' | 'funding' | 'liquidity';
  type SeriesKey = 'funding' | 'price' | 'carry';

  interface FundingRow {
    symbol: string;
    funding: number;
    carry: number;
    borrow: number;
    liquidity: string;
    status: string;
    statusTone: 'positive' | 'negative' | 'neutral';
    kpis: Array<{ label: string; value: string; tone?: 'positive' | 'negative' | 'neutral' }>;
    chart: {
      dates: string[];
      funding: number[];
      price: number[];
      carry: number[];
    };
    positions: Array<{
      symbol: string;
      qty: string;
      spotValue: string;
      pnl: string;
      spotQty: string;
      perpBid: string;
      annualized: string;
      queue: string;
    }>;
  }

  const viewTabs: Array<{ key: ViewKey; label: string }> = [
    { key: 'watch', label: '费率监控' },
    { key: 'positions', label: '当前持仓' },
    { key: 'queue', label: '执行队列' },
  ];

  const legends: Array<{ key: SeriesKey; label: string }> = [
    { key: 'funding', label: '持仓加权费率' },
    { key: 'carry', label: '净 carry' },
    { key: 'price', label: '价格' },
  ];

  const exchanges = ['Bybit', 'Binance', 'OKX'];
  const chartRef = ref<HTMLDivElement | null>(null);
  const { setOptions, resize } = useECharts(chartRef as Ref<HTMLDivElement>);

  const activeView = ref<ViewKey>('watch');
  const selectedExchange = ref('Bybit');
  const selectedSort = ref<SortKey>('carry');
  const selectedSymbol = ref('BTC');
  const visibleSeries = ref<SeriesKey[]>(['funding', 'carry', 'price']);

  const rows = ref<Record<string, FundingRow[]>>({
    Bybit: [
      makeRow('BTC', 0.0054, 9.4, 1.7, '$68M', '主池', 'positive', ['06-18', '06-19', '06-20', '06-21', '06-22', '06-23', '06-24'], [0.0031, 0.0044, 0.0058, 0.0046, 0.0062, 0.0056, 0.0054], [93800, 92700, 91400, 90500, 91800, 91000, 90600], [8.2, 8.6, 9.1, 8.8, 9.8, 9.5, 9.4], '20000', '0.0105', '1.313', '5.78'),
      makeRow('ETH', -0.0028, 7.6, 1.9, '$41M', '观察', 'neutral', ['06-18', '06-19', '06-20', '06-21', '06-22', '06-23', '06-24'], [-0.0012, -0.0024, -0.0018, -0.0021, -0.0032, -0.0029, -0.0028], [3560, 3490, 3412, 3364, 3426, 3384, 3356], [6.9, 7.2, 7.0, 6.8, 7.7, 7.5, 7.6], '16000', '0.0153', '2.157', '1'),
      makeRow('SOL', 0.0102, 14.8, 2.8, '$26M', '高弹性', 'positive', ['06-18', '06-19', '06-20', '06-21', '06-22', '06-23', '06-24'], [0.0041, 0.0058, 0.0061, 0.0076, 0.0092, 0.0109, 0.0102], [142, 138, 133, 129, 134, 131, 128], [11.8, 12.2, 12.8, 13.6, 14.1, 15.0, 14.8], '16000', '0.0185', '3.104', '3'),
      makeRow('DOGE', -0.0003, 10.1, 2.1, '$18M', '短窗', 'neutral', ['06-18', '06-19', '06-20', '06-21', '06-22', '06-23', '06-24'], [0.0008, 0.0004, -0.0006, -0.0003, -0.0001, -0.0004, -0.0003], [0.123, 0.118, 0.111, 0.108, 0.114, 0.112, 0.109], [9.2, 9.6, 10.4, 10.0, 10.2, 10.3, 10.1], '20000', '0.0143', '0.864', '3'),
      makeRow('XRP', -0.0038, 9.5, 2.0, '$22M', '备选', 'neutral', ['06-18', '06-19', '06-20', '06-21', '06-22', '06-23', '06-24'], [-0.001, -0.0022, -0.0035, -0.0031, -0.0041, -0.0040, -0.0038], [0.54, 0.53, 0.51, 0.49, 0.5, 0.49, 0.48], [8.8, 9.0, 9.1, 9.4, 9.8, 9.7, 9.5], '20000', '0.0175', '2.157', '1'),
      makeRow('XAUT', 0.0012, 5.4, 1.4, '$9M', '补充', 'negative', ['06-18', '06-19', '06-20', '06-21', '06-22', '06-23', '06-24'], [0.0015, 0.0016, 0.0013, 0.0014, 0.0012, 0.0011, 0.0012], [2358, 2355, 2349, 2351, 2345, 2338, 2335], [5.8, 5.9, 5.6, 5.7, 5.3, 5.2, 5.4], '12000', '0.0080', '0.745', '2'),
    ],
    Binance: [
      makeRow('BTC', 0.008, 12.4, 2.1, '$90M', '主池', 'positive', ['06-18', '06-19', '06-20', '06-21', '06-22', '06-23', '06-24'], [0.0068, 0.0072, 0.0074, 0.0078, 0.0081, 0.0082, 0.008], [94400, 93600, 92700, 91800, 92400, 91500, 91200], [11.2, 11.5, 11.9, 12.1, 12.7, 12.8, 12.4], '20000', '0.0105', '1.313', '2'),
      makeRow('ETH', -0.0041, 9.1, 2.4, '$52M', '观察', 'neutral', ['06-18', '06-19', '06-20', '06-21', '06-22', '06-23', '06-24'], [-0.0025, -0.0031, -0.0038, -0.0044, -0.0046, -0.0041, -0.0041], [3618, 3540, 3468, 3402, 3450, 3398, 3371], [8.3, 8.8, 9.0, 9.2, 9.6, 9.3, 9.1], '16000', '0.0175', '2.157', '1'),
    ],
    OKX: [
      makeRow('BTC', 0.0062, 10.6, 1.8, '$71M', '标准样本', 'positive', ['06-18', '06-19', '06-20', '06-21', '06-22', '06-23', '06-24'], [0.0049, 0.0053, 0.0059, 0.0063, 0.0061, 0.0064, 0.0062], [94220, 93480, 92520, 91580, 92210, 91620, 91110], [9.6, 9.9, 10.2, 10.6, 10.8, 10.7, 10.6], '18000', '0.0127', '1.102', '1'),
      makeRow('ETH', -0.0034, 8.4, 2.1, '$47M', '平衡', 'neutral', ['06-18', '06-19', '06-20', '06-21', '06-22', '06-23', '06-24'], [-0.0021, -0.0028, -0.0033, -0.0036, -0.0035, -0.0034, -0.0034], [3584, 3520, 3448, 3388, 3432, 3386, 3352], [7.6, 7.9, 8.1, 8.3, 8.5, 8.5, 8.4], '16000', '0.0158', '1.874', '2'),
    ],
  });

  const activeViewLabel = computed(() => viewTabs.find((item) => item.key === activeView.value)?.label ?? '费率监控');
  const filteredRows = computed(() => {
    const source = rows.value[selectedExchange.value] ?? [];
    const next = [...source];
    if (activeView.value === 'positions') return next.filter((item) => item.status !== '补充');
    if (activeView.value === 'queue') return next.filter((item) => item.status !== '主池');
    return next.sort((a, b) => {
      if (selectedSort.value === 'funding') return b.funding - a.funding;
      if (selectedSort.value === 'liquidity') return parseLiquidity(b.liquidity) - parseLiquidity(a.liquidity);
      return b.carry - a.carry;
    });
  });
  const selectedRow = computed(() => {
    const source = filteredRows.value;
    return source.find((item) => item.symbol === selectedSymbol.value) ?? source[0];
  });

  watch(
    filteredRows,
    (next) => {
      if (!next.some((item) => item.symbol === selectedSymbol.value)) {
        selectedSymbol.value = next[0]?.symbol ?? 'BTC';
      }
    },
    { immediate: true },
  );

  watch([selectedRow, visibleSeries], () => renderChart(), { deep: true });
  watch([selectedExchange, activeView, selectedSort], () => nextTick(() => renderChart()));
  onMounted(() => renderChart());

  function makeRow(
    symbol: string,
    funding: number,
    carry: number,
    borrow: number,
    liquidity: string,
    status: string,
    statusTone: 'positive' | 'negative' | 'neutral',
    dates: string[],
    fundingSeries: number[],
    priceSeries: number[],
    carrySeries: number[],
    targetPosition: string,
    avgFunding: string,
    feeAnnual: string,
    queue: string,
  ): FundingRow {
    return {
      symbol,
      funding,
      carry,
      borrow,
      liquidity,
      status,
      statusTone,
      kpis: [
        { label: '目标仓位', value: targetPosition },
        { label: '平均费率', value: `${avgFunding}%`, tone: 'positive' },
        { label: '费率年化', value: `${feeAnnual}%`, tone: 'positive' },
        { label: '策略排序', value: queue },
      ],
      chart: { dates, funding: fundingSeries, price: priceSeries, carry: carrySeries },
      positions: [
        {
          symbol,
          qty: symbol === 'DOGE' ? '-2249467' : symbol === 'XRP' ? '-151.36' : '-1972',
          spotValue: symbol === 'DOGE' ? '11006.71' : symbol === 'BTC' ? '12423.88' : '6269.28',
          pnl: symbol === 'XAUT' ? '-25.1' : symbol === 'BTC' ? '186.2' : symbol === 'ETH' ? '-163.9' : '43.3',
          spotQty: symbol === 'DOGE' ? '2294499.158' : symbol === 'BTC' ? '1971.952' : '1513.4886',
          perpBid: symbol === 'BTC' ? '6.30783' : symbol === 'ETH' ? '40.55' : '0.11748',
          annualized: `${feeAnnual}%`,
          queue,
        },
      ],
    };
  }

  async function renderChart() {
    if (!selectedRow.value) return;
    const series: any[] = [];
    if (visibleSeries.value.includes('funding')) {
      series.push({
        name: '持仓加权费率',
        type: 'bar',
        barWidth: 14,
        itemStyle: {
          color: (params: any) => (Number(params?.data ?? params?.value ?? 0) >= 0 ? '#34d399' : '#fb7185'),
        },
        data: selectedRow.value.chart.funding,
      });
    }
    if (visibleSeries.value.includes('carry')) {
      series.push({
        name: '净 carry',
        type: 'line',
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#f4c35a' },
        data: selectedRow.value.chart.carry,
      });
    }
    if (visibleSeries.value.includes('price')) {
      series.push({
        name: '价格',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbol: 'none',
        lineStyle: { width: 2, color: '#60a5fa' },
        data: selectedRow.value.chart.price,
      });
    }

    await setOptions({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis' },
      legend: { show: false },
      grid: { left: 20, right: 24, top: 16, bottom: 50, containLabel: true },
      xAxis: {
        type: 'category',
        data: selectedRow.value.chart.dates,
        axisLabel: { color: '#94a3b8' },
        axisLine: { lineStyle: { color: 'rgba(148,163,184,.24)' } },
      },
      yAxis: [
        {
          type: 'value',
          name: '费率 / carry',
          axisLabel: { color: '#94a3b8', formatter: (value) => `${value}%` },
          splitLine: { lineStyle: { color: 'rgba(148,163,184,.12)', type: 'dashed' } },
        },
        {
          type: 'value',
          name: '价格',
          axisLabel: { color: '#94a3b8' },
          splitLine: { show: false },
        },
      ],
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        {
          type: 'slider',
          bottom: 10,
          height: 14,
          borderColor: 'rgba(51,65,85,.5)',
          fillerColor: 'rgba(59,130,246,.12)',
          backgroundColor: 'rgba(15,23,42,.78)',
        },
      ],
      series,
    });
    await nextTick();
    resize();
  }

  function toggleSeries(key: SeriesKey) {
    visibleSeries.value = visibleSeries.value.includes(key)
      ? visibleSeries.value.filter((item) => item !== key)
      : [...visibleSeries.value, key];
  }
  function toneClass(value: number) {
    if (value > 0) return 'is-positive';
    if (value < 0) return 'is-negative';
    return '';
  }
  function formatRate(value: number) {
    return `${value > 0 ? '+' : ''}${value.toFixed(4)}%`;
  }
  function parseLiquidity(value: string) {
    return Number(value.replace(/[^0-9.]/g, '')) || 0;
  }
</script>

<style scoped lang="less">
  .funding-terminal {
    display: grid;
    gap: 14px;
    padding: 18px;
    border-radius: 22px;
    background: linear-gradient(180deg, #12161f 0%, #0c1018 100%);
    border: 1px solid rgba(71, 85, 105, 0.5);
    box-shadow: 0 24px 60px rgba(2, 6, 23, 0.42);
    color: #dbe4f0;
  }
  .terminal-toolbar,
  .terminal-panel header,
  .toolbar-left,
  .toolbar-right,
  .legend-switches {
    display: flex;
    align-items: center;
  }
  .terminal-toolbar,
  .terminal-panel header {
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
  }
  .toolbar-left,
  .toolbar-right,
  .legend-switches {
    gap: 8px;
    flex-wrap: wrap;
  }

  .legend-switches--center {
    justify-content: center;
    margin: 14px 0 4px;
  }
  .toolbar-left button,
  .legend-switches button {
    height: 34px;
    padding: 0 14px;
    border: 1px solid rgba(71, 85, 105, 0.7);
    border-radius: 8px;
    background: rgba(15, 23, 42, 0.82);
    color: #94a3b8;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
  }
  .toolbar-left .is-active,
  .legend-switches .is-active {
    color: #f8fafc;
    border-color: rgba(96, 165, 250, 0.88);
    background: rgba(37, 99, 235, 0.3);
  }
  .toolbar-right label {
    display: grid;
    gap: 6px;
  }
  .toolbar-right span {
    color: #64748b;
    font-size: 11px;
    font-weight: 700;
  }
  .toolbar-right select {
    min-width: 118px;
    height: 36px;
    padding: 0 12px;
    border: 1px solid rgba(71, 85, 105, 0.7);
    border-radius: 8px;
    background: rgba(15, 23, 42, 0.9);
    color: #dbe4f0;
  }
  .terminal-body {
    display: grid;
    grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.25fr);
    gap: 14px;
  }
  .terminal-panel {
    border: 1px solid rgba(51, 65, 85, 0.82);
    background: rgba(15, 23, 42, 0.76);
    border-radius: 18px;
    padding: 16px;
    min-width: 0;
  }
  .panel-eyebrow {
    display: none;
  }
  .terminal-panel h3 {
    margin: 0;
    color: #f8fafc;
    font-size: 18px;
    font-weight: 700;
  }
  .panel-meta {
    color: #64748b;
    font-size: 12px;
    font-weight: 700;
  }
  .table-shell,
  .position-table {
    overflow: auto;
  }
  table {
    width: 100%;
    border-collapse: collapse;
  }
  th,
  td {
    padding: 11px 10px;
    border-bottom: 1px solid rgba(51, 65, 85, 0.56);
    text-align: left;
    white-space: nowrap;
    font-size: 12px;
  }
  th {
    color: #64748b;
    font-weight: 700;
  }
  td {
    color: #dbe4f0;
    font-weight: 600;
  }
  tbody tr {
    cursor: pointer;
    transition: background 0.15s ease;
  }
  tbody tr:hover {
    background: rgba(30, 41, 59, 0.55);
  }
  tbody tr.is-selected {
    background: rgba(37, 99, 235, 0.16);
  }
  .status-chip {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 54px;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
  }
  .status-chip.is-positive {
    background: rgba(34, 197, 94, 0.18);
    color: #4ade80;
  }
  .status-chip.is-neutral {
    background: rgba(148, 163, 184, 0.18);
    color: #cbd5e1;
  }
  .status-chip.is-negative {
    background: rgba(251, 113, 133, 0.18);
    color: #fb7185;
  }
  .detail-kpis {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
    margin-bottom: 12px;
  }
  .kpi-card {
    padding: 12px;
    border-radius: 12px;
    background: rgba(2, 6, 23, 0.38);
    border: 1px solid rgba(51, 65, 85, 0.68);
  }
  .kpi-card span {
    display: block;
    color: #64748b;
    font-size: 11px;
  }
  .kpi-card strong {
    display: block;
    margin-top: 8px;
    color: #f8fafc;
    font-size: 18px;
  }
  .detail-chart {
    height: 320px;
    margin-bottom: 12px;
  }
  .is-positive {
    color: #4ade80 !important;
  }
  .is-negative {
    color: #fb7185 !important;
  }
  @media (max-width: 1380px) {
    .terminal-body {
      grid-template-columns: 1fr;
    }
  }
  @media (max-width: 980px) {
    .detail-kpis {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
</style>
