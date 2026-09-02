import { defineComponent, h, onMounted, type PropType, ref } from 'vue';

import {
  getCommodityDashboardV1,
  getCryptoDashboardV1,
  getMacroDashboardV1,
  type MacroDashboardSeries,
} from '@/api/hedgeResearch';

const WIDTH = 960;
const HEIGHT = 320;
const PADDING = { left: 58, right: 24, top: 24, bottom: 38 };
const COLORS = ['#165dff', '#0f8b6d', '#c7931a', '#7c3aed', '#dc2626', '#64748b'];

interface ChartPoint {
  date: string;
  time: number;
  value: number;
}

function seriesPoints(series: MacroDashboardSeries, years: number): ChartPoint[] {
  const cutoff = Date.now() - years * 366 * 24 * 60 * 60 * 1000;
  return series.observations
    .map((item) => ({ date: item.date, time: Date.parse(item.date), value: Number(item.value) }))
    .filter(
      (item) => Number.isFinite(item.time) && Number.isFinite(item.value) && item.time >= cutoff,
    );
}

export default defineComponent({
  name: 'MacroSeriesChart',
  props: {
    groupId: { type: String, required: true },
    years: { type: Number, default: 5 },
    unitLabel: { type: String, default: '' },
    preferredSeriesIds: { type: Array as PropType<string[]>, default: () => [] },
    dataDomain: { type: String as PropType<'macro' | 'commodity' | 'crypto'>, default: 'macro' },
  },
  setup(props) {
    const series = ref<MacroDashboardSeries[]>([]);
    const status = ref<'loading' | 'ready' | 'error'>('loading');

    onMounted(async () => {
      try {
        const dashboard = await (props.dataDomain === 'commodity'
          ? getCommodityDashboardV1
          : props.dataDomain === 'crypto'
          ? getCryptoDashboardV1
          : getMacroDashboardV1)();
        const group = dashboard.groups[props.groupId] ?? [];
        series.value = props.preferredSeriesIds.length
          ? props.preferredSeriesIds
              .map((id) => group.find((item) => item.seriesId === id))
              .filter((item): item is MacroDashboardSeries => Boolean(item))
          : group;
        status.value = series.value.length ? 'ready' : 'error';
      } catch (error) {
        console.warn('[hedgeBoard] dashboard group unavailable', props.groupId, error);
        status.value = 'error';
      }
    });

    return () => {
      if (status.value === 'loading')
        return h('div', { class: 'local-empty' }, '正在加载官方宏观数据…');
      if (status.value === 'error')
        return h('div', { class: 'local-empty' }, '该组官方数据暂不可用。');
      const plotted = series.value.map((item) => ({
        item,
        points: seriesPoints(item, props.years),
      }));
      const allPoints = plotted.flatMap((item) => item.points);
      if (!allPoints.length) return h('div', { class: 'local-empty' }, '当前窗口没有有效观测。');
      const minTime = Math.min(...allPoints.map((item) => item.time));
      const maxTime = Math.max(...allPoints.map((item) => item.time));
      const rawMin = Math.min(...allPoints.map((item) => item.value));
      const rawMax = Math.max(...allPoints.map((item) => item.value));
      const pad = Math.max((rawMax - rawMin) * 0.08, 0.1);
      const minValue = rawMin - pad;
      const maxValue = rawMax + pad;
      const innerWidth = WIDTH - PADDING.left - PADDING.right;
      const innerHeight = HEIGHT - PADDING.top - PADDING.bottom;
      const x = (time: number) => ((time - minTime) / Math.max(maxTime - minTime, 1)) * innerWidth;
      const y = (value: number) =>
        ((maxValue - value) / Math.max(maxValue - minValue, 0.01)) * innerHeight;
      const ticks = Array.from(
        { length: 5 },
        (_, index) => minValue + ((maxValue - minValue) * index) / 4,
      );

      return h('div', { class: 'local-widget-stack' }, [
        h(
          'div',
          { class: 'chart-legend' },
          plotted.map(({ item }, index) =>
            h('span', { key: item.seriesId }, [
              h('i', { style: { backgroundColor: COLORS[index % COLORS.length] } }),
              `${item.label} · ${item.observationDate ?? '—'}${item.isStale ? ' · stale' : ''}`,
            ]),
          ),
        ),
        h('div', { class: 'chart-shell' }, [
          h('svg', { viewBox: `0 0 ${WIDTH} ${HEIGHT}`, class: 'local-chart-svg', role: 'img' }, [
            h('g', { transform: `translate(${PADDING.left},${PADDING.top})` }, [
              ...ticks.flatMap((tick) => {
                const tickY = y(tick);
                return [
                  h('line', {
                    x1: 0,
                    x2: innerWidth,
                    y1: tickY,
                    y2: tickY,
                    class: 'chart-grid-line',
                  }),
                  h(
                    'text',
                    { x: -10, y: tickY + 4, textAnchor: 'end', class: 'chart-axis-label' },
                    tick.toFixed(2),
                  ),
                ];
              }),
              ...plotted.map(({ item, points }, index) =>
                h('path', {
                  key: item.seriesId,
                  d: points
                    .map(
                      (point, pointIndex) =>
                        `${pointIndex ? 'L' : 'M'}${x(point.time).toFixed(2)},${y(
                          point.value,
                        ).toFixed(2)}`,
                    )
                    .join(' '),
                  fill: 'none',
                  stroke: COLORS[index % COLORS.length],
                  strokeWidth: 2.4,
                  strokeLinecap: 'round',
                  strokeLinejoin: 'round',
                }),
              ),
              h(
                'text',
                { x: 0, y: innerHeight + 28, class: 'chart-axis-label' },
                new Date(minTime).toISOString().slice(0, 10),
              ),
              h(
                'text',
                {
                  x: innerWidth,
                  y: innerHeight + 28,
                  textAnchor: 'end',
                  class: 'chart-axis-label',
                },
                new Date(maxTime).toISOString().slice(0, 10),
              ),
              h(
                'text',
                { x: innerWidth, y: 0, textAnchor: 'end', class: 'chart-axis-label' },
                props.unitLabel,
              ),
            ]),
          ]),
        ]),
      ]);
    };
  },
});
