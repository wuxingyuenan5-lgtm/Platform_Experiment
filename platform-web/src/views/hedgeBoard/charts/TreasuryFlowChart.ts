import { defineComponent, h, ref, watch } from 'vue';

import {
  BTC_TREASURY_FLOW_ROWS,
  CHART_HEIGHT,
  CHART_PADDING,
  CHART_WIDTH,
  formatAxis,
  getRange,
  makeTicks,
  renderDateLabels,
  scaleX,
  scaleY,
} from './chartCore';
import { renderChartRangeSelector } from './chartRange';

export default defineComponent({
  name: 'TreasuryFlowChart',
  setup() {
    const startIndex = ref(0);
    const endIndex = ref(0);
    const windowSize = 4;

    watch(
      () => BTC_TREASURY_FLOW_ROWS.length,
      () => {
        const minSpan = Math.max(
          2,
          Math.min(windowSize, BTC_TREASURY_FLOW_ROWS.length || windowSize),
        );
        const maxIndex = Math.max(0, BTC_TREASURY_FLOW_ROWS.length - 1);
        if (maxIndex < minSpan - 1) {
          startIndex.value = 0;
          endIndex.value = maxIndex;
          return;
        }
        if (endIndex.value <= 0) endIndex.value = Math.min(maxIndex, minSpan - 1);
        if (endIndex.value > maxIndex) endIndex.value = maxIndex;
        if (startIndex.value > endIndex.value - (minSpan - 1)) {
          startIndex.value = Math.max(0, endIndex.value - (minSpan - 1));
        }
        if (endIndex.value < startIndex.value + (minSpan - 1)) {
          endIndex.value = Math.min(maxIndex, startIndex.value + (minSpan - 1));
        }
      },
      { immediate: true },
    );

    return () => {
      const minSpan = Math.max(
        2,
        Math.min(windowSize, BTC_TREASURY_FLOW_ROWS.length || windowSize),
      );
      const rows =
        BTC_TREASURY_FLOW_ROWS.length > minSpan
          ? BTC_TREASURY_FLOW_ROWS.slice(startIndex.value, endIndex.value + 1)
          : BTC_TREASURY_FLOW_ROWS;
      const series = [
        { key: 'listed', label: '上市公司', color: '#356df3' },
        { key: 'private', label: '私营财库', color: '#6d93ad' },
        { key: 'funds', label: '基金 / 信托', color: '#9cb0c5' },
      ] as const;
      const allValues = rows.flatMap((row) => series.map((item) => Number(row[item.key])));
      const range = getRange(allValues);
      const innerWidth = CHART_WIDTH - CHART_PADDING.left - CHART_PADDING.right;
      const innerHeight = CHART_HEIGHT - CHART_PADDING.top - CHART_PADDING.bottom;
      const groupWidth = innerWidth / Math.max(rows.length, 1);
      const singleBarWidth = Math.min(26, Math.max(12, groupWidth / 4.2));
      const baseY = scaleY(0, Math.min(0, range.min), range.max, innerHeight);

      return h('div', { class: 'local-widget-stack' }, [
        h('div', { class: 'treasury-kpi' }, [
          h('span', '上市公司私营财库基金 / 信托'),
          h('strong', '40.43'),
        ]),
        h('div', { class: 'chart-topline' }, [
          h('div', { class: 'chart-axis-head' }, [h('span', '净流入（千枚 BTC）'), h('span', '')]),
          h(
            'div',
            { class: 'chart-legend' },
            series.map((item) =>
              h('span', [h('i', { style: { backgroundColor: item.color } }), item.label]),
            ),
          ),
        ]),
        h('div', { class: 'chart-shell' }, [
          h('svg', { viewBox: `0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`, class: 'local-chart-svg' }, [
            h('g', { transform: `translate(${CHART_PADDING.left},${CHART_PADDING.top})` }, [
              ...makeTicks(Math.min(0, range.min), range.max, 4).flatMap((tick) => {
                const y = scaleY(tick, Math.min(0, range.min), range.max, innerHeight);
                return [
                  h('line', { x1: 0, x2: innerWidth, y1: y, y2: y, class: 'chart-grid-line' }),
                  h(
                    'text',
                    { x: -12, y: y + 4, textAnchor: 'end', class: 'chart-axis-label' },
                    formatAxis(tick),
                  ),
                ];
              }),
              h('line', { x1: 0, x2: innerWidth, y1: baseY, y2: baseY, class: 'chart-zero-line' }),
              ...rows.flatMap((row, rowIndex) => {
                const centerX = scaleX(rowIndex, rows.length, innerWidth);
                return series.map((item, seriesIndex) => {
                  const value = Number(row[item.key]);
                  const x = centerX - singleBarWidth * 1.45 + seriesIndex * (singleBarWidth + 4);
                  const y = scaleY(value, Math.min(0, range.min), range.max, innerHeight);
                  return h('rect', {
                    x,
                    y: value >= 0 ? y : baseY,
                    width: singleBarWidth,
                    height: Math.max(1, Math.abs(baseY - y)),
                    rx: 3,
                    fill: item.color,
                    opacity: 0.94,
                  });
                });
              }),
              ...renderDateLabels(
                rows.map((row) => ({ date: String(row.date), left: 0, right: 0 })),
                innerWidth,
                innerHeight,
              ),
            ]),
          ]),
        ]),
        BTC_TREASURY_FLOW_ROWS.length > minSpan
          ? renderChartRangeSelector({
              labels: BTC_TREASURY_FLOW_ROWS.map((row) => String(row.date)),
              values: BTC_TREASURY_FLOW_ROWS.map(
                (row) => Number(row.listed) + Number(row.private) + Number(row.funds),
              ),
              startIndex: startIndex.value,
              endIndex: endIndex.value,
              minWindowSize: minSpan,
              onStartChange: (value) => (startIndex.value = value),
              onEndChange: (value) => (endIndex.value = value),
            })
          : null,
      ]);
    };
  },
});
