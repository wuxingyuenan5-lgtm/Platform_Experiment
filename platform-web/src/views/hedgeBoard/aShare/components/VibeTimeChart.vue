<template>
  <article class="vibe-time-chart">
    <header class="vibe-chart-head"
      ><h3>{{ title }}</h3
      ><div class="range-buttons" role="group" :aria-label="`${title}历史范围`"
        ><button
          v-for="size in [60, 90, 0]"
          :key="size"
          type="button"
          :aria-pressed="range === size"
          :class="{ active: range === size }"
          @click="range = size"
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
  const range = ref(90);
  const hidden = ref(new Set<number>());
  const hover = ref<number | null>(null);
  const left = 76,
    right = 1100,
    top = 22,
    bottom = 302;
  const ticks = [0, 0.25, 0.5, 0.75, 1];
  const start = computed(() => (range.value ? Math.max(0, props.dates.length - range.value) : 0));
  const end = computed(() => Math.max(0, props.dates.length - 1));
  const shownDates = computed(() => props.dates.slice(start.value));
  const visible = computed(() =>
    props.series
      .map((item, index) => ({ item, index }))
      .filter((entry) => !hidden.value.has(entry.index)),
  );
  const numeric = (value: unknown): number | null =>
    value == null || value === '' || !Number.isFinite(Number(value)) ? null : Number(value);
  const hasValues = computed(() =>
    visible.value.some((entry) =>
      entry.item.values.slice(start.value).some((value) => numeric(value) != null),
    ),
  );
  const dateTicks = computed(() => [
    ...new Set(
      Array.from({ length: 7 }, (_, i) =>
        Math.round(start.value + ((end.value - start.value) * i) / 6),
      ),
    ),
  ]);
  const bounds = computed(() => {
    const domain = (axis: string): [number, number] => {
      const items = visible.value.filter((entry) => (entry.item.axis || 'left') === axis);
      const values = items
        .flatMap((entry) =>
          entry.item.values.slice(start.value).map((value) => {
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
    item.values.slice(start.value).forEach((raw, offset) => {
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
    return item.values.slice(start.value).flatMap((raw, offset) => {
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
  watch([range, () => props.dates.length], () => {
    hover.value = null;
  });
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
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
  }
  h3 {
    margin: 0;
    font-size: 15px;
    font-weight: 650;
    color: var(--strategy-text-1, #10233d);
  }
  .range-buttons,
  .vibe-chart-legend {
    display: flex;
    gap: 5px;
    flex-wrap: wrap;
  }
  button {
    padding: 4px 8px;
    font-size: 12px;
    border: 1px solid var(--strategy-border, #d9e3ee);
    border-radius: 5px;
    background: transparent;
    color: var(--strategy-text-2, #354d68);
    cursor: pointer;
  }
  button.active {
    background: var(--strategy-accent-soft, #eaf2ff);
    border-color: #c9dbf7;
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
    margin-top: 12px;
    min-width: 0;
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
    stroke: var(--strategy-border, #d9e3ee);
    stroke-dasharray: 3 5;
  }
  .vibe-chart-line {
    stroke-width: 2;
    fill: none;
  }
  .hover-line {
    stroke: #7b8da4;
    stroke-dasharray: 4;
  }
  .vibe-chart-tooltip {
    position: absolute;
    top: 6px;
    right: 8%;
    padding: 10px 13px;
    border: 1px solid #d9e3ee;
    border-radius: 8px;
    background: rgb(255 255 255 / 96%);
    color: #354d68;
    font-size: 12px;
    box-shadow: 0 4px 16px rgb(20 40 70 / 8%);
    pointer-events: none;
  }
  .chart-empty {
    min-height: 140px;
    display: grid;
    place-content: center;
    color: #60758f;
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
