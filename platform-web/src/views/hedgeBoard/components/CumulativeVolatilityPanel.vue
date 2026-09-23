<template>
  <div class="cumulative-volatility">
    <div class="cumulative-volatility__toolbar">
      <div class="cumulative-volatility__controls">
        <div class="cumulative-volatility__control-group" role="group" aria-label="历史范围">
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
          <button
            type="button"
            :class="{ active: customRangeApplied }"
            :aria-pressed="customRangeApplied"
            @click="openCustomRange"
          >
            自定义
          </button>
        </div>
        <div v-if="customRangeOpen" class="cumulative-volatility__custom-range">
          <label>
            起始
            <input
              v-model="customStartDate"
              type="date"
              :min="availableStartDate"
              :max="availableEndDate"
            />
          </label>
          <span>至</span>
          <label>
            结束
            <input
              v-model="customEndDate"
              type="date"
              :min="availableStartDate"
              :max="availableEndDate"
            />
          </label>
          <button
            type="button"
            class="cumulative-volatility__custom-apply"
            @click="applyCustomRange"
          >
            应用
          </button>
          <button
            type="button"
            class="cumulative-volatility__custom-cancel"
            @click="customRangeOpen = false"
          >
            取消
          </button>
        </div>
        <div class="cumulative-volatility__control-group" role="group" aria-label="采样精度">
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

    <div v-if="status === 'loading'" class="cumulative-volatility__empty"
      >正在读取已落库的累计波动数据…</div
    >
    <div v-else-if="status === 'error' || !dates.length" class="cumulative-volatility__empty">
      {{ status === 'error' ? '当前累计波动数据暂不可用。' : '当前范围暂无有效观测。' }}
    </div>
    <div v-else class="cumulative-volatility__stage">
      <div class="cumulative-volatility__legend" aria-label="盘口颜色与时间说明">
        <span class="cumulative-volatility__legend-note">时间均为 UTC</span>
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
          <i></i>{{ title }}价格（美洲盘首个有效价格）
        </button>
      </div>
      <svg
        class="cumulative-volatility__svg"
        viewBox="0 0 1200 360"
        preserveAspectRatio="none"
        role="img"
        :aria-label="`${title}，${formatDate(dates[0])}至${formatDate(dates.at(-1) ?? dates[0])}`"
        @mousemove="onMove"
        @mouseleave="hoverIndex = null"
      >
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
          :x="plot.right + 12"
          :y="plot.top - 8"
          text-anchor="start"
          class="cumulative-volatility__price-tick cumulative-volatility__price-axis-title"
        >
          价格
        </text>
        <text
          v-for="tick in dateTicks"
          :key="`date-${tick.date}`"
          :x="xForDate(tick.date)"
          y="344"
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
          :y1="yForValue(0)"
          :y2="yForValue(0)"
          class="cumulative-volatility__zero"
        />
        <path
          v-for="series in plottedSeries"
          :key="series.key"
          :d="series.path"
          fill="none"
          :stroke="series.color"
          stroke-width="2.2"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
        <path
          v-if="priceVisible && pricePath"
          :d="pricePath"
          fill="none"
          stroke="#18313c"
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
        <line
          v-if="hoverIndex !== null"
          :x1="xForTimestamp(dates[hoverIndex])"
          :x2="xForTimestamp(dates[hoverIndex])"
          :y1="plot.top"
          :y2="plot.bottom"
          class="cumulative-volatility__hover-line"
        />
      </svg>
      <div v-if="hoverIndex !== null" class="cumulative-volatility__tooltip" role="status">
        <strong>{{ formatDateTime(dates[hoverIndex]) }}</strong>
        <span v-for="series in plottedSeries" :key="series.key">
          <i :style="{ background: series.color }"></i>{{ series.label }}：{{
            valueAt(series, hoverIndex)
          }}
        </span>
        <span v-if="priceVisible && hoverPrice !== null">
          <i class="cumulative-volatility__tooltip-price-dot"></i>{{ title }}价格：{{
            formatPrice(hoverPrice)
          }}
        </span>
      </div>
    </div>

    <ChartRangeSelector
      v-if="allDates.length > 1"
      :labels="allDates"
      :values="rangeValues"
      :start-index="startIndex"
      :end-index="endIndex"
      :min-window-size="minWindowSize"
      :on-start-change="onRangeStartChange"
      :on-end-change="onRangeEndChange"
    />
  </div>
</template>

<script setup lang="ts">
  import { computed, defineComponent, onMounted, PropType, ref, watch } from 'vue';

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
  ] as const;
  const precisionOptions: Array<{ value: CumulativeVolatilityInterval; label: string }> = [
    { value: '15m', label: '15分钟' },
    { value: '1h', label: '1小时' },
    { value: '4h', label: '4小时' },
  ];
  const days = ref<number>(365);
  const precision = ref<CumulativeVolatilityInterval>('15m');
  const response = ref<CumulativeVolatilityData | null>(null);
  const status = ref<'loading' | 'ready' | 'error'>('loading');
  const hoverIndex = ref<number | null>(null);
  const hiddenSessions = ref<Set<string>>(new Set());
  const priceVisible = ref(true);
  const customRangeOpen = ref(false);
  const customRangeApplied = ref(false);
  const customStartDate = ref('');
  const customEndDate = ref('');
  let requestSerial = 0;

  const plot = { left: 76, right: 1120, top: 22, bottom: 300 };
  const sessionSeries = [
    { key: 'asia', label: '亚洲盘 23:00–07:00', color: '#f0c015' },
    { key: 'europe', label: '欧洲盘 07:00–15:00', color: '#2ca02c' },
    { key: 'americas', label: '美洲盘 15:00–23:00', color: '#213ed1' },
  ] as const;

  const points = computed(() => response.value?.points ?? []);
  const allDates = computed(() =>
    [...new Set(points.value.map((point) => point.timestamp))].sort(),
  );
  const availableStartDate = computed(() => allDates.value[0]?.slice(0, 10) ?? '');
  const availableEndDate = computed(() => allDates.value.at(-1)?.slice(0, 10) ?? '');
  const startIndex = ref(0);
  const endIndex = ref(0);
  const minWindowSize = computed(() =>
    Math.max(4, Math.min(allDates.value.length, Math.ceil(allDates.value.length * 0.08))),
  );
  const dates = computed(() => allDates.value.slice(startIndex.value, endIndex.value + 1));
  const valueMap = computed(() => {
    const maps = new Map<string, Map<string, number>>();
    sessionSeries.forEach((series) => maps.set(series.key, new Map()));
    points.value.forEach((point) => {
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
  const bounds = computed(() => {
    if (!allValues.value.length) return { min: -1, max: 1 };
    const min = Math.min(0, ...allValues.value);
    const max = Math.max(0, ...allValues.value);
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
    const commonDates = [...(datesBySession[0] ?? [])].filter((date) =>
      datesBySession.slice(1).every((sessionDates) => sessionDates.has(date)),
    );
    if (commonDates.length) return commonDates.sort();
    return [...new Set(datesBySession.flatMap((sessionDates) => [...sessionDates]))].sort();
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
  const samplesPerSessionDay = computed(() => {
    let max = 1;
    pointsBySession.value.forEach((byDate) =>
      byDate.forEach((group) => {
        max = Math.max(max, group.length);
      }),
    );
    return max;
  });
  const plotSlotCount = computed(() =>
    Math.max(1, visibleSessionDates.value.length * samplesPerSessionDay.value - 1),
  );
  const dateTicks = computed(() => {
    const datesForTicks = visibleSessionDates.value;
    if (datesForTicks.length <= 7)
      return datesForTicks.map((date, index) => ({ date, index, position: index }));
    return Array.from({ length: 7 }, (_, index) => {
      const dateIndex = Math.round((index * (datesForTicks.length - 1)) / 6);
      return { date: datesForTicks[dateIndex], index: dateIndex, position: index };
    });
  });
  const plottedSeries = computed(() =>
    visibleSessionSeries.value.map((series) => {
      const byDate = pointsBySession.value.get(series.key) ?? new Map();
      let path = '';
      let pointIndex = 0;
      visibleSessionDates.value.forEach((sessionDate, dayIndex) => {
        const group = byDate.get(sessionDate) ?? [];
        group.forEach((point, sampleIndex) => {
          const value = visibleValueMap.value.get(series.key)?.get(point.timestamp) ?? NaN;
          if (!Number.isFinite(value)) return;
          const slot = dayIndex * samplesPerSessionDay.value + sampleIndex;
          path += `${pointIndex ? 'L' : 'M'}${xForSlot(slot).toFixed(2)},${yForValue(value).toFixed(
            2,
          )} `;
          pointIndex += 1;
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
    pricePoints.value.forEach((point, index) => {
      const x = xForDate(point.sessionDate);
      path += `${index ? 'L' : 'M'}${x.toFixed(2)},${yForPrice(point.value).toFixed(2)} `;
    });
    return path.trim();
  });
  const pointByTimestamp = computed(() => {
    const result = new Map<string, (typeof points.value)[number]>();
    points.value.forEach((point) => result.set(point.timestamp, point));
    return result;
  });
  const hoverPrice = computed(() => {
    const timestamp = hoverIndex.value == null ? undefined : dates.value[hoverIndex.value];
    const sessionDate = timestamp ? pointByTimestamp.value.get(timestamp)?.sessionDate : undefined;
    if (!sessionDate) return null;
    return priceByDate.value.get(sessionDate) ?? null;
  });

  function xForSlot(slot: number) {
    return plot.left + ((plot.right - plot.left) * slot) / plotSlotCount.value;
  }

  function xForDate(sessionDate: string) {
    return xForSlot(
      Math.max(0, visibleSessionDates.value.indexOf(sessionDate)) * samplesPerSessionDay.value,
    );
  }

  function xForTimestamp(timestamp: string | undefined) {
    if (!timestamp) return plot.left;
    for (const [, byDate] of pointsBySession.value) {
      for (const [sessionDate, group] of byDate) {
        const sampleIndex = group.findIndex((point) => point.timestamp === timestamp);
        if (sampleIndex >= 0) {
          return xForSlot(
            visibleSessionDates.value.indexOf(sessionDate) * samplesPerSessionDay.value +
              sampleIndex,
          );
        }
      }
    }
    return plot.left;
  }

  function yForValue(value: number) {
    const { min, max } = bounds.value;
    return plot.bottom - ((value - min) / Math.max(max - min, 0.01)) * (plot.bottom - plot.top);
  }

  function yForTick(value: number) {
    return yForValue(value);
  }

  function yForPrice(value: number) {
    const { min, max } = priceBounds.value;
    return plot.bottom - ((value - min) / Math.max(max - min, 0.01)) * (plot.bottom - plot.top);
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
    return value.slice(5, 16).replace('T', ' ');
  }

  function formatDateTime(value: string | undefined) {
    if (!value) return '—';
    return value.replace('T', ' ').replace('Z', ' UTC').slice(0, 19);
  }

  function valueAt(series: { key: string }, index: number) {
    const value = visibleValueMap.value.get(series.key)?.get(dates.value[index]);
    return value == null ? '—' : `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  }

  function formatPrice(value: number) {
    if (!Number.isFinite(value)) return '—';
    return value >= 1000
      ? value.toLocaleString('zh-CN', { maximumFractionDigits: 0 })
      : value.toLocaleString('zh-CN', { maximumFractionDigits: 2 });
  }

  function onMove(event: MouseEvent) {
    if (!dates.value.length) return;
    const rect = (event.currentTarget as SVGSVGElement).getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 1200;
    let nearest = 0;
    let distance = Number.POSITIVE_INFINITY;
    dates.value.forEach((timestamp, index) => {
      const candidate = xForTimestamp(timestamp);
      const candidateDistance = Math.abs(candidate - x);
      if (candidateDistance < distance) {
        nearest = index;
        distance = candidateDistance;
      }
    });
    hoverIndex.value = nearest;
  }

  function onRangeStartChange(value: number) {
    startIndex.value = value;
  }

  function onRangeEndChange(value: number) {
    endIndex.value = value;
  }

  function selectPresetRange(value: number) {
    customRangeOpen.value = false;
    customRangeApplied.value = false;
    days.value = value;
  }

  function openCustomRange() {
    if (!allDates.value.length) return;
    customStartDate.value = customStartDate.value || availableStartDate.value;
    customEndDate.value = customEndDate.value || availableEndDate.value;
    customRangeOpen.value = true;
  }

  function applyCustomRange() {
    if (!allDates.value.length || !customStartDate.value || !customEndDate.value) return;
    if (customStartDate.value > customEndDate.value) return;
    const start = allDates.value.findIndex(
      (timestamp) => timestamp.slice(0, 10) >= customStartDate.value,
    );
    const end = [...allDates.value]
      .map((timestamp, index) => ({ timestamp, index }))
      .reverse()
      .find(({ timestamp }) => timestamp.slice(0, 10) <= customEndDate.value)?.index;
    if (start < 0 || end == null || end < start) return;
    startIndex.value = start;
    endIndex.value = Math.max(start, end);
    customRangeApplied.value = true;
    customRangeOpen.value = false;
  }

  async function load() {
    const serial = ++requestSerial;
    status.value = 'loading';
    hoverIndex.value = null;
    try {
      const result = await getCumulativeVolatility(props.asset, days.value, precision.value);
      if (serial !== requestSerial) return;
      response.value = result.data;
      startIndex.value = 0;
      endIndex.value = Math.max(0, allDates.value.length - 1);
      customRangeApplied.value = false;
      customRangeOpen.value = false;
      status.value = result.data.points.length ? 'ready' : 'error';
    } catch (error) {
      if (serial !== requestSerial) return;
      console.warn('[hedgeBoard] cumulative volatility unavailable', props.asset, error);
      response.value = null;
      status.value = 'error';
    }
  }

  onMounted(load);
  watch([days, precision, () => props.asset], load);
</script>

<style scoped lang="less">
  .cumulative-volatility {
    min-width: 0;
    padding: 4px 18px 18px;
    color: var(--hedge-cool-text, #18313c);
  }

  .cumulative-volatility__toolbar,
  .cumulative-volatility__controls,
  .cumulative-volatility__control-group,
  .cumulative-volatility__legend {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .cumulative-volatility__toolbar {
    flex-wrap: wrap;
    justify-content: space-between;
    gap: 16px;
  }

  .cumulative-volatility__custom-range {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 8px;
    border: 1px solid #d9e2ec;
    border-radius: 8px;
    background: #fbfdff;
    color: #6d8293;
    font-size: 12px;
  }

  .cumulative-volatility__custom-range label {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    white-space: nowrap;
  }

  .cumulative-volatility__custom-range input {
    width: 132px;
    height: 26px;
    padding: 0 6px;
    border: 1px solid #cfdbe8;
    border-radius: 5px;
    background: #fff;
    color: #18313c;
    font: inherit;
  }

  .cumulative-volatility__custom-apply,
  .cumulative-volatility__custom-cancel {
    height: 26px;
    padding: 0 9px;
    border-radius: 5px;
    font: inherit;
    cursor: pointer;
  }

  .cumulative-volatility__custom-apply {
    border: 1px solid #4f7bf5;
    background: #4f7bf5;
    color: #fff;
  }

  .cumulative-volatility__custom-cancel {
    border: 1px solid #cfdbe8;
    background: #fff;
    color: #6d8293;
  }

  .cumulative-volatility__legend,
  .cumulative-volatility__legend-note {
    color: var(--hedge-cool-muted, #6d8293);
    font-size: 11px;
  }

  .cumulative-volatility__legend-price {
    padding: 0;
    border: 0;
    background: transparent;
    color: var(--hedge-cool-text, #18313c);
    font-weight: 700;
    cursor: pointer;
  }

  .cumulative-volatility__legend-price i {
    width: 16px;
    height: 3px;
    border-radius: 0;
    background: #18313c;
  }

  .cumulative-volatility__controls {
    flex-wrap: wrap;
  }

  .cumulative-volatility__control-group button {
    min-height: 26px;
    padding: 3px 9px;
    border: 1px solid rgb(109 130 147 / 28%);
    border-radius: 999px;
    background: #fff;
    color: var(--hedge-cool-muted, #526b7d);
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
  }

  .cumulative-volatility__control-group button.active,
  .cumulative-volatility__control-group button:hover,
  .cumulative-volatility__control-group button:focus-visible {
    border-color: rgb(22 93 255 / 42%);
    outline: none;
    background: rgb(22 93 255 / 8%);
    color: #165dff;
  }

  .cumulative-volatility__message {
    margin: 10px 0 0;
    color: var(--hedge-cool-muted, #6d8293);
    font-size: 11px;
  }

  .cumulative-volatility__stage {
    position: relative;
    margin-top: 10px;
  }

  .cumulative-volatility__svg {
    display: block;
    width: 100%;
    min-height: 250px;
    overflow: visible;
  }

  .cumulative-volatility__svg text {
    fill: var(--hedge-cool-muted, #6d8293);
    font-size: 11px;
    font-variant-numeric: tabular-nums;
  }

  .cumulative-volatility__grid {
    stroke-dasharray: 3 5;
    stroke: rgb(193 207 220 / 54%);
  }

  .cumulative-volatility__zero {
    stroke-dasharray: 4 4;
    stroke: rgb(82 107 125 / 50%);
  }

  .cumulative-volatility__price-tick {
    fill: #18313c !important;
    font-weight: 700;
  }

  .cumulative-volatility__hover-line {
    stroke-dasharray: 4 4;
    stroke: rgb(82 107 125 / 68%);
  }

  .cumulative-volatility__tooltip {
    display: grid;
    position: absolute;
    top: 8px;
    right: 18px;
    min-width: 170px;
    padding: 9px 11px;
    border: 1px solid rgb(193 207 220 / 88%);
    border-radius: 10px;
    background: rgb(255 255 255 / 96%);
    box-shadow: 0 8px 24px rgb(31 41 55 / 8%);
    color: var(--hedge-cool-muted, #526b7d);
    font-size: 11px;
    pointer-events: none;
    gap: 5px;
  }

  .cumulative-volatility__tooltip strong {
    color: var(--hedge-cool-text, #18313c);
  }

  .cumulative-volatility__tooltip span {
    display: flex;
    align-items: center;
    gap: 5px;
  }

  .cumulative-volatility__legend {
    flex-wrap: wrap;
    margin-top: 2px;
  }

  .cumulative-volatility__legend span {
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }

  .cumulative-volatility__legend-toggle {
    display: inline-flex;
    align-items: center;
    padding: 0;
    border: 0;
    background: transparent;
    color: var(--hedge-cool-muted, #6d8293);
    font: inherit;
    cursor: pointer;
    gap: 5px;
  }

  .cumulative-volatility__legend-toggle.is-muted {
    opacity: 0.38;
    text-decoration: line-through;
  }

  .cumulative-volatility__legend-toggle:focus-visible {
    border-radius: 6px;
    outline: 1px solid #165dff;
    outline-offset: 3px;
  }

  .cumulative-volatility__legend i,
  .cumulative-volatility__tooltip i,
  .cumulative-volatility__legend-toggle i {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
  }

  .cumulative-volatility__tooltip-price-dot {
    background: #18313c;
  }

  .cumulative-volatility__legend-note {
    margin-left: auto;
  }

  .cumulative-volatility__empty {
    display: grid;
    min-height: 240px;
    place-content: center;
    color: var(--hedge-cool-muted, #6d8293);
    font-size: 13px;
  }

  @media (max-width: 760px) {
    .cumulative-volatility__legend-note {
      width: 100%;
      margin-left: 0;
    }
  }
</style>
