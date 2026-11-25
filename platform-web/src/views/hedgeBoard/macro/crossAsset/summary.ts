import { compute, type SnapshotSeries, type Direction, type Frame, type Computed } from './engine';
import { classify, SYSTEMS, type RuleConfig } from './rules';
import { transitions, type FrameTrend } from './filters';

export type MonitorEvent = {
  symbol: string;
  frame: Frame;
  t: number;
  plottedAt: number;
  system: string;
  side: Direction;
  previous?: Direction;
  kind: string;
  provisional: boolean;
  reason: string;
  age: number;
};
export function isDailyPreview(source: SnapshotSeries, forming: boolean) {
  return forming && source.frame === '1D' && source.lastBarComplete !== true && !!source.intraday;
}
export function summarizeSeries(source: SnapshotSeries, forming: boolean, config: RuleConfig) {
  const preview = isDailyPreview(source, forming),
    events: MonitorEvent[] = [],
    data = compute(source.bars, preview || source.lastBarComplete === true),
    assessed = classify(data, config);
  assessed.history.forEach((h, i) => {
    if (!i) return;
    for (const system of ['composite', ...SYSTEMS] as const) {
      const value = system === 'composite' ? h.direction : h.systems[system].direction,
        previous =
          system === 'composite'
            ? assessed.history[i - 1].direction
            : assessed.history[i - 1].systems[system].direction;
      if (value === previous || value === '不足' || previous === '不足') continue;
      events.push({
        symbol: source.symbol,
        frame: source.frame,
        t: data.bars[i].t,
        plottedAt: data.bars[i].t,
        system,
        side: value,
        previous,
        age: data.bars.length - i - 1,
        kind: value === '震荡' ? '趋势条件解除' : `${value === '多' ? '偏多' : '偏空'}确认`,
        provisional: preview && i === data.bars.length - 1,
        reason: `${system === 'composite' ? '零滞后主方向 · ' : '参考体系 · '}${
          config.buffer
        } ATR · ${config.confirmation}根确认`,
      });
    }
  });
  const index = new Map(data.bars.map((b, i) => [b.t, i]));
  for (const e of data.events) {
    const i = index.get(e.t)!;
    events.push({
      ...e,
      symbol: source.symbol,
      frame: source.frame,
      system: 'original',
      age: data.bars.length - i - 1,
      provisional: preview && i === data.bars.length - 1,
      reason: i < 59 ? '原始事件 · 初始化区间' : 'ChartPrime原始事件 · 未加缓冲',
    });
  }
  const compact: Computed = {
      ...data,
      bars: data.bars.slice(-2),
      lines: {},
      boxes: [],
      events: [],
      atr: [],
    },
    trend: FrameTrend = {
      current: assessed.current.direction,
      since: assessed.current.since,
      events: transitions(assessed.history),
    };
  return {
    source: {
      ...source,
      totalBars: source.bars.length,
      firstTime: source.bars[0]?.t,
      bars: source.bars.slice(-2),
    },
    computed: compact,
    assessed: { current: assessed.current },
    trend,
    events,
  };
}
export type SeriesSummary = ReturnType<typeof summarizeSeries>;
