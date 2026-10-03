import { defineComponent, h, onMounted, type PropType, ref, shallowRef } from 'vue';

import {
  getCommodityDashboardV1,
  getCryptoDashboardV1,
  getMacroDashboardV1,
  type MacroDashboardSeries,
} from '@/api/hedgeResearch';

const WIDTH = 960;
const HEIGHT = 320;
const PADDING = { left: 58, right: 90, top: 24, bottom: 38 };
const COLORS = ['#165dff', '#0f8b6d', '#c7931a', '#7c3aed', '#dc2626', '#64748b'];
const controlStyle = {
  border: '1px solid #dbe4ea',
  borderRadius: '7px',
  padding: '5px 10px',
  background: '#fff',
  fontSize: '12px',
  lineHeight: '18px',
  cursor: 'pointer',
};

interface ChartPoint {
  date: string;
  time: number;
  value: number | null;
}

function seriesPoints(series: MacroDashboardSeries, years: number): ChartPoint[] {
  const cutoff = Date.now() - years * 366 * 24 * 60 * 60 * 1000;
  return series.observations
    .map((item) => ({
      date: item.date,
      time: Date.parse(item.date),
      value: item.value === null ? null : Number(item.value),
    }))
    .filter(
      (item) =>
        Number.isFinite(item.time) &&
        (item.value === null || Number.isFinite(item.value)) &&
        item.time >= cutoff,
    );
}

export default defineComponent({
  name: 'MacroSeriesChart',
  props: {
    groupId: { type: String, required: true },
    presentation: { type: String as PropType<'time' | 'distribution'>, default: 'time' },
    years: { type: Number, default: 5 },
    unitLabel: { type: String, default: '' },
    preferredSeriesIds: { type: Array as PropType<string[]>, default: () => [] },
    dataDomain: { type: String as PropType<'macro' | 'commodity' | 'crypto'>, default: 'macro' },
  },
  setup(props) {
    const selectedYears = ref(props.years);
    const search = ref('');
    const tableView = ref(false);
    const series = shallowRef<MacroDashboardSeries[]>([]);
    const status = ref<'loading' | 'ready' | 'error'>('loading');

    onMounted(async () => {
      try {
        const loader =
          props.dataDomain === 'commodity'
            ? getCommodityDashboardV1
            : props.dataDomain === 'crypto'
            ? getCryptoDashboardV1
            : getMacroDashboardV1;
        const dashboard = await loader();
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
      if (status.value === 'loading') return h('div', { class: 'local-empty' }, '正在加载数据…');
      if (status.value === 'error') return h('div', { class: 'local-empty' }, '该组数据暂不可用。');
      if (props.presentation === 'distribution') {
        const rows = series.value.filter((item) =>
          item.label.toLowerCase().includes(search.value.toLowerCase()),
        );
        const maxValue = Math.max(1, ...series.value.map((item) => Number(item.latestValue ?? 0)));
        return h('div', { class: 'local-widget-stack' }, [
          h('div', { class: 'chart-legend' }, [
            h(
              'span',
              `${rows.length} / ${series.value.length} 项 · ${series.value[0]?.source ?? ''}`,
            ),
            h('input', {
              value: search.value,
              placeholder: '筛选项目',
              'aria-label': '筛选项目',
              style: { ...controlStyle, cursor: 'text', minWidth: '160px' },
              onInput: (event: Event) => {
                search.value = (event.target as HTMLInputElement).value;
              },
            }),
          ]),
          h('div', { style: { maxHeight: '330px', overflow: 'auto' } }, [
            h('table', { style: { width: '100%', borderCollapse: 'collapse', fontSize: '12px' } }, [
              h('thead', [
                h(
                  'tr',
                  ['项目', '数量', '观测日期'].map((label) =>
                    h('th', { style: { textAlign: 'left', padding: '6px' } }, label),
                  ),
                ),
              ]),
              h(
                'tbody',
                rows.map((item) =>
                  h('tr', [
                    h(
                      'td',
                      {
                        style: {
                          padding: '6px',
                          background: `linear-gradient(to right, #165dff15 ${
                            (100 * Number(item.latestValue ?? 0)) / maxValue
                          }%, transparent 0)`,
                        },
                      },
                      [
                        h(
                          'a',
                          {
                            href: item.sourceUrl || undefined,
                            target: '_blank',
                            rel: 'noopener noreferrer',
                          },
                          item.label,
                        ),
                      ],
                    ),
                    h(
                      'td',
                      {
                        style: { padding: '6px', whiteSpace: 'nowrap' },
                        title: String(item.latestValue ?? '—'),
                      },
                      item.latestValue === null
                        ? '—'
                        : `${Number(item.latestValue).toLocaleString('en-US', {
                            maximumFractionDigits: 8,
                          })} ${item.unit}`,
                    ),
                    h(
                      'td',
                      { style: { padding: '6px', whiteSpace: 'nowrap' } },
                      `${item.observationDate ?? '—'}${item.isStale ? ' · 待更新' : ''}`,
                    ),
                  ]),
                ),
              ),
            ]),
          ]),
          h(
            'small',
            { style: { color: '#64748b' } },
            series.value.some((item) =>
              item.qualityFlags.includes('observation_date_is_collection_date'),
            )
              ? '日期为本次采集日期，各企业披露时间可能不同；仅覆盖来源列出的企业。'
              : series.value.some((item) =>
                  item.qualityFlags.includes('source_updated_date_not_uniform_holdings_date'),
                )
              ? '日期为来源最后更新日期，各机构披露与核验方式不同；过期数据保留待更新提示。'
              : '按 UTXO 最后移动时价格分桶，不等同于投资者实际买入成本。',
          ),
        ]);
      }
      const plotted = series.value.map((item) => ({
        item,
        points: seriesPoints(item, selectedYears.value),
      }));
      const allPoints = plotted
        .flatMap((item) => item.points)
        .filter((point): point is ChartPoint & { value: number } => point.value !== null);
      if (!allPoints.length) return h('div', { class: 'local-empty' }, '当前窗口没有有效观测。');
      const controls = h('div', { class: 'chart-legend', style: { gap: '12px' } }, [
        ...[1, 3, 5, 10]
          .filter((years) => years <= props.years)
          .map((years) =>
            h(
              'button',
              {
                type: 'button',
                'aria-pressed': selectedYears.value === years,
                style: {
                  ...controlStyle,
                  color: selectedYears.value === years ? '#165dff' : 'inherit',
                  background: selectedYears.value === years ? '#edf4ff' : '#fff',
                },
                onClick: () => {
                  selectedYears.value = years;
                },
              },
              `${years}年`,
            ),
          ),
        h(
          'button',
          {
            type: 'button',
            onClick: () => {
              tableView.value = !tableView.value;
            },
            style: controlStyle,
          },
          tableView.value ? '查看图表' : '查看数据',
        ),
      ]);
      if (tableView.value) {
        const dates = [
          ...new Set(plotted.flatMap(({ points }) => points.map((point) => point.date))),
        ]
          .sort()
          .reverse()
          .slice(0, 90);
        const values = plotted.map(
          ({ points }) => new Map(points.map((point) => [point.date, point.value])),
        );
        return h('div', { class: 'local-widget-stack' }, [
          controls,
          h('div', { style: { overflow: 'auto', maxHeight: '320px' } }, [
            h('table', { style: { width: '100%', textAlign: 'right', fontSize: '12px' } }, [
              h('caption', '所选窗口最近90个观测日；— 表示该来源当日无观测'),
              h('thead', [
                h('tr', [
                  h('th', '日期'),
                  ...plotted.map(({ item }) => h('th', `${item.label} (${item.unit})`)),
                ]),
              ]),
              h(
                'tbody',
                dates.map((date) =>
                  h('tr', [
                    h('td', date),
                    ...values.map((rows) =>
                      h('td', rows.get(date) == null ? '—' : String(rows.get(date))),
                    ),
                  ]),
                ),
              ),
            ]),
          ]),
        ]);
      }
      const minTime = Math.min(...allPoints.map((item) => item.time));
      const maxTime = Math.max(...allPoints.map((item) => item.time));
      const units = [...new Set(plotted.map(({ item }) => item.unit))];
      const scales = new Map(
        units.map((unit) => {
          const values = plotted
            .filter(({ item }) => item.unit === unit)
            .flatMap(({ points }) => points.map((point) => point.value))
            .filter((value): value is number => value !== null);
          const low = values.length ? Math.min(...values) : 0;
          const high = values.length ? Math.max(...values) : 1;
          const pad = Math.max((high - low) * 0.08, Math.abs(high) * 0.001, 1e-10);
          return [unit, { min: low - pad, max: high + pad }];
        }),
      );
      const innerWidth = WIDTH - PADDING.left - PADDING.right;
      const innerHeight = HEIGHT - PADDING.top - PADDING.bottom;
      const x = (time: number) => ((time - minTime) / Math.max(maxTime - minTime, 1)) * innerWidth;
      const y = (value: number, unit = units[0]) => {
        const scale = scales.get(unit)!;
        return ((scale.max - value) / (scale.max - scale.min)) * innerHeight;
      };
      const scale = scales.get(units[0])!;
      const ticks = Array.from(
        { length: 5 },
        (_, index) => scale.min + ((scale.max - scale.min) * index) / 4,
      );
      const format = (value: number) =>
        new Intl.NumberFormat('en-US', {
          maximumFractionDigits: Math.abs(value) < 0.01 ? 10 : 3,
          notation: Math.abs(value) >= 1000000 ? 'compact' : 'standard',
        }).format(value);

      return h('div', { class: 'local-widget-stack' }, [
        controls,
        h(
          'div',
          { class: 'chart-legend' },
          plotted.map(({ item }, index) =>
            h('span', { key: item.seriesId }, [
              h('i', { style: { backgroundColor: COLORS[index % COLORS.length] } }),
              `${item.label} · ${
                item.latestValue === null ? '—' : format(Number(item.latestValue))
              } ${item.unit} · ${item.observationDate ?? '—'}${
                item.isStale ? ' · 数据待更新' : ''
              }`,
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
                    format(tick),
                  ),
                ];
              }),
              ...units.slice(1).flatMap((unit) => {
                const rightScale = scales.get(unit)!;
                return Array.from({ length: 5 }, (_, i) => {
                  const value = rightScale.min + ((rightScale.max - rightScale.min) * i) / 4;
                  return h(
                    'text',
                    { x: innerWidth + 8, y: y(value, unit) + 4, class: 'chart-axis-label' },
                    format(value),
                  );
                });
              }),
              ...plotted.flatMap(({ item, points }, index) => {
                let penDown = false;
                const path = points
                  .map((point) => {
                    if (point.value === null) {
                      penDown = false;
                      return '';
                    }
                    const command = penDown ? 'L' : 'M';
                    penDown = true;
                    return `${command}${x(point.time).toFixed(2)},${y(
                      point.value,
                      item.unit,
                    ).toFixed(2)}`;
                  })
                  .join(' ');
                const last = points.filter((point) => point.value !== null).at(-1);
                return [
                  h('path', {
                    key: item.seriesId,
                    d: path,
                    fill: 'none',
                    stroke: COLORS[index % COLORS.length],
                    strokeWidth: 2.4,
                  }),
                  ...(last
                    ? [
                        h(
                          'circle',
                          {
                            cx: x(last.time),
                            cy: y(last.value!, item.unit),
                            r: 3.5,
                            fill: COLORS[index % COLORS.length],
                          },
                          [h('title', `${item.label} ${last.date}: ${last.value} ${item.unit}`)],
                        ),
                      ]
                    : []),
                ];
              }),
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
                { x: innerWidth / 2, y: -10, textAnchor: 'middle', class: 'chart-axis-label' },
                units.length > 1
                  ? `${units[0]} (左) / ${units[1]} (右)`
                  : props.unitLabel || units[0],
              ),
            ]),
          ]),
        ]),
        h(
          'div',
          { class: 'chart-legend' },
          series.value.map((item) =>
            h(
              'a',
              { href: item.sourceUrl || undefined, target: '_blank', rel: 'noopener noreferrer' },
              `来源：${item.source} · ${item.frequency}${
                item.qualityFlags.includes('upstream_refresh_failed')
                  ? ' · 最近采集失败，保留旧值'
                  : ''
              }`,
            ),
          ),
        ),
      ]);
    };
  },
});
