export interface EtfFundPeriod {
  code: string;
  name: string;
  value: string | null;
  turnoverYi: string | null;
  unitsYi: string | null;
  deltaUnitsYi: string | null;
  financingBalanceYi: string | null;
  financingNetBuyYi: string | null;
}

export interface EtfPeriod {
  date: string;
  indexClose: string | null;
  indexReturnPct: string | null;
  total: string | null;
  turnoverYi: string | null;
  unitsYi: string | null;
  previousUnitsYi?: string | null;
  deltaUnitsYi: string | null;
  financingBalanceYi: string | null;
  financingNetBuyYi: string | null;
  indexFinancingBalanceYi: string | null;
  indexFinancingNetBuyYi: string | null;
  indexCoveragePct: string | null;
  funds: EtfFundPeriod[];
  partialWeek?: boolean;
  cumulativeUnitsYi?: number | null;
  marketCapRatioPct?: number | null;
}

export function numeric(value: unknown): number | null {
  return value == null || value === '' || !Number.isFinite(Number(value)) ? null : Number(value);
}

export function visiblePeriods(periods: EtfPeriod[], range: number): EtfPeriod[] {
  const last = periods.at(-1)?.date;
  if (!last) return [];
  const start = new Date(last + 'T00:00:00Z');
  start.setUTCDate(start.getUTCDate() - range);
  const visible = periods.filter((r) => !range || r.date >= start.toISOString().slice(0, 10));
  const baseline = numeric(visible.find((r) => numeric(r.unitsYi) != null)?.unitsYi);
  return visible.map((r) => {
    const units = numeric(r.unitsYi);
    return { ...r, cumulativeUnitsYi: baseline == null || units == null ? null : units - baseline };
  });
}

export function withMarketCapRatios(
  rows: EtfPeriod[],
  ratios: Array<{ date: string; ratioPct?: unknown }>,
): EtfPeriod[] {
  const byDate = new Map(ratios.map((r) => [r.date, numeric(r.ratioPct)]));
  return rows.map((row) => ({ ...row, marketCapRatioPct: byDate.get(row.date) ?? null }));
}

export function broadChartOption(
  rows: EtfPeriod[],
  label: string,
  hasIndex = true,
  showRatio = false,
) {
  const ratioVisible = hasIndex && showRatio;
  const format = (value: unknown) =>
    numeric(value) == null
      ? '—'
      : Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 3 });
  return {
    animation: false,
    legend: { top: 4, type: 'scroll', textStyle: { color: '#60758f', fontSize: 12 } },
    grid: { left: ratioVisible ? 142 : 64, right: hasIndex ? 150 : 76, top: 70, bottom: 68 },
    tooltip: {
      trigger: 'axis',
      confine: true,
      axisPointer: { type: 'cross' },
      formatter: (items: Array<{ dataIndex: number }>) => {
        const row = rows[items[0]?.dataIndex];
        if (!row) return '';
        return [
          row.date + (row.partialWeek ? ' · 本周未结束' : ''),
          `净申赎合计：${format(row.total)} 亿元`,
          `份额变动：${format(row.deltaUnitsYi)} 亿份`,
          `所选范围累计份额变动：${format(row.cumulativeUnitsYi)} 亿份`,
          ...(hasIndex ? [`指数收盘：${format(row.indexClose)} 点`] : []),
          ...(ratioVisible ? [`头部ETF市值占比：${format(row.marketCapRatioPct)} %`] : []),
        ].join('<br/>');
      },
    },
    xAxis: {
      type: 'category',
      data: rows.map((r) => r.date),
      boundaryGap: true,
      axisLabel: { color: '#7b8da4', hideOverlap: true, formatter: (v: string) => v.slice(2) },
    },
    yAxis: [
      {
        type: 'value',
        name: '净申赎（亿元）',
        position: 'left',
        splitLine: { lineStyle: { color: '#e8eef5' } },
      },
      {
        type: 'value',
        name: '累计（亿份）',
        position: 'right',
        scale: true,
        splitLine: { show: false },
      },
      {
        type: 'value',
        name: '指数（点）',
        position: 'right',
        offset: 76,
        scale: true,
        splitLine: { show: false },
      },
      {
        type: 'value',
        name: '市值占比（%）',
        position: 'left',
        offset: 76,
        scale: true,
        splitLine: { show: false },
      },
    ]
      .slice(0, ratioVisible ? 4 : hasIndex ? 3 : 2)
      .map((axis) => ({ ...axis, axisLabel: { color: '#7b8da4', fontSize: 11 } })),
    dataZoom: [
      { type: 'inside', zoomOnMouseWheel: 'ctrl', moveOnMouseWheel: false, filterMode: 'filter' },
      { type: 'slider', height: 20, bottom: 8, filterMode: 'filter' },
    ],
    series: [
      {
        name: 'ETF净申赎合计',
        type: 'bar',
        yAxisIndex: 0,
        barMaxWidth: 14,
        itemStyle: { color: (p: { value: number }) => (p.value < 0 ? '#0e9f78' : '#df4b47') },
        data: rows.map((r) => numeric(r.total)),
      },
      {
        name: '累计份额变动',
        type: 'line',
        yAxisIndex: 1,
        showSymbol: false,
        connectNulls: false,
        itemStyle: { color: '#2563eb' },
        lineStyle: { width: 1.8 },
        data: rows.map((r) => r.cumulativeUnitsYi),
      },
      {
        name: label,
        type: 'line',
        yAxisIndex: 2,
        showSymbol: false,
        connectNulls: false,
        itemStyle: { color: '#27364c' },
        lineStyle: { width: 1.8 },
        data: rows.map((r) => numeric(r.indexClose)),
      },
      {
        name: '头部ETF市值占比',
        type: 'line',
        yAxisIndex: 3,
        showSymbol: false,
        connectNulls: false,
        itemStyle: { color: '#7c3aed' },
        lineStyle: { width: 1.8 },
        data: rows.map((r) => numeric(r.marketCapRatioPct)),
      },
    ].filter((s) => (hasIndex || s.yAxisIndex !== 2) && (ratioVisible || s.yAxisIndex !== 3)),
  };
}
