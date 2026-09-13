<template>
  <div class="etf-flow-panel">
    <div v-if="loading" class="etf-flow-panel__state">加载中…</div>
    <div v-else-if="error" class="etf-flow-panel__state etf-flow-panel__state--error">
      {{ error }}
    </div>
    <div v-else-if="days.length === 0" class="etf-flow-panel__state">暂无 ETF 资金流数据</div>
    <div v-else class="etf-flow-panel__body">
      <div class="etf-flow-panel__summary">
        <div class="etf-flow-panel__metric">
          <span>最新数据日</span>
          <strong>{{ observedAt ?? '—' }}</strong>
        </div>
        <div class="etf-flow-panel__metric">
          <span>单位</span>
          <strong>百万美元</strong>
        </div>
      </div>

      <div class="etf-flow-panel__table-wrap">
        <table class="etf-flow-panel__table">
          <thead>
            <tr>
              <th class="etf-flow-panel__corner">日期</th>
              <th
                v-for="ticker in tickers"
                :key="ticker"
                :class="{ 'is-total': ticker === 'Total' }"
              >
                {{ ticker }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="day in days" :key="day.date">
              <th class="etf-flow-panel__date">{{ formatDate(day.date) }}</th>
              <td
                v-for="ticker in tickers"
                :key="ticker"
                :class="[
                  'etf-flow-panel__cell',
                  flowClass(day.flows[ticker]),
                  { 'is-total': ticker === 'Total' },
                ]"
              >
                {{ formatFlow(day.flows[ticker]) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="etf-flow-panel__legend">
        <span><i class="is-inflow"></i>流入</span>
        <span><i class="is-outflow"></i>流出</span>
        <span><i class="is-flat"></i>无变化</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';

  import { getCryptoEtfFlow, type CryptoEtfFlowData } from '@/api/hedgeResearch';

  const loading = ref(true);
  const error = ref('');
  const data = ref<CryptoEtfFlowData | null>(null);

  const observedAt = computed(() => data.value?.observedAt ?? null);
  const tickers = computed(() => data.value?.tickers ?? []);
  const days = computed(() => data.value?.days ?? []);

  function formatDate(iso: string): string {
    const [, m, d] = iso.split('-');
    return `${Number(m)}/${Number(d)}`;
  }

  function formatFlow(value: number | null | undefined): string {
    if (value == null) return '—';
    if (Math.abs(value) < 0.05) return '0.0';
    const sign = value > 0 ? '+' : '';
    return `${sign}${value.toFixed(1)}`;
  }

  function flowClass(value: number | null | undefined): string {
    if (value == null) return 'is-na';
    if (value > 0.05) return 'is-inflow';
    if (value < -0.05) return 'is-outflow';
    return 'is-flat';
  }

  onMounted(async () => {
    try {
      const response = await getCryptoEtfFlow();
      data.value = response.data;
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'ETF 资金流数据获取失败';
    } finally {
      loading.value = false;
    }
  });
</script>

<style scoped lang="less">
  .etf-flow-panel {
    min-height: 180px;
    padding: 6px 2px;
  }

  .etf-flow-panel__state {
    display: flex;
    min-height: 160px;
    align-items: center;
    justify-content: center;
    color: var(--strategy-text-faint, #667085);
    font-size: 13px;
  }

  .etf-flow-panel__state--error {
    color: var(--strategy-danger, #df4d4d);
  }

  .etf-flow-panel__body {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .etf-flow-panel__summary {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  .etf-flow-panel__metric {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 96px;
    padding: 8px 12px;
    border: 1px solid var(--strategy-border, #e5ebf3);
    border-radius: 10px;
    background: var(--strategy-surface-muted, #f5f8fc);
  }

  .etf-flow-panel__metric span {
    color: var(--strategy-text-faint, #667085);
    font-size: 11px;
  }

  .etf-flow-panel__metric strong {
    color: var(--strategy-text-1, #13243d);
    font-size: 14px;
    font-weight: 700;
  }

  .etf-flow-panel__table-wrap {
    overflow-x: auto;
    border: 1px solid var(--strategy-border, #e5ebf3);
    border-radius: 10px;
  }

  .etf-flow-panel__table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    white-space: nowrap;
  }

  .etf-flow-panel__table th,
  .etf-flow-panel__table td {
    padding: 7px 9px;
    border-bottom: 1px solid var(--strategy-border-soft, #edf2f7);
    text-align: right;
  }

  .etf-flow-panel__table thead th {
    position: sticky;
    top: 0;
    background: var(--strategy-table-head-bg, #f7f9fc);
    color: var(--strategy-text-2, #2f3e52);
    font-weight: 700;
  }

  .etf-flow-panel__table thead th.is-total {
    color: var(--strategy-accent-strong, #c94848);
  }

  .etf-flow-panel__table tbody tr:last-child th,
  .etf-flow-panel__table tbody tr:last-child td {
    border-bottom: none;
  }

  .etf-flow-panel__corner,
  .etf-flow-panel__date {
    position: sticky;
    left: 0;
    z-index: 1;
    background: var(--strategy-surface-muted, #f5f8fc);
    color: var(--strategy-text-2, #2f3e52);
    font-weight: 700;
    text-align: left !important;
  }

  .etf-flow-panel__cell {
    font-variant-numeric: tabular-nums;
    font-weight: 600;
  }

  .etf-flow-panel__cell.is-total {
    border-left: 1px solid var(--strategy-border-strong, #d7e0ec);
    font-weight: 800;
  }

  .etf-flow-panel__cell.is-inflow {
    color: var(--strategy-accent-strong, #c94848);
  }

  .etf-flow-panel__cell.is-outflow {
    color: var(--strategy-success, #189b50);
  }

  .etf-flow-panel__cell.is-flat {
    color: var(--strategy-text-faint, #667085);
  }

  .etf-flow-panel__cell.is-na {
    color: var(--strategy-border-strong, #d7e0ec);
  }

  .etf-flow-panel__legend {
    display: flex;
    flex-wrap: wrap;
    gap: 14px;
    color: var(--strategy-text-faint, #667085);
    font-size: 11px;
  }

  .etf-flow-panel__legend span {
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }

  .etf-flow-panel__legend i {
    width: 9px;
    height: 9px;
    border-radius: 3px;
  }

  .etf-flow-panel__legend i.is-inflow {
    background: var(--strategy-accent, #da5b5b);
  }

  .etf-flow-panel__legend i.is-outflow {
    background: var(--strategy-success, #189b50);
  }

  .etf-flow-panel__legend i.is-flat {
    background: var(--strategy-border-strong, #d7e0ec);
  }
</style>
