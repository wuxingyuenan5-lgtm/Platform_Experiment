import type { TreasuryWeeklyRow } from '@/api/hedgeResearch';
import type { EChartsOption, BarSeriesOption, LineSeriesOption } from 'echarts';

export function buildTreasuryWeeklyOptions(
  weeks: TreasuryWeeklyRow[],
  start: string,
  end: string,
): EChartsOption {
  const names = [...new Set(weeks.flatMap((week) => week.companies.map((c) => c.name)))];
  const first = weeks.findIndex((w) => w.weekDate >= start);
  const last = weeks.filter((w) => w.weekDate <= end).length - 1;
  const window = { startValue: Math.max(0, first), endValue: Math.max(0, last) };
  // Keep company colours stable when the visible date window changes.
  const colors = [
    '#5268b8',
    '#9333ea',
    '#06a8c4',
    '#8b5cf6',
    '#e11d48',
    '#64748b',
    '#84a83e',
    '#ea580c',
    '#0284c7',
    '#a855f7',
    '#14b8a6',
    '#b45309',
  ];
  const compact = (value: number) => {
    const abs = Math.abs(value);
    const factor = abs >= 1e9 ? 1e9 : abs >= 1e6 ? 1e6 : abs >= 1e3 ? 1e3 : 1;
    return `${Number((value / factor).toFixed(2))}${
      factor === 1e9 ? 'B' : factor === 1e6 ? 'M' : factor === 1e3 ? 'K' : ''
    }`;
  };
  return {
    animation: false,
    grid: { left: 65, right: 65, top: 65, bottom: 85 },
    legend: {
      type: 'scroll',
      top: 5,
      left: 10,
      right: 10,
      data: ['单周比特币总净流入', '比特币价格', ...names.filter((name) => name === 'Strategy')],
    },
    tooltip: {
      trigger: 'axis',
      confine: true,
      renderMode: 'richText',
      axisPointer: { type: 'cross' },
      formatter: (params) => {
        const point = Array.isArray(params) ? params[0] : params;
        const week = weeks.find(
          (row) => row.weekDate === (point as { axisValue?: string })?.axisValue,
        );
        if (!week) return '';
        return [
          week.weekDate,
          `单周总净流入：${week.netFlowDisplay}`,
          ...week.companies.map((c) => `${c.name}：${c.display}`),
          `单周比特币总净流入：${week.netBtc === null ? '—' : week.netBtcDisplay + ' BTC'}`,
          `比特币价格：${week.btcPriceDisplay}`,
        ].join('\n');
      },
    },
    xAxis: {
      type: 'category',
      data: weeks.map((w) => w.weekDate),
      axisLabel: { hideOverlap: true },
    },
    yAxis: [
      {
        type: 'value',
        show: false,
        axisPointer: { show: false },
        position: 'right',
        axisLabel: { formatter: compact },
        splitLine: { lineStyle: { color: '#e5edf5' } },
      },
      {
        type: 'value',
        name: 'BTC 价格（USD）',
        position: 'left',
        scale: true,
        axisLabel: { formatter: compact },
        splitLine: { show: false },
      },
      {
        type: 'value',
        name: 'BTC',
        position: 'right',
        offset: 0,
        axisLabel: { formatter: compact },
        splitLine: { show: false },
      },
    ],
    dataZoom: [
      { type: 'slider', xAxisIndex: 0, filterMode: 'filter', ...window, bottom: 15, height: 26 },
      { type: 'inside', xAxisIndex: 0, filterMode: 'filter', ...window },
    ],
    series: [
      ...names.map(
        (name, index): BarSeriesOption => ({
          name,
          type: 'bar',
          stack: 'companies',
          stackStrategy: 'samesign',
          yAxisIndex: 0,
          emphasis: { disabled: true },
          itemStyle: { color: name === 'Strategy' ? '#16a34a' : colors[index % colors.length] },
          barMaxWidth: 18,
          data: weeks.map((week) => {
            const company = week.companies.find((c) => c.name === name);
            return company ? Number(company.value) : null;
          }) as BarSeriesOption['data'],
        }),
      ),
      {
        name: '单周比特币总净流入',
        type: 'line',
        yAxisIndex: 2,
        showSymbol: false,
        connectNulls: false,
        lineStyle: { width: 1.5, color: '#64748b' },
        itemStyle: { color: '#64748b' },
        data: weeks.map((w) =>
          w.netBtc === null ? null : Number(w.netBtc),
        ) as LineSeriesOption['data'],
      },
      {
        name: '比特币价格',
        type: 'line',
        yAxisIndex: 1,
        showSymbol: false,
        lineStyle: { width: 2, color: '#111111' },
        itemStyle: { color: '#111111' },
        data: weeks.map((w) => Number(w.btcPriceUsd)),
      },
    ],
  };
}
