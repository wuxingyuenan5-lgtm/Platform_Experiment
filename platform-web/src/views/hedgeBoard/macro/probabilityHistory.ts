import type { MacroProbabilityPoint } from '@/api/hedgeResearch';

export function probabilityHistory(history: MacroProbabilityPoint[]) {
  const points = history
    .filter((point) => point.probability != null && String(point.probability).trim() !== '')
    .map((point) => ({ time: Date.parse(point.observedAt), value: Number(point.probability) }))
    .filter(
      (point) =>
        Number.isFinite(point.time) &&
        Number.isFinite(point.value) &&
        point.value >= 0 &&
        point.value <= 100,
    )
    .sort((a, b) => a.time - b.time);
  const first = points[0];
  const last = points[points.length - 1];
  const span = first && last ? last.time - first.time : 0;
  const coordinates = points.map((point) => ({
    x: span ? ((point.time - first.time) / span) * 220 : 110,
    y: 72 - point.value * 0.72,
  }));
  const change = (days: number) => {
    if (!last) return null;
    const cutoff = last.time - days * 86_400_000;
    const prior = [...points].reverse().find((point) => point.time <= cutoff);
    // A months-old observation is not a one-day or seven-day comparison.
    return prior && cutoff - prior.time <= 86_400_000 ? last.value - prior.value : null;
  };
  return {
    points: coordinates.map((point) => `${point.x.toFixed(2)},${point.y.toFixed(2)}`).join(' '),
    single: coordinates.length === 1 ? coordinates[0] : null,
    count: points.length,
    firstAt: first?.time,
    lastAt: last?.time,
    change1d: change(1),
    change7d: change(7),
  };
}
