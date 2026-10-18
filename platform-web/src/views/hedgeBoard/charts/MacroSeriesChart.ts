import { useDashboardRefresh } from '../useDashboardRefresh';
import { defineComponent, h, type PropType, ref, shallowRef } from 'vue';

import {
  getCommodityDashboardV1,
  getCryptoDashboardV1,
  getMacroDashboardV1,
  type MacroDashboardSeries,
} from '@/api/hedgeResearch';

import SourceSeriesPlot from './SourceSeriesPlot.vue';
import { unitText, frequencyText, regionalFlowColor } from './sourceSeriesOptions';

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
  const cutoff = years === 0 ? -Infinity : Date.now() - years * 366 * 24 * 60 * 60 * 1000;
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
    initiallyHiddenSeriesIds: { type: Array as PropType<string[]>, default: () => [] },
    barSeriesIds: { type: Array as PropType<string[]>, default: () => [] },
    presentation: {
      type: String as PropType<
        'time' | 'distribution' | 'curve' | 'regional-stack' | 'gold-drivers'
      >,
      default: 'time',
    },
    years: { type: Number, default: 5 },
    unitLabel: { type: String, default: '' },
    curveValueLabel: { type: String, default: '结算价' },
    preferredSeriesIds: { type: Array as PropType<string[]>, default: () => [] },
    dataDomain: { type: String as PropType<'macro' | 'commodity' | 'crypto'>, default: 'macro' },
  },
  setup(props) {
    const selectedYears = ref(props.presentation === 'gold-drivers' ? 1 : 0);
    const hidden = ref(new Set<string>(props.initiallyHiddenSeriesIds));
    const search = ref('');
    const tableView = ref(false);
    const tablePage = ref(0);
    const series = shallowRef<MacroDashboardSeries[]>([]);
    const status = ref<'loading' | 'ready' | 'error'>('loading');

    useDashboardRefresh(async () => {
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
      if (props.presentation === 'curve') {
        const rows = series.value;
        const values = rows.map((item) =>
          item.latestValue === null ? NaN : Number(item.latestValue),
        );
        if (
          values.some((value) => !Number.isFinite(value)) ||
          values.length < 2 ||
          rows.some((row) => !/^AU\d{4}$/.test(row.label))
        )
          return h('div', { class: 'local-empty' }, '当前期限结构数据不完整。');
        return h('div', { class: 'local-widget-stack' }, [
          h(
            'div',
            { class: 'chart-legend' },
            `${rows[0].observationDate} · 上期所${props.curveValueLabel} · ${
              props.unitLabel || '元/克'
            }${rows.some((item) => item.isStale) ? ' · 待更新' : ''}`,
          ),
          h(SourceSeriesPlot, {
            mode: 'curve',
            series: rows,
            colors: [props.unitLabel === '%' ? '#a14fba' : '#1689a4'],
            unitLabel: props.unitLabel || '元/克',
          }),
          h('details', [
            h('summary', { style: { cursor: 'pointer', fontSize: '12px' } }, '查看合约数据'),
            h('table', { style: { width: '100%', fontSize: '12px', textAlign: 'left' } }, [
              h('thead', [
                h(
                  'tr',
                  [
                    '合约',
                    `${props.curveValueLabel}（${props.unitLabel || '元/克'}）`,
                    '交易日',
                  ].map((label) => h('th', label)),
                ),
              ]),
              h(
                'tbody',
                rows.map((item) =>
                  h('tr', [
                    h('td', item.label),
                    h('td', String(item.latestValue)),
                    h('td', item.observationDate ?? '—'),
                  ]),
                ),
              ),
            ]),
          ]),
        ]);
      }
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
                          background: `linear-gradient(to right, ${
                            Number(item.latestValue) < 0 ? '#dc262615' : '#165dff15'
                          } ${Math.min(
                            100,
                            (100 * Math.abs(Number(item.latestValue ?? 0))) / maxValue,
                          )}%, transparent 0)`,
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
                          })} ${unitText(item.unit)}`,
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
              item.qualityFlags.includes('addresses_not_people_or_entities'),
            )
              ? '按来源余额区间统计地址数量，地址不等于持币人数或独立实体。日期沿用来源报表。'
              : series.value.some((item) =>
                  item.qualityFlags.includes('observation_date_is_collection_date'),
                )
              ? '日期为本次采集日期，各企业披露时间可能不同；仅覆盖来源列出的企业。'
              : series.value.some((item) =>
                  item.qualityFlags.includes('source_updated_date_not_uniform_holdings_date'),
                )
              ? '日期为来源最后更新日期，各机构披露与核验方式不同；过期数据保留待更新提示。'
              : props.groupId === 'wgcReserves'
              ? 'WGC 最新公开季度截面；各国申报存在时滞，— 表示源站尚无数值。国家记录不等于全球储备总量。'
              : props.groupId === 'wgcPurchases'
              ? 'WGC 月报中明确披露的主要国家当月净购买，单位按报告取整；负值为净售出。不含近似值及未披露购买，不代表完整国家覆盖。'
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

      const controls = h('div', { class: 'chart-legend', style: { gap: '12px' } }, [
        ...[0.25, 1, 3, 0]
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
                  tablePage.value = 0;
                },
              },
              years === 0 ? '全部' : years === 0.25 ? '3个月' : `${years}年`,
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
        const allDates = [
          ...new Set(plotted.flatMap(({ points }) => points.map((point) => point.date))),
        ]
          .sort()
          .reverse();
        const dates = allDates.slice(tablePage.value * 40, (tablePage.value + 1) * 40);
        const values = plotted.map(
          ({ item }) => new Map(item.observations.map((point) => [point.date, point.value])),
        );
        return h('div', { class: 'local-widget-stack' }, [
          controls,
          h('div', { style: { overflow: 'auto', maxHeight: '320px' } }, [
            h('table', { style: { width: '100%', textAlign: 'right', fontSize: '12px' } }, [
              h('caption', `${allDates.length} 个观测日 · — 表示缺失`),
              h('thead', [
                h('tr', [
                  h('th', '日期'),
                  ...plotted.map(({ item }) => h('th', `${item.label} (${unitText(item.unit)})`)),
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
          h('div', { class: 'source-table-pages' }, [
            h(
              'button',
              {
                type: 'button',
                style: controlStyle,
                disabled: tablePage.value === 0,
                onClick: () => {
                  tablePage.value -= 1;
                },
              },
              '上一页',
            ),
            h(
              'span',
              `${allDates.length ? tablePage.value + 1 : 0} / ${Math.ceil(allDates.length / 40)}`,
            ),
            h(
              'button',
              {
                type: 'button',
                style: controlStyle,
                disabled: (tablePage.value + 1) * 40 >= allDates.length,
                onClick: () => {
                  tablePage.value += 1;
                },
              },
              '下一页',
            ),
          ]),
        ]);
      }
      const isAggregate = (item: MacroDashboardSeries) =>
        props.presentation === 'regional-stack' && item.seriesId.endsWith('_global');
      const colorFor = (item: MacroDashboardSeries, index: number) =>
        props.presentation === 'regional-stack'
          ? regionalFlowColor(item.seriesId)
          : COLORS[index % COLORS.length];
      const visible = plotted.filter(
        ({ item }) => !isAggregate(item) && !hidden.value.has(item.seriesId),
      );
      const format = (value: number) =>
        new Intl.NumberFormat('en-US', {
          maximumFractionDigits: Math.abs(value) < 0.01 ? 8 : 4,
        }).format(value);

      return h('div', { class: 'local-widget-stack' }, [
        controls,
        h(
          'div',
          { class: 'source-series-summary' },
          plotted.map(({ item }, index) =>
            h(
              isAggregate(item) ? 'div' : 'button',
              {
                key: item.seriesId,
                type: 'button',
                class: 'source-series-legend',
                'aria-pressed': isAggregate(item) ? undefined : !hidden.value.has(item.seriesId),
                disabled: visible.length === 1 && !hidden.value.has(item.seriesId),
                onClick: () => {
                  if (isAggregate(item)) return;
                  const next = new Set(hidden.value);
                  next.has(item.seriesId) ? next.delete(item.seriesId) : next.add(item.seriesId);
                  hidden.value = next;
                },
              },
              [
                h('i', { style: { backgroundColor: colorFor(item, index) } }),
                h('span', { class: 'source-series-summary__name' }, item.label),
                h(
                  'strong',
                  {},
                  `${item.latestValue == null ? '—' : format(Number(item.latestValue))} ${unitText(
                    item.unit,
                  )}`,
                ),
                h(
                  'small',
                  {},
                  `${item.observationDate ?? '—'}${item.isStale ? ' · 数据待更新' : ''}`,
                ),
              ],
            ),
          ),
        ),
        allPoints.length
          ? h(SourceSeriesPlot, {
              series: visible.map(({ item, points }) => {
                const dates = new Set(points.map((point) => point.date));
                return {
                  ...item,
                  observations: item.observations.filter((row) => dates.has(row.date)),
                };
              }),
              barSeriesIds: props.barSeriesIds,
              colors: visible.map(({ item }) => colorFor(item, series.value.indexOf(item))),
              mode:
                props.presentation === 'gold-drivers'
                  ? 'gold-drivers'
                  : props.presentation === 'regional-stack'
                  ? 'regional-stack'
                  : 'time',
              unitLabel: props.unitLabel,
            })
          : h('div', { class: 'local-empty' }, '当前窗口没有观测，可切换其他范围。'),
        h(
          'div',
          { class: 'source-series-footer' },
          [
            ...new Map(
              series.value.map((item) => [`${item.source}|${item.sourceUrl}`, item]),
            ).values(),
          ].map((item) =>
            h(
              'a',
              { href: item.sourceUrl || undefined, target: '_blank', rel: 'noopener noreferrer' },
              `来源：${item.source} · ${frequencyText(item.frequency)}${
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
