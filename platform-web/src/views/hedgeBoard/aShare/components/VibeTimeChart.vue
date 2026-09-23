<template>
  <article class="vibe-time-chart">
    <header class="vibe-chart-head"
      ><h3>{{ title }}</h3
      ><div class="range-buttons" role="group" :aria-label="`${title}历史范围`"
        ><button
          v-for="size in [60, 90, 0]"
          :key="size"
          type="button"
          :aria-pressed="preset === size"
          :class="{ active: preset === size }"
          @click="setPreset(size)"
          >{{ size ? `近${size}日` : '全部' }}</button
        ></div
      ></header
    >
    <div class="vibe-chart-subtitle"
      ><span>{{ yLabel }}</span
      ><span v-if="rightLabel">右轴：{{ rightLabel }}</span></div
    >
    <div class="vibe-chart-legend">
      <button
        v-for="(item, index) in series"
        :key="item.name"
        type="button"
        class="vibe-legend-btn"
        :class="{ off: hidden.has(index) }"
        :aria-pressed="!hidden.has(index)"
        @click="toggle(index)"
        ><i :style="{ background: item.color }"></i>{{ item.name }}</button
      >
    </div>
    <div v-if="!hasValues" class="chart-empty">{{
      visible.length ? '此范围暂无有效数据' : '点击图例选择要显示的数据'
    }}</div>
    <div v-else class="vibe-chart-stage">
      <svg
        class="vibe-chart-svg"
        viewBox="0 0 1200 350"
        tabindex="0"
        role="img"
        :aria-label="`${title}，${shownDates[0]}至${shownDates.at(-1)}，左右方向键查看数值`"
        @mousemove="onMove"
        @mouseleave="hover = null"
        @focus="hover = end"
        @blur="hover = null"
        @keydown.left.prevent="moveHover(-1)"
        @keydown.right.prevent="moveHover(1)"
      >
        <g v-for="tick in ticks" :key="tick">
          <line
            :x1="left"
            :y1="top + tick * (bottom - top)"
            :x2="right"
            :y2="top + tick * (bottom - top)"
            class="chart-grid"
          />
          <text :x="left - 10" :y="top + tick * (bottom - top) + 4" text-anchor="end">
            {{ axisLabel('left', tick) }}
          </text>
          <text v-if="rightLabel" :x="right + 10" :y="top + tick * (bottom - top) + 4">
            {{ axisLabel('right', tick) }}
          </text>
        </g>
        <text
          v-for="index in dateTicks"
          :key="index"
          :x="x(index)"
          y="336"
          :text-anchor="index === start ? 'start' : index === end ? 'end' : 'middle'"
        >
          {{ dates[index]?.slice(5) }}
        </text>
        <g v-for="entry in visible" :key="entry.item.name">
          <template v-if="entry.item.type === 'bar'">
            <rect
              v-for="bar in bars(entry.item)"
              :key="bar.index"
              :x="bar.x"
              :y="bar.y"
              :width="bar.width"
              :height="bar.height"
              :fill="entry.item.color"
              opacity="0.4"
            />
          </template>
          <template v-else v-for="(segment, index) in segments(entry.item)" :key="index">
            <path
              v-if="entry.item.type === 'area'"
              :d="areaPath(segment, entry.item)"
              :fill="entry.item.color"
              opacity="0.12"
            />
            <polyline
              :points="segment.map((point) => `${point.x},${point.y}`).join(' ')"
              :stroke="entry.item.color"
              class="vibe-chart-line"
            />
          </template>
        </g>
        <line
          v-if="hover != null"
          :x1="x(hover)"
          :x2="x(hover)"
          :y1="top"
          :y2="bottom"
          class="hover-line"
        />
      </svg>
      <div v-if="hover != null" class="vibe-chart-tooltip" role="status"
        ><b>{{ dates[hover] }}</b
        ><div v-for="entry in visible" :key="entry.item.name"
          ><i :style="{ background: entry.item.color }"></i>{{ entry.item.name }}：{{
            valueLabel(entry.item.values[hover], entry.item)
          }}</div
        ></div
      >
    </div>
    <div
      v-if="dates.length > 1"
      class="vibe-chart-range"
      :style="{
        '--range-start': `${rangeStartPercent}%`,
        '--range-end': `${rangeEndPercent}%`,
      }"
    >
      <div class="vibe-chart-range__labels" aria-hidden="true">
        <span>{{ formatDateLabel(dates[start]) }}</span>
        <span>{{ formatDateLabel(dates[end]) }}</span>
      </div>
      <div class="vibe-chart-range__viewport">
        <svg viewBox="0 0 100 20" preserveAspectRatio="none" aria-hidden="true">
          <polyline :points="overviewPoints" />
        </svg>
        <span class="vibe-chart-range__rail" aria-hidden="true"></span>
        <span class="vibe-chart-range__selection" aria-hidden="true"></span>
        <input
          v-model.number="startIndex"
          class="vibe-chart-range__thumb vibe-chart-range__thumb--start"
          type="range"
          min="0"
          :max="maxIndex"
          :aria-label="`${title}起始日期`"
          @input="onStartInput"
        />
        <input
          v-model.number="endIndex"
          class="vibe-chart-range__thumb vibe-chart-range__thumb--end"
          type="range"
          min="0"
          :max="maxIndex"
          :aria-label="`${title}结束日期`"
          @input="onEndInput"
        />
      </div>
    </div>
    <footer
      >{{ shownDates[0] || '—' }} — {{ shownDates.at(-1) || '—'
      }}<span>{{ shownDates.length }}个交易日 · 空缺数据不连线</span></footer
    >
  </article>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue';

  export interface Series {
    name: string;
    values: Array<number | null | undefined>;
    type: 'bar' | 'line' | 'area';
    axis?: 'left' | 'right';
    color: string;
    sign?: 1 | -1;
    unit?: string;
    percent?: boolean;
  }
  const props = defineProps<{
    title: string;
    yLabel: string;
    rightLabel?: string;
    dates: string[];
    series: Series[];
  }>();
  const preset = ref<number | null>(90);
  const startIndex = ref(0);
  const endIndex = ref(0);
  const hidden = ref(new Set<number>());
  const hover = ref<number | null>(null);
  const left = 76,
    right = 1100,
    top = 22,
    bottom = 302;
  const ticks = [0, 0.25, 0.5, 0.75, 1];
  const maxIndex = computed(() => Math.max(0, props.dates.length - 1));
  const start = computed(() =>
    Math.max(0, Math.min(startIndex.value, Math.max(0, endIndex.value - 1))),
  );
  const end = computed(() =>
    Math.max(
      start.value + (props.dates.length > 1 ? 1 : 0),
      Math.min(endIndex.value, maxIndex.value),
    ),
  );
  const shownDates = computed(() => props.dates.slice(start.value, end.value + 1));
  const visible = computed(() =>
    props.series
      .map((item, index) => ({ item, index }))
      .filter((entry) => !hidden.value.has(entry.index)),
  );
  const numeric = (value: unknown): number | null =>
    value == null || value === '' || !Number.isFinite(Number(value)) ? null : Number(value);
  const hasValues = computed(() =>
    visible.value.some((entry) =>
      entry.item.values.slice(start.value, end.value + 1).some((value) => numeric(value) != null),
    ),
  );
  const dateTicks = computed(() => [
    ...new Set(
      Array.from({ length: 7 }, (_, i) =>
        Math.round(start.value + ((end.value - start.value) * i) / 6),
      ),
    ),
  ]);
  const rangeStartPercent = computed(() =>
    maxIndex.value ? (start.value / maxIndex.value) * 100 : 0,
  );
  const rangeEndPercent = computed(() =>
    maxIndex.value ? (end.value / maxIndex.value) * 100 : 100,
  );
  const overviewPoints = computed(() => {
    const item = visible.value[0]?.item || props.series[0];
    if (!item) return '';
    const values = item.values.map((raw) => numeric(raw));
    const finite = values.filter((value): value is number => value != null);
    if (!finite.length) return '';
    const min = Math.min(...finite);
    const max = Math.max(...finite);
    return values
      .map((value, index) => {
        const x = (index / Math.max(values.length - 1, 1)) * 100;
        const y = value == null || max === min ? 10 : 18 - ((value - min) / (max - min)) * 16;
        return `${x.toFixed(2)},${y.toFixed(2)}`;
      })
      .join(' ');
  });
  const bounds = computed(() => {
    const domain = (axis: string): [number, number] => {
      const items = visible.value.filter((entry) => (entry.item.axis || 'left') === axis);
      const values = items
        .flatMap((entry) =>
          entry.item.values.slice(start.value, end.value + 1).map((value) => {
            const n = numeric(value);
            return n == null ? null : n * (entry.item.sign || 1);
          }),
        )
        .filter((value): value is number => value != null);
      if (!values.length) return [0, 1];
      let min = Math.min(...values),
        max = Math.max(...values);
      if (items.some((entry) => entry.item.type === 'bar')) {
        min = Math.min(min, 0);
        max = Math.max(max, 0);
      }
      if (max === min) {
        min -= Math.abs(min) * 0.05 || 1;
        max += Math.abs(max) * 0.05 || 1;
      }
      const margin = (max - min) * 0.08;
      return [min - margin, max + margin];
    };
    return { left: domain('left'), right: domain('right') };
  });
  const x = (index: number) =>
    left + ((right - left) * (index - start.value)) / Math.max(1, end.value - start.value);
  const y = (value: number, item: Series) => {
    const [min, max] = bounds.value[item.axis || 'left'];
    return bottom - ((value - min) / (max - min)) * (bottom - top);
  };
  type Point = { x: number; y: number };
  function segments(item: Series): Point[][] {
    const result: Point[][] = [];
    let current: Point[] = [];
    item.values.slice(start.value, end.value + 1).forEach((raw, offset) => {
      const value = numeric(raw);
      if (value == null) {
        if (current.length) result.push(current);
        current = [];
      } else current.push({ x: x(start.value + offset), y: y(value * (item.sign || 1), item) });
    });
    if (current.length) result.push(current);
    return result;
  }
  function areaPath(points: Point[], item: Series) {
    const baseline = Math.min(bottom, Math.max(top, y(0, item)));
    return `M${points[0].x},${baseline} L${points
      .map((point) => `${point.x},${point.y}`)
      .join(' L')} L${points.at(-1)?.x},${baseline} Z`;
  }
  function bars(item: Series) {
    const width = Math.max(0.5, Math.min(10, ((right - left) / shownDates.value.length) * 0.65));
    return item.values.slice(start.value, end.value + 1).flatMap((raw, offset) => {
      const value = numeric(raw);
      if (value == null) return [];
      const py = y(value * (item.sign || 1), item),
        zero = y(0, item);
      return [
        {
          index: offset,
          x: x(start.value + offset) - width / 2,
          y: Math.min(py, zero),
          height: Math.abs(py - zero),
          width,
        },
      ];
    });
  }
  function axisLabel(axis: 'left' | 'right', tick: number) {
    const [min, max] = bounds.value[axis];
    const value = max - tick * (max - min);
    const percent = visible.value.find((entry) => (entry.item.axis || 'left') === axis)?.item
      .percent;
    return percent
      ? `${(value * 100).toFixed(1)}%`
      : value.toLocaleString('zh-CN', { maximumFractionDigits: 1 });
  }
  function valueLabel(raw: unknown, item: Series) {
    const value = numeric(raw);
    if (value == null) return '—';
    return item.percent
      ? `${(value * 100).toFixed(2)}%`
      : `${value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })}${item.unit || ''}`;
  }
  function toggle(index: number) {
    const next = new Set(hidden.value);
    next.has(index) ? next.delete(index) : next.add(index);
    hidden.value = next;
  }
  function onMove(event: MouseEvent) {
    const rect = (event.currentTarget as SVGSVGElement).getBoundingClientRect();
    const position = ((event.clientX - rect.left) / rect.width) * 1200;
    hover.value = Math.max(
      start.value,
      Math.min(
        end.value,
        Math.round(start.value + ((position - left) / (right - left)) * (end.value - start.value)),
      ),
    );
  }
  function moveHover(delta: number) {
    hover.value = Math.max(start.value, Math.min(end.value, (hover.value ?? end.value) + delta));
  }
  function setPreset(size: number) {
    preset.value = size;
    const max = maxIndex.value;
    endIndex.value = max;
    startIndex.value = size ? Math.max(0, max - size + 1) : 0;
    hover.value = null;
  }
  function onStartInput(event: Event) {
    const value = Number((event.target as HTMLInputElement).value);
    if (Number.isFinite(value)) startIndex.value = value;
    preset.value = null;
    startIndex.value = Math.min(startIndex.value, Math.max(0, endIndex.value - 1));
    hover.value = null;
  }
  function onEndInput(event: Event) {
    const value = Number((event.target as HTMLInputElement).value);
    if (Number.isFinite(value)) endIndex.value = value;
    preset.value = null;
    endIndex.value = Math.max(endIndex.value, Math.min(maxIndex.value, startIndex.value + 1));
    hover.value = null;
  }
  function formatDateLabel(value: string | undefined) {
    if (!value) return '—';
    return value.length > 10 ? value.slice(5, 16).replace('T', ' ') : value.slice(5);
  }
  watch([() => props.dates.length, () => props.dates[0], () => props.dates.at(-1)], () => {
    const max = maxIndex.value;
    if (preset.value != null) {
      endIndex.value = max;
      startIndex.value = preset.value ? Math.max(0, max - preset.value + 1) : 0;
    } else {
      startIndex.value = Math.min(startIndex.value, Math.max(0, max - 1));
      endIndex.value = Math.max(
        startIndex.value + (max > 0 ? 1 : 0),
        Math.min(endIndex.value, max),
      );
    }
    hover.value = null;
  });
  setPreset(90);
</script>

<style scoped lang="less">
  .vibe-time-chart {
    min-width: 0;
    padding: 18px;
    border: 1px solid var(--strategy-border, #d9e3ee);
    border-radius: 12px;
    background: var(--strategy-surface, white);
  }

  .vibe-chart-head,
  .vibe-chart-subtitle,
  footer {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  h3 {
    margin: 0;
    color: var(--strategy-text-1, #10233d);
    font-size: 15px;
    font-weight: 650;
  }

  .range-buttons,
  .vibe-chart-legend {
    display: flex;
    gap: 5px;
    flex-wrap: wrap;
  }

  button {
    padding: 4px 8px;
    border: 1px solid var(--strategy-border, #d9e3ee);
    border-radius: 5px;
    background: transparent;
    color: var(--strategy-text-2, #354d68);
    font-size: 12px;
    cursor: pointer;
  }

  button.active {
    border-color: #c9dbf7;
    background: var(--strategy-accent-soft, #eaf2ff);
    color: var(--strategy-accent, #1d4ed8);
  }

  button:focus-visible,
  svg:focus-visible {
    outline: 2px solid #1d4ed8;
    outline-offset: 3px;
  }

  .vibe-chart-subtitle {
    margin: 9px 0;
    color: var(--strategy-text-3, #60758f);
    font-size: 11px;
  }

  .vibe-legend-btn.off {
    opacity: 0.45;
    text-decoration: line-through;
  }

  i {
    display: inline-block;
    width: 7px;
    height: 7px;
    margin-right: 5px;
    border-radius: 50%;
  }

  .vibe-chart-stage {
    position: relative;
    min-width: 0;
    margin-top: 12px;
  }

  .vibe-chart-range {
    display: grid;
    gap: 5px;
    margin-top: 12px;
  }

  .vibe-chart-range__labels {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    min-height: 14px;
    overflow: hidden;
    color: var(--strategy-text-4, #7b8da4);
    font-size: 10px;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }

  .vibe-chart-range__viewport {
    position: relative;
    height: 24px;
    overflow: hidden;
  }

  .vibe-chart-range__viewport svg {
    position: absolute;
    inset: 1px 0;
    width: 100%;
    height: calc(100% - 2px);
    pointer-events: none;
  }

  .vibe-chart-range__viewport polyline {
    stroke-width: 1.2;
    stroke-linecap: round;
    stroke: rgb(137 167 233 / 80%);
    fill: none;
    stroke-linejoin: round;
  }

  .vibe-chart-range__rail,
  .vibe-chart-range__selection {
    position: absolute;
    top: 50%;
    height: 12px;
    transform: translateY(-50%);
    border-radius: 999px;
  }

  .vibe-chart-range__rail {
    right: 0;
    left: 0;
    border: 1px solid rgb(192 205 227 / 92%);
    background: rgb(225 235 252 / 30%);
    box-shadow: inset 0 1px 1px rgb(255 255 255 / 72%);
  }

  .vibe-chart-range__selection {
    left: var(--range-start);
    width: max(4%, calc(var(--range-end) - var(--range-start)));
    border: 1px solid rgb(142 171 235 / 88%);
    background: rgb(202 218 251 / 45%);
    box-shadow: inset 0 0 0 1px rgb(255 255 255 / 35%);
    pointer-events: none;
  }

  .vibe-chart-range__thumb {
    position: absolute;
    z-index: 2;
    top: 0;
    left: 0;
    width: 100%;
    height: 24px;
    margin: 0;
    appearance: none;
    background: transparent;
    pointer-events: none;
  }

  .vibe-chart-range__thumb::-webkit-slider-runnable-track {
    height: 12px;
    background: transparent;
  }

  .vibe-chart-range__thumb::-moz-range-track {
    height: 12px;
    background: transparent;
  }

  .vibe-chart-range__thumb::-webkit-slider-thumb {
    width: 6px;
    height: 14px;
    margin-top: -1px;
    appearance: none;
    border: 1px solid rgb(146 171 230 / 90%);
    border-radius: 999px;
    background: #fff;
    box-shadow: 0 1px 2px rgb(124 145 186 / 20%);
    cursor: ew-resize;
    pointer-events: auto;
  }

  .vibe-chart-range__thumb::-moz-range-thumb {
    width: 6px;
    height: 14px;
    border: 1px solid rgb(146 171 230 / 90%);
    border-radius: 999px;
    background: #fff;
    box-shadow: 0 1px 2px rgb(124 145 186 / 20%);
    cursor: ew-resize;
    pointer-events: auto;
  }

  .vibe-chart-range__thumb--start {
    z-index: 3;
  }

  .vibe-chart-svg {
    display: block;
    width: 100%;
    height: auto;
    min-height: 210px;
  }

  svg text {
    fill: var(--strategy-text-3, #60758f);
    font-size: 12px;
    font-variant-numeric: tabular-nums;
  }

  .chart-grid {
    stroke-dasharray: 3 5;
    stroke: var(--strategy-border, #d9e3ee);
  }

  .vibe-chart-line {
    stroke-width: 2;
    fill: none;
  }

  .hover-line {
    stroke-dasharray: 4;
    stroke: #7b8da4;
  }

  .vibe-chart-tooltip {
    position: absolute;
    top: 6px;
    right: 8%;
    padding: 10px 13px;
    border: 1px solid #d9e3ee;
    border-radius: 8px;
    background: rgb(255 255 255 / 96%);
    box-shadow: 0 4px 16px rgb(20 40 70 / 8%);
    color: #354d68;
    font-size: 12px;
    pointer-events: none;
  }

  .chart-empty {
    display: grid;
    min-height: 140px;
    color: #60758f;
    place-content: center;
  }

  footer {
    margin-top: 4px;
    color: var(--strategy-text-3, #60758f);
    font-size: 11px;
  }

  @media (max-width: 680px) {
    .vibe-time-chart {
      padding: 12px;
    }

    .vibe-chart-svg {
      min-height: 170px;
    }

    footer span {
      display: none;
    }
  }
</style>
