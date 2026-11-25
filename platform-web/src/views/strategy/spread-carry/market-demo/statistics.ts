import { HOUR, quantile, type Observation, type Episode, type Direction } from './marketDemo';

export const STEP = HOUR / 2;
export const mean = (values: number[]) =>
  values.length ? values.reduce((a, b) => a + b, 0) / values.length : null;
export function describe(values: number[]) {
  const clean = values.filter(Number.isFinite);
  const n = clean.length,
    avg = mean(clean),
    median = quantile(clean, 0.5);
  const sumSquares = avg === null ? 0 : clean.reduce((sum, v) => sum + (v - avg) ** 2, 0);
  const variance = n > 1 ? sumSquares / (n - 1) : null;
  const moment2 = n ? sumSquares / n : 0;
  return {
    n,
    mean: avg,
    median,
    std: variance === null ? null : Math.sqrt(variance),
    min: n ? Math.min(...clean) : null,
    max: n ? Math.max(...clean) : null,
    p01: quantile(clean, 0.01),
    p05: quantile(clean, 0.05),
    p10: quantile(clean, 0.1),
    p25: quantile(clean, 0.25),
    p75: quantile(clean, 0.75),
    p90: quantile(clean, 0.9),
    p95: quantile(clean, 0.95),
    p99: quantile(clean, 0.99),
    mad:
      median === null
        ? null
        : quantile(
            clean.map((v) => Math.abs(v - median)),
            0.5,
          ),
    skew:
      n >= 20 && moment2 > 0
        ? clean.reduce((sum, v) => sum + (v - avg!) ** 3, 0) / n / moment2 ** 1.5
        : null,
    excessKurtosis:
      n >= 20 && moment2 > 0
        ? clean.reduce((sum, v) => sum + (v - avg!) ** 4, 0) / n / moment2 ** 2 - 3
        : null,
  };
}

export function histogram(values: number[], count = 20) {
  const data = values.filter(Number.isFinite);
  if (!data.length) return [];
  const min = Math.min(...data),
    max = Math.max(...data);
  const lower = min === max ? min - 0.5 : min;
  const width = (min === max ? 1 : max - min) / count;
  const bins = Array.from({ length: count }, (_, i) => ({
    low: lower + i * width,
    high: lower + (i + 1) * width,
    count: 0,
  }));
  data.forEach(
    (v) => bins[Math.min(count - 1, Math.max(0, Math.floor((v - lower) / width)))].count++,
  );
  return bins;
}

export function contiguousPairs(rows: Observation[], lag = 1) {
  const pairs: { x: number; y: number; time: number }[] = [];
  let run = 0;
  for (let i = 0; i < rows.length; i++) {
    if (!Number.isFinite(rows[i].mid)) {
      run = 0;
      continue;
    }
    run =
      i && rows[i].time - rows[i - 1].time === STEP && Number.isFinite(rows[i - 1].mid)
        ? run + 1
        : 1;
    if (run > lag) pairs.push({ x: rows[i - lag].mid, y: rows[i].mid, time: rows[i].time });
  }
  return pairs;
}

export function regression(pairs: { x: number; y: number }[]) {
  const n = pairs.length,
    mx = mean(pairs.map((p) => p.x)),
    my = mean(pairs.map((p) => p.y));
  if (n < 3 || mx === null || my === null)
    return { n, slope: null, correlation: null, intercept: null, r2: null };
  let xx = 0,
    yy = 0,
    xy = 0;
  pairs.forEach((p) => {
    xx += (p.x - mx) ** 2;
    yy += (p.y - my) ** 2;
    xy += (p.x - mx) * (p.y - my);
  });
  const slope = xx > 0 ? xy / xx : null;
  const correlation = xx > 0 && yy > 0 ? Math.max(-1, Math.min(1, xy / Math.sqrt(xx * yy))) : null;
  return {
    n,
    slope,
    correlation,
    intercept: slope === null ? null : my - slope * mx,
    r2: correlation === null ? null : correlation ** 2,
  };
}

export function reversionModel(rows: Observation[]) {
  const fit = regression(contiguousPairs(rows));
  const halfLife =
    fit.n >= 40 && fit.slope !== null && fit.slope > 0 && fit.slope < 1
      ? (Math.log(0.5) / Math.log(fit.slope)) * 0.5
      : null;
  return { ...fit, halfLife };
}

export function rollingDistribution(rows: Observation[], size: number) {
  let window: number[] = [];
  return rows.map((row, i) => {
    if (!Number.isFinite(row.mid) || (i && row.time - rows[i - 1].time !== STEP)) window = [];
    if (Number.isFinite(row.mid)) window.push(row.mid);
    if (window.length > size) window.shift();
    const stats = window.length === size ? describe(window) : null;
    return {
      time: row.time,
      median: stats?.median ?? null,
      p10: stats?.p10 ?? null,
      p90: stats?.p90 ?? null,
      std: stats?.std ?? null,
    };
  });
}

export function groupedDistribution(rows: Observation[], group: (row: Observation) => string) {
  const grouped = new Map<string, Observation[]>();
  rows.forEach((row) => {
    const key = group(row);
    grouped.set(key, [...(grouped.get(key) || []), row]);
  });
  return [...grouped].map(([key, values]) => ({
    key,
    ...describe(values.map((v) => v.mid)),
    changeStd: describe(contiguousPairs(values).map((p) => p.y - p.x)).std,
  }));
}

export function sampleQuality(rows: Observation[]) {
  return {
    observations: rows.length,
    days: new Set(rows.map((r) => new Date(r.time + 8 * HOUR).toISOString().slice(0, 10))).size,
    pairs: contiguousPairs(rows).length,
    breaks: rows.filter((r, i) => i > 0 && r.time - rows[i - 1].time !== STEP).length,
    start: rows[0]?.time ?? null,
    end: rows.at(-1)?.time ?? null,
  };
}

export function reopenEvents(rows: Observation[]) {
  return rows.flatMap((row, i) => {
    if (!i || row.time - rows[i - 1].time <= STEP) return [];
    const previous = rows[i - 1];
    return [
      {
        before: previous.time,
        after: row.time,
        gapHours: (row.time - previous.time) / HOUR,
        change: row.mid - previous.mid,
        beforeWidth: previous.width ?? null,
        afterWidth: row.width ?? null,
      },
    ];
  });
}

export function forwardPath(rows: Observation[], event: Episode, hours: number) {
  const index = rows.findIndex((r) => r.time === event.time);
  const path: { hour: number; change: number; mid: number }[] = [];
  if (index < 0) return { complete: false, path };
  const sign = event.direction === 'long' ? 1 : -1;
  const steps = Math.round(hours * 2);
  for (let offset = 0; offset <= steps; offset++) {
    const row = rows[index + offset];
    if (!row || row.time !== event.time + offset * STEP || !Number.isFinite(row.mid))
      return { complete: false, path };
    path.push({ hour: offset / 2, change: sign * (row.mid - event.entry), mid: row.mid });
  }
  return { complete: true, path };
}

export function horizonOutcomes(
  rows: Observation[],
  events: Episode[],
  hours: number,
  direction?: Direction,
) {
  const eligible = events.filter((e) => !direction || e.direction === direction);
  const paths = eligible.map((event) => forwardPath(rows, event, hours));
  const complete = paths.filter((p) => p.complete);
  const changes = complete.map((p) => p.path.at(-1)!.change);
  return {
    hours,
    total: eligible.length,
    n: complete.length,
    censored: paths.length - complete.length,
    p10: quantile(changes, 0.1),
    median: quantile(changes, 0.5),
    p90: quantile(changes, 0.9),
    favorable: changes.length ? (changes.filter((v) => v > 0).length / changes.length) * 100 : null,
    mae: quantile(
      complete.map((p) => Math.max(0, ...p.path.map((x) => -x.change))),
      0.9,
    ),
    mfe: quantile(
      complete.map((p) => Math.max(0, ...p.path.map((x) => x.change))),
      0.5,
    ),
  };
}

export function firstPassage(rows: Observation[], event: Episode, maxHours: number, loss: number) {
  const result = forwardPath(rows, event, maxHours);
  const targetDistance = Math.abs(event.target - event.entry);
  for (const point of result.path.slice(1)) {
    if (point.change <= -loss)
      return { status: 'risk' as const, hours: point.hour, change: point.change };
    if (point.change >= targetDistance)
      return { status: 'target' as const, hours: point.hour, change: point.change };
  }
  return {
    status: result.complete ? ('timeout' as const) : ('censored' as const),
    hours: result.path.at(-1)?.hour ?? 0,
    change: result.path.at(-1)?.change ?? null,
  };
}

export interface DepthLevel {
  price: number;
  quantity: number;
}
export function sweepBook(levels: DepthLevel[], quantity: number) {
  if (
    !Number.isFinite(quantity) ||
    quantity <= 0 ||
    levels.some((l) => !Number.isFinite(l.price) || !Number.isFinite(l.quantity) || l.quantity <= 0)
  )
    return { filled: 0, vwap: null, complete: false };
  let filled = 0,
    notional = 0;
  for (const level of levels) {
    const take = Math.min(quantity - filled, level.quantity);
    notional += take * level.price;
    filled += take;
    if (filled >= quantity) break;
  }
  const complete = Math.abs(filled - quantity) < 1e-9;
  return { filled, complete, vwap: complete ? notional / filled : null };
}

export function demoBook(direction: Direction, stressed: boolean): DepthLevel[] {
  const sign = direction === 'long' ? 1 : -1;
  return [1, 2, 3, 5, 8].map((quantity, i) => ({
    quantity: stressed ? quantity / 4 : quantity,
    price: 4000 + sign * (0.15 + i * (stressed ? 1.2 : 0.15)),
  }));
}
