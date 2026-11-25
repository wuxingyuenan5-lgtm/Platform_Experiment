export interface ThemeFund {
  code: string;
  name: string;
  theme: string;
  scope: string;
  series: Array<{ date: string; units: string | null }>;
  delta: string | null;
  changePct: string | null;
  delta20?: string | null;
  change20Pct?: string | null;
}
export interface ThemePanorama {
  funds: ThemeFund[];
  themes: Array<ThemeFund & { members: string[] }>;
  date: string | null;
  start: string | null;
  start20?: string | null;
  source: string;
  status: string;
}
export function themeChartData(funds: ThemeFund[], range: number, indexed: boolean) {
  const allDates = [...new Set(funds.flatMap((f) => f.series.map((p) => p.date)))].sort();
  const end = allDates.at(-1);
  const cutoff =
    end && range ? new Date(Date.parse(end) - range * 86400000).toISOString().slice(0, 10) : '';
  const dates = allDates.filter((d) => d >= cutoff);
  const colors = [
    '#2563eb',
    '#059669',
    '#d09a15',
    '#7c3aed',
    '#e11d48',
    '#64748b',
    '#0891b2',
    '#d97706',
    '#4f46e5',
    '#16a34a',
    '#9333ea',
    '#0d9488',
    '#be123c',
    '#475569',
  ];
  const series = funds.map((fund, index) => {
    const points = new Map(
      fund.series.map((p) => [p.date, p.units == null ? null : Number(p.units)]),
    );
    const baseline = dates
      .map((d) => points.get(d))
      .find((v) => v != null && Number.isFinite(v) && v > 0);
    return { key: `theme${fund.code || index}`, points, baseline };
  });
  return {
    rows: dates.map(
      (date) =>
        Object.fromEntries([
          ['date', date],
          ...series.map(({ key, points, baseline }) => {
            const v = points.get(date);
            return [
              key,
              v == null || !Number.isFinite(v)
                ? null
                : indexed
                ? baseline
                  ? (v / baseline) * 100
                  : null
                : v,
            ];
          }),
        ]) as { date: string; [key: string]: string | number | null },
    ),
    lines: funds.map((fund, index) => ({
      key: `theme${fund.code || index}`,
      name: fund.name,
      unit: indexed ? '首日=100' : '亿份',
      color: colors[index % colors.length],
    })),
  };
}
