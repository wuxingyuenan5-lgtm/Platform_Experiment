<template>
  <div class="vibe-trend-charts">
    <VibeTimeChart
      title="市场涨跌结构"
      y-label="上涨/下跌家数（家）"
      right-label="涨停/跌停家数（家）"
      :dates="dates"
      :series="marketSeries"
    />
    <VibeTimeChart
      title="市场宽度"
      y-label="市场宽度（%）"
      :dates="dates"
      :series="breadthSeries"
    />
    <template v-if="crowdingRows.length">
      <VibeTimeChart
        title="通信设备 | 成交额占全A与换手率"
        y-label="成交额占全A（%）"
        right-label="换手率（%）"
        :dates="crowdingDates"
        :series="communicationSeries"
      />
      <VibeTimeChart
        title="四行业 | 成交额与成交额占比"
        y-label="成交额（亿元）"
        right-label="成交额占全A（%）"
        :dates="crowdingDates"
        :series="fourIndustrySeries"
      />
    </template>
    <VibeTimeChart
      v-if="innovationRows.length"
      title="创新药 | 成交额占全A与换手率"
      y-label="成交额占全A（%）"
      right-label="换手率（%）"
      :dates="innovationDates"
      :series="innovationSeries"
    />
  </div>
</template>

<script setup lang="ts">
  import { computed, defineComponent, h, ref, watch, type PropType } from 'vue';

  interface HistoryRow {
    date: string;
    advance?: number | null;
    decline?: number | null;
    limit_up?: number | null;
    limit_down?: number | null;
    market_breadth?: number | null;
  }
  interface Series {
    name: string;
    values: Array<number | null | undefined>;
    type: 'bar' | 'line' | 'area';
    axis?: 'left' | 'right';
    color: string;
    sign?: 1 | -1;
    unit?: string;
    percent?: boolean;
  }
  type CrowdingRow = {
    date: string;
    targets?: Record<
      string,
      { amount100m?: number | null; amountShareOfA?: number | null; turnoverPct?: number | null }
    >;
    combined?: { amount100m?: number | null; amountShareOfA?: number | null };
  };
  type InnovationRow = {
    date: string;
    amountShareOfA?: number | null;
    turnoverPct?: number | null;
  };
  const props = defineProps<{
    rows: HistoryRow[];
    crowdingRows?: CrowdingRow[];
    innovationRows?: InnovationRow[];
  }>();
  const dates = computed(() => props.rows.map((row) => row.date));
  const marketSeries = computed<Series[]>(() => [
    {
      name: '上涨家数',
      values: props.rows.map((row) => row.advance),
      type: 'bar',
      color: '#ef4444',
      unit: '家',
    },
    {
      name: '下跌家数',
      values: props.rows.map((row) => row.decline),
      type: 'bar',
      color: '#10b981',
      sign: -1,
      unit: '家',
    },
    {
      name: '涨停家数',
      values: props.rows.map((row) => row.limit_up),
      type: 'line',
      axis: 'right',
      color: '#ef4444',
      unit: '家',
    },
    {
      name: '跌停家数',
      values: props.rows.map((row) => row.limit_down),
      type: 'line',
      axis: 'right',
      color: '#10b981',
      sign: -1,
      unit: '家',
    },
  ]);
  const breadthSeries = computed<Series[]>(() => [
    {
      name: '市场宽度',
      values: props.rows.map((row) => row.market_breadth),
      type: 'line',
      color: '#123d68',
      percent: true,
    },
  ]);
  const crowdingRows = computed(() => props.crowdingRows || []);
  const crowdingDates = computed(() => crowdingRows.value.map((row) => row.date));
  const communicationSeries = computed<Series[]>(() => [
    {
      name: '通信设备成交额占全A',
      type: 'area',
      color: '#2563eb',
      percent: true,
      values: crowdingRows.value.map((row) => row.targets?.['通信设备']?.amountShareOfA),
    },
    {
      name: '通信设备换手率',
      type: 'line',
      axis: 'right',
      color: '#ef4444',
      percent: true,
      values: crowdingRows.value.map((row) => row.targets?.['通信设备']?.turnoverPct),
    },
  ]);
  const fourIndustrySeries = computed<Series[]>(() => [
    {
      name: '四行业合计成交额',
      type: 'bar',
      color: '#4f81bd',
      values: crowdingRows.value.map((row) => row.combined?.amount100m),
    },
    {
      name: '四行业成交额占全A',
      type: 'line',
      axis: 'right',
      color: '#f59e0b',
      percent: true,
      values: crowdingRows.value.map((row) => row.combined?.amountShareOfA),
    },
  ]);
  const innovationRows = computed(() => props.innovationRows || []);
  const innovationDates = computed(() => innovationRows.value.map((row) => row.date));
  const innovationSeries = computed<Series[]>(() => [
    {
      name: '创新药成交额占全A',
      type: 'area',
      color: '#2563eb',
      percent: true,
      values: innovationRows.value.map((row) => row.amountShareOfA),
    },
    {
      name: '创新药换手率',
      type: 'line',
      axis: 'right',
      color: '#f97316',
      percent: true,
      values: innovationRows.value.map((row) => row.turnoverPct),
    },
  ]);

  const VibeTimeChart = defineComponent({
    name: 'VibeTimeChart',
    props: {
      title: { type: String, required: true },
      yLabel: { type: String, required: true },
      rightLabel: { type: String, default: '' },
      dates: { type: Array as PropType<string[]>, required: true },
      series: { type: Array as PropType<Series[]>, required: true },
    },
    setup(chartProps) {
      const last = computed(() => Math.max(0, chartProps.dates.length - 1));
      // These panels are fixed daily history views.  A miniature draggable
      // navigator created thousands of unnecessary pointer/layout updates and
      // repeatedly rendered browser-default tracks, so the chart always shows
      // its bounded persisted window without a second scroll axis.
      const start = ref(0);
      const end = ref(last.value);
      const hidden = ref(new Set<number>());
      const hoverIndex = ref<number | null>(null);
      watch(
        () => chartProps.dates.length,
        () => {
          end.value = last.value;
          start.value = 0;
          hoverIndex.value = null;
        },
        { immediate: true },
      );
      const W = 1200,
        H = 360,
        ml = 72,
        mr = chartProps.rightLabel ? 94 : 40,
        mt = 22,
        mb = 48;
      const x0 = ml,
        x1 = W - mr,
        y0 = mt,
        y1 = H - mb;
      const visible = computed(() =>
        chartProps.series
          .map((series, index) => ({ series, index }))
          .filter((entry) => !hidden.value.has(entry.index)),
      );
      const numeric = (value: unknown) => {
        const n = Number(value);
        return Number.isFinite(n) ? n : null;
      };
      const domain = (axis: 'left' | 'right') => {
        const values: number[] = [];
        visible.value
          .filter((entry) => (entry.series.axis || 'left') === axis)
          .forEach((entry) =>
            entry.series.values.slice(start.value, end.value + 1).forEach((value) => {
              const n = numeric(value);
              if (n != null) values.push(n * (entry.series.sign || 1));
            }),
          );
        if (!values.length) return [-1, 1];
        let lo = Math.min(...values),
          hi = Math.max(...values);
        if (chartProps.title === '市场涨跌结构' || lo < 0) {
          lo = Math.min(0, lo);
          hi = Math.max(0, hi);
        }
        if (lo === hi) {
          lo -= 1;
          hi += 1;
        }
        const padding = (hi - lo) * 0.08;
        return [lo - padding, hi + padding];
      };
      const leftDomain = computed(() => domain('left'));
      const rightDomain = computed(() => domain('right'));
      const span = computed(() => Math.max(1, end.value - start.value));
      const x = (index: number) => x0 + ((x1 - x0) * (index - start.value)) / span.value;
      const y = (value: number, bounds: number[]) =>
        y1 - ((value - bounds[0]) / Math.max(bounds[1] - bounds[0], 1e-9)) * (y1 - y0);
      const pathFor = (entry: { series: Series }) =>
        chartProps.dates
          .slice(start.value, end.value + 1)
          .map((_, offset) => {
            const index = start.value + offset;
            const value = numeric(entry.series.values[index]);
            if (value == null) return null;
            const bounds =
              (entry.series.axis || 'left') === 'right' ? rightDomain.value : leftDomain.value;
            return `${x(index)},${y(value * (entry.series.sign || 1), bounds)}`;
          })
          .filter((point): point is string => Boolean(point))
          .join(' ');
      const ticks = [0, 1, 2, 3, 4];
      const tickLabel = (bounds: number[], index: number, percent = false) => {
        const value = bounds[1] - ((bounds[1] - bounds[0]) * index) / 4;
        return percent ? `${(value * 100).toFixed(1)}%` : value.toFixed(0);
      };
      const toggle = (index: number) => {
        const next = new Set(hidden.value);
        next.has(index) ? next.delete(index) : next.add(index);
        hidden.value = next;
      };
      const onMove = (event: MouseEvent) => {
        const target = event.currentTarget as SVGSVGElement;
        const rect = target.getBoundingClientRect();
        const px = ((event.clientX - rect.left) / rect.width) * W;
        const next = Math.round(start.value + ((px - x0) / (x1 - x0)) * (end.value - start.value));
        hoverIndex.value = Math.max(start.value, Math.min(end.value, next));
      };
      const valueText = (value: unknown, series: Series) => {
        const n = numeric(value);
        if (n == null) return '—';
        return series.percent
          ? `${(n * 100).toFixed(2)}%`
          : `${n.toLocaleString('zh-CN', { maximumFractionDigits: 4 })}${
              series.unit ? ` ${series.unit}` : ''
            }`;
      };
      type NavigatorDrag = {
        mode: 'start' | 'end' | 'window';
        originIndex: number;
        originStart: number;
        originEnd: number;
      };
      const navigatorDrag = ref<NavigatorDrag | null>(null);
      const navigatorIndex = (clientX: number, host: HTMLElement) => {
        const rect = host.getBoundingClientRect();
        const ratio = Math.max(0, Math.min(1, (clientX - rect.left) / Math.max(rect.width, 1)));
        return Math.round(ratio * last.value);
      };
      const beginNavigatorDrag = (event: PointerEvent, mode: NavigatorDrag['mode']) => {
        const host = (event.currentTarget as HTMLElement).closest(
          '.vibe-navigator',
        ) as HTMLElement | null;
        if (!host) return;
        event.preventDefault();
        event.stopPropagation();
        host.setPointerCapture?.(event.pointerId);
        navigatorDrag.value = {
          mode,
          originIndex: navigatorIndex(event.clientX, host),
          originStart: start.value,
          originEnd: end.value,
        };
      };
      const moveNavigatorDrag = (event: PointerEvent) => {
        const drag = navigatorDrag.value;
        if (!drag) return;
        const host = event.currentTarget as HTMLElement;
        const index = navigatorIndex(event.clientX, host);
        if (drag.mode === 'start') start.value = Math.min(index, end.value);
        else if (drag.mode === 'end') end.value = Math.max(index, start.value);
        else {
          const width = drag.originEnd - drag.originStart;
          const delta = index - drag.originIndex;
          const nextStart = Math.max(0, Math.min(last.value - width, drag.originStart + delta));
          start.value = nextStart;
          end.value = nextStart + width;
        }
      };
      const navigatorSeries = computed(() =>
        chartProps.series
          .filter((series) => series.values.some((value) => numeric(value) != null))
          .slice(0, 2),
      );
      const navigatorPathFor = (series: Series) => {
        const points = series.values
          .map((value) => numeric(value))
          .filter((value): value is number => value != null);
        if (!points.length) return '';
        const lo = Math.min(...points);
        const hi = Math.max(...points);
        const spanY = Math.max(hi - lo, 1e-9);
        return series.values
          .map((value, index) => {
            const numericValue = numeric(value);
            if (numericValue == null) return null;
            return `${(index / Math.max(last.value, 1)) * 1200},${
              34 - ((numericValue - lo) / spanY) * 24
            }`;
          })
          .filter((point): point is string => Boolean(point))
          .join(' ');
      };
      return () =>
        h('div', { class: 'vibe-time-chart' }, [
          h('div', { class: 'vibe-chart-head' }, [h('h3', chartProps.title)]),
          h('div', { class: 'vibe-chart-subtitle' }, [
            h('div', { class: 'vibe-sub-left' }, [
              h(
                'div',
                { class: 'vibe-chart-legend' },
                chartProps.series.map((series, index) =>
                  h(
                    'button',
                    {
                      type: 'button',
                      class: ['vibe-legend-btn', hidden.value.has(index) ? 'off' : ''],
                      onClick: () => toggle(index),
                    },
                    [h('span', { style: { background: series.color } }), series.name],
                  ),
                ),
              ),
              h('span', { class: 'vibe-hint' }, chartProps.yLabel),
            ]),
            chartProps.rightLabel
              ? h('div', { class: 'vibe-right-label' }, `右轴：${chartProps.rightLabel}`)
              : null,
          ]),
          h('div', { class: 'vibe-chart-stage' }, [
            h(
              'svg',
              {
                class: 'vibe-chart-svg',
                viewBox: `0 0 ${W} ${H}`,
                onMousemove: onMove,
                onMouseleave: () => {
                  hoverIndex.value = null;
                },
              },
              [
                ticks.flatMap((tick) => {
                  const yy = y0 + ((y1 - y0) * tick) / 4;
                  return [
                    h('line', { x1: x0, y1: yy, x2: x1, y2: yy, class: 'vibe-chart-grid' }),
                    h(
                      'text',
                      { x: x0 - 8, y: yy + 4, 'text-anchor': 'end', class: 'vibe-axis-label' },
                      tickLabel(leftDomain.value, tick, chartProps.yLabel.includes('%')),
                    ),
                    chartProps.rightLabel
                      ? h(
                          'text',
                          { x: x1 + 10, y: yy + 4, class: 'vibe-axis-label' },
                          tickLabel(rightDomain.value, tick),
                        )
                      : null,
                  ];
                }),
                Array.from(
                  new Set(
                    Array.from({ length: 8 }, (_, index) =>
                      Math.round(start.value + ((end.value - start.value) * index) / 7),
                    ),
                  ),
                ).map((index) =>
                  h(
                    'text',
                    {
                      x: x(index),
                      y: H - 15,
                      'text-anchor':
                        index === start.value ? 'start' : index === end.value ? 'end' : 'middle',
                      class: 'vibe-axis-label',
                    },
                    (chartProps.dates[index] || '').slice(5),
                  ),
                ),
                visible.value.flatMap((entry) => {
                  const series = entry.series;
                  const bounds =
                    (series.axis || 'left') === 'right' ? rightDomain.value : leftDomain.value;
                  const bars =
                    series.type === 'bar'
                      ? chartProps.dates
                          .slice(start.value, end.value + 1)
                          .map((_, offset) => {
                            const index = start.value + offset;
                            const value = numeric(series.values[index]);
                            if (value == null) return null;
                            const yy = y(value * (series.sign || 1), bounds),
                              zero = y(0, bounds);
                            const width = Math.max(
                              2,
                              Math.min(10, ((x1 - x0) / (span.value + 1)) * 0.55),
                            );
                            return h('rect', {
                              x: x(index) - width / 2,
                              y: Math.min(yy, zero),
                              width,
                              height: Math.max(1, Math.abs(zero - yy)),
                              fill: series.color,
                              opacity: 0.25,
                            });
                          })
                          .filter(Boolean)
                      : [];
                  const line =
                    series.type === 'line' || series.type === 'area'
                      ? h('polyline', {
                          points: pathFor(entry),
                          class: 'vibe-chart-line',
                          stroke: series.color,
                          fill: 'none',
                        })
                      : null;
                  const area =
                    series.type === 'area'
                      ? h('polygon', {
                          // For positive-only percentage series, y(0) lies outside
                          // the chart. Anchoring to the visible lower bound prevents
                          // the browser from painting a full-height dark wedge.
                          points: `${x(start.value)},${y(Math.max(0, bounds[0]), bounds)} ${pathFor(
                            entry,
                          )} ${x(end.value)},${y(Math.max(0, bounds[0]), bounds)}`,
                          fill: series.color,
                          opacity: 0.16,
                        })
                      : null;
                  return [...bars, area, line];
                }),
              ],
            ),
            hoverIndex.value != null
              ? h('div', { class: 'vibe-chart-tooltip' }, [
                  h('b', chartProps.dates[hoverIndex.value] || ''),
                  ...visible.value.map((entry) =>
                    h(
                      'div',
                      { style: { color: entry.series.color } },
                      `● ${entry.series.name}：${valueText(
                        entry.series.values[hoverIndex.value as number],
                        entry.series,
                      )}`,
                    ),
                  ),
                ])
              : null,
          ]),
          h(
            'div',
            {
              class: 'vibe-navigator',
              onPointermove: moveNavigatorDrag,
              onPointerup: () => {
                navigatorDrag.value = null;
              },
              onPointercancel: () => {
                navigatorDrag.value = null;
              },
            },
            [
              h(
                'svg',
                {
                  class: 'vibe-navigator-svg',
                  viewBox: '0 0 1200 42',
                  preserveAspectRatio: 'none',
                },
                [
                  h('rect', { x: 0, y: 7, width: 1200, height: 28, class: 'vibe-navigator-bg' }),
                  ...navigatorSeries.value.map((series) =>
                    h('polyline', {
                      points: navigatorPathFor(series),
                      class: 'vibe-navigator-line',
                      stroke: series.color,
                    }),
                  ),
                ],
              ),
              h(
                'div',
                {
                  class: 'vibe-navigator-selection',
                  style: {
                    left: `${(start.value / Math.max(last.value, 1)) * 100}%`,
                    width: `${((end.value - start.value) / Math.max(last.value, 1)) * 100}%`,
                  },
                  onPointerdown: (event: PointerEvent) => beginNavigatorDrag(event, 'window'),
                },
                [
                  h('button', {
                    type: 'button',
                    class: 'vibe-navigator-handle is-start',
                    'aria-label': '调整起始时间',
                    onPointerdown: (event: PointerEvent) => beginNavigatorDrag(event, 'start'),
                  }),
                  h('button', {
                    type: 'button',
                    class: 'vibe-navigator-handle is-end',
                    'aria-label': '调整结束时间',
                    onPointerdown: (event: PointerEvent) => beginNavigatorDrag(event, 'end'),
                  }),
                ],
              ),
              h(
                'button',
                {
                  type: 'button',
                  class: 'vibe-navigator-all',
                  onClick: () => {
                    start.value = 0;
                    end.value = last.value;
                  },
                  title: '显示全部时间',
                },
                '全部',
              ),
            ],
          ),
        ]);
    },
  });
</script>

<style scoped>
  .vibe-trend-charts {
    display: grid;
    gap: 14px;
  }

  .vibe-time-chart {
    padding: 10px;
    border: 1px solid var(--strategy-border);
    border-radius: 9px;
    background: var(--strategy-surface-2);
  }

  .vibe-chart-head {
    display: flex;
    justify-content: center;
  }

  .vibe-chart-head h3 {
    margin: 4px 0 8px;
    color: var(--strategy-text-1);
    font-size: 18px;
    font-weight: 720;
    text-align: center;
  }

  .vibe-chart-subtitle {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 4px 4px 6px;
    padding: 7px 12px;
    border: 1px solid var(--strategy-border);
    border-radius: 4px;
    background: var(--strategy-surface);
    font-size: 12px;
    gap: 12px;
  }

  .vibe-sub-left {
    display: flex;
    gap: 14px;
    flex-wrap: wrap;
    align-items: center;
    color: var(--strategy-text-3);
  }

  .vibe-chart-legend {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }

  .vibe-legend-btn {
    padding: 3px 8px;
    border: 1px solid var(--strategy-border);
    border-radius: 4px;
    background: var(--strategy-surface-2);
    color: var(--strategy-text-2);
    font-size: 12px;
    cursor: pointer;
  }

  .vibe-legend-btn span {
    display: inline-block;
    width: 10px;
    height: 10px;
    margin-right: 5px;
    border: 1px solid #0004;
    vertical-align: middle;
  }

  .vibe-legend-btn.off {
    opacity: 0.4;
    text-decoration: line-through;
  }

  .vibe-right-label {
    color: var(--strategy-down);
    font-weight: 720;
  }

  .vibe-chart-stage {
    position: relative;
    overflow: auto;
  }

  .vibe-chart-svg {
    display: block;
    width: 100%;
    min-width: 720px;
    height: auto;
    border: 0;
    outline: 0;
    background: transparent;
    box-shadow: none;
  }

  .vibe-chart-grid {
    stroke-dasharray: 3 4;
    stroke: var(--strategy-border);
    fill: none;
  }

  .vibe-axis-label {
    fill: var(--strategy-text-4);
    font-size: 11px;
  }

  .vibe-chart-line {
    stroke-width: 2.2;
    fill: none;
  }

  .vibe-chart-tooltip {
    position: absolute;
    z-index: 5;
    top: 10px;
    left: 12px;
    min-width: 180px;
    padding: 8px 10px;
    border: 1px solid var(--strategy-border);
    border-radius: 7px;
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-soft);
    font-size: 12px;
    pointer-events: none;
  }

  .vibe-navigator {
    display: none;
  }

  .vibe-navigator-svg {
    position: absolute;
    inset: 3px 8px;
    display: block;
    width: calc(100% - 16px);
    height: 42px;
    overflow: visible;
  }

  .vibe-navigator-bg {
    fill: color-mix(in srgb, var(--strategy-surface-2) 88%, #94a3b8 12%);
  }

  .vibe-navigator-line {
    fill: none;
    stroke-width: 1.5;
    opacity: 0.6;
  }

  .vibe-navigator-selection {
    position: absolute;
    top: 3px;
    bottom: 3px;
    min-width: 10px;
    border: 1px solid var(--strategy-accent-strong);
    background: color-mix(in srgb, var(--strategy-accent-soft) 22%, transparent);
    cursor: grab;
  }

  .vibe-navigator-selection:active {
    cursor: grabbing;
  }

  .vibe-navigator-handle {
    position: absolute;
    top: -1px;
    bottom: -1px;
    width: 7px;
    padding: 0;
    border: 1px solid var(--strategy-accent-strong);
    border-radius: 2px;
    background: var(--strategy-surface);
    cursor: ew-resize;
  }

  .vibe-navigator-handle::after {
    display: block;
    width: 1px;
    height: 16px;
    margin: auto;
    background: var(--strategy-accent-strong);
    content: '';
  }

  .vibe-navigator-handle.is-start {
    left: -5px;
  }

  .vibe-navigator-handle.is-end {
    right: -5px;
  }

  .vibe-navigator-all {
    position: absolute;
    right: 10px;
    bottom: 5px;
    padding: 1px 5px;
    border: 1px solid var(--strategy-border);
    border-radius: 3px;
    background: var(--strategy-surface);
    color: var(--strategy-text-3);
    font-size: 10px;
    cursor: pointer;
  }

  /* VibeTimeChart is rendered with h() instead of the SFC template, so keep
     the chart primitives explicitly scoped through the host wrapper as well.
     This also removes the browser's default black range track/border. */
  .vibe-trend-charts :deep(.vibe-chart-svg),
  .vibe-trend-charts :deep(.vibe-chart-stage),
  .vibe-trend-charts :deep(.vibe-navigator) {
    border: 0;
    outline: 0;
    box-shadow: none;
  }

  .vibe-trend-charts :deep(.vibe-chart-svg) {
    background: transparent;
  }

  /* VibeTimeChart is a runtime child component. Scoped selectors on this SFC
     do not reach its internal nodes, so every interactive navigator primitive
     must be explicitly deep-scoped instead of falling back to browser defaults. */
  .vibe-trend-charts :deep(.vibe-time-chart) {
    padding: 10px;
    border: 1px solid var(--strategy-border);
    border-radius: 9px;
    background: var(--strategy-surface-2);
  }

  .vibe-trend-charts :deep(.vibe-chart-head) {
    display: flex;
    justify-content: center;
  }

  .vibe-trend-charts :deep(.vibe-chart-head h3) {
    margin: 4px 0 8px;
    color: var(--strategy-text-1);
    font-size: 18px;
    font-weight: 720;
    text-align: center;
  }

  .vibe-trend-charts :deep(.vibe-chart-subtitle) {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 4px 4px 6px;
    padding: 7px 12px;
    border: 1px solid var(--strategy-border);
    border-radius: 4px;
    background: var(--strategy-surface);
    font-size: 12px;
    gap: 12px;
  }

  .vibe-trend-charts :deep(.vibe-sub-left),
  .vibe-trend-charts :deep(.vibe-chart-legend) {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
  }

  .vibe-trend-charts :deep(.vibe-sub-left) {
    gap: 14px;
    color: var(--strategy-text-3);
  }

  .vibe-trend-charts :deep(.vibe-legend-btn),
  .vibe-trend-charts :deep(.vibe-navigator-all) {
    border: 1px solid var(--strategy-border);
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
    cursor: pointer;
  }

  .vibe-trend-charts :deep(.vibe-legend-btn) {
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 12px;
  }

  .vibe-trend-charts :deep(.vibe-chart-stage) {
    position: relative;
    overflow: auto;
  }

  .vibe-trend-charts :deep(.vibe-axis-label) {
    fill: var(--strategy-text-4);
    font-size: 11px;
  }

  .vibe-trend-charts :deep(.vibe-chart-grid) {
    fill: none;
    stroke: var(--strategy-border);
    stroke-dasharray: 3 4;
  }

  .vibe-trend-charts :deep(.vibe-chart-line) {
    fill: none;
    stroke-width: 2.2;
  }

  .vibe-trend-charts :deep(.vibe-navigator) {
    display: none;
  }

  .vibe-trend-charts :deep(.vibe-navigator-svg) {
    position: absolute;
    inset: 3px 8px;
    display: block;
    width: calc(100% - 16px);
    height: 42px;
    overflow: visible;
  }

  .vibe-trend-charts :deep(.vibe-navigator-bg) {
    fill: color-mix(in srgb, var(--strategy-surface-2) 88%, #94a3b8 12%);
  }

  .vibe-trend-charts :deep(.vibe-navigator-line) {
    fill: none;
    stroke-width: 1.5;
    opacity: 0.6;
  }

  .vibe-trend-charts :deep(.vibe-navigator-selection) {
    position: absolute;
    top: 3px;
    bottom: 3px;
    min-width: 10px;
    border: 1px solid var(--strategy-accent-strong);
    background: color-mix(in srgb, var(--strategy-accent-soft) 22%, transparent);
    cursor: grab;
  }

  .vibe-trend-charts :deep(.vibe-navigator-handle) {
    position: absolute;
    top: -1px;
    bottom: -1px;
    width: 7px;
    padding: 0;
    border: 1px solid var(--strategy-accent-strong);
    border-radius: 2px;
    background: var(--strategy-surface);
    cursor: ew-resize;
  }

  .vibe-trend-charts :deep(.vibe-navigator-handle::after) {
    display: block;
    width: 1px;
    height: 16px;
    margin: auto;
    background: var(--strategy-accent-strong);
    content: '';
  }

  .vibe-trend-charts :deep(.vibe-navigator-handle.is-start) {
    left: -5px;
  }

  .vibe-trend-charts :deep(.vibe-navigator-handle.is-end) {
    right: -5px;
  }

  .vibe-trend-charts :deep(.vibe-navigator-all) {
    position: absolute;
    right: 10px;
    bottom: 5px;
    padding: 1px 5px;
    border-radius: 3px;
    color: var(--strategy-text-3);
    font-size: 10px;
  }
</style>
