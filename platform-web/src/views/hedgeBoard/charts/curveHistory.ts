import type { MacroDashboardSeries } from '@/api/hedgeResearch';

export function curveDates(series: MacroDashboardSeries[], latestDate: string) {
  return [...new Set(series.flatMap((item) => item.observations.map((row) => row.date)))]
    .filter((date) => date <= latestDate)
    .sort();
}

export function curveAtDate(
  history: MacroDashboardSeries[],
  current: MacroDashboardSeries[],
  date: string,
  latestDate: string,
) {
  const active = new Set(current.map((item) => item.seriesId));
  return history
    .filter((item) => date !== latestDate || active.has(item.seriesId))
    .flatMap((item) => {
      const point = item.observations.find((row) => row.date === date);
      return point ? [{ ...item, latestValue: point.value, observationDate: date }] : [];
    })
    .sort((a, b) => a.label.localeCompare(b.label));
}
