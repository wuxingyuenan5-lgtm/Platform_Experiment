import type { EtfRow, EtfValue } from '@/api/etfTracking';

export const numeric = (value: EtfValue | undefined): number | null =>
  value == null || value === '' || !Number.isFinite(Number(value)) ? null : Number(value);
export function total(rows: EtfRow[], key: string): number | null {
  const values = rows.map((row) => numeric(row[key]));
  return values.length && values.every((v) => v != null)
    ? values.reduce<number>((sum, v) => sum + v!, 0)
    : null;
}
export function trailingSummary(rows: EtfRow[], count: number) {
  const selected = rows.slice(-count);
  const previous = numeric(rows[rows.length - count - 1]?.etf_qfq_close);
  const close = numeric(rows.at(-1)?.etf_qfq_close);
  return {
    count,
    start: selected[0]?.date || '',
    end: selected.at(-1)?.date || '',
    change: previous && close != null ? (close / previous - 1) * 100 : null,
    turnover: selected.length === count ? total(selected, 'etf_qfq_turnover_est_yi') : null,
    flow: selected.length === count ? total(selected, 'flow_yi') : null,
  };
}
export function ranged(rows: EtfRow[], start: string, end: string) {
  return rows.filter((row) => (!start || row.date >= start) && (!end || row.date <= end));
}
export function balanceChange(rows: EtfRow[], start: string, end: string, field: string) {
  const period = ranged(rows, start, end);
  const previous = rows.filter((row) => row.date < start).at(-1);
  const first = numeric(previous?.[field]),
    last = numeric(period.at(-1)?.[field]);
  return first != null && last != null && period.at(-1)?.date === end ? last - first : null;
}
export function alignDates(rows: EtfRow[], dates: string[]): EtfRow[] {
  const byDate = new Map(rows.map((row) => [row.date, row]));
  return dates.map((date) => byDate.get(date) || { date });
}
