export interface SeasonalPoint {
  date: string;
  value?: number | string | null;
}
export function seasonalRows(input: SeasonalPoint[]) {
  const points = input
    .filter(
      (p) =>
        p.value != null &&
        Number.isFinite(Number(p.value)) &&
        Number(p.value) > 0 &&
        /^\d{4}-\d{2}-\d{2}$/.test(p.date),
    )
    .sort((a, b) => a.date.localeCompare(b.date));
  const monthly = new Map<string, SeasonalPoint>();
  for (const p of points) monthly.set(p.date.slice(0, 7), p);
  const years = [...new Set(points.map((p) => Number(p.date.slice(0, 4))))];
  const latest = points.at(-1)?.date || '';
  return years.map((year) => {
    const base = monthly.get(`${year - 1}-12`);
    const months = Array.from({ length: 12 }, (_, i) => {
      const key = `${year}-${String(i + 1).padStart(2, '0')}`;
      const previous = i ? `${year}-${String(i).padStart(2, '0')}` : `${year - 1}-12`;
      const a = monthly.get(previous),
        b = monthly.get(key);
      return a && b ? (Number(b.value) / Number(a.value) - 1) * 100 : null;
    });
    const last = points.filter((p) => p.date.startsWith(String(year))).at(-1);
    return {
      year,
      months,
      annual: base && last ? (Number(last.value) / Number(base.value) - 1) * 100 : null,
      partial: year === new Date().getUTCFullYear(),
      latest,
      curve: base
        ? points
            .filter((p) => p.date.startsWith(String(year)))
            .map((p) => ({
              date: p.date.slice(5),
              value: (Number(p.value) / Number(base.value) - 1) * 100,
            }))
        : [],
    };
  });
}
