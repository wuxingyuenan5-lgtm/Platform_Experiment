<template>
  <ChartExpand :title="title" @expanded-change="chartExpanded = $event">
    <article class="vibe-time-chart"
      ><div ref="plotMeasure" class="vibe-chart-measure"></div>
      <header class="vibe-chart-head"
        ><h3>{{ title }}</h3
        ><div class="range-buttons" role="group" :aria-label="`${title}历史范围`"
          ><button
            v-for="size in frequency === 'monthly' ? [36, 60, 0] : [60, 90, 0]"
            :key="size"
            type="button"
            :aria-pressed="preset === size"
            :class="{ active: preset === size }"
            @click="setPreset(size)"
            >{{ size ? `近${size}${frequency === 'monthly' ? '期' : '日'}` : '全部' }}</button
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
          :viewBox="`0 0 ${plotWidth} ${plotHeight}`"
          :style="{ height: `${plotHeight}px` }"
          tabindex="0"
          role="img"
          :aria-label="`${title}，${shownDates[0]}至${shownDates.at(-1)}，左右方向键查看数值`"
          @mousemove="onMove"
          @mouseleave="hover = null"
          @focus="hover = end"
          @blur="hover = null"
          @keydown.left.prevent="moveHover(-1)"
          @keydown.right.prevent="moveHover(1)"
          @wheel.prevent="onWheel"
          @pointerdown="onPointerDown"
          @pointermove="onPointerMove"
          @pointerup="onPointerUp"
          @pointercancel="onPointerUp"
          @dblclick="onDoubleClick"
        >
          <defs>
            <clipPath :id="clipId">
              <rect :x="left" :y="top" :width="right - left" :height="bottom - top" />
            </clipPath>
          </defs>
          <g v-for="tick in axisTicks('left')" :key="`left-${tick}`">
            <line
              :x1="left"
              :y1="axisY('left', tick)"
              :x2="right"
              :y2="axisY('left', tick)"
              class="chart-grid"
            />
            <text :x="left - 10" :y="axisY('left', tick) + 4" text-anchor="end">
              {{ tickLabel('left', tick) }}
            </text>
          </g>
          <g v-if="rightLabel">
            <text
              v-for="tick in axisTicks('right')"
              :key="`right-${tick}`"
              :x="right + 10"
              :y="axisY('right', tick) + 4"
            >
              {{ tickLabel('right', tick) }}
            </text>
          </g>
          <text
            v-for="index in dateTicks"
            :key="index"
            :x="x(index)"
            :y="plotHeight - 14"
            :text-anchor="index === start ? 'start' : index === end ? 'end' : 'middle'"
          >
            {{ formatDateLabel(dates[index]) }}
          </text>
          <g
            v-for="entry in geometry"
            :key="entry.item.name"
            v-memo="[entry]"
            :clip-path="`url(#${clipId})`"
          >
            <template v-if="entry.item.type === 'bar'">
              <rect
                v-for="bar in entry.bars"
                :key="bar.index"
                :x="bar.x"
                :y="bar.y"
                :width="bar.width"
                :height="bar.height"
                :fill="entry.item.color"
                opacity="0.4"
              />
            </template>
            <template v-else v-for="(segment, index) in entry.segments" :key="index">
              <path
                v-if="entry.item.type === 'area'"
                :d="segment.area"
                :fill="entry.item.color"
                opacity="0.12"
              />
              <polyline
                :points="segment.points"
                :stroke="entry.item.color"
                :stroke-width="entry.item.lineWidth || 2"
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
            <polyline v-for="(segment, index) in overviewPoints" :key="index" :points="segment" />
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
            @wheel.prevent="onRangeWheel"
          />
          <input
            v-model.number="endIndex"
            class="vibe-chart-range__thumb vibe-chart-range__thumb--end"
            type="range"
            min="0"
            :max="maxIndex"
            :aria-label="`${title}结束日期`"
            @input="onEndInput"
            @wheel.prevent="onRangeWheel"
          />
        </div>
      </div>
      <footer
        >{{ shownDates[0] || '—' }} — {{ shownDates.at(-1) || '—'
        }}<span
          >{{ shownDates.length }}{{ frequency === 'monthly' ? '期（月度）' : '个交易日' }} ·
          空缺数据不连线</span
        ></footer
      >
    </article>
  </ChartExpand>
</template>

<script setup lang="ts">
  import { useResearchViewState } from '../../composables/researchWorkspace';
  import ChartExpand from '../../components/ChartExpand.vue';
  import { computed, getCurrentInstance, onBeforeUnmount, ref, watch } from 'vue';
  import { useElementSize, useWindowSize } from '@vueuse/core';
  import { overviewSegments } from './overviewSegments';

  const clipId = `vibe-chart-plot-clip-${getCurrentInstance()!.uid}`;

  export interface Series {
    name: string;
    values: Array<number | null | undefined>;
    type: 'bar' | 'line' | 'area';
    axis?: 'left' | 'right' | 'hidden-price';
    color: string;
    sign?: 1 | -1;
    unit?: string;
    percent?: boolean;
    domain?: [number, number];
    ticks?: number[];
    lineWidth?: number;
  }
  const props = defineProps<{
    title: string;
    yLabel: string;
    rightLabel?: string;
    frequency?: 'monthly';
    precision?: number;
    initialWindow?: number;
    dates: string[];
    series: Series[];
  }>();
  const remembered = useResearchViewState<{
    preset: number | null;
    start: string;
    end: string;
    hidden: number[];
  } | null>(`chart:${props.title}`, null);
  let restored = false;
  onBeforeUnmount(() => {
    if (props.dates.length)
      remembered.value = {
        preset: preset.value,
        start: props.dates[startIndex.value],
        end: props.dates[endIndex.value],
        hidden: [...hidden.value],
      };
  });
  const chartExpanded = ref(false);
  const { height: viewportHeight } = useWindowSize();
  const defaultWindow = props.initialWindow ?? (props.frequency === 'monthly' ? 60 : 90);
  const preset = ref<number | null>(defaultWindow);
  const startIndex = ref(0);
  const endIndex = ref(0);
  const hidden = ref(new Set<number>());
  const hover = ref<number | null>(null);
  const plotMeasure = ref<HTMLElement>();
  const { width: measuredWidth } = useElementSize(plotMeasure);
  const plotWidth = computed(() => Math.max(280, measuredWidth.value || 600));
  const plotHeight = computed(() =>
    Math.round(
      chartExpanded.value
        ? Math.max(320, viewportHeight.value - 360)
        : Math.max(280, Math.min(420, plotWidth.value / 1.8)),
    ),
  );
  const left = 62,
    top = 22;
  const bottom = computed(() => plotHeight.value - 48);
  const right = computed(() => plotWidth.value - (props.rightLabel ? 66 : 24));
  const defaultTicks = [0, 0.25, 0.5, 0.75, 1];
  const axisState = ref<Record<'left' | 'right', { domain: [number, number]; manual: boolean }>>({
    left: { domain: [0, 1], manual: false },
    right: { domain: [0, 1], manual: false },
  });
  const priceBounds = ref<[number, number]>([0, 1]);
  const drag = ref<{ region: 'left' | 'right' | 'plot'; x: number; y: number } | null>(null);
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
  const dateTicks = computed(() => {
    const count = Math.max(2, Math.min(7, Math.floor((right.value - left) / 85) + 1));
    return [
      ...new Set(
        Array.from({ length: count }, (_, i) =>
          Math.round(start.value + ((end.value - start.value) * i) / (count - 1)),
        ),
      ),
    ];
  });
  const rangeStartPercent = computed(() =>
    maxIndex.value ? (start.value / maxIndex.value) * 100 : 0,
  );
  const rangeEndPercent = computed(() =>
    maxIndex.value ? (end.value / maxIndex.value) * 100 : 100,
  );
  const overviewPoints = computed(() => {
    const item = visible.value[0]?.item;
    return item ? overviewSegments(item.values) : [];
  });
  function dataDomain(axis: 'left' | 'right'): [number, number] {
    const items = visible.value.filter((entry) => (entry.item.axis || 'left') === axis);
    const values = items
      .flatMap((entry) =>
        entry.item.values.map((value) => {
          const n = numeric(value);
          return n == null ? null : n * (entry.item.sign || 1);
        }),
      )
      .filter((value): value is number => value != null);
    const fixed = items.find((entry) => entry.item.domain)?.item.domain;
    if (fixed) return fixed;
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
  }
  const bounds = computed(() => ({
    left: axisState.value.left.domain,
    right: axisState.value.right.domain,
  }));
  const autoDomains = computed(() => ({
    left: dataDomain('left'),
    right: dataDomain('right'),
  }));
  const x = (index: number) =>
    left + ((right.value - left) * (index - start.value)) / Math.max(1, end.value - start.value);
  const y = (value: number, item: Series) => {
    const axis = item.axis === 'hidden-price' ? 'left' : item.axis || 'left';
    let plotted = value;
    if (item.axis === 'hidden-price') {
      const [pMin, pMax] = priceBounds.value;
      plotted = pMin === pMax ? 0.5 : (value - pMin) / (pMax - pMin);
      const [lMin, lMax] = autoDomains.value.left;
      plotted = lMin + plotted * (lMax - lMin);
    }
    const [min, max] = bounds.value[axis];
    return bottom.value - ((plotted - min) / (max - min)) * (bottom.value - top);
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
    const baseline = Math.min(bottom.value, Math.max(top, y(0, item)));
    return `M${points[0].x},${baseline} L${points
      .map((point) => `${point.x},${point.y}`)
      .join(' L')} L${points.at(-1)?.x},${baseline} Z`;
  }
  function bars(item: Series) {
    const width = Math.max(
      0.5,
      Math.min(10, ((right.value - left) / shownDates.value.length) * 0.65),
    );
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
  const geometry = computed(() =>
    visible.value.map(({ item }) => ({
      item,
      bars: item.type === 'bar' ? bars(item) : [],
      segments:
        item.type === 'bar'
          ? []
          : segments(item).map((points) => ({
              points: points.map((point) => `${point.x},${point.y}`).join(' '),
              area: item.type === 'area' ? areaPath(points, item) : '',
            })),
    })),
  );
  function axisTicks(axis: 'left' | 'right') {
    const [min, max] = bounds.value[axis];
    const item = visible.value.find((entry) => (entry.item.axis || 'left') === axis)?.item;
    if (!axisState.value[axis].manual && item?.ticks) return item.ticks;
    return defaultTicks.map((position) => max - position * (max - min));
  }
  function axisY(axis: 'left' | 'right', value: number) {
    const [min, max] = bounds.value[axis];
    return bottom.value - ((value - min) / (max - min)) * (bottom.value - top);
  }
  function tickLabel(axis: 'left' | 'right', tick: number) {
    const percent = visible.value.find((entry) => (entry.item.axis || 'left') === axis)?.item
      .percent;
    return percent
      ? `${(tick * 100).toFixed(1)}%`
      : tick.toLocaleString('zh-CN', { maximumFractionDigits: props.precision ?? 1 });
  }
  function valueLabel(raw: unknown, item: Series) {
    const value = numeric(raw);
    if (value == null) return '—';
    return item.percent
      ? `${(value * 100).toFixed(2)}%`
      : `${value.toLocaleString('zh-CN', { maximumFractionDigits: props.precision ?? 2 })}${
          item.unit || ''
        }`;
  }
  function toggle(index: number) {
    const next = new Set(hidden.value);
    next.has(index) ? next.delete(index) : next.add(index);
    hidden.value = next;
    syncAutoAxisDomains();
  }
  function syncAutoAxisDomains() {
    for (const axis of ['left', 'right'] as const) {
      if (!axisState.value[axis].manual)
        axisState.value[axis] = { domain: dataDomain(axis), manual: false };
    }
  }
  function onMove(event: MouseEvent) {
    const rect = (event.currentTarget as SVGSVGElement).getBoundingClientRect();
    const position = ((event.clientX - rect.left) / rect.width) * plotWidth.value;
    hover.value = Math.max(
      start.value,
      Math.min(
        end.value,
        Math.round(
          start.value + ((position - left) / (right.value - left)) * (end.value - start.value),
        ),
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
  function resetAxis(axis: 'left' | 'right') {
    axisState.value[axis] = { domain: dataDomain(axis), manual: false };
  }
  function resetTime() {
    setPreset(preset.value ?? defaultWindow);
  }
  function axisAt(event: MouseEvent | WheelEvent): 'left' | 'right' | 'plot' {
    const rect = (event.currentTarget as SVGSVGElement).getBoundingClientRect();
    const px = ((event.clientX - rect.left) / rect.width) * plotWidth.value;
    return px < left ? 'left' : px > right.value ? 'right' : 'plot';
  }
  function onWheel(event: WheelEvent) {
    const region = axisAt(event);
    if (region === 'plot') {
      const span = Math.max(2, end.value - start.value + 1);
      const next = Math.max(
        2,
        Math.min(props.dates.length, span * (event.deltaY > 0 ? 1.12 : 0.88)),
      );
      const rect = (event.currentTarget as SVGSVGElement).getBoundingClientRect();
      const position = ((event.clientX - rect.left) / rect.width) * plotWidth.value;
      const ratio = Math.max(0, Math.min(1, (position - left) / (right.value - left)));
      const center = start.value + ratio * (end.value - start.value);
      startIndex.value = Math.max(0, Math.round(center - ratio * (next - 1)));
      endIndex.value = Math.min(maxIndex.value, startIndex.value + Math.round(next) - 1);
      preset.value = null;
    } else updateAxis(region, event.deltaY, event.clientY, event.currentTarget as SVGSVGElement);
  }
  function updateAxis(
    axis: 'left' | 'right',
    delta: number,
    pointerY: number,
    element: SVGSVGElement,
  ) {
    const current = axisState.value[axis].domain;
    const rect = element.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (pointerY - rect.top) / rect.height));
    const factor = delta > 0 ? 1.12 : 0.88;
    const range = current[1] - current[0];
    const anchor = current[1] - ratio * range;
    const nextRange = range * factor;
    axisState.value[axis] = {
      domain: [anchor - (1 - ratio) * nextRange, anchor + ratio * nextRange],
      manual: true,
    };
  }
  function onPointerDown(event: PointerEvent) {
    const region = axisAt(event);
    drag.value = { region, x: event.clientX, y: event.clientY };
    (event.currentTarget as SVGSVGElement).setPointerCapture(event.pointerId);
  }
  function onPointerMove(event: PointerEvent) {
    if (!drag.value) return;
    const dx = event.clientX - drag.value.x;
    const dy = event.clientY - drag.value.y;
    if (drag.value.region === 'plot') {
      const span = end.value - start.value;
      const shift = Math.round((-dx / 1024) * span);
      startIndex.value = Math.max(0, Math.min(maxIndex.value - span, start.value + shift));
      endIndex.value = Math.min(maxIndex.value, startIndex.value + span);
      for (const axis of ['left', 'right'] as const) {
        const [min, max] = axisState.value[axis].domain;
        const shift = ((max - min) * dy) / (bottom.value - top);
        axisState.value[axis] = { domain: [min + shift, max + shift], manual: true };
      }
    } else updateAxis(drag.value.region, dy, event.clientY, event.currentTarget as SVGSVGElement);
    drag.value = { ...drag.value, x: event.clientX, y: event.clientY };
  }
  function onPointerUp() {
    drag.value = null;
  }
  function onDoubleClick(event: MouseEvent) {
    const region = axisAt(event);
    if (region === 'left' || region === 'right') resetAxis(region);
    else resetTime();
  }
  function onRangeWheel(event: WheelEvent) {
    const span = Math.max(2, end.value - start.value + 1);
    const next = Math.max(
      2,
      Math.min(props.dates.length, Math.round(span * (event.deltaY > 0 ? 1.15 : 0.85))),
    );
    endIndex.value = Math.min(maxIndex.value, start.value + next - 1);
    startIndex.value = Math.max(0, endIndex.value - next + 1);
    preset.value = null;
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
    if (props.frequency === 'monthly') return value.slice(0, 7);
    return value.length > 10 ? value.slice(5, 16).replace('T', ' ') : value.slice(5);
  }
  watch(
    [() => props.dates.length, () => props.dates[0], () => props.dates.at(-1), () => props.series],
    () => {
      const max = maxIndex.value;
      if (!restored && props.dates.length && remembered.value) {
        const saved = remembered.value;
        preset.value = saved.preset;
        const a = props.dates.findIndex((d) => d >= saved.start);
        const z = props.dates.findIndex((d) => d >= saved.end);
        startIndex.value = Math.max(0, a);
        endIndex.value = z < 0 ? max : z;
        hidden.value = new Set(saved.hidden);
        restored = true;
      }
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
      syncAutoAxisDomains();
      const prices = props.series
        .filter((item) => item.axis === 'hidden-price')
        .flatMap((item) => item.values.map(numeric))
        .filter((value): value is number => value != null);
      if (prices.length) priceBounds.value = [Math.min(...prices), Math.max(...prices)];
    },
    { immediate: true, deep: true },
  );
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

  .vibe-chart-measure {
    width: 100%;
    height: 0;
  }

  .vibe-chart-svg {
    display: block;
    width: 100%;
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

    footer span {
      display: none;
    }
  }
</style>
