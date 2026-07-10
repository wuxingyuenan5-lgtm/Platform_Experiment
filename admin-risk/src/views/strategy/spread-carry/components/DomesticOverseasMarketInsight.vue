<template>
  <section class="market-insight">
    <div class="market-tabs">
      <button
        v-for="item in metalTabs"
        :key="item.key"
        type="button"
        class="market-tab"
        :class="{ 'is-active': activeMetal === item.key }"
        @click="activeMetal = item.key"
      >
        {{ item.label }}
      </button>
    </div>

    <div class="headline-strip">
      <span>国内{{ activeSnapshot.label }}: <strong class="is-warm">{{ activeSnapshot.domesticSpot }}</strong></span>
      <span>国外{{ activeSnapshot.label }}: <strong class="is-cool">{{ activeSnapshot.overseasSpot }}</strong></span>
    </div>

    <div class="fx-grid">
      <article v-for="item in activeSnapshot.fxCards" :key="item.label" class="fx-card">
        <label>{{ item.label }}</label>
        <strong>{{ item.value }}</strong>
      </article>
    </div>

    <div class="insight-grid">
      <article class="insight-card">
        <header>
          <span>期货换月</span>
        </header>
        <table class="compact-table">
          <thead>
            <tr>
              <th>合约</th>
              <th>持仓占比</th>
              <th>剩余天数</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in activeSnapshot.rollRows" :key="row.contract">
              <td>
                {{ row.contract }}
                <em v-if="row.main" class="main-badge">M</em>
              </td>
              <td>{{ row.ratio }}</td>
              <td>{{ row.days }}</td>
            </tr>
          </tbody>
        </table>
      </article>

      <article class="insight-card">
        <header class="insight-card__head">
          <span>期限结构</span>
          <button type="button" class="refresh-btn">刷新</button>
        </header>
        <table class="compact-table">
          <thead>
            <tr>
              <th>合约</th>
              <th>价格</th>
              <th>溢价</th>
              <th>当前年化</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in activeSnapshot.termRows" :key="row.contract">
              <td>{{ row.contract }}</td>
              <td>{{ row.price }}</td>
              <td>{{ row.premium }}</td>
              <td>{{ row.annualized }}</td>
            </tr>
          </tbody>
        </table>
      </article>

      <article class="insight-card">
        <header>
          <span>海内外溢价分析</span>
        </header>
        <table class="compact-table compact-table--center">
          <thead>
            <tr>
              <th></th>
              <th>当前</th>
              <th>10%</th>
              <th>50%</th>
              <th>90%</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in activeSnapshot.premiumRows" :key="row.label">
              <td>{{ row.label }}</td>
              <td>{{ row.current }}</td>
              <td>{{ row.p10 }}</td>
              <td>{{ row.p50 }}</td>
              <td>{{ row.p90 }}</td>
            </tr>
          </tbody>
        </table>
      </article>

      <article class="insight-card">
        <header>
          <span>库存费年化</span>
        </header>
        <table class="compact-table compact-table--center">
          <thead>
            <tr>
              <th></th>
              <th class="is-warm">多</th>
              <th class="is-cool">空</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in activeSnapshot.carryRows" :key="row.label">
              <td>{{ row.label }}</td>
              <td>{{ row.long }}</td>
              <td>{{ row.short }}</td>
            </tr>
          </tbody>
        </table>
      </article>
    </div>

    <article class="history-card">
      <header class="history-head">
        <div>
          <h3>库存费历史图表</h3>
        </div>

        <div class="history-controls">
          <label class="control-select">
            <select v-model="historyPeriod">
              <option value="day">天</option>
              <option value="week">周</option>
            </select>
          </label>
          <label class="control-select">
            <select v-model="historySymbol">
              <option v-for="symbol in activeSnapshot.symbolOptions" :key="symbol" :value="symbol">{{ symbol }}</option>
            </select>
          </label>
          <input v-model="startDate" type="date" />
          <span class="dash">—</span>
          <input v-model="endDate" type="date" />
        </div>
      </header>

      <div ref="historyChartRef" class="history-chart"></div>
    </article>
  </section>
</template>

<script setup lang="ts">
  import type { Ref } from 'vue';
  import { computed, nextTick, onMounted, ref, watch } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';

  type MetalKey = 'gold' | 'silver' | 'copper';

  const activeMetal = ref<MetalKey>('gold');
  const historyPeriod = ref<'day' | 'week'>('day');
  const historySymbol = ref('XAUUSD+');
  const startDate = ref('2026-03-16');
  const endDate = ref('2026-04-16');

  const metalTabs = [
    { key: 'gold', label: '金' },
    { key: 'silver', label: '银' },
    { key: 'copper', label: '铜' },
  ] as const;

  const snapshots = {
    gold: {
      label: '金',
      domesticSpot: '1,055.5 元',
      overseasSpot: '4,812.77 美元',
      symbolOptions: ['XAUUSD+', 'SHFE.au2606', 'SHFE.au2612'],
      fxCards: [
        { label: '离岸汇率', value: '6.8182' },
        { label: '在岸汇率', value: '6.8213' },
        { label: '金汇率', value: '6.8214' },
      ],
      rollRows: [
        { contract: '沪金2606', ratio: '63.10%', days: '60天', main: true },
        { contract: '沪金2608', ratio: '22.66%', days: '123天' },
        { contract: '沪金2610', ratio: '7.82%', days: '182天' },
        { contract: '沪金2612', ratio: '4.60%', days: '243天' },
        { contract: '沪金2702', ratio: '1.02%', days: '305天' },
      ],
      termRows: [
        { contract: 'SHFE.au2604', price: '1,053', premium: '5.00', annualized: '174.14%' },
        { contract: 'SHFE.au2605', price: '1,056.38', premium: '8.38', annualized: '9.73%' },
        { contract: 'SHFE.au2606', price: '1,058.1', premium: '10.10', annualized: '5.77%' },
        { contract: 'SHFE.au2608', price: '1,061', premium: '13.00', annualized: '3.65%' },
        { contract: 'SHFE.au2610', price: '1,063.6', premium: '15.60', annualized: '2.97%' },
      ],
      premiumRows: [
        { label: '近一月', current: '34.18%', p10: '-5.2', p50: '2.67', p90: '6.54' },
        { label: '近一季度', current: '44.29%', p10: '-23.71', p50: '1.42', p90: '8.89' },
        { label: '近一年', current: '48.23%', p10: '-8.87', p50: '0.68', p90: '10.29' },
      ],
      carryRows: [
        { label: '今日年化', long: '-5.22%', short: '3.27%' },
        { label: '近一周最高', long: '-4.96%', short: '3.49%' },
        { label: '近一周最低', long: '-6%', short: '3.17%' },
        { label: '月平均', long: '-5.9%', short: '3.22%' },
      ],
      line: [4860, 4850, 4820, 4600, 4550, 4480, 4400, 4430, 4420, 4470, 4500, 4520, 4780, 4760, 4750, 4750, 4760, 4810, 4808, 4805, 4802, 4815, 4818],
      longBars: [-100, -94, -92, -75, -74, -73, -70, -71, -69, -68, -67, -66, -74, -76, -75, -74, -74, -75, -76, -75, -74, -73, -71],
      shortBars: [52, 48, 47, 28, 28, 28, 28, 39, 39, 35, 35, 36, 39, 39, 40, 40, 40, 39, 39, 39, 39, 41, 40],
    },
    silver: {
      label: '银',
      domesticSpot: '8,766 元',
      overseasSpot: '36.18 美元',
      symbolOptions: ['XAGUSD+', 'SHFE.ag2510', 'SHFE.ag2512'],
      fxCards: [
        { label: '离岸汇率', value: '6.8182' },
        { label: '在岸汇率', value: '6.8213' },
        { label: '银汇率', value: '6.8136' },
      ],
      rollRows: [
        { contract: '沪银2510', ratio: '48.22%', days: '91天', main: true },
        { contract: '沪银2512', ratio: '28.16%', days: '152天' },
        { contract: '沪银2602', ratio: '15.10%', days: '214天' },
        { contract: '沪银2604', ratio: '8.52%', days: '274天' },
      ],
      termRows: [
        { contract: 'SHFE.ag2508', price: '8,742', premium: '1.84', annualized: '21.60%' },
        { contract: 'SHFE.ag2510', price: '8,766', premium: '2.08', annualized: '12.44%' },
        { contract: 'SHFE.ag2512', price: '8,792', premium: '2.34', annualized: '8.90%' },
        { contract: 'SHFE.ag2602', price: '8,828', premium: '2.70', annualized: '6.72%' },
      ],
      premiumRows: [
        { label: '近一月', current: '26.52%', p10: '-1.8', p50: '1.34', p90: '3.11' },
        { label: '近一季度', current: '31.46%', p10: '-4.2', p50: '1.58', p90: '4.48' },
        { label: '近一年', current: '37.28%', p10: '-7.6', p50: '2.04', p90: '5.73' },
      ],
      carryRows: [
        { label: '今日年化', long: '-3.41%', short: '2.26%' },
        { label: '近一周最高', long: '-2.98%', short: '2.45%' },
        { label: '近一周最低', long: '-3.76%', short: '1.98%' },
        { label: '月平均', long: '-3.23%', short: '2.12%' },
      ],
      line: [36.3, 36.1, 35.9, 35.4, 35.1, 34.8, 34.7, 34.9, 35.2, 35.4, 35.5, 35.8, 36.0, 36.2, 36.1, 36.0, 35.9, 36.0, 36.1, 36.2, 36.18, 36.16, 36.18],
      longBars: [-72, -70, -69, -54, -53, -51, -49, -48, -47, -45, -44, -43, -46, -47, -47, -46, -45, -44, -43, -42, -42, -41, -41],
      shortBars: [38, 36, 35, 22, 22, 21, 22, 24, 25, 25, 26, 27, 28, 28, 28, 27, 27, 27, 27, 28, 28, 28, 28],
    },
    copper: {
      label: '铜',
      domesticSpot: '80,982 元',
      overseasSpot: '9,842 美元',
      symbolOptions: ['COPPER', 'SHFE.cu2511', 'SHFE.cu2512'],
      fxCards: [
        { label: '离岸汇率', value: '6.8182' },
        { label: '在岸汇率', value: '6.8213' },
        { label: '铜汇率', value: '6.8139' },
      ],
      rollRows: [
        { contract: '沪铜2511', ratio: '51.38%', days: '108天', main: true },
        { contract: '沪铜2512', ratio: '23.40%', days: '138天' },
        { contract: '沪铜2601', ratio: '14.72%', days: '169天' },
        { contract: '沪铜2602', ratio: '10.50%', days: '198天' },
      ],
      termRows: [
        { contract: 'SHFE.cu2509', price: '80,660', premium: '1,642.16', annualized: '16.22%' },
        { contract: 'SHFE.cu2510', price: '80,918', premium: '1,900.16', annualized: '12.03%' },
        { contract: 'SHFE.cu2511', price: '80,982', premium: '1,964.18', annualized: '10.88%' },
        { contract: 'SHFE.cu2512', price: '81,144', premium: '2,126.18', annualized: '9.64%' },
      ],
      premiumRows: [
        { label: '近一月', current: '52.40%', p10: '496.54', p50: '1148.83', p90: '1801.11' },
        { label: '近一季度', current: '58.22%', p10: '-150.64', p50: '908.28', p90: '2071.93' },
        { label: '近一年', current: '61.10%', p10: '-2091.13', p50: '1772.2', p90: '2918.44' },
      ],
      carryRows: [
        { label: '今日年化', long: '-2.84%', short: '1.92%' },
        { label: '近一周最高', long: '-2.41%', short: '2.18%' },
        { label: '近一周最低', long: '-3.01%', short: '1.66%' },
        { label: '月平均', long: '-2.72%', short: '1.80%' },
      ],
      line: [9870, 9858, 9834, 9780, 9734, 9702, 9688, 9704, 9735, 9756, 9788, 9812, 9830, 9846, 9859, 9864, 9871, 9880, 9888, 9899, 9878, 9854, 9842],
      longBars: [-58, -57, -56, -45, -44, -43, -42, -41, -40, -40, -39, -39, -40, -40, -40, -39, -38, -38, -38, -39, -39, -39, -39],
      shortBars: [31, 30, 29, 18, 18, 17, 17, 18, 19, 20, 21, 21, 22, 22, 22, 22, 22, 22, 22, 23, 23, 23, 23],
    },
  } as const;

  const activeSnapshot = computed(() => snapshots[activeMetal.value]);

  watch(
    activeMetal,
    () => {
      historySymbol.value = activeSnapshot.value.symbolOptions[0];
      nextTick(() => renderHistoryChart());
    },
  );

  watch([historyPeriod, historySymbol, startDate, endDate], () => {
    renderHistoryChart();
  });

  const historyChartRef = ref<HTMLDivElement | null>(null);
  const { setOptions, resize } = useECharts(historyChartRef as Ref<HTMLDivElement>);

  async function renderHistoryChart() {
    const data = activeSnapshot.value;
    await setOptions({
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
      legend: {
        top: 12,
        itemWidth: 10,
        itemHeight: 10,
        textStyle: { color: '#7f8c9d' },
        data: ['价差', '多头', '空头'],
      },
      grid: { left: 18, right: 24, top: 54, bottom: 62, containLabel: true },
      xAxis: {
        type: 'category',
        data: [
          '2026-03-17', '2026-03-18', '2026-03-19', '2026-03-20', '2026-03-21', '2026-03-22', '2026-03-24',
          '2026-03-26', '2026-03-28', '2026-03-30', '2026-04-01', '2026-04-03', '2026-04-05', '2026-04-07',
          '2026-04-09', '2026-04-11', '2026-04-13', '2026-04-15', '2026-04-16', '2026-04-17', '2026-04-18',
          '2026-04-19', '2026-04-20',
        ],
        axisTick: { show: false },
        axisLabel: { color: '#98a2b3', hideOverlap: true },
      },
      yAxis: [
        {
          type: 'value',
          name: '库存费',
          min: -120,
          max: 90,
          axisLabel: { color: '#98a2b3' },
          splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.16)', type: 'dashed' } },
        },
        {
          type: 'value',
          name: '价格',
          position: 'right',
          axisLabel: { color: '#98a2b3' },
          splitLine: { show: false },
        },
      ],
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        {
          type: 'slider',
          height: 18,
          bottom: 10,
          backgroundColor: 'rgba(240, 244, 248, 0.9)',
          fillerColor: 'rgba(125, 167, 255, 0.12)',
          borderColor: 'rgba(205, 214, 224, 0.8)',
        },
      ],
      series: [
        {
          name: '多头',
          type: 'bar',
          stack: 'carry',
          barWidth: 22,
          itemStyle: { color: '#d33131', borderRadius: [0, 0, 4, 4] },
          data: data.longBars,
        },
        {
          name: '空头',
          type: 'bar',
          stack: 'carry',
          barWidth: 22,
          itemStyle: { color: '#22b573', borderRadius: [4, 4, 0, 0] },
          data: data.shortBars,
        },
        {
          name: '价差',
          type: 'line',
          yAxisIndex: 1,
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 3, color: '#e0a221' },
          data: data.line,
        },
      ],
    });

    await nextTick();
    resize();
  }

  onMounted(() => {
    renderHistoryChart();
  });
</script>

<style scoped lang="less">
  .market-insight {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 12px 0 0;
  }

  .market-tabs {
    display: inline-flex;
    width: fit-content;
    overflow: hidden;
    border: 1px solid #efe4d3;
    border-radius: 14px;
    background: #fff;
  }

  .market-tab {
    min-width: 46px;
    height: 36px;
    padding: 0 18px;
    border: none;
    border-right: 1px solid #efe4d3;
    background: transparent;
    color: #7b8794;
    font-size: 14px;
    font-weight: 700;
    cursor: pointer;
  }

  .market-tab:last-child {
    border-right: none;
  }

  .market-tab.is-active {
    background: #fbfbf9;
    color: #c75f5f;
  }

  .headline-strip {
    display: flex;
    justify-content: center;
    gap: 28px;
    padding: 12px 16px 2px;
    color: #263446;
    font-size: 18px;
    font-weight: 800;
  }

  .headline-strip strong {
    font-weight: 900;
  }

  .is-warm {
    color: #df5a5a;
  }

  .is-cool {
    color: #31b47a;
  }

  .fx-grid,
  .insight-grid {
    display: grid;
    gap: 12px;
  }

  .fx-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .insight-grid {
    grid-template-columns: 1.04fr 1.04fr 1fr 0.88fr;
  }

  .fx-card,
  .insight-card,
  .history-card {
    border: 1px solid #efefef;
    border-radius: 18px;
    background: #fff;
    box-shadow: 0 10px 24px rgba(18, 29, 53, 0.04);
  }

  .fx-card {
    min-height: 86px;
    padding: 14px 18px;
  }

  .fx-card label {
    display: block;
    color: #7d8897;
    font-size: 13px;
    font-weight: 700;
  }

  .fx-card strong {
    display: block;
    margin-top: 6px;
    color: #283548;
    font-size: 18px;
    font-weight: 800;
  }

  .insight-card {
    padding: 14px 0 0;
    overflow: hidden;
  }

  .insight-card header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 0;
    padding: 0 18px 12px;
    color: #445264;
    font-size: 16px;
    font-weight: 800;
  }

  .insight-card__head .refresh-btn {
    margin-left: auto;
  }

  .refresh-btn {
    height: 30px;
    padding: 0 12px;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    background: #fff;
    color: #667085;
    cursor: pointer;
  }

  .compact-table {
    width: 100%;
    border-collapse: collapse;
  }

  .compact-table th,
  .compact-table td {
    padding: 11px 18px;
    border-bottom: 1px solid #f2f4f7;
    text-align: left;
    font-size: 13px;
    white-space: nowrap;
  }

  .compact-table th {
    color: #8a97aa;
    font-weight: 700;
  }

  .compact-table td {
    color: #334155;
    font-weight: 700;
  }

  .compact-table--center th,
  .compact-table--center td {
    text-align: center;
  }

  .compact-table tbody tr:last-child td {
    border-bottom: none;
  }

  .main-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 14px;
    height: 14px;
    margin-left: 4px;
    border-radius: 999px;
    background: #dc3d3d;
    color: #fff;
    font-size: 10px;
    font-style: normal;
    font-weight: 800;
  }

  .history-card {
    padding: 14px 16px 12px;
  }

  .history-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 8px;
  }

  .history-head h3 {
    margin: 0;
    color: #364254;
    font-size: 18px;
    font-weight: 800;
  }

  .history-controls {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .history-controls input,
  .history-controls select {
    height: 34px;
    padding: 0 12px;
    border: 1px solid #d9dee7;
    border-radius: 10px;
    background: #fff;
    color: #556273;
    font-size: 13px;
    font-weight: 600;
  }

  .control-select {
    display: inline-flex;
  }

  .dash {
    color: #9aa5b1;
    font-weight: 700;
  }

  .history-chart {
    height: 360px;
  }

  @media (max-width: 1400px) {
    .insight-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 980px) {
    .headline-strip,
    .history-head,
    .history-controls {
      flex-direction: column;
      align-items: flex-start;
    }

    .fx-grid,
    .insight-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
