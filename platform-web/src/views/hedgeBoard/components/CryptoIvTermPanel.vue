<template>
  <div class="iv-panel">
    <div v-if="loading" class="iv-panel__state">加载中…</div>
    <div v-else-if="error" class="iv-panel__state iv-panel__state--error">{{ error }}</div>
    <div v-else-if="!snapshot || snapshot.tenors.length === 0" class="iv-panel__state">
      暂无 IV 数据
    </div>
    <div v-else class="iv-panel__body">
      <!-- 顶部标题 + 时间戳 + 视图切换按钮 -->
      <header class="iv-panel__header">
        <h4 class="iv-panel__title">ATM IV · 期限结构</h4>
        <div class="iv-panel__mode">
          <button
            type="button"
            class="iv-panel__mode-btn"
            :class="{ 'iv-panel__mode-btn--active': mode === 'table' }"
            aria-label="表格视图"
            :aria-pressed="mode === 'table'"
            @click="mode = 'table'"
          >
            <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
              <rect x="1.5" y="3" width="13" height="2" rx="0.5" />
              <rect x="1.5" y="7" width="13" height="2" rx="0.5" />
              <rect x="1.5" y="11" width="13" height="2" rx="0.5" />
            </svg>
          </button>
          <button
            type="button"
            class="iv-panel__mode-btn"
            :class="{ 'iv-panel__mode-btn--active': mode === 'chart' }"
            aria-label="折线视图"
            :aria-pressed="mode === 'chart'"
            @click="onSwitchToChart"
          >
            <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
              <polyline
                points="1,13 4,7 7,9 10,3 15,8"
                fill="none"
                stroke="currentColor"
                stroke-width="1.6"
                stroke-linejoin="round"
                stroke-linecap="round"
              />
            </svg>
          </button>
        </div>
      </header>
      <div class="iv-panel__meta">
        <span
          v-for="t in snapshot.tenors"
          :key="t.tenor"
          class="iv-panel__legend"
          :style="{ color: TENOR_COLORS[t.tenor] }"
        >
          <span class="iv-panel__legend-dot" :style="{ background: TENOR_COLORS[t.tenor] }"></span>
          <span class="iv-panel__legend-name">{{ t.tenor }}</span>
          <strong>{{ t.iv.toFixed(2) }}%</strong>
          <small>{{ formatTs(snapshot.observedAt) }}</small>
        </span>
      </div>

      <!-- 表格视图 -->
      <div v-if="mode === 'table'" class="iv-panel__table-wrap">
        <table class="iv-panel__table">
          <thead>
            <tr>
              <th>期限</th>
              <th>当前</th>
              <th>区间最低</th>
              <th>区间最高</th>
              <th>历史最低</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in snapshot.tenors" :key="t.tenor">
              <td class="iv-panel__tenor" :style="{ color: TENOR_COLORS[t.tenor] }">
                <span
                  class="iv-panel__tenor-dot"
                  :style="{ background: TENOR_COLORS[t.tenor] }"
                ></span>
                {{ t.tenor }}
              </td>
              <td class="iv-panel__iv">{{ formatIv(t.iv) }}</td>
              <td class="iv-panel__iv iv-panel__iv--low">{{
                formatIv(stats[t.tenor]?.rangeLow)
              }}</td>
              <td class="iv-panel__iv iv-panel__iv--high">{{
                formatIv(stats[t.tenor]?.rangeHigh)
              }}</td>
              <td class="iv-panel__iv iv-panel__iv--lowest">{{
                formatIv(stats[t.tenor]?.historyLow)
              }}</td>
            </tr>
          </tbody>
        </table>
        <p class="iv-panel__footnote">
          统计范围为已有的每日 IV 历史；缺失期限保留为空，不代表全市场历史极值。
        </p>
      </div>

      <!-- 折线视图 -->
      <div v-else class="iv-panel__chart-wrap">
        <div v-if="historyLoading" class="iv-panel__state">历史加载中…</div>
        <div v-if="historyError" class="iv-panel__state iv-panel__state--error">
          {{ historyError }}
        </div>
        <SourceSeriesPlot
          v-if="!historyLoading && chartSeries.some((item) => item.observations.length)"
          :series="chartSeries"
          :colors="chartSeries.map((item) => TENOR_COLORS[item.label])"
          unit-label="%"
        />
        <p v-else-if="!historyLoading && !historyError" class="iv-panel__state">暂无 IV 历史数据</p>
        <p class="iv-panel__footnote">
          Deribit 1M / 3M / 6M / 1Y ATM IV · 可拖动时间范围，悬停查看原始数值。
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';

  import {
    getCryptoIvHistory,
    getCryptoIvSnapshot,
    type CryptoIvHistoryPoint,
    type CryptoIvHistoryStats,
    type CryptoIvSnapshotData,
    type MacroDashboardSeries,
  } from '@/api/hedgeResearch';

  import SourceSeriesPlot from '../charts/SourceSeriesPlot.vue';

  // Stable colors for option tenors.
  const TENOR_COLORS: Record<string, string> = {
    '1M': '#5b8def',
    '3M': '#e6c34a',
    '6M': '#5fc76f',
    '1Y': '#e88a3f',
  };

  const loading = ref(true);
  const error = ref('');
  const snapshot = ref<CryptoIvSnapshotData | null>(null);
  const stats = ref<Record<string, CryptoIvHistoryStats>>({});

  type Mode = 'table' | 'chart';
  const mode = ref<Mode>('chart');
  const historyLoading = ref(false);
  const historyError = ref('');
  const histories = ref<Record<string, CryptoIvHistoryPoint[]>>({});

  async function loadSnapshot() {
    const r = await getCryptoIvSnapshot();
    snapshot.value = r.data;
    await loadHistories();
  }

  async function loadHistories() {
    if (historyLoading.value) return;
    const missing = (snapshot.value?.tenors ?? []).filter((item) => !histories.value[item.tenor]);
    if (!missing.length) return;
    historyLoading.value = true;
    const failures: string[] = [];
    await Promise.all(
      missing.map(async (item) => {
        try {
          const result = await getCryptoIvHistory(item.tenor as '1M' | '3M' | '6M' | '1Y', 365);
          histories.value[item.tenor] = result.data.history;
          stats.value[item.tenor] = result.data.stats;
        } catch {
          failures.push(item.tenor);
        }
      }),
    );
    historyError.value = failures.length
      ? `${failures.join(' / ')} 历史暂不可用；再次切换折线视图可重试。`
      : '';
    historyLoading.value = false;
  }
  function onSwitchToChart() {
    mode.value = 'chart';
    loadHistories();
  }

  function formatIv(v: number | null | undefined): string {
    if (v == null) return '—';
    return `${v.toFixed(2)}%`;
  }

  function formatTs(iso: string | null | undefined): string {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    const hh = String(d.getHours()).padStart(2, '0');
    const mm = String(d.getMinutes()).padStart(2, '0');
    return `${m}-${dd} ${hh}:${mm}`;
  }

  const chartSeries = computed<MacroDashboardSeries[]>(() =>
    (snapshot.value?.tenors ?? []).map((tenor) => ({
      seriesId: `deribit_iv_${tenor.tenor}`,
      label: tenor.tenor,
      status: 'ready',
      unit: 'percent',
      frequency: 'daily',
      timezone: 'UTC',
      source: 'Deribit',
      sourceUrl: 'https://www.deribit.com/',
      isStale: false,
      methodologyVersion: 'iv-history',
      qualityFlags: [],
      observations: (histories.value[tenor.tenor] ?? []).map((point) => ({
        date: point.observedAt,
        value: point.iv,
      })),
    })),
  );
  onMounted(async () => {
    try {
      await loadSnapshot();
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'IV 数据获取失败';
    } finally {
      loading.value = false;
    }
  });
</script>

<style scoped lang="less">

  @media (max-width: 600px) {
    .iv-panel {
      padding: 0 14px 16px;
    }

    .iv-panel__meta {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .iv-panel__legend {
      min-height: 80px;
    }

    .iv-panel__table th,
    .iv-panel__table td {
      padding: 10px 8px;
      white-space: nowrap;
    }
  }

  .iv-panel {
    min-height: 220px;
    padding: 0 20px 18px;
  }

  .iv-panel__state {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 160px;
    color: var(--strategy-text-faint, #667085);
    font-size: 13px;
  }

  .iv-panel__state--error {
    color: var(--strategy-danger, #df4d4d);
  }

  .iv-panel__body {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  /* --- Header --- */
  .iv-panel__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-height: 30px;
  }

  .iv-panel__title {
    margin: 0;
    color: var(--strategy-text-1, #13243d);
    font-size: 14px;
    font-weight: 700;
  }

  .iv-panel__mode {
    display: inline-flex;
    overflow: hidden;
    border: 1px solid var(--strategy-border, #e5ebf3);
    border-radius: 6px;
  }

  .iv-panel__mode-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 30px;
    padding: 0;
    transition: all 0.12s;
    border: 0;
    background: var(--strategy-surface-muted, #f5f8fc);
    color: var(--strategy-text-2, #2f3e52);
    cursor: pointer;
  }

  .iv-panel__mode-btn + .iv-panel__mode-btn {
    border-left: 1px solid var(--strategy-border, #e5ebf3);
  }

  .iv-panel__mode-btn:hover {
    background: #fff;
  }

  .iv-panel__mode-btn--active {
    background: #fff;
    box-shadow: inset 0 -2px 0 var(--strategy-accent-strong, #0b3f9e);
    color: var(--strategy-accent-strong, #0b3f9e);
  }

  .iv-panel__meta {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 8px;
    margin: 2px 0 4px;
    color: var(--strategy-text-faint, #667085);
    font-size: 12px;
  }

  .iv-panel__meta-time {
    color: var(--strategy-text-2, #2f3e52);
    font-weight: 600;
  }

  .iv-panel__legend {
    display: grid;
    grid-template-columns: 8px minmax(0, 1fr);
    align-content: start;
    gap: 3px 8px;
    min-height: 96px;
    padding: 10px 12px;
    border: 1px solid #e5ecf3;
    border-radius: 8px;
    background: #f8fafc;
    font-variant-numeric: tabular-nums;
  }

  .iv-panel__legend strong,
  .iv-panel__legend small {
    grid-column: 2;
  }

  .iv-panel__legend strong {
    color: #20384d;
    font-size: 14px;
  }

  .iv-panel__legend small {
    color: #738497;
    font-size: 11px;
  }

  .iv-panel__legend-name {
    color: #60758a;
  }

  .iv-panel__legend-dot {
    width: 8px;
    height: 8px;
    margin-top: 5px;
    border-radius: 2px;
  }

  /* --- 表格 --- */
  .iv-panel__table-wrap {
    overflow-x: auto;
    border: 1px solid var(--strategy-border, #e5ebf3);
    border-radius: 10px;
  }

  .iv-panel__table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
  }

  .iv-panel__table th,
  .iv-panel__table td {
    padding: 14px;
    border-bottom: 1px solid var(--strategy-border-soft, #edf2f7);
    text-align: center;
  }

  .iv-panel__table thead th {
    background: var(--strategy-table-head-bg, #f7f9fc);
    color: var(--strategy-text-2, #2f3e52);
    font-weight: 700;
  }

  .iv-panel__table tbody tr:last-child td {
    border-bottom: none;
  }

  .iv-panel__tenor {
    font-weight: 700;
    text-align: left !important;
  }

  .iv-panel__tenor-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    margin-right: 6px;
    border-radius: 2px;
  }

  .iv-panel__iv {
    color: var(--strategy-text-1, #13243d);
    font-weight: 700;
    font-variant-numeric: tabular-nums;
  }

  .iv-panel__iv--low,
  .iv-panel__iv--lowest {
    color: #5b8def;
  }

  .iv-panel__iv--high {
    color: #e88a3f;
  }

  .iv-panel__footnote {
    margin: 0;
    padding-top: 10px;
    border-top: 1px solid #e8eef4;
    color: var(--strategy-text-faint, #667085);
    font-size: 11px;
    line-height: 1.5;
  }

  /* --- 折线 --- */
  .iv-panel__chart-wrap {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .iv-panel__chart {
    width: 100%;
    height: auto;
    border: 1px solid var(--strategy-border, #e5ebf3);
    border-radius: 10px;
    background: #fff;
  }

  .iv-panel__grid {
    stroke-width: 1;
    stroke: var(--strategy-border-soft, #edf2f7);
  }

  .iv-panel__axis {
    fill: var(--strategy-text-faint, #667085);
    font-size: 10px;
  }

  .iv-panel__series-label {
    font-size: 10px;
    font-weight: 700;
  }
</style>
