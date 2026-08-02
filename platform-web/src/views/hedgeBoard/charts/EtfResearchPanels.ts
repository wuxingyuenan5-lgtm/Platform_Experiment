import { defineComponent, h } from 'vue';

import { marketData } from '../nativeData/generated/marketData';
import {
  buildLinePath,
  buildWeeklyFlowRows,
  CHART_PADDING,
  CHART_WIDTH,
  formatAxis,
  formatSigned,
  getRange,
  makeTicks,
  regionLabel,
  renderDateLabels,
  scaleX,
  scaleY,
} from './chartCore';

export const EtfWeeklyFlowsPanel = defineComponent({
  name: 'EtfWeeklyFlowsPanel',
  setup() {
    return () => {
      const rows = buildWeeklyFlowRows();
      const panelHeight = 340;
      const innerWidth = CHART_WIDTH - CHART_PADDING.left - CHART_PADDING.right;
      const innerHeight = panelHeight - CHART_PADDING.top - CHART_PADDING.bottom;
      const flowValues = rows.flatMap((row) => {
        const positive = [row.northAmerica, row.europe, row.asia, row.other].filter(
          (value) => value > 0,
        );
        const negative = [row.northAmerica, row.europe, row.asia, row.other].filter(
          (value) => value < 0,
        );
        return [
          positive.reduce((sum, value) => sum + value, 0),
          negative.reduce((sum, value) => sum + value, 0),
        ];
      });
      const flowRange = getRange(flowValues, true);
      const goldRange = getRange(rows.map((row) => row.goldPrice));
      const zeroY = scaleY(0, flowRange.min, flowRange.max, innerHeight);
      const groupWidth = innerWidth / Math.max(rows.length, 1);
      const flowTicks = makeTicks(flowRange.min, flowRange.max, 4);
      const goldTicks = makeTicks(goldRange.min, goldRange.max, 4);
      const series = [
        { key: 'northAmerica', label: '北美', color: marketData.etf.regionColors['North America'] },
        { key: 'europe', label: '欧洲', color: marketData.etf.regionColors.Europe },
        { key: 'asia', label: '亚洲', color: marketData.etf.regionColors.Asia },
        { key: 'other', label: '其他', color: marketData.etf.regionColors.Other },
      ] as const;
      const barWidth = Math.max(14, groupWidth * 0.58);
      const goldPath = buildLinePath(
        rows.map((row) => ({ date: row.date, left: 0, right: row.goldPrice })),
        (_row, index) => scaleX(index, rows.length, innerWidth),
        (row) => scaleY(row.right, goldRange.min, goldRange.max, innerHeight),
      );

      return h('div', { class: 'local-widget-stack etf-weekly-panel' }, [
        h('div', { class: 'etf-weekly-panel__toolbar' }, [
          h('div', { class: 'etf-weekly-panel__toggle' }, [
            h('button', { type: 'button', class: 'is-active' }, '吨'),
            h('button', { type: 'button' }, '美元'),
          ]),
          h('div', { class: 'etf-weekly-panel__actions' }, [
            h('div', { class: 'etf-weekly-panel__periods' }, [
              h('button', { type: 'button' }, '每年'),
              h('button', { type: 'button' }, '季度'),
              h('button', { type: 'button' }, '每月'),
              h('button', { type: 'button', class: 'is-active' }, '每周'),
            ]),
          ]),
        ]),
        h('div', { class: 'etf-weekly-panel__axis-head' }, [
          h('span', '需求（吨）'),
          h('span', '黄金（美元/盎司）'),
        ]),
        h(
          'div',
          {
            class: 'chart-shell chart-shell--etf-weekly',
            style: {
              position: 'relative',
              paddingTop: '8px',
              borderRadius: 0,
              borderLeft: 'none',
              borderRight: 'none',
              borderBottom: 'none',
              background: 'transparent',
            },
          },
          [
            h(
              'svg',
              {
                viewBox: `0 0 ${CHART_WIDTH} ${panelHeight}`,
                class: 'local-chart-svg',
                role: 'img',
              },
              [
                h('g', { transform: `translate(${CHART_PADDING.left},${CHART_PADDING.top})` }, [
                  ...flowTicks.flatMap((tick) => {
                    const y = scaleY(tick, flowRange.min, flowRange.max, innerHeight);
                    return [
                      h('line', {
                        key: `flow-grid-${tick}`,
                        x1: 0,
                        x2: innerWidth,
                        y1: y,
                        y2: y,
                        class: 'chart-grid-line',
                      }),
                      h(
                        'text',
                        {
                          key: `flow-axis-${tick}`,
                          x: -12,
                          y: y + 4,
                          textAnchor: 'end',
                          class: 'chart-axis-label',
                        },
                        formatAxis(tick),
                      ),
                    ];
                  }),
                  h('line', {
                    x1: 0,
                    x2: innerWidth,
                    y1: zeroY,
                    y2: zeroY,
                    class: 'chart-zero-line',
                  }),
                  ...goldTicks.map((tick) =>
                    h(
                      'text',
                      {
                        key: `gold-axis-${tick}`,
                        x: innerWidth + 12,
                        y: scaleY(tick, goldRange.min, goldRange.max, innerHeight) + 4,
                        textAnchor: 'start',
                        class: 'chart-axis-label',
                      },
                      formatAxis(tick),
                    ),
                  ),
                  ...rows.flatMap((row, rowIndex) => {
                    let positiveOffset = zeroY;
                    let negativeOffset = zeroY;
                    const centerX = rowIndex * groupWidth + groupWidth / 2;
                    return series.map((item) => {
                      const raw = row[item.key];
                      const barHeight = Math.abs(
                        scaleY(raw, flowRange.min, flowRange.max, innerHeight) - zeroY,
                      );
                      if (raw >= 0) {
                        positiveOffset -= barHeight;
                        return h('rect', {
                          key: `${row.date}-${item.key}`,
                          x: centerX - barWidth / 2,
                          y: positiveOffset,
                          width: barWidth,
                          height: Math.max(barHeight, 1),
                          rx: 3,
                          fill: item.color,
                          opacity: 0.92,
                        });
                      }
                      const currentY = negativeOffset;
                      negativeOffset += barHeight;
                      return h('rect', {
                        key: `${row.date}-${item.key}`,
                        x: centerX - barWidth / 2,
                        y: currentY,
                        width: barWidth,
                        height: Math.max(barHeight, 1),
                        rx: 3,
                        fill: item.color,
                        opacity: 0.92,
                      });
                    });
                  }),
                  h('path', {
                    d: goldPath,
                    fill: 'none',
                    stroke: '#d3a13a',
                    strokeWidth: 2.5,
                    strokeLinecap: 'round',
                  }),
                  ...renderDateLabels(
                    rows.map((row) => ({ date: row.date, left: 0, right: 0 })),
                    innerWidth,
                    innerHeight,
                  ),
                ]),
              ],
            ),
          ],
        ),
        h('div', { class: 'chart-legend chart-legend--weekly etf-weekly-panel__legend' }, [
          ...series.map((item) =>
            h('span', { key: item.key }, [
              h('i', { style: { backgroundColor: item.color } }),
              item.label,
            ]),
          ),
          h('span', { key: 'gold' }, [
            h('i', { style: { backgroundColor: '#d3a13a' } }),
            '金价（右轴）',
          ]),
        ]),
      ]);
    };
  },
});

export const YtdSummaryPanel = defineComponent({
  name: 'YtdSummaryPanel',
  setup() {
    return () => {
      const asia = marketData.etf.ytdSummary.find((item) => item.region === 'Asia');
      return h('div', { class: 'local-widget-stack ytd-module' }, [
        h('div', { class: 'ytd-module__metrics' }, [
          h('article', [h('span', '统计口径'), h('strong', 'Year to Date')]),
          h('article', [h('span', '最新周度'), h('strong', marketData.etf.latestWeek)]),
          h('article', [
            h('span', '亚洲需求'),
            h('strong', `${asia?.demandTonnes?.toFixed(2) ?? '0.00'} 吨`),
          ]),
        ]),
        h('div', { class: 'ytd-module__table' }, [
          h('div', { class: 'ytd-module__table-head' }, [
            h('span', '地区'),
            h('span', '年内流量'),
            h('span', '持仓吨数'),
            h('span', '需求吨数'),
          ]),
          ...marketData.etf.ytdSummary.map((item) =>
            h('div', { key: item.region, class: 'ytd-module__table-row' }, [
              h('strong', regionLabel(item.region)),
              h('span', `${formatSigned(item.flowUsdMn)} 百万美元`),
              h('span', `${item.holdingsTonnes.toFixed(2)} 吨`),
              h('span', `${formatSigned(item.demandTonnes)} 吨`),
            ]),
          ),
        ]),
      ]);
    };
  },
});
