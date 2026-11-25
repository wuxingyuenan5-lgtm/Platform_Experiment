import type { FlowAnalysis, FlowFund, FlowGroup, FlowPeriod } from '@/api/etfFlows';

// Synthetic, deterministic observations. Never persisted or used by the real-data API.
const definitions = [
  ['股票宽基', '沪深300'],
  ['股票宽基', '上证50'],
  ['股票宽基', '中证500'],
  ['股票宽基', '中证1000'],
  ['股票宽基', '中证2000'],
  ['股票宽基', '科创50'],
  ['股票宽基', '创业板指'],
  ['股票宽基', '中证A500'],
  ['股票宽基', '双创50'],
  ['行业主题', '机器人'],
  ['行业主题', '银行'],
  ['行业主题', '国防军工'],
  ['行业主题', '半导体'],
  ['行业主题', '芯片设备'],
  ['行业主题', '通信'],
  ['行业主题', '5G'],
  ['行业主题', '电网设备'],
  ['行业主题', '人工智能'],
  ['行业主题', '新能源车'],
  ['行业主题', '有色金属'],
  ['行业主题', '证券'],
  ['行业主题', '医药'],
  ['行业主题', '消费'],
  ['跨境', '海外股票'],
  ['债券', '国债'],
  ['商品', '黄金'],
  ['货币', '场内货币'],
];
const sessions: string[] = [];
for (
  let d = new Date('2025-01-01T00:00:00Z');
  d <= new Date('2026-11-09T00:00:00Z');
  d.setUTCDate(d.getUTCDate() + 1)
) {
  if (d.getUTCDay() !== 0 && d.getUTCDay() !== 6) sessions.push(d.toISOString().slice(0, 10));
}
function period(index: number, start: string, end: string): FlowPeriod {
  const days = sessions.filter((d) => d >= start && d <= end);
  const flow = days.reduce((sum, day) => {
    const t = sessions.indexOf(day);
    const trend =
      day.slice(5, 7) >= '10'
        ? index < 9
          ? 8
          : index % 4 < 2
          ? 0.9
          : -0.6
        : index < 9
        ? -1.5
        : Math.cos(index) * 0.6;
    return sum + trend + Math.sin(t * 0.4 + index) * (index < 9 ? 3 : 0.8);
  }, 0);
  const scale = 240 + (27 - index) * 42;
  return {
    flow: days.length ? String(flow) : null,
    scale: String(scale),
    ratio: days.length ? String((flow / scale) * 100) : null,
    complete: !!days.length,
    covered: days.length,
    expected: days.length,
  };
}
function aggregate(items: FlowFund[]): Omit<FlowGroup, 'name'> {
  const sum = (key: 'current' | 'previous'): FlowPeriod => {
    const p = items.map((f) => f[key]);
    const flow = p.reduce((s, v) => s + Number(v.flow), 0);
    const scale = p.reduce((s, v) => s + Number(v.scale), 0);
    const complete = p.every((v) => v.complete);
    return {
      flow: complete ? String(flow) : null,
      scale: String(scale),
      ratio: complete ? String((flow / scale) * 100) : null,
      complete,
      covered: p.reduce((s, v) => s + v.covered, 0),
      expected: p.reduce((s, v) => s + v.expected, 0),
    };
  };
  const current = sum('current'),
    previous = sum('previous');
  return {
    current,
    previous,
    count: items.length,
    recovery:
      Number(previous.flow) < 0 && Number(current.flow) > 0
        ? String((Number(current.flow) / -Number(previous.flow)) * 100)
        : null,
  };
}
export function etfFlowDemo(params: Record<string, string | number>): FlowAnalysis {
  const end = String(params.end || sessions.at(-1));
  const eligible = sessions.filter((d) => d <= end);
  const start = String(params.start || eligible.slice(-Number(params.days || 20))[0]);
  const prior = sessions.filter((d) => d < start);
  const length = eligible.filter((d) => d >= start).length;
  const previousStart = String(params.previous_start || prior.slice(-length)[0]);
  const previousEnd = String(params.previous_end || prior.at(-1));
  if (!length || !prior.length || previousStart > previousEnd || previousEnd >= start)
    throw new Error('演示区间无有效样本');
  const funds: FlowFund[] = definitions.map(([asset, group], i) => {
    const current = period(i, start, end),
      previous = period(i, previousStart, previousEnd);
    return {
      name: `${group}演示ETF`,
      code: `DEMO-${String(i + 1).padStart(2, '0')}`,
      group,
      asset,
      count: 1,
      current,
      previous,
      recovery:
        Number(previous.flow) < 0 && Number(current.flow) > 0
          ? String((Number(current.flow) / -Number(previous.flow)) * 100)
          : null,
      sourceDate: '2026-11-09',
      sourceStatus: 'demo',
      sourceUrls: [],
    };
  });
  const grouped = (key: 'asset' | 'group') =>
    [...new Set(funds.map((f) => f[key]))].map((name) => ({
      name,
      ...aggregate(funds.filter((f) => f[key] === name)),
    }));
  return {
    date: '2026-11-09',
    status: 'demo',
    retrievedAt: '',
    start,
    end,
    previousStart,
    previousEnd,
    sessions,
    funds,
    groups: grouped('group'),
    assets: grouped('asset'),
    summary: aggregate(funds),
    source: '合成演示数据 · 非真实市场观测',
    scope:
      '演示全市场大类、细分行业、跟踪指数与持有人交互；数值不复用文章结论，日期仅为模拟工作日（未使用交易所节假日日历）。',
  };
}

export function demoHolders(code: string) {
  const seed = Number(code.split('-')[1] || 1);
  return Array.from({ length: 10 }, (_, i) => {
    const before = i === 8 ? 0 : 12 - i + seed * 0.03;
    const after = i === 9 ? 0 : before + (i % 2 ? -0.4 : 0.8);
    return {
      name: `演示机构${String.fromCharCode(65 + i)}`,
      before,
      after,
      delta: after - before,
      state: !before ? '新进' : !after ? '退出' : after > before ? '增持' : '减持',
    };
  });
}
