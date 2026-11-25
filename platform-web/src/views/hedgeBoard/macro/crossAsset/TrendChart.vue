<template>
  <div
    ref="host"
    class="trend-chart"
    :style="{ height: chartHeight + 'px' }"
    role="img"
    :aria-label="ariaLabel"
  ></div>
</template>

<script setup lang="ts">
  import { computed, nextTick, ref, watch, type Ref } from 'vue';
  import { useWindowSize } from '@vueuse/core';
  import type { EChartsOption } from 'echarts';
  import { MarkAreaComponent, MarkLineComponent } from 'echarts/components';
  import { useECharts } from '@/hooks/web/useECharts';
  import echarts from '@/utils/lib/echarts';
  import { compute, type SnapshotSeries, type Frame } from './engine';
  import { GROUP_LINES, type System } from './rules';
  import {
    AUXILIARY_NAMES,
    auxiliaryAvailability,
    computeAuxiliary,
    formatActivity,
    type Auxiliary,
  } from './auxiliary';
  import { KALMAN_NAMES, kalmanHullSupertrend, kalmanPrice, type KalmanOverlay } from './kalman';

  echarts.use([MarkAreaComponent, MarkLineComponent]);

  const props = withDefaults(
    defineProps<{
      source: SnapshotSeries;
      frame: Frame;
      expanded?: boolean;
      groups: System[];
      auxiliary: Auxiliary[];
      kalman: KalmanOverlay[];
      kalmanPaint: KalmanOverlay | 'none';
      range?: number;
      levels?: boolean;
      signalAt?: number;
    }>(),
    { range: 120, levels: true, signalAt: undefined, expanded: false },
  );

  const host = ref<HTMLDivElement | null>(null);
  const { height: viewportHeight } = useWindowSize();
  const chartHeight = computed(() =>
    Math.max(420 + props.auxiliary.length * 90, props.expanded ? viewportHeight.value - 180 : 0),
  );
  const chart = useECharts(host as Ref<HTMLDivElement>);
  const COLORS: Record<string, string> = {
    PMA12: '#a77a24',
    PMA144: '#298f9f',
    PMA169: '#298f9f',
    PMA288: '#8c6bbb',
    PMA338: '#8c6bbb',
    PMA576: '#ba7272',
    PMA676: '#ba7272',
    MA20: '#c18b28',
    MA60: '#467cac',
    MA100: '#9064ad',
    MA200: '#8a7353',
    EMA20: '#d49b27',
    EMA60: '#4f9bb9',
    EMA100: '#b06da1',
    EMA200: '#9a9080',
    E15: '#4382d0',
    ZLMA: '#16886e',
  };
  const overlayColor = (trend: number) =>
    trend > 0 ? '#16886e' : trend < 0 ? '#c34a4a' : '#748086';
  const date = (seconds: number) => new Date(seconds * 1000).toISOString().slice(0, 10);
  const finite = (value: unknown): value is number =>
    typeof value === 'number' && Number.isFinite(value);

  function buildOptions(): EChartsOption {
    const data = compute(
      props.source.bars,
      props.source.lastBarComplete === true || !!props.source.rolling,
    );
    const bars = data.bars;
    const labels = bars.map((bar) => date(bar.t));
    const indicators = computeAuxiliary(bars);
    const availability = auxiliaryAvailability(bars, props.frame);
    const selectedLines = props.groups.flatMap((group) => GROUP_LINES[group] || []);
    const overlays: Record<KalmanOverlay, ReturnType<typeof kalmanPrice>> = {
      price: props.kalman.includes('price') ? kalmanPrice(bars) : [],
      hull: props.kalman.includes('hull') ? kalmanHullSupertrend(bars) : [],
    };
    const hullMarks = props.kalman.includes('hull')
      ? overlays.hull.flatMap((point, i) =>
          point.signal
            ? [
                {
                  name: point.signal > 0 ? 'Kalman转多' : 'Kalman转空',
                  coord: [labels[i], point.signal > 0 ? bars[i].l : bars[i].h],
                  value: point.signal > 0 ? '多' : '空',
                  symbol: 'arrow',
                  itemStyle: { color: overlayColor(point.signal) },
                },
              ]
            : [],
        )
      : [];
    const paneCount = props.auxiliary.length;
    const mainHeight = chartHeight.value - (paneCount ? 120 + paneCount * 90 : 90);
    const grids = [{ left: 58, right: 18, top: 38, height: mainHeight } as const];
    const xAxes = [
      {
        type: 'category' as const,
        data: labels,
        boundaryGap: true,
        axisLabel: { hideOverlap: true, show: !paneCount },
      },
    ];
    const yAxes = [{ scale: true, splitLine: { lineStyle: { color: '#edf0f3' } } }];
    const series: any[] = [];
    const candles = bars.map((bar, index) => {
      const paint = props.kalmanPaint === 'none' ? undefined : overlays[props.kalmanPaint]?.[index];
      const color = paint?.value == null ? undefined : overlayColor(paint.trend);
      const candleColor =
        props.source.rolling && !props.source.lastBarComplete && index === bars.length - 1
          ? '#c18b28'
          : color;
      return {
        value: [bar.o, bar.c, bar.l, bar.h],
        itemStyle: candleColor
          ? {
              color: candleColor,
              color0: candleColor,
              borderColor: candleColor,
              borderColor0: candleColor,
            }
          : undefined,
      };
    });
    series.push({
      type: 'candlestick',
      name: '价格',
      data: candles,
      xAxisIndex: 0,
      yAxisIndex: 0,
      itemStyle: {
        color: '#16886e',
        color0: '#c34a4a',
        borderColor: '#16886e',
        borderColor0: '#c34a4a',
      },
      markPoint: hullMarks.length
        ? {
            symbol: 'arrow',
            symbolSize: 11,
            label: { show: false },
            data: hullMarks,
          }
        : undefined,
    });
    function coloredLine(
      name: string,
      values: (number | null)[],
      directions: number[],
      color: (direction: number) => string,
      dashed = false,
    ) {
      for (const direction of [-1, 0, 1])
        series.push({
          type: 'line',
          name,
          data: values.map((value, i) =>
            directions[i] === direction || directions[i + 1] === direction ? value : null,
          ),
          xAxisIndex: 0,
          yAxisIndex: 0,
          showSymbol: false,
          connectNulls: false,
          lineStyle: { color: color(direction), width: 2, type: dashed ? 'dashed' : 'solid' },
          itemStyle: { color: color(directions.at(-1) || 0) },
        });
    }
    function fillBand(
      name: string,
      a: (number | null)[],
      b: (number | null)[],
      color: string,
      include: (i: number) => boolean = () => true,
    ) {
      const base = a.map((value, i) =>
        value == null || b[i] == null || !include(i) ? null : Math.min(value, b[i]!),
      );
      series.push({
        type: 'line',
        name: '__' + name + '-base',
        stack: name,
        data: base,
        silent: true,
        showSymbol: false,
        lineStyle: { opacity: 0 },
        areaStyle: { opacity: 0 },
        z: 0,
      });
      series.push({
        type: 'line',
        name: '__' + name + '-fill',
        stack: name,
        data: a.map((value, i) =>
          base[i] == null || value == null || b[i] == null ? null : Math.abs(value - b[i]!),
        ),
        silent: true,
        showSymbol: false,
        lineStyle: { opacity: 0 },
        areaStyle: { color },
        z: 0,
      });
    }
    const zColor = (value: number) =>
      value > 0 ? '#30d453' : value < 0 ? '#4043f1' : 'transparent';
    selectedLines.forEach((key) => {
      if (key === 'ZLMA' || key === 'E15') {
        const values = data.lines[key];
        const directions = values.map((value, i) =>
          key === 'E15'
            ? value! < data.lines.ZLMA[i]!
              ? 1
              : -1
            : i < 3 || value === data.lines.ZLMA[i - 3]
            ? 0
            : value! > data.lines.ZLMA[i - 3]!
            ? 1
            : -1,
        );
        coloredLine(key, values, directions, zColor);
        return;
      }
      series.push({
        type: 'line',
        name: key,
        data: data.lines[key] || [],
        xAxisIndex: 0,
        yAxisIndex: 0,
        showSymbol: false,
        connectNulls: false,
        lineStyle: {
          color: COLORS[key] || '#76808b',
          width: key === 'ZLMA' ? 2 : 1,
          type: key.startsWith('EMA') ? 'dashed' : 'solid',
        },
        itemStyle: { color: COLORS[key] || '#76808b' },
      });
    });
    for (const [a, b, color] of [
      ['PMA144', 'PMA169', '#298f9f22'],
      ['PMA288', 'PMA338', '#8c6bbb22'],
      ['PMA576', 'PMA676', '#ba727222'],
    ])
      if (selectedLines.includes(a) && selectedLines.includes(b))
        fillBand(a + b, data.lines[a], data.lines[b], color);
    const zeroLagVisible = selectedLines.includes('ZLMA');
    if (zeroLagVisible && selectedLines.includes('E15'))
      for (const direction of [-1, 1])
        fillBand(
          'zeroLag' + direction,
          data.lines.ZLMA,
          data.lines.E15,
          direction > 0 ? '#30d45325' : '#4043f125',
          (i) =>
            direction > 0
              ? data.lines.ZLMA[i]! > data.lines.E15[i]!
              : data.lines.ZLMA[i]! <= data.lines.E15[i]!,
        );
    props.kalman.forEach((key) =>
      coloredLine(
        KALMAN_NAMES[key],
        overlays[key].map((point) => point.value),
        overlays[key].map((point) => point.trend),
        overlayColor,
        key === 'hull',
      ),
    );

    if (props.levels && zeroLagVisible && labels.length) {
      const areas = data.boxes.flatMap((box) => {
        const start = labels.indexOf(date(box.start));
        const end = labels.indexOf(date(box.end));
        return start < 0 || end < 0
          ? []
          : [
              [
                {
                  xAxis: labels[start],
                  yAxis: box.top,
                  itemStyle: {
                    color: box.side === '多' ? '#16886e18' : '#4043f118',
                    borderColor: box.side === '多' ? '#16886e88' : '#4043f188',
                  },
                },
                { xAxis: labels[Math.max(start, end)], yAxis: box.bottom },
              ],
            ];
      });
      series[0].markArea = { silent: true, data: areas };
    }
    if (zeroLagVisible && labels.length) {
      series[0].markPoint = {
        ...(series[0].markPoint || {}),
        symbolSize: 8,
        label: { show: false },
        data: [
          ...hullMarks,
          ...data.events
            .filter((event) => event.kind === 'ZLMA交叉' || props.levels)
            .flatMap((event) => {
              const i = labels.indexOf(date(event.plottedAt));
              return i < 0
                ? []
                : [
                    {
                      name: event.kind,
                      coord: [
                        labels[i],
                        event.kind === 'ZLMA交叉'
                          ? data.lines.ZLMA[i]
                          : event.side === '多'
                          ? bars[i].l
                          : bars[i].h,
                      ],
                      value: event.kind,
                      symbol: event.kind === 'ZLMA交叉' ? 'diamond' : 'triangle',
                      symbolRotate: event.side === '多' ? 0 : 180,
                      itemStyle: { color: event.side === '多' ? '#16886e' : '#4043f1' },
                    },
                  ];
            }),
        ],
      };
    }
    if (props.signalAt != null && labels.includes(date(props.signalAt)))
      series[0].markLine = {
        silent: true,
        symbol: 'none',
        lineStyle: { color: '#c18b28', type: 'dashed' },
        data: [{ xAxis: date(props.signalAt), label: { formatter: '信号观测' } }],
      };

    const auxValues: Record<Auxiliary, (number | null)[]> = {
      macd: indicators.histogram,
      rsi: indicators.rsi,
      volume: indicators.volume,
      amount: indicators.amount,
    };
    const auxHeight = 60;
    const graphics: any[] = [];
    props.auxiliary.forEach((key, index) => {
      const pane = index + 1;
      const top = mainHeight + 68 + index * 90;
      grids.push({
        left: 58,
        right: 18,
        top,
        height: auxHeight,
      } as any);
      xAxes.push({
        type: 'category',
        data: labels,
        gridIndex: pane,
        axisLabel: { show: index === paneCount - 1, hideOverlap: true },
      } as any);
      yAxes.push({
        gridIndex: pane,
        scale: key !== 'rsi',
        splitNumber: 2,
        axisLabel: {
          formatter: (value: number) =>
            key === 'amount'
              ? '$' + formatActivity(value)
              : key === 'volume'
              ? formatActivity(value)
              : String(value),
        },
        splitLine: { lineStyle: { color: '#edf0f3' } },
        min: key === 'rsi' ? 0 : undefined,
        max: key === 'rsi' ? 100 : undefined,
      } as any);
      if (availability[key]) {
        graphics.push({
          type: 'text',
          left: 70,
          top: top + 10,
          style: {
            text: `${AUXILIARY_NAMES[key]}：${availability[key]}`,
            fill: '#89939f',
            fontSize: 12,
          },
        });
      } else if (key === 'macd') {
        series.push({
          type: 'bar',
          name: 'MACD柱',
          data: indicators.histogram,
          xAxisIndex: pane,
          yAxisIndex: pane,
          itemStyle: { color: (p: any) => (Number(p.value) >= 0 ? '#16886e99' : '#c34a4a99') },
        });
        series.push({
          type: 'line',
          name: 'DIF',
          data: indicators.dif,
          xAxisIndex: pane,
          yAxisIndex: pane,
          showSymbol: false,
          connectNulls: false,
          lineStyle: { color: '#467cac' },
        });
        series.push({
          type: 'line',
          name: 'DEA',
          data: indicators.dea,
          xAxisIndex: pane,
          yAxisIndex: pane,
          showSymbol: false,
          connectNulls: false,
          lineStyle: { color: '#c18b28' },
        });
      } else if (key === 'rsi')
        series.push({
          type: 'line',
          name: 'RSI(14)',
          data: auxValues[key],
          xAxisIndex: pane,
          yAxisIndex: pane,
          showSymbol: false,
          connectNulls: false,
          lineStyle: { color: '#9064ad', width: 2 },
          markLine: {
            silent: true,
            symbol: 'none',
            lineStyle: { color: '#9064ad66', type: 'dashed' },
            data: [{ yAxis: 30 }, { yAxis: 50 }, { yAxis: 70 }],
          },
        });
      else
        series.push({
          type: 'bar',
          name: AUXILIARY_NAMES[key],
          data: auxValues[key],
          xAxisIndex: pane,
          yAxisIndex: pane,
          itemStyle: { color: '#467cac99' },
        });
    });
    const targetIndex =
      props.signalAt == null ? -1 : bars.findIndex((bar) => bar.t === props.signalAt);
    const zoomCount = Math.min(
      props.range && props.range > 0 ? props.range : labels.length,
      labels.length,
    );
    const zoomFrom =
      targetIndex >= 0
        ? Math.max(
            0,
            Math.min(targetIndex - Math.floor(zoomCount * 0.65), labels.length - zoomCount),
          )
        : Math.max(0, labels.length - zoomCount);
    const zoomTo =
      targetIndex >= 0
        ? Math.min(Math.max(0, labels.length - 1), zoomFrom + zoomCount + 2)
        : Math.max(0, labels.length - 1);
    const zoomStart = labels.length > 1 ? (zoomFrom / (labels.length - 1)) * 100 : 0;
    const zoomEnd = labels.length > 1 ? (zoomTo / (labels.length - 1)) * 100 : 100;
    return {
      animation: false,
      title: {
        text: `${props.source.symbol} · ${props.frame}`,
        left: 8,
        top: 4,
        textStyle: { fontSize: 13, fontWeight: 'normal' },
      },
      legend: {
        type: 'scroll',
        top: 4,
        left: 140,
        right: 8,
        data: [
          ...new Set(series.filter((item) => !item.name.startsWith('__')).map((item) => item.name)),
        ],
      },
      grid: grids,
      xAxis: xAxes,
      yAxis: yAxes,
      graphic: graphics,
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: xAxes.map((_, i) => i),
          start: labels.length ? zoomStart : 0,
          end: labels.length ? zoomEnd : 100,
        },
        { type: 'slider', xAxisIndex: xAxes.map((_, i) => i), bottom: 4, height: 18 },
      ],
      tooltip: {
        renderMode: 'richText',
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        formatter: (params: any) => {
          const first = Array.isArray(params) ? params[0] : params;
          const i = labels.indexOf(first?.axisValue);
          const bar = bars[i];
          if (!bar) return String(first?.axisValue || '');
          const rows = [
            date(bar.t),
            `开 ${bar.o.toFixed(2)} 高 ${bar.h.toFixed(2)} 低 ${bar.l.toFixed(
              2,
            )} 收 ${bar.c.toFixed(2)}`,
          ];
          const display = (value: number | null | undefined) =>
            finite(value) ? value.toFixed(2) : '历史不足';
          selectedLines.forEach((key) => rows.push(key + '：' + display(data.lines[key][i])));
          props.kalman.forEach((key) =>
            rows.push(KALMAN_NAMES[key] + '：' + display(overlays[key][i]?.value)),
          );
          props.auxiliary.forEach((key) =>
            rows.push(
              AUXILIARY_NAMES[key] +
                '：' +
                (availability[key] ||
                  (key === 'macd'
                    ? 'DIF ' +
                      display(indicators.dif[i]) +
                      ' / DEA ' +
                      display(indicators.dea[i]) +
                      ' / 柱 ' +
                      display(indicators.histogram[i]) +
                      ' · ' +
                      indicators.macdSource[i]
                    : key === 'rsi'
                    ? display(auxValues[key][i]) + ' · ' + indicators.rsiSource[i]
                    : key === 'volume'
                    ? display(auxValues[key][i]) + ' 股 / 份'
                    : display(auxValues[key][i]) + ' USD · ' + indicators.amountSource[i])),
            ),
          );
          if (zeroLagVisible)
            data.events
              .filter((e) => e.plottedAt === bar.t && (e.kind === 'ZLMA交叉' || props.levels))
              .forEach((e) =>
                rows.push(
                  '原始事件 ' + e.kind + ' · 观测 ' + date(e.t) + ' · 图示 ' + date(e.plottedAt),
                ),
              );
          rows.push(`来源：${props.source.source || '快照'} · ${props.source.fetchedAt}`);
          return rows.join('\n');
        },
      },
      axisPointer: { link: [{ xAxisIndex: 'all' }] },
      series,
    };
  }

  const ariaLabel = `跨资产趋势图${props.source.symbol ? `：${props.source.symbol}` : ''}`;
  let previousWindow = '';
  watch(
    () => [
      props.source,
      props.frame,
      props.groups,
      props.auxiliary,
      props.kalman,
      props.kalmanPaint,
      props.range,
      props.levels,
      props.signalAt,
      chartHeight.value,
    ],
    async () => {
      await nextTick();
      const windowKey = [
        props.source.symbol,
        props.frame,
        props.source.bars[0]?.t,
        props.source.aggregation,
        props.range,
        props.signalAt,
      ].join('/');
      const current =
        windowKey === previousWindow && host.value?.querySelector('svg')
          ? chart.getInstance()?.getOption()
          : undefined;
      const options = buildOptions();
      const previousZoom = (
        current?.dataZoom as Array<{ start?: number; end?: number }> | undefined
      )?.[0];
      if (
        previousZoom &&
        Number.isFinite(previousZoom.start) &&
        Number.isFinite(previousZoom.end)
      ) {
        for (const zoom of options.dataZoom as Array<{ start?: number; end?: number }>) {
          zoom.start = previousZoom.start;
          zoom.end = previousZoom.end;
        }
      }
      previousWindow = windowKey;
      chart.setOptions(options, true);
    },
    { immediate: true, deep: true },
  );
</script>

<style scoped>
  .trend-chart {
    width: 100%;
    height: clamp(420px, 56vw, 720px);
    min-height: 420px;
    border-radius: 8px;
    background: var(--panel, #fff);
  }
</style>
