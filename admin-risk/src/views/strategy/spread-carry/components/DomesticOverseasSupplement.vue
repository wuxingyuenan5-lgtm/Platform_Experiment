<template>
  <section class="domestic-supplement">
    <article class="spread-card domestic-analysis-card">
      <header>
        <span>价差分析</span>
      </header>

      <div class="domestic-analysis-scroll">
        <table class="domestic-analysis-table">
          <thead>
            <tr>
              <th rowspan="2">标的</th>
              <th rowspan="2">当前价差</th>
              <th rowspan="2">近一月 (%)</th>
              <th rowspan="2">近一季度 (%)</th>
              <th rowspan="2">近半年 (%)</th>
              <th rowspan="2">近一年 (%)</th>
              <th colspan="4">10%</th>
              <th colspan="4">50%</th>
              <th colspan="4">90%</th>
            </tr>
            <tr>
              <th>近一月</th>
              <th>近一季度</th>
              <th>近半年</th>
              <th>近一年</th>
              <th>近一月</th>
              <th>近一季度</th>
              <th>近半年</th>
              <th>近一年</th>
              <th>近一月</th>
              <th>近一季度</th>
              <th>近半年</th>
              <th>近一年</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in domesticAnalysisRows" :key="row.name">
              <td>{{ row.name }}</td>
              <td>{{ row.current }}</td>
              <td>{{ row.month }}</td>
              <td>{{ row.quarter }}</td>
              <td>{{ row.halfYear }}</td>
              <td>{{ row.year }}</td>
              <td>{{ row.p10Month }}</td>
              <td>{{ row.p10Quarter }}</td>
              <td>{{ row.p10HalfYear }}</td>
              <td>{{ row.p10Year }}</td>
              <td>{{ row.p50Month }}</td>
              <td>{{ row.p50Quarter }}</td>
              <td>{{ row.p50HalfYear }}</td>
              <td>{{ row.p50Year }}</td>
              <td>{{ row.p90Month }}</td>
              <td>{{ row.p90Quarter }}</td>
              <td>{{ row.p90HalfYear }}</td>
              <td>{{ row.p90Year }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </article>

    <article class="spread-card domestic-realtime-card">
      <header class="domestic-realtime-head">
        <span>实时价差</span>
        <div class="domestic-realtime-toolbar">
          <button type="button" @click="$emit('refresh')">刷新</button>
          <label class="chart-select chart-select--plain">
            <select v-model="domesticRealtimeSymbol">
              <option value="金">金</option>
              <option value="银">银</option>
              <option value="铜">铜</option>
            </select>
          </label>
        </div>
      </header>

      <table class="domestic-realtime-table">
        <thead>
          <tr>
            <th>标的</th>
            <th>最新价</th>
            <th>海外价格</th>
            <th>价差</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in domesticRealtimeRows" :key="row.symbol">
            <td>{{ row.symbol }}</td>
            <td>{{ row.lastPrice }}</td>
            <td>{{ row.overseasPrice }}</td>
            <td>{{ row.spread }}</td>
          </tr>
        </tbody>
      </table>
    </article>
  </section>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue';

  defineEmits<{
    (event: 'refresh'): void;
  }>();

  const domesticRealtimeSymbol = ref<'金' | '银' | '铜'>('金');

  const domesticAnalysisRows = [
    {
      name: '铜',
      current: '1,964.18',
      month: '100',
      quarter: '89.54',
      halfYear: '97.43',
      year: '99.17',
      p10Month: '496.54',
      p10Quarter: '-150.64',
      p10HalfYear: '-2,412.82',
      p10Year: '-8,790.24',
      p50Month: '1,148.83',
      p50Quarter: '908.28',
      p50HalfYear: '-1,772.2',
      p50Year: '-2,091.13',
      p90Month: '1,801.11',
      p90Quarter: '2,071.93',
      p90HalfYear: '9.3',
      p90Year: '13.4',
    },
    {
      name: '银',
      current: '2.08',
      month: '80',
      quarter: '50.32',
      halfYear: '87.05',
      year: '95.63',
      p10Month: '1.81',
      p10Quarter: '1.10',
      p10HalfYear: '0.15',
      p10Year: '-0.04',
      p50Month: '2.17',
      p50Quarter: '2.35',
      p50HalfYear: '0.43',
      p50Year: '0.43',
      p90Month: '2.87',
      p90Quarter: '4.8',
      p90HalfYear: '6.1',
      p90Year: '7.2',
    },
    {
      name: '金',
      current: '0.95',
      month: '36',
      quarter: '44.29',
      halfYear: '55.2',
      year: '48.27',
      p10Month: '-5.01',
      p10Quarter: '-23.71',
      p10HalfYear: '-7.49',
      p10Year: '-8.87',
      p50Month: '1.85',
      p50Quarter: '1.41',
      p50HalfYear: '-0.06',
      p50Year: '0.68',
      p90Month: '12.2',
      p90Quarter: '8.64',
      p90HalfYear: '11.8',
      p90Year: '16.2',
    },
  ] as const;

  const domesticRealtimeRows = computed(() => {
    const maps = {
      金: [
        { symbol: 'SHFE.au2605', lastPrice: '1,059.4', overseasPrice: '4,820.48', spread: '2.84' },
        { symbol: 'SHFE.au2606', lastPrice: '1,060.9', overseasPrice: '4,820.48', spread: '4.34' },
        { symbol: 'SHFE.au2607', lastPrice: '1,062.96', overseasPrice: '4,820.48', spread: '6.4' },
        { symbol: 'SHFE.au2608', lastPrice: '1,063.7', overseasPrice: '4,820.48', spread: '7.14' },
        { symbol: 'SHFE.au2610', lastPrice: '1,066.04', overseasPrice: '4,820.48', spread: '9.48' },
        { symbol: 'SHFE.au2612', lastPrice: '1,068.76', overseasPrice: '4,820.48', spread: '12.2' },
        { symbol: 'SHFE.au2702', lastPrice: '1,071.7', overseasPrice: '4,820.48', spread: '15.14' },
        { symbol: 'SHFE.au2704', lastPrice: '1,075.18', overseasPrice: '4,820.48', spread: '18.62' },
      ],
      银: [
        { symbol: 'SHFE.ag2508', lastPrice: '8,742', overseasPrice: '36.18', spread: '1.84' },
        { symbol: 'SHFE.ag2510', lastPrice: '8,766', overseasPrice: '36.18', spread: '2.08' },
        { symbol: 'SHFE.ag2512', lastPrice: '8,792', overseasPrice: '36.18', spread: '2.34' },
        { symbol: 'SHFE.ag2602', lastPrice: '8,828', overseasPrice: '36.18', spread: '2.70' },
      ],
      铜: [
        { symbol: 'SHFE.cu2508', lastPrice: '80,420', overseasPrice: '9,842', spread: '1,402.16' },
        { symbol: 'SHFE.cu2509', lastPrice: '80,660', overseasPrice: '9,842', spread: '1,642.16' },
        { symbol: 'SHFE.cu2510', lastPrice: '80,918', overseasPrice: '9,842', spread: '1,900.16' },
        { symbol: 'SHFE.cu2511', lastPrice: '80,982', overseasPrice: '9,842', spread: '1,964.18' },
      ],
    } as const;

    return maps[domesticRealtimeSymbol.value];
  });
</script>

<style scoped lang="less">
  .domestic-supplement {
    display: grid;
    grid-template-columns: minmax(0, 1.45fr) minmax(300px, 0.55fr);
    gap: 12px;
  }

  .spread-card {
    padding: var(--strategy-space-3);
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-panel);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-card);
  }

  .spread-card header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-card-title);
    font-weight: 800;
  }

  .spread-card header button {
    height: var(--strategy-control-height);
    padding: 0 var(--strategy-space-2);
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
    font-size: var(--strategy-font-base);
    font-weight: 700;
    box-shadow: var(--strategy-shadow-soft);
    cursor: pointer;
  }

  .domestic-analysis-scroll {
    overflow-x: auto;
  }

  .domestic-analysis-table,
  .domestic-realtime-table {
    width: 100%;
    border-collapse: collapse;
  }

  .domestic-analysis-table {
    min-width: 1320px;
  }

  .domestic-analysis-table th,
  .domestic-analysis-table td,
  .domestic-realtime-table th,
  .domestic-realtime-table td {
    padding: 9px 10px;
    border-bottom: 1px solid var(--strategy-border-soft);
    text-align: right;
    font-size: var(--strategy-font-sm);
  }

  .domestic-analysis-table th,
  .domestic-realtime-table th {
    color: var(--strategy-text-3);
    font-weight: 800;
    background: var(--strategy-table-head-bg);
  }

  .domestic-analysis-table td,
  .domestic-realtime-table td {
    color: var(--strategy-text-2);
    font-weight: 700;
  }

  .domestic-analysis-table th:first-child,
  .domestic-analysis-table td:first-child,
  .domestic-realtime-table th:first-child,
  .domestic-realtime-table td:first-child {
    text-align: left;
  }

  .domestic-realtime-head,
  .domestic-realtime-toolbar {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .domestic-realtime-head {
    justify-content: space-between;
  }

  .chart-select select {
    height: var(--strategy-control-height);
    padding: 0 var(--strategy-space-2);
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
    font-size: var(--strategy-font-base);
    font-weight: 700;
    box-shadow: var(--strategy-shadow-soft);
  }

  @media (max-width: 1480px) {
    .domestic-supplement {
      grid-template-columns: 1fr;
    }
  }
</style>
