<template>
  <div class="cumulative-volatility macro-series-chart">
    <div class="cumulative-volatility__toolbar">
      <div class="cumulative-volatility__controls">
        <div
          class="cumulative-volatility__control-group source-chart-controls"
          role="group"
          aria-label="历史范围"
        >
          <button
            v-for="item in rangeOptions"
            :key="item.value"
            type="button"
            :class="{ active: days === item.value && !customRangeApplied }"
            :aria-pressed="days === item.value && !customRangeApplied"
            @click="selectPresetRange(item.value)"
          >
            {{ item.label }}
          </button>
        </div>
        <div
          class="cumulative-volatility__control-group source-chart-controls"
          role="group"
          aria-label="采样精度"
        >
          <button
            v-for="item in precisionOptions"
            :key="item.value"
            type="button"
            :class="{ active: precision === item.value }"
            :aria-pressed="precision === item.value"
            @click="precision = item.value"
          >
            {{ item.label }}
          </button>
        </div>
      </div>
    </div>

    <p v-if="response?.message" class="cumulative-volatility__message">{{ response.message }}</p>

    <p v-if="missingDayCount" class="cumulative-volatility__message"
      >所选区间有 {{ missingDayCount }} 天无观测，按实际日期显示，缺口处不连线。</p
    >
    <div
      v-if="status === 'loading' && !response?.points.length"
      class="cumulative-volatility__empty"
      >正在读取已落库的累计波动数据…</div
    >
    <div v-else-if="status === 'error' || !dates.length" class="cumulative-volatility__empty">
      {{ status === 'error' ? '当前累计波动数据暂不可用。' : '当前范围暂无有效观测。' }}
    </div>
    <div v-else class="cumulative-volatility__stage">
      <div class="cumulative-volatility__legend" aria-label="盘口颜色与时间说明">
        <button
          v-for="series in sessionSeries"
          :key="series.key"
          type="button"
          class="cumulative-volatility__legend-toggle"
          :class="{ 'is-muted': hiddenSessions.has(series.key) }"
          :aria-pressed="!hiddenSessions.has(series.key)"
          @click="toggleSession(series.key)"
        >
          <i :style="{ background: series.color }"></i>{{ series.label }}
        </button>
        <button
          type="button"
          class="cumulative-volatility__legend-toggle cumulative-volatility__legend-price"
          :class="{ 'is-muted': !priceVisible }"
          :aria-pressed="priceVisible"
          @click="togglePrice"
        >
          <i></i>价格
        </button>
        <span class="cumulative-volatility__legend-note">UTC</span>
      </div>
      <div class="cumulative-volatility__plot">
        <svg
          ref="motionPlot"
          class="cumulative-volatility__svg"
          :viewBox="`0 0 ${plotWidth} ${plotHeight}`"
          :style="{ height: plotHeight + 'px' }"
          role="img"
          :aria-label="`${title}，${formatDate(dates[0])}至${formatDate(dates.at(-1) ?? dates[0])}`"
          @pointermove="onMove"
          @pointerleave="hoverIndex = null"
        >
          <text :x="plot.left" :y="plot.top - 14">累计波动（%）</text>
          <g v-for="tick in ticks" :key="tick">
            <line
              :x1="plot.left"
              :x2="plot.right"
              :y1="yForTick(tick)"
              :y2="yForTick(tick)"
              class="cumulative-volatility__grid"
            />
            <text :x="plot.left - 12" :y="yForTick(tick) + 4" text-anchor="end">
              {{ tick.toFixed(1) }}%
            </text>
          </g>
          <template v-if="priceVisible">
            <text
              v-for="tick in priceTicks"
              :key="`price-${tick}`"
              :x="plot.right + 12"
              :y="yForPrice(tick) + 4"
              text-anchor="start"
              class="cumulative-volatility__price-tick"
            >
              {{ formatPrice(tick) }}
            </text>
          </template>
          <text
            v-if="priceVisible"
            :x="plot.right"
            :y="plot.top - 14"
            text-anchor="end"
            class="cumulative-volatility__price-tick cumulative-volatility__price-axis-title"
          >
            价格
          </text>
          <text
            v-for="tick in dateTicks"
            :key="`date-${tick.date}`"
            :x="xForDate(tick.date)"
            :y="plot.bottom + 24"
            :text-anchor="
              tick.position === 0
                ? 'start'
                : tick.position === dateTicks.length - 1
                ? 'end'
                : 'middle'
            "
          >
            {{ formatDate(tick.date) }}
          </text>
          <line
            :x1="plot.left"
            :x2="plot.right"
            :y1="plot.bottom"
            :y2="plot.bottom"
            class="cumulative-volatility__axis"
          />
          <line
            :x1="plot.left"
            :x2="plot.right"
            :y1="yForValue(0)"
            :y2="yForValue(0)"
            class="cumulative-volatility__zero"
          />
          <g data-chart-kind="line">
            <path
              v-for="series in plottedSeries"
              :key="series.key"
              :d="series.path"
              fill="none"
              :stroke="series.color"
              stroke-width="1.2"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
            <path
              v-if="priceVisible && pricePath"
              :d="pricePath"
              fill="none"
              stroke="#111111"
              stroke-width="2.3"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </g>
          <line
            v-if="hoverIndex !== null"
            :x1="xForSlot(hoverIndex)"
            :x2="xForSlot(hoverIndex)"
            :y1="plot.top"
            :y2="plot.bottom"
            class="cumulative-volatility__hover-line"
          />
        </svg>
        <div
          v-if="hoverIndex !== null"
          class="cumulative-volatility__tooltip"
          :style="tooltipPosition"
        >
          <strong>{{ hoverSessionDate }} · 各盘第 {{ hoverSampleIndex + 1 }} 个采样点</strong>
          <span v-for="series in plottedSeries" :key="series.key">
            <i :style="{ background: series.color }"></i>{{ series.label.slice(0, 3) }}
            <b>{{ valueAt(series, hoverIndex) }}</b>
          </span>
          <span v-if="priceVisible && hoverPrice !== null">
            <i class="cumulative-volatility__tooltip-price-dot"></i>价格
            <b>{{ formatPrice(hoverPrice, true) }}</b>
          </span>
        </div>
      </div>
    </div>

    <div
      class="cumulative-volatility__navigator"
      :style="{
        marginInlineStart: plot.left + 'px',
        marginInlineEnd: plotWidth - plot.right + 'px',
      }"
    >
      <ChartRangeSelector
        v-if="allDates.length > 1"
        :labels="rangeLabels"
        :values="rangeValues"
        :timeline="timeline"
        :start-index="startIndex"
        :end-index="endIndex"
        :min-window-size="minWindowSize"
        :on-start-change="onRangeStartChange"
        :on-end-change="onRangeEndChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useChartReveal } from '@/hooks/web/chartMotion';

  import {
    computed,
    defineComponent,
    onMounted,
    nextTick,
    onBeforeUnmount,
    PropType,
    ref,
    shallowRef,
    watch,
  } from 'vue';

  import {
    getCumulativeVolatility,
    type CumulativeVolatilityData,
    type CumulativeVolatilityInterval,
  } from '@/api/hedgeResearch';
  import { renderChartRangeSelector } from '../charts/chartRange';

  const ChartRangeSelector = defineComponent({
    name: 'CumulativeVolatilityRangeSelector',
    props: {
      labels: { type: Array as PropType<string[]>, required: true },
      values: { type: Array as PropType<number[]>, required: true },
      startIndex: { type: Number, required: true },
      endIndex: { type: Number, required: true },
      minWindowSize: { type: Number, required: true },
      timeline: {
        type: Object as PropType<{ positions: number[]; previewPath: string }>,
        required: true,
      },
      onStartChange: {
        type: Function as PropType<(value: number) => void>,
        required: true,
      },
      onEndChange: {
        type: Function as PropType<(value: number) => void>,
        required: true,
      },
    },
    setup(props) {
      return () =>
        renderChartRangeSelector({
          labels: props.labels,
          values: props.values,
          startIndex: props.startIndex,
          endIndex: props.endIndex,
          minWindowSize: props.minWindowSize,
          timeline: props.timeline,
          onStartChange: props.onStartChange,
          onEndChange: props.onEndChange,
        });
    },
  });

  const props = defineProps<{ asset: 'btc' | 'gold'; title: string }>();

  const rangeOptions = [
    { value: 7, label: '近7日' },
    { value: 30, label: '近30日' },
    { value: 90, label: '近90日' },
    { value: 365, label: '近1年' },
    { value: 0, label: '全部' },
  ] as const;
  const precisionOptions: Array<{ value: CumulativeVolatilityInterval; label: string }> = [
    { value: '15m', label: '15分钟' },
    { value: '1h', label: '1小时' },
    { value: '4h', label: '4小时' },
  ];
  const days = ref<number>(365);
  const precision = ref<CumulativeVolatilityInterval>('15m');
  const response = shallowRef<CumulativeVolatilityData | null>(null);
  const fullResponse = shallowRef<CumulativeVolatilityData | null>(null);
  const status = ref<'loading' | 'ready' | 'error'>('loading');
  const hoverIndex = ref<number | null>(null);
  const hiddenSessions = ref<Set<string>>(new Set());
  const priceVisible = ref(true);
  const customRangeApplied = ref(false);
  let loadSerial = 0;
  let windowSerial = 0;
  const loadingFull = ref(false);
  let rangeTimer: ReturnType<typeof setTimeout> | undefined;

  const plotWidth = ref(1200);
  const plotHeight = computed(() => Math.max(300, Math.min(420, plotWidth.value * 0.36)));
  const plot = computed(() => ({
    left: plotWidth.value < 480 ? 47 : 60,
    right: plotWidth.value - (priceVisible.value ? 70 : 18),
    top: 36,
    bottom: plotHeight.value - 40,
  }));
  const sessionSeries = [
    { key: 'asia', label: '亚洲盘 23:00–07:00', color: '#f0c015' },
    { key: 'europe', label: '欧洲盘 07:00–15:00', color: '#2ca02c' },
    { key: 'americas', label: '美洲盘 15:00–23:00', color: '#213ed1' },
  ] as const;

  const points = computed(() => response.value?.points ?? []);
  const allDates = computed(() =>
    [...new Set((fullResponse.value?.points ?? []).map((point) => point.timestamp))].sort(),
  );
  const startIndex = ref(0);
  const endIndex = ref(0);
  const minWindowSize = computed(() => Math.min(4, allDates.value.length));
  const dates = computed(() => allDates.value.slice(startIndex.value, endIndex.value + 1));
  const valueMap = computed(() => {
    const maps = new Map<string, Map<string, number>>();
    sessionSeries.forEach((series) => maps.set(series.key, new Map()));
    (fullResponse.value?.points ?? []).forEach((point) => {
      const value = Number(point.value);
      if (!Number.isFinite(value) || !maps.has(point.session)) return;
      maps.get(point.session)!.set(point.timestamp, value);
    });
    return maps;
  });
  const rangeValues = computed(() =>
    allDates.value.map((date) => {
      const values = sessionSeries
        .map((series) => valueMap.value.get(series.key)?.get(date))
        .filter((value): value is number => value != null && Number.isFinite(value));
      return values.length ? Math.max(...values.map((value) => Math.abs(value))) : 0;
    }),
  );
  const rangeLabels = computed(() =>
    allDates.value.map((date) => date.slice(0, 16).replace('T', ' ')),
  );
  const timeline = computed(() => {
    const times = allDates.value.map((date) => Date.parse(date));
    const start = times[0] ?? 0;
    const duration = (times.at(-1) ?? start) - start || 1;
    const positions = times.map((time) => (time - start) / duration);
    const buckets = Array<number | null>(361).fill(null);
    positions.forEach((position, index) => {
      const bin = Math.round(position * 360);
      buckets[bin] = Math.max(buckets[bin] ?? 0, rangeValues.value[index]);
    });
    const maximum = Math.max(1e-6, ...buckets.map((value) => value ?? 0));
    const previewPath = buckets
      .map((value, index) => {
        if (value === null) return '';
        const y = (21 - (value / maximum) * 18).toFixed(1);
        return buckets[index - 1] != null ? `L${index},${y}` : `M${index},${y}h0.5`;
      })
      .join('');
    return { positions, previewPath };
  });
  const bounds = computed(() => {
    if (!allValues.value.length) return { min: -1, max: 1 };
    const min = allValues.value.reduce((limit, value) => Math.min(limit, value), 0);
    const max = allValues.value.reduce((limit, value) => Math.max(limit, value), 0);
    const padding = Math.max((max - min) * 0.1, 0.5);
    return { min: min - padding, max: max + padding };
  });
  const ticks = computed(() => {
    const { min, max } = bounds.value;
    return Array.from({ length: 5 }, (_, index) => max - ((max - min) * index) / 4);
  });
  const visibleSessionDates = computed(() => {
    const selected = new Set(dates.value);
    const datesBySession = sessionSeries.map(
      (series) =>
        new Set(
          points.value
            .filter(
              (point) =>
                point.session === series.key && selected.has(point.timestamp) && point.sessionDate,
            )
            .map((point) => point.sessionDate as string),
        ),
    );
    const observed = [
      ...new Set(datesBySession.flatMap((sessionDates) => [...sessionDates])),
    ].sort();
    if (!observed.length) return [];
    const start = Date.parse(observed[0]);
    const end = Date.parse(observed.at(-1)!);
    return Array.from({ length: Math.round((end - start) / 86_400_000) + 1 }, (_, i) =>
      new Date(start + i * 86_400_000).toISOString().slice(0, 10),
    );
  });
  const missingDayCount = computed(() => {
    const selected = new Set(dates.value);
    const observed = new Set(
      points.value.filter((p) => selected.has(p.timestamp)).map((p) => p.sessionDate),
    );
    return visibleSessionDates.value.filter((day) => !observed.has(day)).length;
  });
  const pointsBySession = computed(() => {
    const selected = new Set(dates.value);
    const result = new Map<string, Map<string, Array<(typeof points.value)[number]>>>();
    sessionSeries.forEach((series) => result.set(series.key, new Map()));
    points.value.forEach((point) => {
      if (!selected.has(point.timestamp) || !point.sessionDate || !result.has(point.session))
        return;
      const byDate = result.get(point.session)!;
      const group = byDate.get(point.sessionDate) ?? [];
      group.push(point);
      byDate.set(point.sessionDate, group);
    });
    result.forEach((byDate) =>
      byDate.forEach((group) => group.sort((a, b) => a.timestamp.localeCompare(b.timestamp))),
    );
    return result;
  });
  // The API already performs the requested-window/session rebase. Keep this
  // map as a presentation lookup only: the browser must not recalculate
  // cumulative values or normalize them a second time.
  const visibleValueMap = computed(() => {
    const maps = new Map<string, Map<string, number>>();
    sessionSeries.forEach((series) => maps.set(series.key, new Map()));
    pointsBySession.value.forEach((byDate, session) => {
      const map = maps.get(session);
      if (!map) return;
      byDate.forEach((group) => {
        group.forEach((point) => {
          const value = Number(point.value);
          if (Number.isFinite(value)) map.set(point.timestamp, value);
        });
      });
    });
    return maps;
  });
  const visibleSessionSeries = computed(() =>
    sessionSeries.filter((series) => !hiddenSessions.value.has(series.key)),
  );
  const allValues = computed(() =>
    visibleSessionSeries.value
      .map((series) => visibleValueMap.value.get(series.key))
      .flatMap((map) => [...(map?.values() ?? [])])
      .filter(Number.isFinite),
  );
  const renderedPrecision = computed(() => response.value?.interval ?? precision.value);
  const samplesPerSessionDay = computed(
    () => 480 / { '15m': 15, '1h': 60, '4h': 240 }[renderedPrecision.value],
  );
  function sampleSlot(point: (typeof points.value)[number]) {
    const startHour = point.session === 'asia' ? -1 : point.session === 'europe' ? 7 : 15;
    const start = Date.parse(point.sessionDate!) + startHour * 3_600_000;
    const minutes = { '15m': 15, '1h': 60, '4h': 240 }[renderedPrecision.value];
    return Math.floor((Date.parse(point.timestamp) - start) / (minutes * 60_000));
  }
  const plotSlotCount = computed(() =>
    Math.max(1, visibleSessionDates.value.length * samplesPerSessionDay.value - 1),
  );
  const dateTicks = computed(() => {
    const datesForTicks = visibleSessionDates.value;
    const count = Math.max(
      3,
      Math.min(7, Math.floor((plot.value.right - plot.value.left) / 85) + 1),
    );
    if (datesForTicks.length <= count)
      return datesForTicks.map((date, index) => ({ date, index, position: index }));
    return Array.from({ length: count }, (_, index) => {
      const dateIndex = Math.round((index * (datesForTicks.length - 1)) / (count - 1));
      return { date: datesForTicks[dateIndex], index: dateIndex, position: index };
    });
  });
  const plottedSeries = computed(() =>
    visibleSessionSeries.value.map((series) => {
      const byDate = pointsBySession.value.get(series.key) ?? new Map();
      let path = '';
      let previousSlot: number | null = null;
      visibleSessionDates.value.forEach((sessionDate, dayIndex) => {
        const group = byDate.get(sessionDate) ?? [];
        group.forEach((point) => {
          const value = visibleValueMap.value.get(series.key)?.get(point.timestamp) ?? NaN;
          if (!Number.isFinite(value)) return;
          const slot = dayIndex * samplesPerSessionDay.value + sampleSlot(point);
          path += `${previousSlot !== null && slot === previousSlot + 1 ? 'L' : 'M'}${xForSlot(
            slot,
          ).toFixed(2)},${yForValue(value).toFixed(2)} `;
          previousSlot = slot;
        });
      });
      return { ...series, path: path.trim() };
    }),
  );
  const priceByDate = computed(() => {
    const selected = new Set(dates.value);
    const result = new Map<string, number>();
    points.value
      .filter(
        (point) =>
          point.session === 'americas' &&
          selected.has(point.timestamp) &&
          Boolean(point.sessionDate) &&
          point.price != null,
      )
      .sort((a, b) => a.timestamp.localeCompare(b.timestamp))
      .forEach((point) => {
        const value = Number(point.price);
        if (Number.isFinite(value) && !result.has(point.sessionDate)) {
          result.set(point.sessionDate, value);
        }
      });
    return result;
  });
  const pricePoints = computed(() =>
    [...priceByDate.value.entries()]
      .filter(([sessionDate]) => visibleSessionDates.value.includes(sessionDate))
      .map(([sessionDate, value]) => ({ sessionDate, value }))
      .sort((a, b) => a.sessionDate.localeCompare(b.sessionDate)),
  );
  const priceBounds = computed(() => {
    const values = pricePoints.value.map((point) => point.value).filter(Number.isFinite);
    if (!values.length) return { min: 0, max: 1 };
    const min = Math.min(...values);
    const max = Math.max(...values);
    const padding = Math.max((max - min) * 0.08, Math.abs(max) * 0.01, 0.01);
    return { min: min - padding, max: max + padding };
  });
  const priceTicks = computed(() => {
    const { min, max } = priceBounds.value;
    return Array.from({ length: 5 }, (_, index) => max - ((max - min) * index) / 4);
  });
  const pricePath = computed(() => {
    let path = '';
    let previousDate: string | undefined;
    pricePoints.value.forEach((point) => {
      const x = xForDate(point.sessionDate);
      const continuous =
        previousDate && Date.parse(point.sessionDate) - Date.parse(previousDate) === 86_400_000;
      path += `${continuous ? 'L' : 'M'}${x.toFixed(2)},${yForPrice(point.value).toFixed(2)} `;
      previousDate = point.sessionDate;
    });
    return path.trim();
  });
  const hoverSessionDate = computed(() =>
    hoverIndex.value == null
      ? undefined
      : visibleSessionDates.value[Math.floor(hoverIndex.value / samplesPerSessionDay.value)],
  );
  const hoverSampleIndex = computed(() => (hoverIndex.value ?? 0) % samplesPerSessionDay.value);
  const hoverPrice = computed(() => {
    const sessionDate = hoverSessionDate.value;
    if (!sessionDate) return null;
    return priceByDate.value.get(sessionDate) ?? null;
  });

  function xForSlot(slot: number) {
    const { left, right } = plot.value;
    return left + ((right - left) * slot) / plotSlotCount.value;
  }

  function xForDate(sessionDate: string) {
    return xForSlot(
      Math.max(0, visibleSessionDates.value.indexOf(sessionDate)) * samplesPerSessionDay.value,
    );
  }

  function yForValue(value: number) {
    const { min, max } = bounds.value;
    const { bottom, top } = plot.value;
    return bottom - ((value - min) / Math.max(max - min, 0.01)) * (bottom - top);
  }

  function yForTick(value: number) {
    return yForValue(value);
  }

  function yForPrice(value: number) {
    const { min, max } = priceBounds.value;
    const { bottom, top } = plot.value;
    return bottom - ((value - min) / Math.max(max - min, 0.01)) * (bottom - top);
  }

  function toggleSession(key: string) {
    const next = new Set(hiddenSessions.value);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    hiddenSessions.value = next;
  }

  function togglePrice() {
    priceVisible.value = !priceVisible.value;
  }

  function formatDate(value: string | undefined) {
    if (!value) return '—';
    return (
      visibleSessionDates.value.length > 180 ? value.slice(0, 16) : value.slice(5, 16)
    ).replace('T', ' ');
  }

  function valueAt(series: { key: string }, index: number) {
    const sessionDate = visibleSessionDates.value[Math.floor(index / samplesPerSessionDay.value)];
    const point = pointsBySession.value
      .get(series.key)
      ?.get(sessionDate)
      ?.find((p) => sampleSlot(p) === index % samplesPerSessionDay.value);
    const value = point ? Number(point.value) : null;
    return value == null ? '—' : `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  }

  function formatPrice(value: number, detail = false) {
    if (!Number.isFinite(value)) return '—';
    return value >= 1000 && !detail
      ? value.toLocaleString('zh-CN', { maximumFractionDigits: 0 })
      : value.toLocaleString('zh-CN', { maximumFractionDigits: 2 });
  }

  function onMove(event: MouseEvent) {
    if (!dates.value.length) return;
    const rect = (event.currentTarget as SVGSVGElement).getBoundingClientRect();
    if (!rect.width) return;
    const x = ((event.clientX - rect.left) / rect.width) * plotWidth.value;
    const { left, right } = plot.value;
    const ratio = Math.max(0, Math.min(1, (x - left) / (right - left)));
    hoverIndex.value = Math.round(ratio * plotSlotCount.value);
  }

  const tooltipPosition = computed(() => {
    const x = xForSlot(hoverIndex.value ?? 0);
    const width = Math.min(226, plotWidth.value - 16);
    const left = x > plotWidth.value / 2 ? x - width - 12 : x + 12;
    return {
      width: `${width}px`,
      left: `${Math.max(8, Math.min(plotWidth.value - width - 8, left))}px`,
    };
  });

  function onRangeStartChange(value: number) {
    reveal.cancel();
    startIndex.value = value;
    customRangeApplied.value = true;
  }

  function onRangeEndChange(value: number) {
    reveal.cancel();
    endIndex.value = value;
    customRangeApplied.value = true;
  }

  function selectPresetRange(value: number) {
    customRangeApplied.value = false;
    days.value = value;
    if (!allDates.value.length && !loadingFull.value) {
      void load();
      return;
    }
    applyPresetIndices();
  }

  let fullController: AbortController | undefined;
  let windowController: AbortController | undefined;
  async function load() {
    fullController?.abort();
    windowController?.abort();
    fullController = new AbortController();
    clearTimeout(rangeTimer);
    const serial = ++loadSerial;
    ++windowSerial;
    loadingFull.value = true;
    status.value = 'loading';
    hoverIndex.value = null;
    try {
      const result = await getCumulativeVolatility(
        props.asset,
        0,
        precision.value,
        undefined,
        fullController.signal,
      );
      if (serial !== loadSerial) return;
      const previousWindow = customRangeApplied.value
        ? {
            start: allDates.value[startIndex.value],
            end: allDates.value[endIndex.value],
          }
        : null;
      response.value = result.data;
      fullResponse.value = result.data;
      if (previousWindow?.start && previousWindow.end) {
        startIndex.value = Math.max(
          0,
          allDates.value.findIndex((t) => t >= previousWindow.start),
        );
        endIndex.value = Math.max(
          startIndex.value,
          allDates.value.reduce((last, t, i) => (t <= previousWindow.end ? i : last), -1),
        );
      } else {
        applyPresetIndices();
        customRangeApplied.value = false;
      }
      await nextTick();
      if (serial !== loadSerial) return;
      loadingFull.value = false;
      status.value = 'ready';
      scheduleWindowRead();
    } catch (error) {
      if (serial !== loadSerial) return;
      console.warn('[hedgeBoard] cumulative volatility unavailable', props.asset, error);
      response.value = null;
      fullResponse.value = null;
      loadingFull.value = false;
      status.value = 'error';
    }
  }

  function applyPresetIndices() {
    const last = allDates.value.at(-1);
    if (!last) return;
    const cutoff = days.value === 0 ? -Infinity : Date.parse(last) - days.value * 86_400_000;
    startIndex.value = Math.max(
      0,
      allDates.value.findIndex((date) => Date.parse(date) >= cutoff),
    );
    endIndex.value = allDates.value.length - 1;
    // Also reapply when the preset was already selected but the slider moved.
    scheduleWindowRead();
  }

  function scheduleWindowRead() {
    clearTimeout(rangeTimer);
    if (loadingFull.value) return;
    const serial = ++windowSerial;
    hoverIndex.value = null;
    if (!allDates.value.length) return;
    const window = { start: allDates.value[startIndex.value], end: allDates.value[endIndex.value] };
    const asset = props.asset;
    const interval = precision.value;
    windowController?.abort();
    if (
      startIndex.value === 0 &&
      endIndex.value === allDates.value.length - 1 &&
      fullResponse.value
    ) {
      response.value = fullResponse.value;
      status.value = 'ready';
      return;
    }
    windowController = new AbortController();
    const signal = windowController.signal;
    rangeTimer = setTimeout(async () => {
      try {
        const result = await getCumulativeVolatility(asset, 0, interval, window, signal);
        if (serial !== windowSerial) return;
        response.value = result.data;
        status.value = 'ready';
      } catch {
        if (serial !== windowSerial) return;
        status.value = 'error';
      }
    }, 180);
  }

  onMounted(load);
  const motionPlot = ref<SVGElement>();
  watch(
    motionPlot,
    (element, _, onCleanup) => {
      if (!element || typeof ResizeObserver === 'undefined') return;
      const observer = new ResizeObserver(([entry]) => {
        if (entry.contentRect.width > 0) plotWidth.value = entry.contentRect.width;
      });
      observer.observe(element);
      onCleanup(() => observer.disconnect());
    },
    { flush: 'post' },
  );
  const reveal = useChartReveal(motionPlot);
  watch([response, days, hiddenSessions, priceVisible], () => void reveal(points.value.length), {
    flush: 'post',
  });
  watch([precision, () => props.asset], load);
  watch([startIndex, endIndex], scheduleWindowRead);
  onBeforeUnmount(() => {
    fullController?.abort();
    windowController?.abort();
    clearTimeout(rangeTimer);
    loadSerial += 1;
    windowSerial += 1;
  });
</script>

<style scoped lang="less" src="../charts/macroSeriesChart.less"></style>
<style scoped lang="less">
  .cumulative-volatility {
    min-width: 0;
    padding: 4px 16px 12px;
    color: #24384b;
  }

  .cumulative-volatility__controls,
  .cumulative-volatility__control-group,
  .cumulative-volatility__legend {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
  }

  .cumulative-volatility__controls {
    gap: 8px 16px;
  }

  .cumulative-volatility__legend {
    margin: 12px 0 4px;
    gap: 6px 14px;
  }

  .cumulative-volatility__legend-toggle {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    min-height: 24px;
    padding: 0;
    border: 0;
    background: transparent;
    color: #405870;
    font-size: 12px;
    cursor: pointer;
  }

  .cumulative-volatility__legend-toggle.is-muted {
    opacity: 0.45;
  }

  .cumulative-volatility__legend i {
    width: 14px;
    height: 2px;
    border-radius: 2px;
    background: #111;
  }

  .cumulative-volatility__legend-price i {
    height: 3px;
  }

  .cumulative-volatility__legend-note {
    margin-left: auto;
    color: #627488;
    font-size: 11px;
  }

  .cumulative-volatility__plot {
    position: relative;
  }

  .cumulative-volatility__svg {
    display: block;
    width: 100%;
    font-family: inherit;
  }

  .cumulative-volatility__svg text {
    fill: #627488;
    font-size: 12px;
    font-variant-numeric: tabular-nums;
  }

  .cumulative-volatility__grid {
    stroke: #e6edf4;
  }

  .cumulative-volatility__axis {
    stroke: #d7e0e9;
  }

  .cumulative-volatility__zero,
  .cumulative-volatility__hover-line {
    stroke-dasharray: 4 4;
    stroke: #8496ab;
  }

  .cumulative-volatility__zero {
    opacity: 0.68;
  }

  .cumulative-volatility__tooltip {
    display: grid;
    position: absolute;
    top: 44px;
    gap: 5px;
    box-sizing: border-box;
    padding: 9px 11px;
    border: 1px solid #dbe4ec;
    border-radius: 6px;
    background: #fff;
    box-shadow: 0 4px 14px rgb(31 41 55 / 10%);
    font-size: 12px;
    font-variant-numeric: tabular-nums;
    pointer-events: none;
  }

  .cumulative-volatility__tooltip span {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .cumulative-volatility__tooltip b {
    margin-left: auto;
  }

  .cumulative-volatility__tooltip i {
    width: 7px;
    height: 7px;
    border-radius: 50%;
  }

  .cumulative-volatility__tooltip-price-dot {
    background: #111;
  }

  .cumulative-volatility__navigator :deep(.chart-range) {
    margin-top: 0;
  }

  .cumulative-volatility__navigator :deep(.chart-range__labels) {
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    height: auto !important;
    min-height: 14px;
    color: #627488 !important;
    gap: 4px 8px;
    font-variant-numeric: tabular-nums;
  }

  .cumulative-volatility__navigator :deep(.chart-range__label) {
    position: static !important;
    transform: none !important;
  }

  .cumulative-volatility__navigator :deep(.chart-range__viewport) {
    touch-action: none;
  }

  .cumulative-volatility__navigator :deep(.chart-range__rail),
  .cumulative-volatility__navigator :deep(.chart-range__selection) {
    height: 24px !important;
    box-shadow: none !important;
  }

  .cumulative-volatility__navigator :deep(.chart-range__rail) {
    background: #f5f8fb !important;
  }

  .cumulative-volatility__navigator :deep(.chart-range__selection) {
    border-color: rgb(71 123 194 / 42%) !important;
    background: rgb(22 93 255 / 10%) !important;
  }

  .cumulative-volatility__navigator :deep(.chart-range__preview) {
    position: absolute;
    z-index: 1;
    width: 100%;
    height: 100%;
    stroke-width: 1;
    stroke: #a2b9dc;
    pointer-events: none;
    inset: 0;
  }

  .cumulative-volatility__navigator :deep(.chart-range__handle) {
    width: 8px !important;
    height: 20px !important;
    border: 1px solid #477bc2 !important;
    border-radius: 3px !important;
    background: #dce8f8 !important;
    box-shadow: none !important;
  }

  .cumulative-volatility__navigator :deep(.chart-range__handle--start) {
    left: -4px !important;
  }

  .cumulative-volatility__navigator :deep(.chart-range__handle--end) {
    right: -4px !important;
  }

  .cumulative-volatility__navigator :deep(.chart-range__handle:focus-visible) {
    outline: 2px solid #477bc2;
    outline-offset: 3px;
  }

  .cumulative-volatility__message {
    margin: 8px 0 0;
    color: #627488;
    font-size: 11px;
  }

  .cumulative-volatility__empty {
    display: grid;
    min-height: 240px;
    place-content: center;
    color: #627488;
    font-size: 13px;
  }

  @media (max-width: 600px) {
    .cumulative-volatility {
      padding-inline: 8px;
    }

    .cumulative-volatility__legend {
      gap: 4px 10px;
    }
  }
</style>
