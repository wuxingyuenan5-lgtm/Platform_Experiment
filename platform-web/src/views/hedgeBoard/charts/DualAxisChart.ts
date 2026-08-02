import { defineComponent, h, type PropType, ref, watch } from 'vue';

import MetricStrip from '../components/MetricStrip';
import {
  buildLinePath,
  CHART_HEIGHT,
  CHART_PADDING,
  CHART_WIDTH,
  formatAxis,
  formatNumber,
  getRange,
  makeTicks,
  renderDateLabels,
  scaleX,
  scaleY,
  type DualChartRow,
} from './chartCore';
import { renderChartRangeSelector } from './chartRange';

export default defineComponent({
  name: 'DualAxisChart',
  props: {
    rows: { type: Array as PropType<DualChartRow[]>, required: true },
    leftLabel: { type: String, required: true },
    rightLabel: { type: String, required: true },
    leftUnit: { type: String, required: true },
    rightUnit: { type: String, required: true },
    leftColor: { type: String, required: true },
    rightColor: { type: String, required: true },
    barPositiveColor: { type: String, default: '' },
    barNegativeColor: { type: String, default: '' },
    barWidthRatio: { type: Number, default: 0.78 },
    leftAsBars: { type: Boolean, default: false },
    divergingBars: { type: Boolean, default: false },
    showRangeSlider: { type: Boolean, default: false },
    windowSize: { type: Number, default: 8 },
  },
  setup(props) {
    const startIndex = ref(0);
    const endIndex = ref(0);

    watch(
      () => [props.rows.length, props.windowSize, props.showRangeSlider],
      () => {
        const minSpan = Math.max(
          2,
          Math.min(props.windowSize, props.rows.length || props.windowSize),
        );
        const maxIndex = Math.max(0, props.rows.length - 1);
        if (!props.showRangeSlider || maxIndex < minSpan - 1) {
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
      const minSpan = props.showRangeSlider
        ? Math.max(2, Math.min(props.windowSize, props.rows.length || props.windowSize))
        : props.rows.length;
      const visibleRows =
        props.showRangeSlider && props.rows.length > minSpan
          ? props.rows.slice(startIndex.value, endIndex.value + 1)
          : props.rows;
      const innerWidth = CHART_WIDTH - CHART_PADDING.left - CHART_PADDING.right;
      const innerHeight = CHART_HEIGHT - CHART_PADDING.top - CHART_PADDING.bottom;
      const leftRange = getRange(
        visibleRows.map((row) => row.left),
        props.divergingBars,
      );
      const rightRange = getRange(visibleRows.map((row) => row.right));
      const zeroY = scaleY(0, leftRange.min, leftRange.max, innerHeight);
      const leftLinePath = props.leftAsBars
        ? ''
        : buildLinePath(
            visibleRows,
            (_row, index) => scaleX(index, visibleRows.length, innerWidth),
            (row) => scaleY(row.left, leftRange.min, leftRange.max, innerHeight),
          );
      const rightLinePath = buildLinePath(
        visibleRows,
        (_row, index) => scaleX(index, visibleRows.length, innerWidth),
        (row) => scaleY(row.right, rightRange.min, rightRange.max, innerHeight),
      );
      const leftTicks = makeTicks(leftRange.min, leftRange.max, 4);
      const rightTicks = makeTicks(rightRange.min, rightRange.max, 4);
      const barWidth = Math.max(
        8,
        (innerWidth / Math.max(visibleRows.length, 1) - 10) * props.barWidthRatio,
      );

      return h('div', { class: 'local-widget-stack' }, [
        h(MetricStrip, {
          metrics: [
            [props.leftLabel, `${formatNumber(visibleRows.at(-1)?.left ?? 0)} ${props.leftUnit}`],
            [
              props.rightLabel,
              `${formatNumber(visibleRows.at(-1)?.right ?? 0)} ${props.rightUnit}`,
            ],
            ['更新', visibleRows.at(-1)?.date ?? '-'],
          ],
        }),
        h('div', { class: 'chart-topline' }, [
          h('div', { class: 'chart-axis-head' }, [
            h('span', `${props.leftLabel}（${props.leftUnit}）`),
            h('span', `${props.rightLabel}（${props.rightUnit}）`),
          ]),
          h('div', { class: 'chart-legend' }, [
            h('span', [h('i', { style: { backgroundColor: props.leftColor } }), props.leftLabel]),
            h('span', [h('i', { style: { backgroundColor: props.rightColor } }), props.rightLabel]),
          ]),
        ]),
        h('div', { class: 'chart-shell' }, [
          h(
            'svg',
            { viewBox: `0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`, class: 'local-chart-svg', role: 'img' },
            [
              h('g', { transform: `translate(${CHART_PADDING.left},${CHART_PADDING.top})` }, [
                ...leftTicks.flatMap((tick) => {
                  const y = scaleY(tick, leftRange.min, leftRange.max, innerHeight);
                  return [
                    h('line', {
                      key: `left-line-${tick}`,
                      x1: 0,
                      x2: innerWidth,
                      y1: y,
                      y2: y,
                      class: 'chart-grid-line',
                    }),
                    h(
                      'text',
                      {
                        key: `left-text-${tick}`,
                        x: -12,
                        y: y + 4,
                        textAnchor: 'end',
                        class: 'chart-axis-label',
                      },
                      formatAxis(tick),
                    ),
                  ];
                }),
                h('line', { x1: 0, x2: innerWidth, y1: zeroY, y2: zeroY, class: 'chart-zero-line' }),
                ...rightTicks.map((tick) =>
                  h(
                    'text',
                    {
                      key: `right-${tick}`,
                      x: innerWidth + 12,
                      y: scaleY(tick, rightRange.min, rightRange.max, innerHeight) + 4,
                      textAnchor: 'start',
                      class: 'chart-axis-label',
                    },
                    formatAxis(tick),
                  ),
                ),
                props.leftAsBars
                  ? h(
                      'g',
                      visibleRows.map((row, index) => {
                        const y = scaleY(row.left, leftRange.min, leftRange.max, innerHeight);
                        return h('rect', {
                          key: `bar-${row.date}`,
                          x: scaleX(index, visibleRows.length, innerWidth) - barWidth / 2,
                          y: row.left >= 0 ? y : zeroY,
                          width: barWidth,
                          height: Math.max(1, Math.abs(zeroY - y)),
                          rx: 3,
                          fill:
                            row.left >= 0
                              ? props.barPositiveColor || props.leftColor
                              : props.barNegativeColor || props.leftColor,
                          opacity: 0.88,
                        });
                      }),
                    )
                  : h('path', {
                      d: leftLinePath,
                      fill: 'none',
                      stroke: props.leftColor,
                      strokeWidth: 2.4,
                      strokeLinecap: 'round',
                      strokeLinejoin: 'round',
                    }),
                h('path', {
                  d: rightLinePath,
                  fill: 'none',
                  stroke: props.rightColor,
                  strokeWidth: 2.6,
                  strokeLinecap: 'round',
                  strokeLinejoin: 'round',
                }),
                ...renderDateLabels(visibleRows, innerWidth, innerHeight),
              ]),
            ],
          ),
        ]),
        props.showRangeSlider && props.rows.length > minSpan
          ? renderChartRangeSelector({
              labels: props.rows.map((row) => row.date),
              values: props.rows.map((row) => row.right),
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
