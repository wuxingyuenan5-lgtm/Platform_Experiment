import type { EquityPoint } from '@/api/equityObservatory';
import type { FinanceRow } from './FinancingChart.vue';

export const hkNumber = (value: unknown): number | null =>
  value == null || value === '' || !Number.isFinite(Number(value)) || Number(value) <= 0
    ? null
    : Number(value);

export function compareHongKong(
  prices: EquityPoint[],
  benchmark: EquityPoint[],
  days: number,
): { rows: FinanceRow[]; baseDate: string | null } {
  const left = new Map(prices.map((row) => [row.date, hkNumber(row.value)]));
  const right = new Map(benchmark.map((row) => [row.date, hkNumber(row.value)]));
  let dates = [...left.keys()].filter((date) => right.has(date)).sort();
  if (days && dates.length) {
    const start = new Date(dates.at(-1)! + 'T00:00:00Z');
    start.setUTCDate(start.getUTCDate() - days);
    dates = dates.filter((date) => date >= start.toISOString().slice(0, 10));
  }
  const baseDate = dates.find((date) => left.get(date) != null && right.get(date) != null) || null;
  if (!baseDate) return { rows: [], baseDate: null };
  return {
    baseDate,
    rows: dates.map((date) => ({
      date,
      hongKong:
        date < baseDate || left.get(date) == null
          ? null
          : (left.get(date)! / left.get(baseDate)!) * 100,
      mainland:
        date < baseDate || right.get(date) == null
          ? null
          : (right.get(date)! / right.get(baseDate)!) * 100,
    })),
  };
}
