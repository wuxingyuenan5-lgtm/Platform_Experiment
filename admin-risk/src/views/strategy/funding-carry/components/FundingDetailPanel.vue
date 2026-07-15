<template>
  <section class="detail-panel">

    <div class="compact-shell">
      <section class="chart-grid">
        <article class="chart-card">
          <div class="chart-toolbar">
            <h3>期现价差</h3>

          </div>

          <div ref="basisChartRef" class="borrow-chart"></div>
        </article>

        <article class="chart-card">
          <div class="chart-toolbar">
            <h3>借贷费率</h3>
          </div>

          <div ref="borrowChartRef" class="borrow-chart"></div>
        </article>
      </section>

      <section class="table-grid">
        <article class="table-card">
          <div class="table-head">
            <div>
              <h3>期现价差表</h3>
            </div>
          </div>

          <table class="data-table">
            <thead>
              <tr>
                <th>日期</th>
                <th>期现价差</th>
                <th>结构评分</th>
                <th>执行备注</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in basisRows" :key="row.date">
                <td>{{ row.date }}</td>
                <td :class="row.tone">{{ row.value }}</td>
                <td>{{ row.score }}</td>
                <td>{{ row.note }}</td>
              </tr>
            </tbody>
          </table>
        </article>

        <article class="table-card">
          <div class="table-head">
            <div>
              <h3>借贷费率表</h3>
            </div>
          </div>

          <table class="data-table">
            <thead>
              <tr>
                <th>日期</th>
                <th>借贷费率</th>
                <th>净 Carry</th>
                <th>执行备注</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in borrowRows" :key="row.date">
                <td>{{ row.date }}</td>
                <td :class="row.borrowTone">{{ row.borrow }}</td>
                <td :class="row.netTone">{{ row.netCarry }}</td>
                <td>{{ row.note }}</td>
              </tr>
            </tbody>
          </table>
        </article>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
  import { computed, nextTick, onMounted, ref, watch, type Ref } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';
  import type { FundingAssetResearch, FundingExchange, FundingMarketRange, FundingSymbol } from '../types';

  const props = defineProps<{
    exchange: FundingExchange;
    symbol: FundingSymbol;
    selectedRange: FundingMarketRange;
    resolution: string;
    startDate: string;
    endDate: string;
    research: FundingAssetResearch;
  }>();

  const basisChartRef = ref<HTMLDivElement | null>(null);
  const borrowChartRef = ref<HTMLDivElement | null>(null);
  const basisChart = useECharts(basisChartRef as Ref<HTMLDivElement>);
  const borrowChart = useECharts(borrowChartRef as Ref<HTMLDivElement>);

  const borrowSeriesMap: Record<FundingSymbol, { dates: string[]; basis: number[]; borrow: number[] }> = {
    BTC: {
      dates: ['05-28', '05-30', '06-01', '06-03', '06-05', '06-07', '06-09', '06-11', '06-13', '06-15', '06-17', '06-19', '06-21', '06-23', '06-24'],
      basis: [3.8, 3.4, 2.9, 3.1, 2.1, 1.2, 1.5, 2.4, 3.2, 2.8, 2.1, 1.7, 1.9, 2.2, 2.6],
      borrow: [-1.8, -1.7, -1.7, -1.6, -1.6, -1.5, -1.5, -1.6, -1.7, -1.7, -1.6, -1.7, -1.7, -1.8, -1.7],
    },
    ETH: {
      dates: ['05-28', '05-30', '06-01', '06-03', '06-05', '06-07', '06-09', '06-11', '06-13', '06-15', '06-17', '06-19', '06-21', '06-23', '06-24'],
      basis: [3.1, 2.8, 2.2, 2.6, 1.8, 0.9, 1.1, 2.0, 2.8, 2.5, 1.9, 1.4, 1.7, 2.0, 2.2],
      borrow: [-2.2, -2.1, -2.0, -1.9, -1.9, -1.8, -1.8, -1.9, -2.0, -2.0, -1.9, -1.9, -2.0, -2.1, -1.9],
    },
    SOL: {
      dates: ['05-28', '05-30', '06-01', '06-03', '06-05', '06-07', '06-09', '06-11', '06-13', '06-15', '06-17', '06-19', '06-21', '06-23', '06-24'],
      basis: [6.4, 6.0, 5.2, 5.7, 4.8, 3.4, 3.8, 4.6, 5.3, 5.0, 4.3, 3.7, 4.1, 4.9, 5.2],
      borrow: [-3.0, -2.9, -2.8, -2.7, -2.7, -2.6, -2.6, -2.7, -2.8, -2.8, -2.7, -2.7, -2.8, -2.9, -2.8],
    },
    DOGE: {
      dates: ['05-28', '05-30', '06-01', '06-03', '06-05', '06-07', '06-09', '06-11', '06-13', '06-15', '06-17', '06-19', '06-21', '06-23', '06-24'],
      basis: [4.4, 4.1, 3.7, 4.0, 3.5, 2.8, 3.0, 3.7, 4.1, 3.8, 3.4, 3.1, 3.3, 3.7, 3.9],
      borrow: [-2.5, -2.4, -2.4, -2.3, -2.3, -2.2, -2.2, -2.3, -2.4, -2.4, -2.3, -2.3, -2.4, -2.5, -2.4],
    },
    XRP: {
      dates: ['05-28', '05-30', '06-01', '06-03', '06-05', '06-07', '06-09', '06-11', '06-13', '06-15', '06-17', '06-19', '06-21', '06-23', '06-24'],
      basis: [3.9, 3.6, 3.0, 3.2, 2.5, 1.6, 1.8, 2.5, 3.0, 2.7, 2.1, 1.7, 1.8, 2.0, 2.3],
      borrow: [-2.1, -2.1, -2.0, -1.9, -1.9, -1.8, -1.8, -1.9, -2.0, -2.0, -1.9, -1.9, -2.0, -2.1, -2.0],
    },
    XAUT: {
      dates: ['05-28', '05-30', '06-01', '06-03', '06-05', '06-07', '06-09', '06-11', '06-13', '06-15', '06-17', '06-19', '06-21', '06-23', '06-24'],
      basis: [1.7, 1.6, 1.4, 1.5, 1.2, 0.8, 0.9, 1.1, 1.3, 1.2, 1.0, 0.9, 1.0, 1.1, 1.2],
      borrow: [-1.4, -1.4, -1.3, -1.3, -1.2, -1.2, -1.2, -1.2, -1.3, -1.3, -1.2, -1.2, -1.3, -1.4, -1.4],
    },
  };

  const currentBorrowSeries = computed(() => borrowSeriesMap[props.symbol] ?? borrowSeriesMap.BTC);

  const visibleSlice = computed(() => {
    const { dates, basis, borrow } = currentBorrowSeries.value;
    const start = new Date(props.startDate).getTime();
    const end = new Date(props.endDate).getTime();
    const filteredIndexes = dates
      .map((date, index) => ({ date: `2026-${date}`, index }))
      .filter((item) => {
        const time = new Date(item.date).getTime();
        return time >= start && time <= end;
      })
      .map((item) => item.index);

    const scopedIndexes = filteredIndexes.length
      ? filteredIndexes
      : dates.map((_, index) => index);

    let rangeIndexes = scopedIndexes;
    if (props.selectedRange === '7d') rangeIndexes = scopedIndexes.slice(-7);
    if (props.selectedRange === '30d') rangeIndexes = scopedIndexes.slice(-30);

    return {
      dates: rangeIndexes.map((index) => dates[index]),
      basis: rangeIndexes.map((index) => basis[index]),
      borrow: rangeIndexes.map((index) => borrow[index]),
    };
  });

  const basisRows = computed(() =>
    visibleSlice.value.dates.map((date, index) => {
      const basis = visibleSlice.value.basis[index];
      return {
        date: `2026-${date}`,
        value: `${basis.toFixed(2)}%`,
        score: basis >= 4 ? '高' : basis >= 2 ? '中' : '低',
        tone: basis >= 0 ? 'tone-positive' : 'tone-negative',
        note: basis >= 4 ? '结构厚度充足，可继续跟踪。' : basis >= 2 ? '结构仍在，但需结合费率确认。' : '结构偏薄，执行优先级下降。',
      };
    }),
  );

  const borrowRows = computed(() =>
    visibleSlice.value.dates.map((date, index) => {
      const borrow = visibleSlice.value.borrow[index];
      const basis = visibleSlice.value.basis[index];
      const netCarry = basis + borrow;
      return {
        date: `2026-${date}`,
        borrow: `${borrow.toFixed(2)}%`,
        netCarry: `${netCarry > 0 ? '+' : ''}${netCarry.toFixed(2)}%`,
        borrowTone: borrow >= 0 ? 'tone-positive' : 'tone-negative',
        netTone: netCarry >= 0 ? 'tone-positive' : 'tone-negative',
        note: netCarry > 1 ? '净 carry 仍有厚度，可研究执行。' : netCarry > 0 ? '边际可做，但需严控滑点。' : '净 carry 偏弱，暂不建议放大。',
      };
    }),
  );

  async function renderBasisChart() {
    await basisChart.setOptions({
      color: ['#3da6de'],
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
      },
      legend: { show: false },
      grid: {
        left: 20,
        right: 20,
        top: 32,
        bottom: 54,
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: visibleSlice.value.dates,
        axisTick: { show: false },
        axisLabel: { color: '#98a2b3' },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#98a2b3' },
        splitLine: {
          lineStyle: {
            color: 'rgba(148, 163, 184, 0.18)',
            type: 'dashed',
          },
        },
      },
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        {
          type: 'slider',
          height: 16,
          bottom: 8,
          borderColor: 'rgba(205, 214, 224, 0.8)',
          fillerColor: 'rgba(125, 167, 255, 0.12)',
          backgroundColor: 'rgba(240, 244, 248, 0.9)',
        },
      ],
      series: [
        {
          name: '期现价差',
          type: 'line',
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 3, color: '#3da6de' },
          data: visibleSlice.value.basis,
        },
      ],
    });

    await nextTick();
    basisChart.resize();
  }

  async function renderBorrowChart() {
    await borrowChart.setOptions({
      color: ['#f2c94c'],
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
      },
      legend: { show: false },
      grid: {
        left: 20,
        right: 20,
        top: 32,
        bottom: 54,
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: visibleSlice.value.dates,
        axisTick: { show: false },
        axisLabel: { color: '#98a2b3' },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#98a2b3' },
        splitLine: {
          lineStyle: {
            color: 'rgba(148, 163, 184, 0.18)',
            type: 'dashed',
          },
        },
      },
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        {
          type: 'slider',
          height: 16,
          bottom: 8,
          borderColor: 'rgba(205, 214, 224, 0.8)',
          fillerColor: 'rgba(125, 167, 255, 0.12)',
          backgroundColor: 'rgba(240, 244, 248, 0.9)',
        },
      ],
      series: [
        {
          name: '借贷费率',
          type: 'bar',
          barWidth: 14,
          itemStyle: {
            borderRadius: [6, 6, 0, 0],
            color: '#ffd15a',
          },
          data: visibleSlice.value.borrow,
        },
      ],
    });

    await nextTick();
    borrowChart.resize();
  }

  watch(
    () => [props.symbol, props.selectedRange, props.startDate, props.endDate],
    () => {
      renderBasisChart();
      renderBorrowChart();
    },
  );

  onMounted(() => {
    renderBasisChart();
    renderBorrowChart();
  });
</script>

<style scoped lang="less">
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
    text-align: left;
    border-bottom: 1px solid var(--strategy-border-soft);
    font-size: var(--strategy-font-sm);
  }

  .data-table th {
    color: var(--strategy-text-3);
    font-weight: 700;
    background: var(--strategy-table-head-bg);
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
  }
</style>
