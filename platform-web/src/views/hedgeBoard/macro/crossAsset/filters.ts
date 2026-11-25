import { FRAMES, type Direction, type Frame } from './engine';
import type { Assessment } from './rules';

export type FrameRule = Direction | 'any';
export interface FrameCondition {
  state: FrameRule;
  turn: 'any' | 'changed' | '多' | '空' | '震荡';
  from: 'any' | '多' | '空' | '震荡';
  lookback: number;
}
export interface TrendFilters {
  rules: Record<Frame, FrameCondition>;
  match: 'all' | 'any';
  stillCurrent: boolean;
}
export interface TrendSort {
  by: 'event' | 'priority' | 'symbol';
  frame: Frame | 'matched';
  order: 'desc' | 'asc';
}
export const defaultCondition = (): FrameCondition => ({
  state: 'any',
  turn: 'any',
  from: 'any',
  lookback: 5,
});
export const defaultTrendFilters = (): TrendFilters => ({
  rules: {
    '1D': defaultCondition(),
    '3D': defaultCondition(),
    '1W': defaultCondition(),
    M: defaultCondition(),
  },
  match: 'all',
  stillCurrent: true,
});
export const defaultTrendSort = (): TrendSort => ({ by: 'event', frame: 'matched', order: 'desc' });
export const activeCondition = (r: FrameCondition) => r.state !== 'any' || r.turn !== 'any';
export const hasTurnCondition = (f: TrendFilters) => FRAMES.some((x) => f.rules[x].turn !== 'any');
export type Transition = {
  index: number;
  age: number;
  t: number;
  previous: Direction;
  direction: Direction;
};
export function transitions(h: Assessment[]) {
  const out: Transition[] = [];
  h.forEach((x, i) => {
    const p = h[i - 1]?.direction;
    if (p && p !== '不足' && x.direction !== '不足' && p !== x.direction)
      out.push({
        index: i,
        age: h.length - 1 - i,
        t: x.since,
        previous: p,
        direction: x.direction,
      });
  });
  return out;
}
export interface FrameTrend {
  current: Direction;
  events: Transition[];
  since: number;
}
export type AssetTrends = Partial<Record<Frame, FrameTrend>>;
export function matrixTransitions(e: Transition[]) {
  const m = new Map<string, Transition>();
  for (const x of e) m.set(`${x.previous}/${x.direction}`, x);
  return [...m.values()].sort((a, b) => a.index - b.index);
}
export function frameTransitions(t: FrameTrend | undefined, r: FrameCondition, still: boolean) {
  if (!t || r.turn === 'any') return [];
  return t.events.filter(
    (e) =>
      (r.lookback === 0 || e.age < r.lookback) &&
      (r.turn === 'changed' || e.direction === r.turn) &&
      (r.from === 'any' || e.previous === r.from) &&
      (!still || (t.current === e.direction && t.since === e.t)),
  );
}
export function matchesFrame(t: FrameTrend | undefined, r: FrameCondition, still: boolean) {
  return (
    (r.state === 'any' || (t?.current || '不足') == r.state) &&
    (r.turn === 'any' || frameTransitions(t, r, still).length > 0)
  );
}
export function recentTransitions(t: AssetTrends, f: TrendFilters) {
  return FRAMES.flatMap((frame) =>
    matchesFrame(t[frame], f.rules[frame], f.stillCurrent)
      ? frameTransitions(t[frame], f.rules[frame], f.stillCurrent).map((e) => ({ ...e, frame }))
      : [],
  ).sort((a, b) => b.t - a.t || FRAMES.indexOf(a.frame) - FRAMES.indexOf(b.frame));
}
export function matchesTrend(t: AssetTrends, f: TrendFilters) {
  const checks = FRAMES.filter((x) => activeCondition(f.rules[x])).map((x) =>
    matchesFrame(t[x], f.rules[x], f.stillCurrent),
  );
  return !checks.length || (f.match === 'all' ? checks.every(Boolean) : checks.some(Boolean));
}
export function sortTransition(t: AssetTrends, f: TrendFilters, s: TrendSort) {
  const af = FRAMES.filter((x) => activeCondition(f.rules[x])),
    frames = s.frame === 'matched' ? (af.length ? af : FRAMES) : [s.frame];
  if (hasTurnCondition(f) && (s.frame === 'matched' || f.rules[s.frame].turn !== 'any'))
    return recentTransitions(t, f).find((e) => frames.includes(e.frame));
  return frames
    .flatMap((frame) => (t[frame]?.events || []).map((e) => ({ ...e, frame })))
    .sort((a, b) => b.t - a.t || FRAMES.indexOf(a.frame) - FRAMES.indexOf(b.frame))[0];
}
export function compareEventTime(
  a: number | undefined,
  b: number | undefined,
  o: TrendSort['order'],
) {
  if (a == null) return b == null ? 0 : 1;
  if (b == null) return -1;
  return o === 'desc' ? b - a : a - b;
}
export interface TrendPreset {
  id: string;
  name: string;
  filters: TrendFilters;
  sort: TrendSort;
}
function preset(
  id: string,
  name: string,
  changes: Partial<Record<Frame, Partial<FrameCondition>>>,
  frame: TrendSort['frame'],
  match: TrendFilters['match'] = 'all',
) {
  const filters = defaultTrendFilters();
  for (const f of FRAMES) Object.assign(filters.rules[f], changes[f]);
  filters.match = match;
  return { id, name, filters, sort: { ...defaultTrendSort(), frame } };
}
export const TREND_PRESETS = [
  preset(
    'daily-bull',
    '日线转多 · 周月多头',
    { '1D': { state: '多', turn: '多', lookback: 0 }, '1W': { state: '多' }, M: { state: '多' } },
    '1D',
  ),
  preset(
    'daily-bear',
    '日线转空 · 周月空头',
    { '1D': { state: '空', turn: '空', lookback: 0 }, '1W': { state: '空' }, M: { state: '空' } },
    '1D',
  ),
  preset(
    'weekly-bull',
    '周线转多 · 月线多头',
    { '1W': { state: '多', turn: '多', lookback: 0 }, M: { state: '多' } },
    '1W',
  ),
  preset(
    'pullback',
    '日线转空 · 周月多头',
    { '1D': { state: '空', turn: '空', lookback: 0 }, '1W': { state: '多' }, M: { state: '多' } },
    '1D',
  ),
  ...(['多', '空', '震荡'] as const).map((side) =>
    preset(
      `recent-${side}`,
      `任一周期转${side === '震荡' ? '中性' : side}`,
      Object.fromEntries(FRAMES.map((f) => [f, { turn: side }])),
      'matched',
      'any',
    ),
  ),
];
export function conditionSummary(r: FrameCondition) {
  const labels: Record<Direction, string> = {
      多: '偏多',
      空: '偏空',
      震荡: '中性',
      不足: '待验证',
    },
    p = r.state === 'any' ? [] : [`当前${labels[r.state]}`];
  if (r.turn !== 'any') {
    p.push(r.turn === 'changed' ? '任意转向' : `转${labels[r.turn]}`);
    if (r.from !== 'any') p.push(`由${labels[r.from]}转入`);
    p.push(r.lookback ? `近${r.lookback}根` : '全部历史');
  }
  return p.join(' · ');
}
export function impossibleCondition(r: FrameCondition, still: boolean) {
  return (
    r.turn !== 'any' &&
    r.turn !== 'changed' &&
    (r.from === r.turn || (still && r.state !== 'any' && r.state !== r.turn))
  );
}
export function readFilterSettings(value: unknown) {
  if (!value || typeof value !== 'object') return null;
  const { filters, sort } = value as { filters?: TrendFilters; sort?: TrendSort };
  if (
    !filters ||
    !sort ||
    !['all', 'any'].includes(filters.match) ||
    typeof filters.stillCurrent !== 'boolean' ||
    !['event', 'priority', 'symbol'].includes(sort.by) ||
    !['matched', ...FRAMES].includes(sort.frame) ||
    !['desc', 'asc'].includes(sort.order)
  )
    return null;
  for (const f of FRAMES) {
    const r = filters.rules?.[f];
    if (
      !r ||
      !['any', '多', '空', '震荡', '不足'].includes(r.state) ||
      !['any', 'changed', '多', '空', '震荡'].includes(r.turn) ||
      !['any', '多', '空', '震荡'].includes(r.from) ||
      !Number.isInteger(r.lookback) ||
      r.lookback < 0 ||
      r.lookback > 1000
    )
      return null;
  }
  return { filters, sort };
}
