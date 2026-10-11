import type { MacroDashboardSeries } from '@/api/hedgeResearch';

export function buildSourceCurveOptions(
  rows: MacroDashboardSeries[],
  color: string,
  unit = '元/克',
) {
  const data = rows.map((item, index) => ({
    label: { position: index === 0 ? 'right' : 'top' },
    value: [
      Date.UTC(2000 + Number(item.label.slice(2, 4)), Number(item.label.slice(4, 6)) - 1, 1),
      Number(item.latestValue),
    ],
    name: item.label,
    original: item.latestValue,
  }));
  return {
    animation: false,
    useUTC: true,
    grid: { left: 12, right: 24, top: 46, bottom: 30, containLabel: true },
    tooltip: {
      trigger: 'item',
      confine: true,
      renderMode: 'richText',
      formatter: (point: { data: { name: string; original: unknown } }) =>
        `${point.data.name}\n${point.data.original} ${unit}`,
    },
    xAxis: {
      type: 'time',
      splitNumber: 5,
      minInterval: 60 * 24 * 60 * 60 * 1000,
      axisLabel: {
        fontSize: 12,
        color: '#627488',
        hideOverlap: true,
        formatter: (value: number) => new Date(value).toISOString().slice(2, 7),
      },
      axisLine: { lineStyle: { color: '#d7e0e9' } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      scale: true,
      name: unit,
      splitNumber: 4,
      nameTextStyle: { fontSize: 12, color: '#627488' },
      axisLabel: { fontSize: 12, color: '#627488' },
      splitLine: { lineStyle: { color: '#edf1f5' } },
    },
    series: [
      {
        type: 'line',
        data,
        connectNulls: false,
        smooth: false,
        symbolSize: 7,
        lineStyle: { color, width: 2 },
        itemStyle: { color },
        label: {
          show: true,
          position: 'top',
          fontSize: 12,
          formatter: (point: { dataIndex: number; data: { original: unknown } }) =>
            point.dataIndex === 0 || point.dataIndex === data.length - 1
              ? String(point.data.original)
              : '',
        },
        labelLayout: { hideOverlap: true },
      },
    ],
  };
}

const UNITS: Record<string, string> = {
  percent: '%',
  index: '指数',
  addresses: '地址',
  ratio: '倍',
  contracts: '手',
  tonnes: '吨',
  'troy oz': '金衡盎司',
  usd_million: '百万美元',
  'USD million': '百万美元',
  usd_billion: '十亿美元',
  usd_trillion: '万亿美元',
  persons: '人',
  'USD billion': '十亿美元',
  'USD tn': '万亿美元',
  'USD/share': '美元/份',
};
export const unitText = (unit: string) => UNITS[unit] ?? unit;
export const frequencyText = (frequency: string) =>
  ({
    daily: '日度',
    daily_business_day: '交易日',
    daily_last_collected_snapshot: '每日最新快照',
    weekly: '周度',
    monthly: '月度',
    quarterly: '季度',
    hourly: '小时',
    intraday: '日内',
  }[frequency] ?? frequency);

export function buildSourceSeriesOptions(
  series: MacroDashboardSeries[],
  colors: string[],
  overrideUnit?: string,
) {
  const units = [...new Set(series.map((s) => s.unit))];
  return {
    animation: false,
    useUTC: true,
    color: colors,
    grid: {
      left: 12,
      right: units.length > 1 ? 18 + Math.max(0, units.length - 2) * 65 : 18,
      top: 36,
      bottom: 78,
      containLabel: true,
    },
    tooltip: {
      trigger: 'axis',
      confine: true,
      renderMode: 'richText',
      backgroundColor: '#fff',
      borderColor: '#dbe4ec',
      textStyle: { color: '#24384b', fontSize: 12 },
      axisPointer: { type: 'line', lineStyle: { color: '#8496ab', type: 'dashed' } },
      formatter: (input: unknown) => {
        const items = (Array.isArray(input) ? input : [input]) as Array<{
          seriesIndex: number;
          data: [number, number | null];
        }>;
        return items
          .map((p) => {
            const source = series[p.seriesIndex];
            if (!source || !Array.isArray(p.data)) return '';
            const observation = source.observations.find((r) => Date.parse(r.date) === p.data[0]);
            const day = observation?.date ?? new Date(p.data[0]).toISOString().slice(0, 10);
            const original = observation?.value;
            const label = source.label.match(/.{1,24}/gu)?.join('\n') ?? source.label;
            return `${day}\n${label}\n${original == null ? '—' : original} ${unitText(
              source.unit,
            )}`;
          })
          .filter(Boolean)
          .join('\n\n');
      },
    },
    xAxis: {
      type: 'time',
      splitNumber: 4,
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#d7e0e9' } },
      axisTick: { show: false },
      axisLabel: { color: '#627488', fontSize: 12, hideOverlap: true },
      splitLine: { show: false },
    },
    yAxis: units.map((unit, index) => ({
      type: 'value',
      name: units.length === 1 && overrideUnit ? unitText(overrideUnit) : unitText(unit),
      position: index === 0 ? 'left' : 'right',
      offset: Math.max(0, index - 1) * 65,
      nameGap: 16,
      nameTextStyle: { color: '#627488', fontSize: 12 },
      scale: true,
      splitNumber: 4,
      axisLabel: {
        color: '#627488',
        fontSize: 12,
        hideOverlap: true,
        formatter: (value: number) =>
          new Intl.NumberFormat('en-US', {
            maximumFractionDigits: Math.abs(value) < 0.01 ? 6 : 2,
            notation: Math.abs(value) >= 1000000 ? 'compact' : 'standard',
          }).format(value),
      },
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { show: index === 0, lineStyle: { color: '#edf1f5' } },
    })),
    dataZoom: [
      {
        type: 'slider',
        bottom: 10,
        height: 24,
        start: 0,
        end: 100,
        filterMode: 'none',
        borderColor: '#dce5ee',
        fillerColor: 'rgba(22,93,255,0.1)',
        backgroundColor: '#f5f8fb',
        handleStyle: { color: '#477bc2' },
        textStyle: { fontSize: 11, color: '#627488' },
        showDetail: true,
      },
    ],
    series: series.map((item, index) => ({
      id: item.seriesId,
      name: item.label,
      type: 'line',
      yAxisIndex: units.indexOf(item.unit),
      data: item.observations.map((r) => [
        Date.parse(r.date),
        r.value == null ? null : Number(r.value),
      ]),
      connectNulls: false,
      smooth: false,
      showSymbol: item.observations.filter((r) => r.value != null).length <= 1,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { width: 1.8, color: colors[index] },
      itemStyle: { color: colors[index] },
      emphasis: { focus: 'series' },
    })),
  };
}
