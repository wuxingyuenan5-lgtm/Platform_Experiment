// Formula adaptation of Pulu_ and ChartPrime Pine sources, MPL-2.0.
// Source references are retained in licenses/indicator-sources.txt.
import type { Bar, Frame } from './types';

export type { Bar, Frame, Snapshot, SnapshotSeries } from './types';
export const FRAMES: Frame[] = ['1D', '3D', '1W', 'M'];
export const FRAME_NAMES = { '1D': '日线', '3D': '三日线', '1W': '周线', M: '月线' } as const;
export const PMA = [12, 144, 169, 288, 338, 576, 676];
export const PERIODS = [20, 60, 100, 200];
export type Direction = '多' | '空' | '震荡' | '不足';
export type TrendBox = {
  start: number;
  end: number;
  top: number;
  bottom: number;
  side: '多' | '空';
  price: number;
};
export type Signal = { t: number; plottedAt: number; kind: string; side: '多' | '空' };
export interface Computed {
  bars: Bar[];
  lines: Record<string, (number | null)[]>;
  boxes: TrendBox[];
  events: Signal[];
  a: Direction;
  z: Direction;
  p: Direction;
  bands: Direction[];
  atr: (number | null)[];
}
export const crossUp = (a: number, b: number, pa: number, pb: number) => a > b && pa <= pb;
export const crossDown = (a: number, b: number, pa: number, pb: number) => a < b && pa >= pb;
export function ema(xs: number[], n: number): number[] {
  const alpha = 2 / (n + 1);
  return xs.reduce<number[]>((out, x, i) => {
    out.push(i ? alpha * x + (1 - alpha) * out[i - 1] : x);
    return out;
  }, []);
}
export function sma(xs: number[], n: number): (number | null)[] {
  let sum = 0;
  return xs.map((x, i) => {
    sum += x;
    if (i >= n) sum -= xs[i - n];
    return i + 1 >= n ? sum / n : null;
  });
}
export function atr(bars: Bar[], n = 200): (number | null)[] {
  let sum = 0,
    value: number | null = null;
  return bars.map((b, i) => {
    const tr = i
      ? Math.max(b.h - b.l, Math.abs(b.h - bars[i - 1].c), Math.abs(b.l - bars[i - 1].c))
      : b.h - b.l;
    if (i < n) sum += tr;
    if (i === n - 1) value = sum / n;
    else if (i >= n) value = (value! * (n - 1) + tr) / n;
    return value;
  });
}
export function maturity(n: number, count: number) {
  const residual = Math.pow(1 - 2 / (n + 1), Math.max(0, count - 1));
  return {
    residual,
    eligible: count >= n,
    label: count < n ? '历史不足' : residual > 0.01 ? '初始化中' : '已预热',
  };
}
export function compute(input: Bar[], includeForming = false): Computed {
  const bars = includeForming ? input : input.slice(0, -1),
    c = bars.map((b) => b.c),
    lines: Computed['lines'] = {};
  for (const n of PMA) lines[`PMA${n}`] = ema(c, n);
  for (const n of PERIODS) {
    lines[`MA${n}`] = sma(c, n);
    lines[`EMA${n}`] = ema(c, n);
  }
  const e = ema(c, 15),
    z = ema(
      c.map((x, i) => 2 * x - e[i]),
      15,
    ),
    av = atr(bars);
  lines.E15 = e;
  lines.ZLMA = z;
  const boxes: TrendBox[] = [],
    events: Signal[] = [];
  let current: TrendBox | null = null,
    previousCross = false;
  for (let i = 1; i < bars.length; i++) {
    const b = bars[i],
      p = bars[i - 1],
      up = crossUp(z[i], e[i], z[i - 1], e[i - 1]),
      dn = crossDown(z[i], e[i], z[i - 1], e[i - 1]);
    if (up || dn) {
      events.push({ t: b.t, plottedAt: b.t, kind: 'ZLMA交叉', side: up ? '多' : '空' });
      current =
        av[i] == null
          ? null
          : {
              start: b.t,
              end: b.t,
              top: up ? z[i] : z[i] + av[i]!,
              bottom: up ? z[i] - av[i]! : z[i],
              side: up ? '多' : '空',
              price: b.c,
            };
      if (current) boxes.push(current);
    }
    if (current) {
      current.end = b.t;
      if (!up && !dn && !previousCross) {
        if (crossUp(b.l, current.top, p.l, current.top) && e[i] < z[i])
          events.push({ t: b.t, plottedAt: p.t, kind: '趋势位向上确认', side: '多' });
        if (crossDown(b.h, current.bottom, p.h, current.bottom) && e[i] > z[i])
          events.push({ t: b.t, plottedAt: p.t, kind: '趋势位向下确认', side: '空' });
      }
    }
    previousCross = up || dn;
  }
  const k = bars.length - 1;
  let a: Direction = '不足',
    zd: Direction = '不足';
  if (bars.length >= 60) {
    const s20 = lines.MA20[k]!,
      s60 = lines.MA60[k]!,
      e20 = lines.EMA20[k]!,
      e60 = lines.EMA60[k]!;
    a =
      c[k] > s20 &&
      c[k] > e20 &&
      s20 > s60 &&
      e20 > e60 &&
      s20 > lines.MA20[k - 3]! &&
      e20 > lines.EMA20[k - 3]!
        ? '多'
        : c[k] < s20 &&
          c[k] < e20 &&
          s20 < s60 &&
          e20 < e60 &&
          s20 < lines.MA20[k - 3]! &&
          e20 < lines.EMA20[k - 3]!
        ? '空'
        : '震荡';
    zd = z[k] > e[k] ? '多' : z[k] < e[k] ? '空' : '震荡';
  }
  const bands: Direction[] = [
    [144, 169],
    [288, 338],
    [576, 676],
  ].map(([x, y]) => {
    if (bars.length < y + 3) return '不足';
    const fast = lines[`PMA${x}`],
      slow = lines[`PMA${y}`],
      mid = (fast[k]! + slow[k]!) / 2,
      prev = (fast[k - 3]! + slow[k - 3]!) / 2;
    return c[k] > Math.max(fast[k]!, slow[k]!) && fast[k]! > slow[k]! && mid > prev
      ? '多'
      : c[k] < Math.min(fast[k]!, slow[k]!) && fast[k]! < slow[k]! && mid < prev
      ? '空'
      : '震荡';
  });
  return {
    bars,
    lines,
    boxes,
    events,
    a,
    z: zd,
    p: bands.includes('不足')
      ? '不足'
      : bands.every((v) => v === '多')
      ? '多'
      : bands.every((v) => v === '空')
      ? '空'
      : '震荡',
    bands,
    atr: av,
  };
}
export function validateBars(bars: Bar[]) {
  const issues: string[] = [];
  bars.forEach((b, i) => {
    if (![b.t, b.o, b.h, b.l, b.c, b.v].every(Number.isFinite)) issues.push(`nonfinite:${i}`);
    if (b.l > Math.min(b.o, b.c) || b.h < Math.max(b.o, b.c) || b.h < b.l || b.v < 0 || b.l <= 0)
      issues.push(`ohlcv:${i}`);
    if (i && b.t <= bars[i - 1].t) issues.push(`order:${i}`);
  });
  return issues;
}
