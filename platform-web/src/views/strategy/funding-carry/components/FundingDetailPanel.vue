<template>
  <section class="detail-panel">
    <div class="compact-shell">
      <section class="chart-grid">
        <article class="chart-card">
          <div class="chart-toolbar">
            <h3>期现价差</h3>
            <span>{{ context?.perpetualSymbol ?? '--' }}</span>
          </div>
          <div ref="basisChartRef" class="borrow-chart"></div>
        </article>

        <article class="chart-card">
          <div class="chart-toolbar">
            <h3>借贷费率</h3>
            <span>真实数据待接入</span>
          </div>
          <div class="empty-chart">当前账户接口未提供借贷费率历史序列</div>
        </article>
      </section>

      <section class="table-grid">
        <article class="table-card">
          <div class="table-head"><h3>期现价差表</h3></div>
          <table class="data-table">
            <thead>
              <tr><th>时间</th><th>期现价差</th><th>现货中间价</th><th>永续中间价</th></tr>
            </thead>
            <tbody>
              <tr v-if="context">
                <td>{{ formatTime(context.asOf) }}</td>
                <td :class="basisTone">{{ context.basis ?? '--' }}</td>
                <td>{{ context.spotQuote?.mid ?? '--' }}</td>
                <td>{{ context.perpetualQuote?.mid ?? '--' }}</td>
              </tr>
              <tr v-else><td colspan="4" class="empty-cell">尚无真实行情</td></tr>
            </tbody>
          </table>
        </article>

        <article class="table-card">
          <div class="table-head"><h3>资金费率与账户状态</h3></div>
          <table class="data-table">
            <thead>
              <tr><th>资金费率</th><th>下次结算</th><th>可用资金</th><th>数据状态</th></tr>
            </thead>
            <tbody>
              <tr v-if="context">
                <td :class="fundingTone">{{ fundingRateLabel }}</td>
                <td>{{ formatTime(context.nextFundingTime) }}</td>
                <td>{{ context.activeReservation?.fundingAvailable ?? '--' }}</td>
                <td>{{ dataStateLabel }}</td>
              </tr>
              <tr v-else><td colspan="4" class="empty-cell">尚无真实账户数据</td></tr>
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

  const props = defineProps<{
    context: Record<string, any> | null;
    workspace: Record<string, any> | null;
  }>();

  const basisChartRef = ref<HTMLDivElement | null>(null);
  const basisChart = useECharts(basisChartRef as Ref<HTMLDivElement>);

  const fundingRatePercent = computed(() => {
    const value = Number(props.context?.fundingRate);
    return Number.isFinite(value) ? value * 100 : null;
  });
  const fundingRateLabel = computed(() =>
    fundingRatePercent.value === null ? '--' : `${fundingRatePercent.value.toFixed(4)}%`,
  );
  const fundingTone = computed(() =>
    fundingRatePercent.value !== null && fundingRatePercent.value < 0 ? 'negative' : 'positive',
  );
  const basisTone = computed(() => (Number(props.context?.basis) < 0 ? 'negative' : 'positive'));
  const dataStateLabel = computed(() => {
    if (!props.context) return '不可用';
    if (props.context.dataQualityState === 'authoritative') return '权威实时';
    return props.context.dataQualityState ?? '实时';
  });

  function formatTime(value: unknown) {
    if (!value) return '--';
    const date = new Date(String(value));
    return Number.isNaN(date.getTime())
      ? String(value)
      : date.toLocaleString('zh-CN', { hour12: false });
  }

  async function renderBasisChart() {
    const basis = Number(props.context?.basis);
    await basisChart.setOptions({
      tooltip: { trigger: 'axis' },
      grid: { left: 24, right: 20, top: 22, bottom: 34, containLabel: true },
      xAxis: {
        type: 'category',
        data: props.context ? [formatTime(props.context.asOf)] : [],
        axisTick: { show: false },
        axisLabel: { color: '#697589' },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#697589' },
        splitLine: { lineStyle: { color: '#edf2f7' } },
      },
      series: [
        {
          type: 'line',
          smooth: true,
          symbolSize: 8,
          lineStyle: { color: '#cf3f4f', width: 2 },
          data: Number.isFinite(basis) ? [basis] : [],
        },
      ],
    });
    await nextTick();
    basisChart.resize();
  }

  watch(() => props.context, renderBasisChart, { deep: true });
  onMounted(renderBasisChart);
</script>

<style scoped lang="less">
  .detail-panel {
    color: var(--strategy-text-1);
  }

  .compact-shell {
    display: grid;
    gap: 16px;
  }

  .chart-grid,
  .table-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
  }

  .chart-card,
  .table-card {
    overflow: hidden;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-panel);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-card);
  }

  .chart-card {
    padding: 18px;
  }

  .chart-toolbar,
  .table-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;
  }

  h3 {
    margin: 0;
    color: var(--strategy-text-1);
    font-size: 16px;
    font-weight: 800;
  }

  .chart-toolbar span {
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  .borrow-chart,
  .empty-chart {
    height: 260px;
  }

  .empty-chart {
    display: grid;
    border-radius: 14px;
    background: var(--strategy-surface-muted);
    color: var(--strategy-text-faint);
    place-items: center;
  }

  .table-head {
    padding: 18px 18px 0;
  }

  .data-table {
    width: 100%;
    border-collapse: collapse;
  }

  .data-table th,
  .data-table td {
    padding: 13px 16px;
    border-bottom: 1px solid var(--strategy-border-soft);
    font-size: 13px;
    text-align: left;
  }

  .data-table th {
    background: var(--strategy-table-head-bg);
    color: var(--strategy-text-3);
    font-weight: 700;
  }

  .positive {
    color: var(--strategy-success);
    font-weight: 800;
  }

  .negative {
    color: var(--strategy-danger);
    font-weight: 800;
  }

  .empty-cell {
    color: var(--strategy-text-faint);
    text-align: center !important;
  }

  @media (max-width: 980px) {
    .chart-grid,
    .table-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
