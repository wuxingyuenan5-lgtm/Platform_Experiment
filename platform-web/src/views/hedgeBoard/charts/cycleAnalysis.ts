import type { SeasonalPoint } from './seasonality';

export type PricePoint = { date: string; value: number };
export const dayNumber = (date: string) => Date.parse(date + 'T00:00:00Z') / 86400000;
export const monthKey = (date: string) => date.slice(0, 7);
export function shiftMonth(month: string, n: number) {
  const [y, m] = month.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1 + n, 1)).toISOString().slice(0, 7);
}
export function cleanPoints(input: SeasonalPoint[], positive = true): PricePoint[] {
  const unique = new Map<string, number>();
  for (const p of input) {
    const v = p.value == null || p.value === '' ? NaN : Number(p.value);
    if (/^\d{4}-\d{2}-\d{2}$/.test(p.date) && Number.isFinite(v) && (!positive || v > 0))
      unique.set(p.date, v);
  }
  return [...unique]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, value]) => ({ date, value }));
}
export function monthRange(first: string | undefined, last: string | undefined) {
  const out: string[] = [];
  if (!first || !last) return out;
  for (let month = first; month <= last; month = shiftMonth(month, 1)) out.push(month);
  return out;
}
export function quantile(input: number[], q: number): number | null {
  if (!input.length) return null;
  const a = [...input].sort((x, y) => x - y),
    i = (a.length - 1) * q;
  return a[Math.floor(i)] + (a[Math.ceil(i)] - a[Math.floor(i)]) * (i % 1);
}
export function distribution(a: number[]) {
  return {
    n: a.length,
    mean: a.length ? a.reduce((x, y) => x + y, 0) / a.length : null,
    median: quantile(a, 0.5),
    low: quantile(a, 0.25),
    high: quantile(a, 0.75),
    min: a.length ? Math.min(...a) : null,
    max: a.length ? Math.max(...a) : null,
    win: a.length ? (a.filter((v) => v > 0).length / a.length) * 100 : null,
  };
}
export function monthlyDistributions(input: SeasonalPoint[], start: number, end: number) {
  const points = cleanPoints(input),
    months = new Map<string, PricePoint>();
  for (const p of points) months.set(monthKey(p.date), p);
  // The latest observed month is not treated as a completed month.
  const latest = monthKey(points.at(-1)?.date || '');
  return Array.from({ length: 12 }, (_, i) => {
    const samples: number[] = [];
    for (const [key, p] of months) {
      const year = Number(key.slice(0, 4));
      if (year < start || year > end || Number(key.slice(5)) !== i + 1 || key >= latest) continue;
      const previous = months.get(shiftMonth(key, -1));
      const monthEnd = dayNumber(shiftMonth(key, 1) + '-01') - 1;
      const previousEnd = dayNumber(key + '-01') - 1;
      if (
        previous &&
        monthEnd - dayNumber(p.date) <= 7 &&
        previousEnd - dayNumber(previous.date) <= 7
      )
        samples.push((p.value / previous.value - 1) * 100);
    }
    return { month: i + 1, ...distribution(samples) };
  });
}

export interface DrawdownEpisode {
  peak: string;
  trough: string;
  end: string;
  recovered: boolean;
  depth: number;
  fallingDays: number;
  recoveryDays: number | null;
  underwaterDays: number;
  gap: boolean;
  curve: { day: number; value: number | null }[];
}
export function drawdownCycles(input: SeasonalPoint[], threshold = 10) {
  const points = cleanPoints(input),
    episodes: DrawdownEpisode[] = [];
  let peak = 0,
    trough = 0,
    inDrawdown = false;
  function append(last: number, recovered: boolean) {
    const depth = (points[trough].value / points[peak].value - 1) * 100;
    if (-depth + 1e-9 < threshold) return;
    let gap = false;
    const curve = points.slice(peak, last + 1).flatMap((p, i, a) => {
      const day = dayNumber(p.date) - dayNumber(points[peak].date);
      const missing = i > 0 && dayNumber(p.date) - dayNumber(a[i - 1].date) > 7;
      gap ||= missing;
      return [
        ...(missing ? [{ day: day - 1, value: null }] : []),
        { day, value: (p.value / points[peak].value - 1) * 100 },
      ];
    });
    episodes.push({
      peak: points[peak].date,
      trough: points[trough].date,
      end: points[last].date,
      recovered,
      depth,
      fallingDays: dayNumber(points[trough].date) - dayNumber(points[peak].date),
      recoveryDays: recovered
        ? dayNumber(points[last].date) - dayNumber(points[trough].date)
        : null,
      underwaterDays: dayNumber(points[last].date) - dayNumber(points[peak].date),
      gap,
      curve,
    });
  }
  for (let i = 1; i < points.length; i++) {
    if (points[i].value >= points[peak].value) {
      if (inDrawdown) append(i, true);
      peak = trough = i;
      inDrawdown = false;
    } else {
      inDrawdown = true;
      if (points[i].value < points[trough].value) trough = i;
    }
  }
  if (inDrawdown) append(points.length - 1, false);
  return {
    episodes,
    current: points.length ? (points.at(-1)!.value / points[peak].value - 1) * 100 : null,
    peakDate: points[peak]?.date,
    latest: points.at(-1)?.date,
    recoveryMedian: quantile(
      episodes.filter((e) => e.recovered && !e.gap).map((e) => e.underwaterDays),
      0.5,
    ),
  };
}

export function monthlyLevels(input: SeasonalPoint[]) {
  const out = new Map<string, PricePoint>();
  for (const p of cleanPoints(input, false)) out.set(monthKey(p.date), p);
  return out;
}
export const regimeNames = ['增长↑ / 通胀↓', '增长↑ / 通胀↑', '增长↓ / 通胀↑', '增长↓ / 通胀↓'];
export function economicRegimes(growth: SeasonalPoint[], inflation: SeasonalPoint[]) {
  const g = monthlyLevels(growth),
    c = monthlyLevels(inflation);
  return [...g.keys()]
    .filter((m) => [0, -1, -2, -3].every((n) => g.has(shiftMonth(m, n)) && c.has(shiftMonth(m, n))))
    .map((month) => {
      const growthDelta = g.get(month)!.value - g.get(shiftMonth(month, -3))!.value;
      const inflationDelta = c.get(month)!.value - c.get(shiftMonth(month, -3))!.value;
      const regime =
        growthDelta === 0 || inflationDelta === 0
          ? -1
          : growthDelta > 0
          ? inflationDelta > 0
            ? 1
            : 0
          : inflationDelta > 0
          ? 2
          : 3;
      return {
        month,
        growth: g.get(month)!.value,
        inflation: c.get(month)!.value,
        growthDelta,
        inflationDelta,
        regime,
      };
    });
}
export function monthReturn(
  prices: SeasonalPoint[],
  month: string,
  horizon: number,
): number | null {
  return returnFromMonths(
    monthlyLevels(prices),
    monthKey(cleanPoints(prices).at(-1)?.date || ''),
    month,
    horizon,
  );
}
function returnFromMonths(
  a: Map<string, PricePoint>,
  last: string,
  month: string,
  horizon: number,
): number | null {
  const end = shiftMonth(month, horizon),
    start = horizon ? month : shiftMonth(month, -1);
  const b = a.get(start),
    e = a.get(end);
  if (!b || !e || b.value <= 0 || e.value <= 0 || end >= last) return null;
  // Require each intermediate month and a genuine month-end observation.
  for (let m = start; m <= end; m = shiftMonth(m, 1)) {
    const p = a.get(m);
    if (!p || dayNumber(shiftMonth(m, 1) + '-01') - 1 - dayNumber(p.date) > 7) return null;
  }
  return (e.value / b.value - 1) * 100;
}
export function conditionalReturns(
  prices: SeasonalPoint[],
  regimes: { month: string; regime: number }[],
  horizon = 0,
) {
  const monthly = monthlyLevels(prices),
    last = monthKey(cleanPoints(prices).at(-1)?.date || '');
  return regimeNames.map((name, index) => ({
    name,
    ...distribution(
      regimes.flatMap((r) => {
        const v = r.regime === index ? returnFromMonths(monthly, last, r.month, horizon) : null;
        return v == null ? [] : [v];
      }),
    ),
  }));
}
export function policyTurns(input: SeasonalPoint[]) {
  const p = cleanPoints(input, false),
    events: { date: string; direction: number; rate: number }[] = [];
  let direction = 0,
    lastChange = '';
  for (let i = 1; i < p.length; i++) {
    if (dayNumber(p[i].date) - dayNumber(p[i - 1].date) > 7) {
      direction = 0;
      continue;
    }
    const change = Math.sign(p[i].value - p[i - 1].value);
    if (change) {
      if (change !== direction)
        events.push({ date: p[i].date, direction: change, rate: p[i].value });
      direction = change;
      lastChange = p[i].date;
    }
  }
  return { events, direction, lastChange, latest: p.at(-1) };
}
export function eventReturn(prices: SeasonalPoint[], date: string, months: number): number | null {
  const p = cleanPoints(prices),
    base = p.filter((x) => x.date < date).at(-1);
  const targetDate = new Date(date + 'T00:00:00Z');
  const day = targetDate.getUTCDate();
  targetDate.setUTCDate(1);
  targetDate.setUTCMonth(targetDate.getUTCMonth() + months);
  const lastDay = new Date(
    Date.UTC(targetDate.getUTCFullYear(), targetDate.getUTCMonth() + 1, 0),
  ).getUTCDate();
  targetDate.setUTCDate(Math.min(day, lastDay));
  const target = targetDate.toISOString().slice(0, 10),
    end = p.find((x) => x.date >= target);
  if (
    !base ||
    !end ||
    dayNumber(date) - dayNumber(base.date) > 7 ||
    dayNumber(end.date) - dayNumber(target) > 7
  )
    return null;
  if (
    p.some(
      (x, i) =>
        i &&
        x.date > base.date &&
        x.date <= end.date &&
        dayNumber(x.date) - dayNumber(p[i - 1].date) > 7,
    )
  )
    return null;
  return (end.value / base.value - 1) * 100;
}
export function driverRegimes(first: SeasonalPoint[], second: SeasonalPoint[]) {
  const a = monthlyLevels(first),
    b = monthlyLevels(second);
  return [...a.keys()].flatMap((month) => {
    const prior = shiftMonth(month, -3);
    if (![0, -1, -2, -3].every((n) => a.has(shiftMonth(month, n)) && b.has(shiftMonth(month, n))))
      return [];
    const da = a.get(month)!.value - a.get(prior)!.value,
      db = b.get(month)!.value - b.get(prior)!.value;
    if (!da || !db) return [];
    return [{ month, regime: da > 0 ? (db > 0 ? 1 : 0) : db > 0 ? 2 : 3 }];
  });
}
export function rotation(input: { id: string; observations: SeasonalPoint[] }[], months: number) {
  const maps = input.map((s) => ({ id: s.id, points: monthlyLevels(s.observations) }));
  const lastMonths = input.map((s) => monthKey(cleanPoints(s.observations).at(-1)?.date || ''));
  const common = maps.length
    ? [...maps[0].points.keys()]
        .filter((m) => maps.every((s) => s.points.has(m)) && lastMonths.every((last) => m < last))
        .sort()
    : [];
  const history = common.flatMap((month) => {
    const base = shiftMonth(month, -months);
    if (
      !maps.every((s) => {
        for (let m = base; m <= month; m = shiftMonth(m, 1)) {
          const p = s.points.get(m);
          if (!p || p.value <= 0 || dayNumber(shiftMonth(m, 1) + '-01') - 1 - dayNumber(p.date) > 7)
            return false;
        }
        return true;
      })
    )
      return [];
    const ranks = maps
      .map((s) => ({
        id: s.id,
        value: (s.points.get(month)!.value / s.points.get(base)!.value - 1) * 100,
      }))
      .sort((a, b) => b.value - a.value);
    return [{ month, ranks }];
  });
  return { history, latest: history.at(-1) };
}

export function correlationWindows(input: { id: string; observations: SeasonalPoint[] }[]) {
  const maps = input.map((s) => ({
    id: s.id,
    points: new Map(cleanPoints(s.observations).map((p) => [p.date, p.value])),
  }));
  const dates = maps.length
    ? [...maps[0].points.keys()].filter((d) => maps.every((s) => s.points.has(d))).sort()
    : [];
  let start = 0;
  for (let i = 1; i < dates.length; i++)
    if (dayNumber(dates[i]) - dayNumber(dates[i - 1]) > 7) start = i;
  const common = dates.slice(start),
    returns = maps.map((s) =>
      common.slice(1).map((d, i) => s.points.get(d)! / s.points.get(common[i])! - 1),
    );
  const pairs: { first: string; second: string; n20: number | null; n60: number | null }[] = [];
  function corr(a: number[], b: number[], n: number) {
    if (a.length < n || b.length < n) return null;
    const x = a.slice(-n),
      y = b.slice(-n),
      mx = x.reduce((s, v) => s + v, 0) / n,
      my = y.reduce((s, v) => s + v, 0) / n;
    const xx = x.reduce((s, v) => s + (v - mx) ** 2, 0),
      yy = y.reduce((s, v) => s + (v - my) ** 2, 0);
    return xx && yy
      ? x.reduce((s, v, i) => s + (v - mx) * (y[i] - my), 0) / Math.sqrt(xx * yy)
      : null;
  }
  for (let i = 0; i < maps.length; i++)
    for (let j = i + 1; j < maps.length; j++)
      pairs.push({
        first: maps[i].id,
        second: maps[j].id,
        n20: corr(returns[i], returns[j], 20),
        n60: corr(returns[i], returns[j], 60),
      });
  return { date: common.at(-1), pairs };
}
