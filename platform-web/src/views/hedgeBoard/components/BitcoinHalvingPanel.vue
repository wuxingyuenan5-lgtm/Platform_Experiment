<template>
  <div class="halving-panel">
    <p v-if="loading" role="status">正在读取减半周期数据…</p>
    <p v-else-if="error" role="alert">{{ error }}</p>
    <template v-else>
      <div class="halving-controls">
        <div role="group" aria-label="减半周期范围">
          <button
            v-for="days in [365, 730, 0]"
            :key="days"
            :aria-pressed="windowDays === days"
            @click="windowDays = days"
          >
            {{ days ? `${days}天` : '全部' }}
          </button>
        </div>
        <button :aria-pressed="logScale" @click="logScale = !logScale">{{
          logScale ? '对数坐标' : '线性坐标'
        }}</button>
      </div>
      <p class="halving-note"
        >减半日 = 100 · UTC 日度价格（多交易所均价） · Blockchain.com · 资料截至 {{ cutoff
        }}{{ stale ? ' · 待更新' : '' }}</p
      >
      <div class="halving-layout">
        <div ref="plotHost" class="halving-main">
          <div class="halving-legend" role="group" aria-label="显示减半周期">
            <button
              v-for="(cycle, index) in cycles"
              :key="cycle.seriesId"
              :aria-pressed="!hiddenCycles.has(cycle.seriesId)"
              :disabled="visibleCycles.length === 1 && !hiddenCycles.has(cycle.seriesId)"
              @click="toggleCycle(cycle.seriesId)"
            >
              <span :style="{ background: colors[index] }" aria-hidden="true"></span>
              {{ cycle.label }}
            </button>
          </div>
          <svg
            :viewBox="`0 0 ${chartWidth} ${chartHeight}`"
            :style="{ height: `${chartHeight}px` }"
            role="img"
            aria-label="BTC 四次减半后的价格表现"
            @mousemove="moveCursor"
          >
            <g v-for="tick in ticks" :key="tick">
              <line
                x1="60"
                :x2="rightEdge"
                :y1="y(tick)"
                :y2="y(tick)"
                stroke="#e2e8f0"
                stroke-dasharray="3 4"
              />
              <text x="52" :y="y(tick) + 4" text-anchor="end" class="axis">
                {{ tick.toLocaleString('en-US', { maximumFractionDigits: 0 }) }}
              </text>
            </g>
            <g v-for="day in dayTicks" :key="day">
              <line :x1="x(day)" :x2="x(day)" y1="20" :y2="plotBottom" stroke="#f1f5f9" />
              <text :x="x(day)" :y="plotBottom + 22" text-anchor="middle" class="axis">
                {{ day }}
              </text>
            </g>
            <text x="60" y="12" class="axis">价格指数</text>
            <path
              v-for="(cycle, index) in cycles"
              :key="cycle.seriesId"
              v-show="!hiddenCycles.has(cycle.seriesId)"
              :d="path(cycle)"
              fill="none"
              :stroke="colors[index]"
              stroke-width="2"
            />
            <line
              :x1="x(cursorDay)"
              :x2="x(cursorDay)"
              y1="20"
              :y2="plotBottom"
              stroke="#64748b"
              stroke-dasharray="4 4"
            />
            <template v-for="(cycle, index) in cycles" :key="`${cycle.seriesId}-cursor`">
              <circle
                v-if="!hiddenCycles.has(cycle.seriesId) && pointAt(cycle)?.value != null"
                :cx="x(cursorDay)"
                :cy="y(Number(pointAt(cycle)?.value))"
                r="4"
                :fill="colors[index]"
                stroke="white"
                stroke-width="1.5"
              />
            </template>
            <text :x="rightEdge" :y="chartHeight - 12" text-anchor="end" class="axis">
              减半后天数
            </text>
          </svg>
          <label class="halving-slider"
            >减半后第 {{ cursorDay }} 天
            <input
              v-model.number="cursorDay"
              type="range"
              min="0"
              :max="maxDay"
              step="1"
              aria-label="减半后天数"
            />
          </label>
        </div>
        <div class="halving-table"
          ><table>
            <thead
              ><tr><th>减半周期</th><th>对应日期</th><th>价格指数</th><th>累计涨跌</th></tr></thead
            >
            <tbody>
              <tr
                v-for="(cycle, index) in cycles"
                :key="cycle.seriesId"
                :class="{ 'cycle-hidden': hiddenCycles.has(cycle.seriesId) }"
              >
                <td
                  ><a
                    :href="cycle.blockUrl"
                    target="_blank"
                    rel="noopener noreferrer"
                    :style="{ color: colors[index] }"
                    >{{ cycle.label }}</a
                  ></td
                >
                <td data-label="对应日期">{{ pointAt(cycle)?.date ?? '—' }}</td>
                <td data-label="价格指数">{{ formatValue(pointAt(cycle)?.value) }}</td>
                <td data-label="累计涨跌">{{
                  pointAt(cycle)?.value == null
                    ? '—'
                    : `${(Number(pointAt(cycle)?.value) - 100).toFixed(2)}%`
                }}</td>
              </tr>
            </tbody>
          </table></div
        >
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
  import { useDashboardRefresh } from '../useDashboardRefresh';

  import { useElementSize } from '@vueuse/core';
  import { computed, ref, shallowRef, watch } from 'vue';
  import { getCryptoDashboardV1, type MacroDashboardSeries } from '@/api/hedgeResearch';

  interface CyclePoint {
    date: string;
    day: number;
    value: number | null;
  }
  interface Cycle extends MacroDashboardSeries {
    points: CyclePoint[];
    byDay: Map<number, CyclePoint>;
    blockUrl: string;
  }
  const plotHost = ref<HTMLElement | null>(null);
  const { width } = useElementSize(plotHost);
  const chartWidth = computed(() => Math.max(300, width.value));
  const chartHeight = computed(() =>
    Math.round(Math.max(280, Math.min(420, chartWidth.value / 1.8))),
  );
  const plotBottom = computed(() => chartHeight.value - 60);
  const rightEdge = computed(() => chartWidth.value - 22);
  const cycles = shallowRef<Cycle[]>([]);
  const loading = ref(true),
    error = ref(''),
    windowDays = ref(0),
    cursorDay = ref(365),
    logScale = ref(true);
  const colors = ['#20a5a5', '#369dc3', '#a14fba', '#cf8adb'];
  const hiddenCycles = ref(new Set<string>());
  const visibleCycles = computed(() =>
    cycles.value.filter((cycle) => !hiddenCycles.value.has(cycle.seriesId)),
  );
  function toggleCycle(id: string) {
    const next = new Set(hiddenCycles.value);
    if (next.has(id)) next.delete(id);
    else if (visibleCycles.value.length > 1) next.add(id);
    hiddenCycles.value = next;
  }
  const maxDay = computed(() =>
    Math.max(
      1,
      Math.min(
        windowDays.value || Infinity,
        Math.max(...cycles.value.flatMap((c) => c.points.map((p) => p.day)), 1),
      ),
    ),
  );
  const dayTicks = computed(() =>
    [0, 0.25, 0.5, 0.75, 1].map((fraction) => Math.round(maxDay.value * fraction)),
  );
  watch(maxDay, (days) => {
    cursorDay.value = Math.min(cursorDay.value, days);
  });
  const cutoff = computed(
    () =>
      cycles.value
        .map((c) => c.asOf ?? '')
        .sort()
        .at(-1) || '—',
  );
  const stale = computed(() => cycles.value.some((c) => c.isStale));
  const values = computed(() =>
    visibleCycles.value
      .flatMap((c) =>
        c.points
          .filter((p) => p.day <= maxDay.value && p.value !== null)
          .map((p) => Number(p.value)),
      )
      .filter((v) => v > 0),
  );
  const transform = (value: number) => (logScale.value ? Math.log10(value) : value);
  const bounds = computed(() => {
    const all = [...values.value, 100].map(transform);
    const minimum = Math.min(...all),
      maximum = Math.max(...all);
    const step = 10 ** Math.floor(Math.log10(Math.max(maximum, 1)));
    const low = logScale.value ? Math.floor(minimum) : 0;
    const high = logScale.value ? Math.ceil(maximum) : Math.ceil(maximum / step) * step;
    return { low, span: high - low || 1 };
  });
  const ticks = computed(() =>
    logScale.value
      ? Array.from(
          { length: Math.round(bounds.value.span) + 1 },
          (_, index) => 10 ** (bounds.value.low + index),
        )
      : [0, 0.25, 0.5, 0.75, 1].map((fraction) => fraction * bounds.value.span),
  );
  const x = (day: number) => 60 + (day / maxDay.value) * (rightEdge.value - 60);
  const y = (value: number) =>
    plotBottom.value -
    ((transform(value) - bounds.value.low) / bounds.value.span) * (plotBottom.value - 20);
  function path(cycle: Cycle) {
    let previous = -2;
    return cycle.points
      .filter((p) => p.day <= maxDay.value)
      .map((point) => {
        if (point.value === null || point.value <= 0) {
          previous = -2;
          return '';
        }
        const command = point.day === previous + 1 ? 'L' : 'M';
        previous = point.day;
        return `${command}${x(point.day).toFixed(2)},${y(point.value).toFixed(2)}`;
      })
      .join(' ');
  }
  const pointAt = (cycle: Cycle) => cycle.byDay.get(cursorDay.value);
  const formatValue = (value: number | null | undefined) =>
    value == null ? '—' : value.toFixed(2);
  function moveCursor(event: MouseEvent) {
    const rect = (event.currentTarget as SVGElement).getBoundingClientRect();
    cursorDay.value = Math.round(
      Math.max(
        0,
        Math.min(
          1,
          (((event.clientX - rect.left) / rect.width) * chartWidth.value - 60) /
            (rightEdge.value - 60),
        ),
      ) * maxDay.value,
    );
  }
  useDashboardRefresh(async () => {
    try {
      const result = await getCryptoDashboardV1();
      error.value = '';
      const group = result.groups.halvingCycles ?? [];
      if (group.length !== 4) throw new Error('incomplete cycles');
      cycles.value = group.map((series) => {
        const baseDate = series.qualityFlags
          .find((flag) => flag.startsWith('base_date:'))
          ?.slice(10);
        const height = series.qualityFlags
          .find((flag) => flag.startsWith('halving_block:'))
          ?.slice(14);
        const start = Date.parse(`${baseDate}T00:00:00Z`);
        if (!Number.isFinite(start) || !height) throw new Error('missing cycle identity');
        const points = series.observations.map((point) => ({
          date: point.date,
          day: Math.round((Date.parse(`${point.date}T00:00:00Z`) - start) / 86400000),
          value: point.value === null ? null : Number(point.value),
        }));
        return {
          ...series,
          label: `${baseDate?.slice(0, 4)} 周期`,
          points,
          byDay: new Map(points.map((point) => [point.day, point])),
          blockUrl: `https://www.blockchain.com/explorer/blocks/btc/${height}`,
        };
      });
    } catch {
      error.value = '减半周期数据暂不可用。';
    } finally {
      loading.value = false;
    }
  });
</script>

<style scoped>
  .halving-panel {
    width: 100%;
    min-width: 0;
    padding: 0 20px 20px;
    color: #334155;
    container: halving-panel / inline-size;
  }

  .halving-controls,
  .halving-controls > div {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }

  .halving-controls {
    justify-content: space-between;
  }

  button {
    padding: 5px 10px;
    border: 1px solid #dbe4ea;
    border-radius: 7px;
    background: white;
    font-size: 12px;
    cursor: pointer;
  }

  button[aria-pressed='true'] {
    background: #edf4ff;
    color: #165dff;
  }

  button:focus-visible,
  input:focus-visible {
    outline: 2px solid #165dff;
    outline-offset: 3px;
  }

  .halving-legend {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-start;
    margin: 12px 0 6px;
    gap: 6px;
  }

  .halving-legend button {
    display: inline-flex;
    align-items: center;
    border-color: transparent;
    background: transparent;
    color: #334155;
    gap: 5px;
  }

  .halving-legend button[aria-pressed='false'] {
    opacity: 0.4;
    text-decoration: line-through;
  }

  .halving-legend span {
    width: 9px;
    height: 9px;
    border-radius: 2px;
  }

  .halving-table {
    margin-top: 12px;
    padding-left: 20px;
    overflow-x: auto;
    border-left: 1px solid #e4ebf2;
  }

  .cycle-hidden {
    opacity: 0.45;
  }

  .halving-note {
    margin: 12px 0 0;
    color: #64748b;
    font-size: 12px;
  }

  svg {
    display: block;
    width: 100%;
  }

  .axis {
    fill: #64748b;
    font-size: 13px;
  }

  .halving-slider {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 12px;
  }

  input {
    flex: 1;
    min-width: 90px;
  }

  table {
    width: 100%;
    margin-top: 10px;
    border-collapse: collapse;
    font-size: 12px;
  }

  th,
  td {
    padding: 5px 3px;
    text-align: right;
    white-space: nowrap;
  }

  th:first-child,
  td:first-child {
    text-align: left;
  }

  .halving-layout {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 240px;
    gap: 24px;
    align-items: start;
  }

  .halving-main {
    min-width: 0;
  }

  .halving-table table,
  .halving-table tbody {
    display: block;
    margin: 0;
  }

  .halving-table thead {
    display: none;
  }

  .halving-table tr {
    display: grid;
    grid-template-columns: 1fr;
    padding: 6px 0;
    border-bottom: 1px solid #e4ebf2;
  }

  .halving-table tr:last-child {
    border-bottom: 0;
  }

  .halving-table td {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding: 2px 0;
    line-height: 1.45;
    font-variant-numeric: tabular-nums;
  }

  .halving-table td:first-child {
    padding-bottom: 5px;
    font-weight: 700;
  }

  .halving-table td[data-label]::before {
    content: attr(data-label);
    color: #718396;
  }

  @container halving-panel (max-width: 850px) {
    .halving-layout {
      grid-template-columns: minmax(0, 1fr);
      gap: 12px;
    }

    .halving-table {
      padding-left: 0;
      border-left: 0;
    }

    .halving-table tbody {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 0 20px;
    }
  }

  @media (max-width: 600px) {
    .halving-panel {
      padding: 0 14px 16px;
    }

    .halving-table tbody {
      grid-template-columns: 1fr;
    }

    .halving-slider {
      flex-wrap: wrap;
    }

    svg {
      height: auto;
    }
  }
</style>
