import type { EChartsOption, LineSeriesOption } from 'echarts';

export interface GoldFactorRow {
  date: string;
  available: boolean;
  gold: number;
  nominalYield?: number;
  breakeven?: number;
  fedFunds?: number | null;
  mid?: number;
  tips?: number;
  yieldFactor?: number;
  premium?: number;
  monetaryObservation?: string;
}
export interface GoldFactorData {
  status: string;
  rows?: GoldFactorRow[];
  calibration?: { start: string; end: string; duration: number };
  sources?: { source: string; sourceUrl?: string; observationDate?: string }[];
}
export const factorNames = {
  mid: '货币基准',
  tips: '盈亏平衡通胀因子',
  yieldFactor: '名义利率因子',
  premium: '剩余溢价',
};
export function goldFactorOptions(rows: GoldFactorRow[], contribution: boolean): EChartsOption {
  const common = rows.filter((r) => r.available);
  const base = common[0];
  const colors = {
    gold: '#b98927',
    mid: '#888b92',
    tips: '#6667b7',
    yieldFactor: '#7f9f45',
    premium: '#d49b23',
  };
  const tops = contribution ? [5, 31, 49, 68] : [4, 27, 42, 54, 66, 78];
  const heights = contribution ? [20, 12, 12, 22] : [18, 10, 7, 7, 7, 13];
  const labels = contribution
    ? ['黄金 · USD/oz', '名义利率因子 · %', '剩余溢价 · %', '因子与金价变动 · %']
    : [
        '黄金 · USD/oz',
        '利率 · %',
        '货币基准 · USD/oz',
        '盈亏平衡通胀 · 倍',
        '名义利率 · 倍',
        '剩余溢价 · 倍',
      ];
  const series: LineSeriesOption[] = [];
  function add(
    key: keyof GoldFactorRow,
    name: string,
    panel: number,
    color: string,
    change = false,
    area = false,
  ) {
    const source = key === 'gold' && !change ? rows : common;
    const points: [string, number | null][] = [];
    let previous = '';
    for (const row of source) {
      if (previous && Date.parse(row.date) - Date.parse(previous) > 7 * 86400000)
        points.push([new Date(Date.parse(previous) + 86400000).toISOString(), null]);
      const value = row[key],
        anchor = base?.[key];
      points.push([
        `${row.date}T00:00:00Z`,
        typeof value !== 'number'
          ? null
          : change
          ? typeof anchor === 'number' && anchor > 0
            ? 100 * (value / anchor - 1)
            : null
          : value,
      ]);
      previous = row.date;
    }
    series.push({
      type: 'line',
      name,
      xAxisIndex: panel,
      yAxisIndex: panel,
      showSymbol: false,
      connectNulls: false,
      lineStyle: { width: key === 'gold' ? 1.4 : 1.15, color },
      itemStyle: { color },
      areaStyle: area ? { color, opacity: 0.22 } : undefined,
      data: points as LineSeriesOption['data'],
    });
  }
  add('gold', '黄金现货', 0, colors.gold, false, true);
  if (contribution) {
    add('yieldFactor', '名义利率因子', 1, colors.yieldFactor, true, true);
    add('premium', '剩余溢价', 2, colors.premium, true, true);
    for (const key of ['mid', 'tips', 'yieldFactor', 'premium'] as const)
      add(key, factorNames[key], 3, colors[key], true, key === 'yieldFactor' || key === 'premium');
    add('gold', '金价累计变动', 3, colors.gold, true);
  } else {
    add('fedFunds', '联邦基金有效利率', 1, colors.tips, false, true);
    add('nominalYield', '10年名义利率', 1, '#677b9d');
    for (const [index, key] of (['mid', 'tips', 'yieldFactor', 'premium'] as const).entries())
      add(key, factorNames[key], index + 2, colors[key], false, true);
  }
  return {
    animation: false,
    tooltip: {
      trigger: 'axis',
      confine: true,
      renderMode: 'richText',
      valueFormatter: (v) =>
        typeof v === 'number' ? v.toLocaleString('en-US', { maximumFractionDigits: 3 }) : '—',
    },
    legend: {
      type: 'scroll',
      bottom: 32,
      left: 'center',
      itemWidth: 12,
      itemHeight: 3,
      icon: 'rect',
      textStyle: { fontSize: 11, color: '#677681' },
    },
    axisPointer: { link: [{ xAxisIndex: 'all' }] },
    grid: tops.map((top, i) => ({ left: 82, right: 34, top: `${top}%`, height: `${heights[i]}%` })),
    xAxis: tops.map((_, gridIndex) => ({
      type: 'time',
      gridIndex,
      min: `${rows[0]?.date}T00:00:00Z`,
      max: `${rows.at(-1)?.date}T00:00:00Z`,
      axisLabel: { show: gridIndex === tops.length - 1, hideOverlap: true, fontSize: 10 },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#b9c0c5' } },
      splitLine: { show: true, lineStyle: { color: '#e9edf0', width: 0.6 } },
    })),
    yAxis: labels.map((name, gridIndex) => ({
      type: 'value',
      gridIndex,
      name,
      scale: true,
      splitNumber: 3,
      nameGap: 8,
      nameTextStyle: { align: 'left', fontSize: 11, color: '#697985' },
      axisLabel: { fontSize: 10, formatter: (v: number) => Number(v.toFixed(2)).toLocaleString() },
      splitLine: { lineStyle: { color: '#e2e7eb', width: 0.6 } },
    })),
    dataZoom: [
      { type: 'inside', xAxisIndex: tops.map((_, i) => i), filterMode: 'none' },
      {
        type: 'slider',
        xAxisIndex: tops.map((_, i) => i),
        bottom: 0,
        height: 18,
        filterMode: 'none',
      },
    ],
    series,
  };
}
