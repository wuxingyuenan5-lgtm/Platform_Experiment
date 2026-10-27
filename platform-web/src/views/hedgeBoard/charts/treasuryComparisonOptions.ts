import type { MacroDashboardSeries } from '@/api/hedgeResearch';

export const TREASURY_LINES = [
  ['dff', 'DFF', '#c9a500', 0],
  ['us_treasury_3m', 'US03MY', '#2563eb', 0],
  ['us_treasury_2y', 'US02Y', '#e88918', 0],
  ['us_treasury_10y', 'US10Y', '#171717', 0],
  ['us_treasury_30y', 'US30Y', '#e24a59', 0],
  ['ust_2y_3m_pct', 'US02Y−US03MY', '#5a8fd8', 1],
  ['ust_10y_2y_pct', 'US10Y−US02Y', '#08a996', 1],
  ['ust_30y_10y_pct', 'US30Y−US10Y', '#d5448b', 1],
] as const;

export function buildTreasuryComparisonOptions(series: MacroDashboardSeries[]) {
  const byId = new Map(series.map((s) => [s.seriesId, s]));
  // Trading-session axis: do not introduce weekend gaps from calendar-day DFF.
  const dates = [
    ...new Set(
      series
        .filter((s) => s.seriesId.startsWith('us_treasury_'))
        .flatMap((s) => s.observations.map((o) => o.date)),
    ),
  ].sort();
  const values = new Map(
    series.map((s) => [s.seriesId, new Map(s.observations.map((o) => [o.date, o.value]))]),
  );
  return {
    animation: false,
    color: TREASURY_LINES.map((l) => l[2]),
    legend: { top: 4, type: 'scroll', textStyle: { fontSize: 11, color: '#61788e' } },
    grid: [
      { left: 24, right: 72, top: 60, height: '57%' },
      { left: 24, right: 72, top: '73%', bottom: 65 },
    ],
    axisPointer: { link: [{ xAxisIndex: 'all' }] },
    tooltip: {
      trigger: 'axis',
      confine: true,
      renderMode: 'richText',
      formatter: (params: unknown) => {
        const items = (Array.isArray(params) ? params : []) as Array<{
          name?: string;
          marker?: string;
          seriesName?: string;
          value?: unknown;
        }>;
        return items.length
          ? [
              items[0].name || '',
              ...items.map(
                (i) =>
                  `${i.marker || ''}${i.seriesName || ''}：${
                    i.value == null ? '—' : Number(i.value).toFixed(3)
                  }%`,
              ),
            ].join('\n')
          : '';
      },
    },
    xAxis: [0, 1].map((i) => ({
      type: 'category',
      gridIndex: i,
      data: dates,
      boundaryGap: false,
      axisLabel: { show: !!i, color: '#71869e', hideOverlap: true },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#d7e3ed' } },
    })),
    yAxis: [0, 1].map((i) => ({
      type: 'value',
      gridIndex: i,
      position: 'right',
      scale: true,
      name: i ? '期限利差（百分点）' : '年化收益率（%）',
      splitNumber: i ? 3 : 5,
      axisLabel: { color: '#71869e' },
      splitLine: { lineStyle: { color: '#e5edf4' } },
    })),
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: [0, 1],
        filterMode: 'filter',
        zoomOnMouseWheel: 'ctrl',
        moveOnMouseWheel: false,
      },
      { type: 'slider', xAxisIndex: [0, 1], filterMode: 'filter', height: 20, bottom: 8 },
    ],
    series: TREASURY_LINES.filter((l) => byId.has(l[0])).map(([id, name, color, pane]) => ({
      name,
      type: 'line',
      xAxisIndex: pane,
      yAxisIndex: pane,
      showSymbol: false,
      step: id === 'dff' ? 'end' : false,
      connectNulls: false,
      data: dates.map((day) => {
        const value = values.get(id)?.get(day);
        return value == null || !Number.isFinite(Number(value)) ? null : Number(value);
      }),
      lineStyle: { color, width: id === 'dff' ? 2.5 : 1.6 },
      itemStyle: { color },
      ...(id === 'ust_2y_3m_pct'
        ? {
            markLine: {
              silent: true,
              symbol: 'none',
              label: { show: false },
              lineStyle: { color: '#8292a2', type: 'dashed' },
              data: [{ yAxis: 0 }],
            },
          }
        : {}),
    })),
  };
}
