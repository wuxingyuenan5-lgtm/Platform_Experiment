import type { MacroDashboardSeries } from '@/api/hedgeResearch';

export function periodValues(series: MacroDashboardSeries): Map<string, number | null> {
  const values = new Map<string, number | null>();
  if (!['monthly', 'quarterly'].includes(series.frequency)) return values;
  // Source observation periods, never release dates or filled weekly averages.
  for (const row of [...series.observations].sort((a, b) => a.date.localeCompare(b.date))) {
    const value = row.value === null ? null : Number(row.value);
    if (/^\d{4}-\d{2}-\d{2}$/.test(row.date) && (value === null || Number.isFinite(value))) {
      values.set(row.date.slice(0, 7), value);
    }
  }
  return values;
}

export function precedingPeriod(month: string, frequency: string): string {
  const [year, part] = month.split('-').map(Number);
  const ordinal = year * 12 + part - 1 - (frequency === 'quarterly' ? 3 : 1);
  return `${Math.floor(ordinal / 12)}-${String((ordinal % 12) + 1).padStart(2, '0')}`;
}

export function periodDelta(series: MacroDashboardSeries): number | null {
  const values = periodValues(series);
  const latest = [...values.keys()].sort().at(-1);
  if (!latest) return null;
  const value = values.get(latest);
  const previous = values.get(precedingPeriod(latest, series.frequency));
  return value == null || previous == null ? null : value - previous;
}

export function pulseMonths(end: string, count = 12): string[] {
  const [year, month] = end.split('-').map(Number);
  const ordinal = year * 12 + month - 1;
  return Array.from({ length: count }, (_, i) => {
    const value = ordinal - i;
    return `${Math.floor(value / 12)}-${String((value % 12) + 1).padStart(2, '0')}`;
  });
}

export function pulseColor(value: number | null | undefined, history: (number | null)[]): string {
  if (value == null || !Number.isFinite(value)) return 'transparent';
  const valid = history.filter((item): item is number => item !== null && Number.isFinite(item));
  if (valid.length < 6) return 'transparent';
  const min = Math.min(...valid),
    max = Math.max(...valid);
  if (max === min) return 'transparent';
  const relative = ((value - min) / (max - min) - 0.5) * 2;
  return relative >= 0
    ? `rgba(220, 38, 38, ${Math.min(0.22, relative * 0.22)})`
    : `rgba(22, 93, 255, ${Math.min(0.2, -relative * 0.2)})`;
}
