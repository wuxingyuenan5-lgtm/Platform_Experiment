export type FlowLevel = 'daily' | 'weekly' | 'monthly';
export interface BroadFlowInput {
  dates: string[];
  cats: string[];
  colors: string[];
  series: Record<string, Array<number | string | null>>;
  historyScope?: string;
  coverage?: Record<
    string,
    Record<string, { expected: number; covered: number; missingCodes?: string[] }>
  >;
}
export interface IndexPrices {
  [key: string]: { name: string; rows: Array<{ date: string; close: number | string | null }> };
}
export interface FlowPeriod {
  date: string;
  from: string;
  values: Record<string, number | null>;
  total: number | null;
  cumulative: number | null;
  prices: Record<string, number | null>;
  priceDate?: string;
  qualityNote?: string;
}
export const maxIndexOffset = 10000;
export const offsetUnit = (level: FlowLevel) =>
  ({ daily: '交易日', weekly: '周', monthly: '月' }[level]);
export function offsetDescription(offset: number, level: FlowLevel): string {
  return offset ? `${offset > 0 ? '后移' : '前移'}${Math.abs(offset)}${offsetUnit(level)}` : '';
}
export const indexChoices = [
  { key: 'hs300', label: '沪深300', color: '#d18a30' },
  { key: 'csi1000', label: '中证1000', color: '#336fcc' },
  { key: 'star50', label: '科创50', color: '#9561bd' },
  { key: 'chinext', label: '创业板指', color: '#138975' },
];
export const numeric = (value: unknown): number | null =>
  value == null || value === '' || !Number.isFinite(Number(value)) ? null : Number(value);
export function flowDailyAverage(value: unknown, sessions: number): number | null {
  const total = numeric(value);
  return total == null || !Number.isInteger(sessions) || sessions < 1 ? null : total / sessions;
}
export function rangeStart(last: string, days: number): string {
  if (!days || !last) return '';
  const date = new Date(last + 'T00:00:00Z');
  if (days === 1095) date.setUTCFullYear(date.getUTCFullYear() - 3);
  else if (days === 365) date.setUTCFullYear(date.getUTCFullYear() - 1);
  else date.setUTCDate(date.getUTCDate() - days);
  return date.toISOString().slice(0, 10);
}
function bucket(day: string, level: FlowLevel): string {
  if (level === 'daily') return day;
  if (level === 'monthly') return day.slice(0, 7);
  const date = new Date(day + 'T00:00:00Z');
  date.setUTCDate(date.getUTCDate() - ((date.getUTCDay() + 6) % 7));
  return date.toISOString().slice(0, 10);
}
export function flowPeriods(
  data: BroadFlowInput,
  indices: IndexPrices,
  level: FlowLevel,
  range: number,
): FlowPeriod[] {
  const cutoff = rangeStart(data.dates.at(-1) || '', range);
  const priceMaps = Object.fromEntries(
    Object.entries(indices).map(([key, value]) => [
      key,
      new Map(value.rows.map((row) => [row.date, numeric(row.close)])),
    ]),
  );
  const groups = new Map<string, number[]>();
  data.dates.forEach((day, i) => {
    if (day < cutoff) return;
    const key = bucket(day, level);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(i);
  });
  let cumulative: number | null = 0;
  return [...groups.values()].map((positions) => {
    const first = positions[0],
      last = positions.at(-1)!;
    const values = Object.fromEntries(
      data.cats.map((category) => {
        const points = positions.map((i) => numeric(data.series[category]?.[i]));
        const valid = points.filter((v): v is number => v != null);
        return [category, valid.length ? valid.reduce((sum, v) => sum + v, 0) : null];
      }),
    );
    const items = Object.values(values);
    const known = items.filter((v): v is number => v != null);
    const allUnknown = positions.every((i) => {
      const groups = Object.values(data.coverage?.[data.dates[i]] || {});
      return groups.length && groups.every((g) => g.covered === 0);
    });
    const total = known.length && !allUnknown ? known.reduce((sum, v) => sum + v, 0) : null;
    const partialDates = positions.filter(
      (i) =>
        data.cats.some(
          (cat) =>
            numeric(data.series[cat]?.[i]) == null &&
            data.coverage?.[data.dates[i]]?.[cat]?.expected !== 0,
        ) ||
        Object.values(data.coverage?.[data.dates[i]] || {}).some((c) => c.covered < c.expected),
    );
    cumulative = cumulative == null || total == null ? null : cumulative + total;
    return {
      date: data.dates[last],
      from: data.dates[first],
      values,
      total,
      cumulative,
      ...(partialDates.length
        ? { qualityNote: `${partialDates.length}个交易日覆盖不完整，按已取得成员汇总` }
        : {}),
      prices: Object.fromEntries(
        indexChoices.map(({ key }) => [key, priceMaps[key]?.get(data.dates[last]) ?? null]),
      ),
    };
  });
}

export function offsetFlowPeriods(
  rows: FlowPeriod[],
  offset: number,
  level: FlowLevel,
): FlowPeriod[] {
  if (!rows.length || !offset || !Number.isInteger(offset) || Math.abs(offset) > maxIndexOffset)
    return rows;
  const start = Math.min(0, offset);
  const end = rows.length + Math.max(0, offset);
  return Array.from({ length: end - start }, (_, position) => {
    const i = position + start;
    const cash = rows[i];
    const price = rows[i - offset];
    const date =
      cash?.date ||
      (i < 0
        ? `${rows[0].date} 前${-i}${offsetUnit(level)}`
        : `${rows.at(-1)!.date} 后${i - rows.length + 1}${offsetUnit(level)}`);
    return {
      date,
      from: cash?.from || date,
      values: cash?.values || Object.fromEntries(Object.keys(rows[0].values).map((k) => [k, null])),
      total: cash?.total ?? null,
      cumulative: cash?.cumulative ?? null,
      prices: price?.prices || {},
      priceDate: price?.date,
      ...(cash?.qualityNote ? { qualityNote: cash.qualityNote } : {}),
    };
  });
}

export function flowChartOption(
  rows: FlowPeriod[],
  data: BroadFlowInput,
  selected: string[],
  level: FlowLevel,
  indexOffset = 0,
) {
  const offset = selected.length ? indexOffset : 0;
  rows = offsetFlowPeriods(rows, offset, level);
  const shifted = offsetDescription(offset, level);
  const period = { daily: '当日', weekly: '当周', monthly: '当月' }[level];
  return {
    animation: false,
    legend: { top: 0, type: 'scroll', itemWidth: 12, itemHeight: 9, textStyle: { fontSize: 11 } },
    grid: { top: 65, left: 72, right: selected.length ? 150 : 76, bottom: 66 },
    tooltip: {
      trigger: 'axis',
      confine: true,
      valueFormatter: (v: unknown) =>
        numeric(v) == null ? '—' : Number(v).toLocaleString('zh-CN', { maximumFractionDigits: 2 }),
      renderMode: shifted ? 'richText' : 'html',
      formatter: (
        params: Array<{
          dataIndex: number;
          seriesIndex: number;
          seriesName: string;
          value: unknown;
          marker?: string;
        }>,
      ) => {
        const row = rows[params[0]?.dataIndex];
        if (!row) return '';
        const total = numeric(row.total);
        const lines = [
          row?.date || '',
          `${period}合计净流入：${
            total == null ? '—' : total.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
          } 亿元`,
          ...params.map((p) => {
            const isPrice = p.seriesIndex > data.cats.length;
            const value = numeric(p.value);
            return `${p.seriesName}：${
              value == null ? '—' : value.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
            }${isPrice ? ' 点' : ' 亿元'}${
              isPrice && row?.priceDate ? `（原日期 ${row.priceDate}）` : ''
            }`;
          }),
          ...(row.qualityNote ? [row.qualityNote] : []),
        ];
        if (shifted) return lines.join('\n');
        const escape = (text: string) =>
          text.replace(
            /[&<>"']/g,
            (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]!),
          );
        return lines
          .map((text, i) =>
            i === 1
              ? `<strong>${escape(text)}</strong>`
              : `${i > 1 ? params[i - 2]?.marker || '' : ''}${escape(text)}`,
          )
          .join('<br/>');
      },
    },
    xAxis: { type: 'category', data: rows.map((r) => r.date), axisLabel: { hideOverlap: true } },
    yAxis: [
      {
        type: 'value',
        name: `${period}净流入（亿元）`,
        splitLine: { lineStyle: { color: '#e6edf5' } },
      },
      {
        type: 'value',
        name: '累计（亿元）',
        nameTextStyle: { align: 'left', fontSize: 11 },
        position: 'right',
        splitLine: { show: false },
      },
      {
        type: 'value',
        name: '指数（点）',
        nameTextStyle: { align: 'left', fontSize: 11 },
        position: 'right',
        offset: 80,
        scale: true,
        show: selected.length > 0,
        splitLine: { show: false },
      },
    ],
    dataZoom: [
      { type: 'inside', zoomOnMouseWheel: 'ctrl', moveOnMouseWheel: false },
      { type: 'slider', height: 20, bottom: 10 },
    ],
    series: [
      ...data.cats.map((name, i) => ({
        name,
        type: 'bar',
        stack: 'flows',
        data: rows.map((r) => r.values[name]),
        itemStyle: { color: data.colors[i % data.colors.length] },
      })),
      {
        name: '累计净流入',
        type: 'line',
        yAxisIndex: 1,
        data: rows.map((r) => r.cumulative),
        showSymbol: false,
        connectNulls: false,
        itemStyle: { color: '#243648' },
        lineStyle: { width: 2 },
      },
      ...indexChoices
        .filter((item) => selected.includes(item.key))
        .map((item) => ({
          name: `${item.label}价格${shifted ? `（${shifted}）` : ''}`,
          type: 'line',
          yAxisIndex: 2,
          data: rows.map((r) => r.prices[item.key] ?? null),
          showSymbol: false,
          connectNulls: false,
          itemStyle: { color: item.color },
          lineStyle: { width: 1.6 },
        })),
    ],
  };
}
