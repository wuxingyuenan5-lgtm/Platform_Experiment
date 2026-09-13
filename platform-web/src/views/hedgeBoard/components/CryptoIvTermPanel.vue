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
        <h4 class="iv-panel__title">BTC ATM IV 期限结构</h4>
        <div class="iv-panel__mode">
          <button
            type="button"
            class="iv-panel__mode-btn"
            :class="{ 'iv-panel__mode-btn--active': mode === 'table' }"
            aria-label="表格视图"
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
        <span class="iv-panel__meta-time">{{ formatTs(snapshot.observedAt) }}</span>
        <span
          v-for="t in snapshot.tenors"
          :key="t.tenor"
          class="iv-panel__legend"
          :style="{ color: TENOR_COLORS[t.tenor] }"
        >
          <span class="iv-panel__legend-dot" :style="{ background: TENOR_COLORS[t.tenor] }"></span>
          <span>{{ t.tenor }} {{ t.iv.toFixed(2) }}%</span>
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
              <td class="iv-panel__iv">{{ formatIv(stats[t.tenor]?.current) }}</td>
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
          区间 = 库内累积快照窗口（按日落库，每条 = 一日 1M/3M/6M/1Y IV）； 历史最低 =
          同一窗口最小值；首次上线仅 1 个数据点，区间 = 当前。
        </p>
      </div>

      <!-- 折线视图 -->
      <div v-else class="iv-panel__chart-wrap">
        <div v-if="historyLoading" class="iv-panel__state">历史加载中…</div>
        <div v-else-if="historyError" class="iv-panel__state iv-panel__state--error">
          {{ historyError }}
        </div>
        <svg
          v-else
          class="iv-panel__chart"
          :viewBox="`0 0 ${chart.width} ${chart.height}`"
          role="img"
          aria-label="BTC ATM IV 历史走势"
        >
          <g v-for="tick in chart.yTicks" :key="tick.value">
            <line
              :x1="chart.pad.left"
              :x2="chart.width - chart.pad.right"
              :y1="tick.y"
              :y2="tick.y"
              class="iv-panel__grid"
            />
            <text :x="chart.pad.left - 6" :y="tick.y + 3" text-anchor="end" class="iv-panel__axis">
              {{ tick.label }}
            </text>
          </g>
          <g v-for="series in chart.series" :key="series.tenor">
            <polyline
              v-if="series.points.length"
              :points="series.points"
              fill="none"
              :stroke="TENOR_COLORS[series.tenor]"
              stroke-width="1.5"
              stroke-linejoin="round"
              stroke-linecap="round"
            />
          </g>
          <text
            v-for="tick in chart.xTicks"
            :key="tick.label + tick.x"
            :x="tick.x"
            :y="chart.height - chart.pad.bottom + 14"
            text-anchor="middle"
            class="iv-panel__axis"
          >
            {{ tick.label }}
          </text>
          <text
            v-for="series in chart.series"
            :key="'label-' + series.tenor"
            :x="chart.width - chart.pad.right - 4"
            :y="series.labelY"
            text-anchor="end"
            class="iv-panel__series-label"
            :style="{ fill: TENOR_COLORS[series.tenor] }"
          >
            {{ series.tenor }} {{ series.lastValue ? series.lastValue.toFixed(1) + '%' : '—' }}
          </text>
        </svg>
        <p class="iv-panel__footnote">
          历史 = 每时段每日落库累积的 IV 序列；首次上线仅有 1 个点，后续将累积。 颜色沿用
          data.rtatrade.xyz 风格：1M 蓝 / 3M 黄 / 6M 绿 / 1Y 橙。
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
    type CryptoIvSnapshotTenor,
  } from '@/api/hedgeResearch';

  // data.rtatrade.xyz 风格的固定时段配色
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
  const mode = ref<Mode>('table');
  const historyLoading = ref(false);
  const historyError = ref('');
  const histories = ref<Record<string, CryptoIvHistoryPoint[]>>({});

  async function loadSnapshot() {
    const r = await getCryptoIvSnapshot();
    snapshot.value = r.data;
    // 串行拿 4 个时段历史（区间最低/最高/历史最低）
    for (const t of r.data.tenors) {
      try {
        const h = await getCryptoIvHistory(t.tenor as '1M' | '3M' | '6M' | '1Y', 365);
        stats.value[t.tenor] = h.data.stats;
      } catch (e) {
        stats.value[t.tenor] = {
          current: null,
          rangeLow: null,
          rangeHigh: null,
          historyLow: null,
          historyHigh: null,
          count: 0,
        };
      }
    }
  }

  async function loadHistories() {
    if (Object.keys(histories.value).length) return;
    historyLoading.value = true;
    historyError.value = '';
    try {
      const tenors = snapshot.value?.tenors ?? [];
      for (const t of tenors) {
        const r = await getCryptoIvHistory(t.tenor as '1M' | '3M' | '6M' | '1Y', 365);
        histories.value[t.tenor] = r.data.history;
      }
    } catch (e) {
      historyError.value = e instanceof Error ? e.message : '历史加载失败';
    } finally {
      historyLoading.value = false;
    }
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

  // --- 折线图布局 ---
  const chart = computed(() => {
    const width = 720;
    const height = 280;
    const pad = { left: 40, right: 80, top: 16, bottom: 28 };
    const innerW = width - pad.left - pad.right;
    const innerH = height - pad.top - pad.bottom;

    const allPoints = Object.values(histories.value).flat();
    if (allPoints.length === 0)
      return {
        width,
        height,
        pad,
        series: [] as Array<{
          tenor: string;
          points: string;
          lastValue: number | null;
          labelY: number;
        }>,
        xTicks: [] as Array<{ x: number; label: string }>,
        yTicks: [] as Array<{ value: number; label: string; y: number }>,
      };

    // Y 范围固定 28-65%（贴 data.rtatrade.xyz 截图）
    const yLo = 28;
    const yHi = 65;
    const yScale = (v: number) => pad.top + ((yHi - v) / (yHi - yLo)) * innerH;
    const yTicks = [0, 0.25, 0.5, 0.75, 1].map((r) => ({
      value: yHi - r * (yHi - yLo),
      label: `${(yHi - r * (yHi - yLo)).toFixed(0)}%`,
      y: yScale(yHi - r * (yHi - yLo)),
    }));

    // X 范围：所有 history 的最早/最晚日期
    const dates = allPoints.map((p) => p.observedAt).sort();
    const xMin = dates[0];
    const xMax = dates[dates.length - 1];
    const span = new Date(xMax).getTime() - new Date(xMin).getTime();
    const xRange = span === 0 ? 1 : span;
    const xScale = (ts: string) =>
      pad.left + ((new Date(ts).getTime() - new Date(xMin).getTime()) / xRange) * innerW;

    const xTicks = [0, 0.25, 0.5, 0.75, 1].map((r) => {
      const ts = new Date(
        new Date(xMin).getTime() + r * (new Date(xMax).getTime() - new Date(xMin).getTime()),
      );
      const yy = String(ts.getFullYear()).slice(2);
      const m = ts.getMonth() + 1;
      const d = ts.getDate();
      return { x: pad.left + r * innerW, label: `${yy}-${m}-${d < 10 ? '0' + d : d}` };
    });

    const series = (snapshot.value?.tenors ?? []).map((t: CryptoIvSnapshotTenor) => {
      const pts = (histories.value[t.tenor] ?? []).filter(
        (p): p is { observedAt: string; iv: number } => p.iv != null,
      );
      const polyline = pts
        .map((p) => `${xScale(p.observedAt).toFixed(1)},${yScale(p.iv).toFixed(1)}`)
        .join(' ');
      const last = pts.length ? pts[pts.length - 1].iv : null;
      const labelY = last != null ? yScale(last) : pad.top;
      return { tenor: t.tenor, points: polyline, lastValue: last, labelY };
    });

    return { width, height, pad, series, xTicks, yTicks };
  });

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
  .iv-panel {
    min-height: 220px;
    padding: 6px 2px;
  }

  .iv-panel__state {
    display: flex;
    min-height: 160px;
    align-items: center;
    justify-content: center;
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
  }

  .iv-panel__title {
    margin: 0;
    color: var(--strategy-text-1, #13243d);
    font-size: 14px;
    font-weight: 700;
  }

  .iv-panel__mode {
    display: inline-flex;
    border: 1px solid var(--strategy-border, #e5ebf3);
    border-radius: 6px;
    overflow: hidden;
  }

  .iv-panel__mode-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 24px;
    padding: 0;
    border: 0;
    background: var(--strategy-surface-muted, #f5f8fc);
    color: var(--strategy-text-2, #2f3e52);
    cursor: pointer;
    transition: all 0.12s;
  }

  .iv-panel__mode-btn + .iv-panel__mode-btn {
    border-left: 1px solid var(--strategy-border, #e5ebf3);
  }

  .iv-panel__mode-btn:hover {
    background: #ffffff;
  }

  .iv-panel__mode-btn--active {
    background: #ffffff;
    color: var(--strategy-accent-strong, #0b3f9e);
    box-shadow: inset 0 -2px 0 var(--strategy-accent-strong, #0b3f9e);
  }

  .iv-panel__meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 14px;
    color: var(--strategy-text-faint, #667085);
    font-size: 12px;
  }

  .iv-panel__meta-time {
    color: var(--strategy-text-2, #2f3e52);
    font-weight: 600;
  }

  .iv-panel__legend {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }

  .iv-panel__legend-dot {
    width: 8px;
    height: 8px;
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
    padding: 8px 14px;
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
    text-align: left !important;
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  .iv-panel__tenor-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 2px;
  }

  .iv-panel__iv {
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    color: var(--strategy-text-1, #13243d);
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
    background: #ffffff;
  }

  .iv-panel__grid {
    stroke: var(--strategy-border-soft, #edf2f7);
    stroke-width: 1;
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
