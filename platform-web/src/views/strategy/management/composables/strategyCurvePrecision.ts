import type { StrategyPnlProfile } from '@/data/sample/strategy';

export type CurvePrecision = 'week' | 'day' | 'hour' | '5min';
export const curvePrecisions = [
  { key: 'week', label: '周度' },
  { key: 'day', label: '日度' },
  { key: 'hour', label: '1H' },
  { key: '5min', label: '5min' },
] as const;

/** Sample the last observed cumulative value per period; never invent intraday points. */
export function samplePnlCurve(
  profile: StrategyPnlProfile,
  precision: CurvePrecision,
): StrategyPnlProfile {
  if (!profile.timestamps?.length) return profile;
  const period = { week: 604800000, day: 86400000, hour: 3600000, '5min': 300000 }[precision];
  const offset = 8 * 3600000; // Strategy reporting timezone: Asia/Shanghai.
  const monday = precision === 'week' ? 4 * 86400000 : 0;
  const buckets = new Map<number, number>();
  profile.timestamps.forEach((value, index) => {
    const time = Date.parse(value);
    if (Number.isFinite(time)) buckets.set(Math.floor((time + offset - monday) / period), index);
  });
  const indices = [...buckets.entries()].sort(([a], [b]) => a - b).map(([, index]) => index);
  const sample = (data: number[]) =>
    indices.filter((index) => index < data.length).map((index) => data[index]);
  return {
    ...profile,
    timestamps: indices.map((index) => profile.timestamps![index]),
    xLabels: indices.map((index) => {
      const date = new Date(profile.timestamps![index]);
      return date.toLocaleString('zh-CN', {
        timeZone: 'Asia/Shanghai',
        hour12: false,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        ...(precision === 'hour' || precision === '5min'
          ? ({ hour: '2-digit', minute: '2-digit' } as const)
          : {}),
      });
    }),
    netValues: sample(profile.netValues),
    dailyReturns: sample(profile.dailyReturns),
    breakdownSeries: profile.breakdownSeries.map((item) => ({ ...item, data: sample(item.data) })),
    detailCurves: profile.detailCurves.map((item) => ({ ...item, data: sample(item.data) })),
  };
}
