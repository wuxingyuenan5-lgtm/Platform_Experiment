import { h, type VNode } from 'vue';

import { marketData } from '../nativeData/generated/marketData';

export interface DualChartRow {
  date: string;
  left: number;
  right: number;
}

export interface WeeklyFlowRow {
  date: string;
  northAmerica: number;
  europe: number;
  asia: number;
  other: number;
  goldPrice: number;
}

export const CHART_WIDTH = 760;
export const CHART_HEIGHT = 320;
export const CHART_PADDING = { top: 28, right: 82, bottom: 50, left: 74 } as const;

export const BTC_ETF_FLOW_ROWS: DualChartRow[] = [
  { date: '2026-05-28', left: 112, right: 68240 },
  { date: '2026-05-29', left: 86, right: 67680 },
  { date: '2026-05-30', left: -24, right: 67120 },
  { date: '2026-06-02', left: 158, right: 68860 },
  { date: '2026-06-03', left: 194, right: 69440 },
  { date: '2026-06-04', left: 76, right: 70120 },
  { date: '2026-06-05', left: 142, right: 70980 },
  { date: '2026-06-08', left: 121, right: 71340 },
  { date: '2026-06-09', left: 166, right: 71820 },
  { date: '2026-06-10', left: -18, right: 71260 },
  { date: '2026-06-11', left: 204, right: 72640 },
  { date: '2026-06-12', left: 187, right: 73480 },
];

export const BTC_TREASURY_FLOW_ROWS: ReadonlyArray<Record<string, number | string>> = [
  { date: '2026-03', listed: 18.4, private: 6.1, funds: 4.3 },
  { date: '2026-04', listed: 26.8, private: 7.9, funds: 5.7 },
  { date: '2026-05', listed: 31.2, private: 9.4, funds: 6.6 },
  { date: '2026-06', listed: 24.6, private: 8.7, funds: 5.3 },
  { date: '2026-07', listed: 36.1, private: 10.6, funds: 7.2 },
  { date: '2026-08', listed: 29.7, private: 9.1, funds: 6.2 },
];

export function scaleX(index: number, total: number, innerWidth: number) {
  if (total <= 1) return 0;
  return (index / (total - 1)) * innerWidth;
}

export function scaleY(value: number, min: number, max: number, innerHeight: number) {
  if (max === min) return innerHeight / 2;
  return innerHeight - ((value - min) / (max - min)) * innerHeight;
}

export function getRange(values: number[], includeZero = false) {
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const rawMin = includeZero ? Math.min(0, minValue) : minValue;
  const rawMax = includeZero ? Math.max(0, maxValue) : maxValue;
  const padding = (rawMax - rawMin || 1) * 0.12;
  return { min: rawMin - padding, max: rawMax + padding };
}

export function makeTicks(min: number, max: number, count: number) {
  if (count <= 1) return [min, max];
  return Array.from({ length: count }, (_, index) => min + ((max - min) * index) / (count - 1));
}

export function formatAxis(value: number) {
  return Math.abs(value) >= 100 ? value.toFixed(0) : value.toFixed(2);
}

export function formatNumber(value: number) {
  return Math.abs(value) >= 100 ? value.toFixed(0) : value.toFixed(2);
}

export function formatSigned(value: number) {
  return `${value > 0 ? '+' : ''}${formatNumber(value)}`;
}

export function buildLinePath(
  rows: DualChartRow[],
  getX: (row: DualChartRow, index: number) => number,
  getY: (row: DualChartRow) => number,
) {
  return rows
    .map(
      (row, index) =>
        `${index === 0 ? 'M' : 'L'} ${getX(row, index).toFixed(2)} ${getY(row).toFixed(2)}`,
    )
    .join(' ');
}

export function renderDateLabels(
  rows: DualChartRow[],
  innerWidth: number,
  innerHeight: number,
): Array<VNode | null> {
  const step = Math.max(1, Math.floor(rows.length / 6));
  return rows
    .map((row, index) => {
      if (index % step !== 0 && index !== rows.length - 1) return null;
      return h(
        'text',
        {
          key: `${row.date}-label`,
          x: scaleX(index, rows.length, innerWidth),
          y: innerHeight + 22,
          textAnchor: 'middle',
          class: 'chart-axis-label',
        },
        row.date.slice(5),
      );
    })
    .filter((item): item is VNode => item !== null);
}

export function mergeGoldWithSeries(
  key: 'nominal10Y' | 'real10Y' | 'breakeven10Y',
): DualChartRow[] {
  const goldMap = new Map<string, number>(
    marketData.spdr.history.map((point) => [point.date as string, point.goldPrice]),
  );
  return marketData.treasury.history
    .filter((point) => goldMap.has(point.date as string))
    .slice(-120)
    .map((point) => ({
      date: point.date,
      left: goldMap.get(point.date as string) ?? 0,
      right: point[key],
    }));
}

export function mergeGoldWithGvz(): DualChartRow[] {
  const goldMap = new Map<string, number>(
    marketData.spdr.history.map((point) => [point.date as string, point.goldPrice]),
  );
  return marketData.options.history
    .filter((point) => goldMap.has(point.date as string))
    .slice(-120)
    .map((point) => ({
      date: point.date,
      left: goldMap.get(point.date as string) ?? 0,
      right: point.gvz,
    }));
}

export function buildWeeklyFlowRows(): WeeklyFlowRow[] {
  const goldMap = new Map<string, number>(
    marketData.spdr.history.map((point) => [point.date as string, point.goldPrice]),
  );
  let latestKnownGold: number = marketData.spot.price;
  return marketData.etf.weeklyFlows.map((row) => {
    const date = String(row.date);
    const matchedGold = goldMap.get(date);
    if (typeof matchedGold === 'number') latestKnownGold = matchedGold;
    return {
      date,
      northAmerica: Number(row['North America'] ?? 0),
      europe: Number(row.Europe ?? 0),
      asia: Number(row.Asia ?? 0),
      other: Number(row.Other ?? 0),
      goldPrice: latestKnownGold,
    };
  });
}

export function regionLabel(value: string) {
  switch (value) {
    case 'North America':
      return '北美';
    case 'Europe':
      return '欧洲';
    case 'Asia':
      return '亚洲';
    case 'Other':
      return '其他';
    default:
      return value;
  }
}
