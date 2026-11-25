import Decimal from 'decimal.js';
import type { MonitorItem } from '@/api/cnMarketMonitor';
import type { CapitalDashboard, CapitalRow } from '@/api/platform/aShareCapital';
import type { MacroDashboardSeries } from '@/api/hedgeResearch';

export function numeric(value: unknown): number | null {
  if (value == null || typeof value === 'boolean' || String(value).trim() === '') return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}
export function formatResearch(value: unknown, digits = 2) {
  const n = numeric(value);
  return n === null ? '—' : n.toLocaleString('zh-CN', { maximumFractionDigits: digits });
}
type Point = { date: string; value?: string | number | null };
function values(rows: Point[]) {
  const result = new Map<string, string | number | null>();
  for (const r of rows) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(r.date)) continue;
    // Conflicting duplicate observations must not silently select a winner.
    const value = numeric(r.value) === null ? null : r.value!;
    if (result.has(r.date) && numeric(result.get(r.date)) !== numeric(value))
      result.set(r.date, null);
    else if (!result.has(r.date)) result.set(r.date, value);
  }
  return result;
}
function sum(v: Array<string | number | null | undefined>): string | null {
  if (!v.length || v.some((x) => numeric(x) === null)) return null;
  return v.reduce<Decimal>((total, x) => total.plus(x!), new Decimal(0)).toString();
}

/** These are archived observation windows, not an independently certified exchange calendar. */
export function financingSentiment(series: MacroDashboardSeries[]) {
  const buy = values(
    series.find((s) => s.seriesId === 'cn_margin_financing_buy')?.observations || [],
  );
  const dates = [...new Set(series.flatMap((s) => s.observations.map((p) => p.date)))].sort();
  const raw: Array<{ date: string; sentiment: number | null }> = dates.map((date, i) => {
    const window = dates.slice(Math.max(0, i - 59), i + 1);
    const total60 = window.length === 60 ? sum(window.map((d) => buy.get(d))) : null;
    const total20 = window.length === 60 ? sum(window.slice(-20).map((d) => buy.get(d))) : null;
    const sentiment =
      total60 !== null && new Decimal(total60).gt(0) && total20 !== null
        ? new Decimal(total20).div(total60).times(100).toNumber()
        : null;
    return { date, sentiment };
  });
  // Empirical percentile of the current value within the trailing 252 observations.
  // All 252 inputs are required; warm-up and gaps remain null.
  return raw.map((row, i) => {
    const history = raw.slice(Math.max(0, i - 251), i + 1).map((r) => numeric(r.sentiment));
    const current = numeric(row.sentiment);
    const complete = history.length === 252 && history.every((v) => v !== null);
    const rank =
      complete && current !== null
        ? (history.filter((v) => v! <= current).length / 252) * 100
        : null;
    return { ...row, rank, neutral: 100 / 3 };
  });
}

export function crowdingChanges(
  items: MonitorItem[],
  metric: 'amount' | 'turnover',
  window: number,
) {
  const dates = [
    ...new Set(items.flatMap((item) => (item.history || []).map((r) => r.date))),
  ].sort();
  const date = dates.at(-1),
    baseDate = dates.at(-window - 1);
  const rows = items.map((item) => {
    const history = values((item.history || []).map((r) => ({ date: r.date, value: r[metric] })));
    const current = numeric(date ? history.get(date) : null);
    const base = numeric(baseDate ? history.get(baseDate) : null);
    return {
      code: item.code,
      name: item.name,
      value: current,
      change: current !== null && base !== null ? current - base : null,
    };
  });
  return { date, baseDate, rows };
}

export function capitalComparison(data: CapitalDashboard, window: number) {
  const balance = values(data.macro.cn_margin_financing_balance?.observations || []);
  const etf = values(data.etf.rows);
  const dates = [...new Set([...balance.keys(), ...etf.keys()])].sort();
  const rows = dates.map((date, i): CapitalRow => {
    const now = balance.get(date),
      previous = balance.get(dates[i - 1]);
    return {
      date,
      etf: etf.get(date) ?? null,
      financing:
        numeric(now) !== null && numeric(previous) !== null
          ? new Decimal(now!).minus(previous!).toString()
          : null,
    };
  });
  // Keep the latest date even when one source lags; never hide the missing tail.
  const selected = rows.slice(-window);
  const etfCount = selected.filter((r) => numeric(r.etf) !== null).length;
  const financingCount = selected.filter((r) => numeric(r.financing) !== null).length;
  const totalEtf = selected.length === window ? sum(selected.map((r) => r.etf)) : null;
  const totalFinancing = selected.length === window ? sum(selected.map((r) => r.financing)) : null;
  const pairs = selected.filter((r) => numeric(r.etf) !== null && numeric(r.financing) !== null);
  let correlation: number | null = null;
  if (pairs.length >= 20) {
    const xs = pairs.map((r) => Number(r.etf)),
      ys = pairs.map((r) => Number(r.financing));
    const mx = xs.reduce((a, b) => a + b, 0) / pairs.length;
    const my = ys.reduce((a, b) => a + b, 0) / pairs.length;
    const vx = xs.reduce((a, x) => a + (x - mx) ** 2, 0);
    const vy = ys.reduce((a, y) => a + (y - my) ** 2, 0);
    if (vx > 0 && vy > 0)
      correlation = Math.max(
        -1,
        Math.min(1, xs.reduce((a, x, i) => a + (x - mx) * (ys[i] - my), 0) / Math.sqrt(vx * vy)),
      );
  }
  let relationship = '窗口数据不足';
  if (totalEtf !== null && totalFinancing !== null) {
    const a = new Decimal(totalEtf).cmp(0),
      b = new Decimal(totalFinancing).cmp(0);
    relationship =
      a > 0 && b > 0
        ? 'ETF净申购 · 融资余额增加'
        : a < 0 && b < 0
        ? 'ETF净赎回 · 融资余额减少'
        : a > 0 && b < 0
        ? 'ETF净申购 · 融资余额减少'
        : a < 0 && b > 0
        ? 'ETF净赎回 · 融资余额增加'
        : '至少一项净变化为零';
  }
  return {
    rows,
    selected,
    start: selected[0]?.date,
    end: selected.at(-1)?.date,
    etfCount,
    financingCount,
    totalEtf,
    totalFinancing,
    correlation,
    pairs: pairs.length,
    relationship,
  };
}

export type ResearchPoint = {
  date: string;
  value: string | number | null;
  close?: string | number | null;
};

/** Monday-aligned calendar weeks. Retain missing calendar weeks rather than compressing history. */
export function weeklyResearch(
  rows: ResearchPoint[],
  mode: 'sum' | 'last',
  asOf: string,
  sessions: string[] = [],
) {
  const byDay = values(rows);
  const closes = new Map(rows.map((r) => [r.date, r.close ?? null]));
  const monday = (day: string) => {
    const d = new Date(day + 'T00:00:00Z');
    d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 6) % 7));
    return d.toISOString().slice(0, 10);
  };
  const days = [...byDay.keys()].sort();
  if (!days.length) return [];
  const groups = new Map<string, string[]>();
  for (const day of days) {
    const week = monday(day);
    groups.set(week, [...(groups.get(week) || []), day]);
  }
  const expected = new Map<string, string[]>();
  for (const day of sessions) {
    const week = monday(day);
    expected.set(week, [...(expected.get(week) || []), day]);
  }
  const end = monday(days.at(-1)!);
  const result: Array<{
    date: string;
    value: string | number | null;
    close: string | number | null;
    partial: boolean;
  }> = [];
  for (let cursor = monday(days[0]); cursor <= end; ) {
    const verified =
      sessions.length > 0 && cursor >= monday(sessions[0]) && cursor <= monday(sessions.at(-1)!);
    const group = verified
      ? (expected.get(cursor) || []).filter((d) => d <= asOf)
      : groups.get(cursor) || [];
    const last = group.at(-1);
    const friday = new Date(cursor + 'T00:00:00Z');
    friday.setUTCDate(friday.getUTCDate() + 4);
    const partial = friday.toISOString().slice(0, 10) >= asOf;
    // Only the independent exchange calendar can identify a fully closed week.
    if (!verified || expected.has(cursor))
      result.push({
        date: last || friday.toISOString().slice(0, 10),
        value:
          mode === 'sum'
            ? sum(group.map((d) => byDay.get(d)))
            : last
            ? byDay.get(last) ?? null
            : null,
        close: last ? closes.get(last) ?? null : null,
        partial,
      });
    const next = new Date(cursor + 'T00:00:00Z');
    next.setUTCDate(next.getUTCDate() + 7);
    cursor = next.toISOString().slice(0, 10);
  }
  return result;
}

/** 52 calendar-week empirical ranks; a second 52-week window supplies mean ± population SD. */
export function researchBands(rows: Array<ResearchPoint & { partial?: boolean }>, window = 52) {
  const stats = (v: Array<number | null>) => {
    if (v.length !== window || v.some((n) => n === null)) return null;
    const a = v as number[];
    const mean = a.reduce((s, n) => s + n, 0) / window;
    const sd = Math.sqrt(a.reduce((s, n) => s + (n - mean) ** 2, 0) / window);
    return { mean, sd };
  };
  const ranked = rows.map((row, i) => {
    const v = numeric(row.value);
    const slice = rows.slice(Math.max(0, i - window + 1), i + 1);
    const history = slice.map((r) => (r.partial ? null : numeric(r.value)));
    const s = stats(history);
    return {
      ...row,
      rank:
        s && v !== null && !row.partial
          ? (history.filter((n) => n! <= v).length / window) * 100
          : null,
      mean: s?.mean ?? null,
      upper: s ? s.mean + s.sd : null,
      lower: s ? s.mean - s.sd : null,
    };
  });
  return ranked.map((row, i) => {
    const s = stats(ranked.slice(Math.max(0, i - window + 1), i + 1).map((r) => r.rank));
    return {
      ...row,
      rankMean: s?.mean ?? null,
      rankUpper: s ? s.mean + s.sd : null,
      rankLower: s ? s.mean - s.sd : null,
      relative:
        s && s.sd > 0 && row.rank !== null
          ? ((row.rank - (s.mean - s.sd)) / (2 * s.sd)) * 100
          : null,
    };
  });
}

export function linearFit(points: Array<{ x: number; y: number }>) {
  if (points.length < 20) return null;
  const n = points.length,
    mx = points.reduce((s, p) => s + p.x, 0) / n,
    my = points.reduce((s, p) => s + p.y, 0) / n;
  const xx = points.reduce((s, p) => s + (p.x - mx) ** 2, 0),
    yy = points.reduce((s, p) => s + (p.y - my) ** 2, 0);
  if (!xx || !yy) return null;
  const xy = points.reduce((s, p) => s + (p.x - mx) * (p.y - my), 0),
    slope = xy / xx;
  const correlation = Math.max(-1, Math.min(1, xy / Math.sqrt(xx * yy)));
  const ends = [Math.min(...points.map((p) => p.x)), Math.max(...points.map((p) => p.x))];
  return {
    correlation,
    r2: correlation ** 2,
    slope,
    intercept: my - slope * mx,
    line: ends.map((x) => [x, my + slope * (x - mx)]),
  };
}

export function alignedResearchRanks(
  series: Array<{
    key: string;
    rows: Array<{ date: string; rank: number | null; partial?: boolean }>;
  }>,
) {
  // Trading-week observations use the last session; reports use Sunday.
  // Join by the same Monday-Sunday period without carrying older values forward.
  const week = (value: string) => {
    const day = new Date(value + 'T00:00:00Z');
    day.setUTCDate(day.getUTCDate() + ((7 - day.getUTCDay()) % 7));
    return day.toISOString().slice(0, 10);
  };
  const indexed = series.map((item) => ({
    key: item.key,
    rows: new Map(item.rows.map((r) => [week(r.date), r.partial ? null : r.rank])),
  }));
  const dates = [...new Set(indexed.flatMap((item) => [...item.rows.keys()]))].sort();
  return dates.map((date) => ({
    date,
    ...Object.fromEntries(indexed.map((item) => [item.key, item.rows.get(date) ?? null])),
  }));
}

export function pairedCapitalPoints(
  rows: CapitalRow[],
  prices: Array<{ date: string; value: unknown }>,
) {
  const price = values(prices.map((r) => ({ date: r.date, value: numeric(r.value) })));
  const calendar = [...new Set([...rows.map((r) => r.date), ...price.keys()])].sort();
  const previous = new Map(calendar.map((day, i) => [day, calendar[i - 1]]));
  return rows.map((r) => {
    const currentPrice = numeric(price.get(r.date)),
      priorPrice = numeric(price.get(previous.get(r.date)!));
    return {
      date: r.date,
      etf: numeric(r.etf),
      financing: numeric(r.financing),
      marketReturn:
        currentPrice !== null && priorPrice !== null && priorPrice > 0
          ? (currentPrice / priorPrice - 1) * 100
          : null,
    };
  });
}
