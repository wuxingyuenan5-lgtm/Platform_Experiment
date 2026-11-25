import type { EChartsOption } from 'echarts';

export interface MarketStructureRow {
  date: string;
  advance?: number | null;
  decline?: number | null;
  limit_up?: number | null;
  limit_down?: number | null;
  market_breadth?: number | null;
  csi300Close?: number | string | null;
}
export type MarketStructureRange = 90 | 365 | 1095 | 0;
const numeric = (value: unknown) =>
  value == null || value === '' || !Number.isFinite(Number(value)) ? null : Number(value);

export function structureRows(input: MarketStructureRow[]) {
  const rows = [...input].sort((a, b) => a.date.localeCompare(b.date));
  const start = rows.findIndex((row) =>
    [row.advance, row.decline, row.limit_up, row.limit_down].some(
      (value) => numeric(value) != null,
    ),
  );
  return start < 0 ? [] : rows.slice(start);
}

export function structureWindow(rows: MarketStructureRow[], range: MarketStructureRange) {
  if (!rows.length || !range) return { startValue: 0, endValue: Math.max(0, rows.length - 1) };
  const cutoff = new Date(`${rows.at(-1)!.date}T00:00:00Z`);
  if (range === 90) cutoff.setUTCDate(cutoff.getUTCDate() - 89);
  else cutoff.setUTCFullYear(cutoff.getUTCFullYear() - (range === 365 ? 1 : 3));
  const start = rows.findIndex((row) => row.date >= cutoff.toISOString().slice(0, 10));
  return { startValue: Math.max(0, start), endValue: rows.length - 1 };
}

export function buildMarketStructureOptions(
  rows: MarketStructureRow[],
  range: MarketStructureRange,
): EChartsOption {
  const window = structureWindow(rows, range);
  const definitions = [
    { name: '上涨家数', key: 'advance', axis: 0, type: 'bar', sign: 1, color: '#ef4444' },
    { name: '下跌家数', key: 'decline', axis: 0, type: 'bar', sign: -1, color: '#10b981' },
    { name: '涨停家数（全A）', key: 'limit_up', axis: 1, type: 'line', sign: 1, color: '#ef4444' },
    {
      name: '跌停家数（全A）',
      key: 'limit_down',
      axis: 1,
      type: 'line',
      sign: -1,
      color: '#10b981',
    },
    { name: '沪深300', key: 'csi300Close', axis: 2, type: 'line', sign: 1, color: '#000000' },
  ] as const;
  return {
    animation: false,
    legend: {
      type: 'scroll',
      top: 8,
      left: 12,
      right: 12,
      textStyle: { color: '#627488', fontSize: 12 },
    },
    grid: { left: 66, right: 62, top: 65, bottom: 76 },
    tooltip: {
      trigger: 'axis',
      confine: true,
      renderMode: 'richText',
      axisPointer: { type: 'cross' },
      valueFormatter: (value) =>
        value == null ? '—' : Math.abs(Number(value)).toLocaleString('zh-CN'),
    },
    xAxis: {
      type: 'category',
      data: rows.map((row) => row.date),
      boundaryGap: true,
      axisLine: { lineStyle: { color: '#d7e0e9' } },
      axisTick: { show: false },
      axisLabel: {
        color: '#627488',
        fontSize: 11,
        hideOverlap: true,
        formatter: (date: string) => date.slice(2),
      },
    },
    yAxis: [
      {
        type: 'value',
        name: '上涨 / 下跌（家）',
        min: -6000,
        max: 6000,
        interval: 2000,
        axisLabel: {
          color: '#627488',
          showMinLabel: false,
          showMaxLabel: false,
          formatter: (value: number) => value.toLocaleString('zh-CN'),
        },
        splitLine: { lineStyle: { color: '#edf1f5' } },
      },
      {
        type: 'value',
        name: '涨停 / 跌停（家）',
        position: 'right',
        min: -300,
        max: 300,
        interval: 100,
        axisLabel: {
          color: '#627488',
          showMinLabel: false,
          showMaxLabel: false,
          formatter: (value: number) => value.toLocaleString('zh-CN'),
        },
        splitLine: { show: false },
      },
      { type: 'value', show: false, scale: true, min: 'dataMin', max: 'dataMax' },
    ],
    dataZoom: [
      {
        type: 'inside',
        filterMode: 'filter',
        zoomOnMouseWheel: 'ctrl',
        moveOnMouseWheel: false,
        ...window,
      },
      {
        type: 'slider',
        filterMode: 'filter',
        bottom: 10,
        height: 24,
        borderColor: '#dce5ee',
        fillerColor: 'rgba(22,93,255,0.1)',
        backgroundColor: '#f5f8fb',
        handleStyle: { color: '#477bc2' },
        textStyle: { fontSize: 11, color: '#627488' },
        showDetail: true,
        ...window,
      },
    ],
    series: definitions.map((item) => ({
      name: item.name,
      type: item.type,
      yAxisIndex: item.axis,
      data: rows.map((row) => {
        const value = numeric(row[item.key]);
        return value == null || (item.axis === 2 && value <= 0) ? null : value * item.sign;
      }),
      barMaxWidth: 18,
      barGap: '-100%',
      showSymbol: false,
      connectNulls: false,
      itemStyle: { color: item.color, opacity: item.type === 'bar' ? 0.5 : 1 },
      lineStyle: { width: item.axis === 1 ? 3 : 2.5 },
    })),
  };
}
