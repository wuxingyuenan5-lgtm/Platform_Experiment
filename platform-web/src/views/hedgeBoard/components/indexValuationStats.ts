import type { EquityValue } from '@/api/equityObservatory';

export interface ValuePoint {
  date: string;
  value: EquityValue;
}
export const finiteValue = (v: unknown): number | null =>
  v == null || v === '' || !Number.isFinite(Number(v)) ? null : Number(v);
export function valuationWindow(history: ValuePoint[], years: number, asOf: string) {
  const end = new Date(asOf + 'T00:00:00Z');
  const y = end.getUTCFullYear() - years,
    month = end.getUTCMonth();
  const day = Math.min(end.getUTCDate(), new Date(Date.UTC(y, month + 1, 0)).getUTCDate());
  const start = years ? new Date(Date.UTC(y, month, day)).toISOString().slice(0, 10) : '';
  return [
    ...new Map(
      history.filter((p) => p.date <= asOf && p.date >= start).map((p) => [p.date, p]),
    ).values(),
  ].sort((a, b) => a.date.localeCompare(b.date));
}
export function valuationStats(
  history: ValuePoint[],
  years: number,
  asOf: string,
  zeroValid = false,
) {
  const window = valuationWindow(history, years, asOf);
  const valid = window.filter(
    (p) => finiteValue(p.value) != null && (zeroValid ? Number(p.value) >= 0 : Number(p.value) > 0),
  );
  const latest = window.at(-1);
  const value = finiteValue(latest?.value);
  const eligible = value != null && (zeroValid ? value >= 0 : value > 0);
  const values = valid.map((p) => Number(p.value)).sort((a, b) => a - b);
  const quantile = (p: number) => {
    if (!values.length) return null;
    const k = (values.length - 1) * p,
      i = Math.floor(k);
    return values[i] + (values[Math.ceil(k)] - values[i]) * (k - i);
  };
  const gaps = valid
    .slice(1)
    .map((p, i) => (Date.parse(p.date) - Date.parse(valid[i].date)) / 86400000)
    .sort((a, b) => a - b);
  const gap = gaps[Math.floor(gaps.length / 2)] || 1;
  const minimum = gap <= 7 ? 252 : gap <= 45 ? 36 : gap <= 120 ? 12 : 5;
  const rank =
    eligible && values.length >= minimum
      ? ((values.filter((v) => v < value!).length + values.filter((v) => v === value).length / 2) /
          values.length) *
        100
      : null;
  return {
    latest,
    value,
    rank,
    count: values.length,
    minimum,
    start: valid[0]?.date,
    end: valid.at(-1)?.date,
    min: values[0] ?? null,
    max: values.at(-1) ?? null,
    p20: quantile(0.2),
    median: quantile(0.5),
    p80: quantile(0.8),
  };
}

export type ValuationCadence = 'observation' | 'week' | 'month';
// Display sampling only. Statistics always use the original observations.
export function valuationSample(history: ValuePoint[], cadence: ValuationCadence) {
  const rows = [...history].sort((a, b) => a.date.localeCompare(b.date));
  if (cadence === 'observation') return rows;
  const buckets = new Map<string, ValuePoint>();
  for (const point of rows) {
    const day = new Date(point.date + 'T00:00:00Z');
    if (cadence === 'week') day.setUTCDate(day.getUTCDate() - ((day.getUTCDay() + 6) % 7));
    const key = cadence === 'month' ? point.date.slice(0, 7) : day.toISOString().slice(0, 10);
    buckets.set(key, point);
  }
  return [...buckets.values()];
}
