import type { EChartsOption } from 'echarts';
import type { PositionRow } from '../components/goldResearch';
import type { MacroDashboardObservation } from '@/api/hedgeResearch';

export function cotChanges(first: PositionRow, last: PositionRow) {
  const spreads = (r: PositionRow) => {
    const groups = Object.entries(r.categories).filter(
      ([key]) => !['producer', 'nonreportable'].includes(key),
    );
    return groups.some(([, g]) => g.spreading == null)
      ? null
      : groups.reduce((n, [, g]) => n + g.spreading!, 0);
  };
  const oi = last.openInterest - first.openInterest;
  const a = spreads(first),
    b = spreads(last);
  const spread = a == null || b == null ? null : b - a;
  const rows = [
    { label: '总未平仓量', long: oi, short: oi },
    {
      label: '扣除套利',
      long: spread == null ? null : oi - spread,
      short: spread == null ? null : oi - spread,
    },
    { label: '套利持仓', long: spread, short: spread },
  ];
  for (const [key, group] of Object.entries(last.categories)) {
    const previous = first.categories[key];
    rows.push({
      label: group.label,
      long: group.long - previous.long,
      short: group.short - previous.short,
    });
    if (group.spreading !== null && previous.spreading !== null) {
      const change = group.spreading - previous.spreading;
      rows.push({ label: `${group.label}套利`, long: change, short: change });
    }
  }
  return rows;
}

export function cotChangeOptions(first: PositionRow, last: PositionRow): EChartsOption {
  const rows = cotChanges(first, last);
  return {
    animation: false,
    color: ['#b48a43', '#647bb5'],
    legend: { top: 0 },
    tooltip: { trigger: 'axis', confine: true, renderMode: 'richText' },
    grid: { left: 70, right: 25, top: 45, bottom: 105 },
    xAxis: {
      type: 'category',
      data: rows.map((r) => r.label),
      axisLabel: { rotate: 25, interval: 0, fontSize: 10 },
    },
    yAxis: { type: 'value', name: '持仓变动 · 手' },
    series: (['long', 'short'] as const).map((key) => ({
      type: 'bar',
      name: key === 'long' ? '多头变动' : '空头变动',
      data: rows.map((r) => r[key]),
      barMaxWidth: 24,
    })),
  };
}

export function cotHistoryOptions(
  history: PositionRow[],
  price: MacroDashboardObservation[],
  start: string,
  end: string,
): EChartsOption {
  const rows = history.filter((r) => r.date >= start && r.date <= end);
  const prices = price.filter((r) => r.date >= start && r.date <= end);
  return {
    animation: false,
    color: ['#b48a43', '#5373b9', '#7b9a68'],
    legend: { top: 0 },
    tooltip: {
      trigger: 'axis',
      confine: true,
      renderMode: 'richText',
      axisPointer: { type: 'cross' },
    },
    axisPointer: { link: [{ xAxisIndex: 'all' }] },
    grid: [
      { left: 65, right: 25, top: 50, height: '30%' },
      { left: 65, right: 25, top: '49%', bottom: 70 },
    ],
    xAxis: [0, 1].map((gridIndex) => ({
      type: 'time',
      gridIndex,
      min: `${start}T00:00:00Z`,
      max: `${end}T00:00:00Z`,
    })),
    yAxis: [
      { type: 'value', gridIndex: 0, scale: true, name: '黄金 · USD/oz' },
      { type: 'value', gridIndex: 1, name: '持仓 / OI · %' },
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], filterMode: 'none' },
      { type: 'slider', xAxisIndex: [0, 1], bottom: 15, height: 22, filterMode: 'none' },
    ],
    series: [
      {
        type: 'line',
        name: '黄金现货',
        xAxisIndex: 0,
        yAxisIndex: 0,
        showSymbol: false,
        connectNulls: false,
        data: prices.map((p) => [`${p.date}T00:00:00Z`, p.value == null ? null : Number(p.value)]),
      },
      ...(['long', 'short'] as const).map((key) => ({
        type: 'line' as const,
        name: `资产管理机构${key === 'long' ? '多' : '空'}头（含套利）`,
        xAxisIndex: 1,
        yAxisIndex: 1,
        showSymbol: false,
        connectNulls: false,
        data: rows.map((r) => [
          `${r.date}T00:00:00Z`,
          r.categories.managed.spreading == null
            ? null
            : ((r.categories.managed[key] + r.categories.managed.spreading) / r.openInterest) * 100,
        ]),
      })),
    ],
  };
}
