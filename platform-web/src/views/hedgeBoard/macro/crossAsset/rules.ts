import { atr, maturity, type Computed, type Direction } from './engine';

export const RULE_VERSION = 'trend-framework-3.0-zlma';
export const SYSTEMS = ['pma', 'zlma', 'sma', 'ema'] as const;
export type System = (typeof SYSTEMS)[number];
export const SYSTEM_NAMES: Record<System, string> = {
  pma: '蒲鲁均线带',
  zlma: '零滞后趋势',
  sma: '简单均线',
  ema: '指数均线',
};
export const GROUP_LINES: Record<System, string[]> = {
  pma: [12, 144, 169, 288, 338, 576, 676].map((n) => `PMA${n}`),
  zlma: ['E15', 'ZLMA'],
  sma: [20, 60, 100, 200].map((n) => `MA${n}`),
  ema: [20, 60, 100, 200].map((n) => `EMA${n}`),
};
export interface RuleConfig {
  buffer: number;
  confirmation: number;
}
export const DEFAULT_RULE: RuleConfig = { buffer: 0.1, confirmation: 2 };
export type Evidence = { label: string; value: number; side: Direction };
export type SystemState = {
  direction: Direction;
  raw: Direction;
  evidence: Evidence[];
  ready: boolean;
  reason: string;
};
export type Assessment = {
  systems: Record<System, SystemState>;
  direction: Direction;
  eligible: number;
  bulls: number;
  bears: number;
  since: number;
  transitions: number;
};
export type AssetInfo = { symbol: string; kind?: string; category?: string; structure?: string };
export function assetClass(s: AssetInfo) {
  if (s.kind === 'stock') return '个股';
  const text = `${s.category || ''} ${s.structure || ''}`;
  if (/杠杆|反向/.test(text)) return '杠杆 / 反向';
  if (/现金|短债|浮息/.test(text)) return '现金 / 短债';
  if (/主动权益收益/.test(text)) return '收益策略';
  if (/债券|国债|通胀债|信用/.test(text)) return '债券';
  if (/数字/.test(text)) return '数字资产';
  if (/贵金属|商品/.test(text)) return '商品 / 美元';
  if (/另类|波动率/.test(text)) return '另类策略';
  return '权益ETF';
}
export function assetPolicy(s: AssetInfo) {
  const group = assetClass(s),
    excluded = ['现金 / 短债', '收益策略', '杠杆 / 反向', '另类策略'].includes(group);
  const note =
    group === '现金 / 短债'
      ? '现金与短债采用观察口径；除息价格下跳可能触发假信号，不进入统一参数选择。'
      : group === '收益策略'
      ? '派息与期权收益未计入价格序列；方向仅描述价格，不代表含分红回报，不进入统一参数选择。'
      : group === '杠杆 / 反向'
      ? '多空描述本产品价格方向，不能直接等同于基础指数方向；每日重置与路径损耗单独评估，不进入统一参数选择。'
      : group === '另类策略'
      ? '期货、波动率与另类收益结构单独评估，不进入统一参数选择。'
      : group === '债券'
      ? '债券价格偏多通常对应收益率下行；票息未计入回测回报。'
      : group === '商品 / 美元'
      ? '方向针对该产品价格；期货展期与现货走势可能不同。'
      : group === '数字资产'
      ? 'ETF交易时段与底层资产全天交易不同；短历史周期不补造长均线。'
      : '统一参数描述价格趋势；多空状态与实际仓位决策分开。';
  return { group, excluded, note };
}
const side = (n: number, band: number): Direction => (n > band ? '多' : n < -band ? '空' : '震荡');
const eligibleEma = (n: number, count: number) =>
  maturity(n, count).residual <= 0.01 && count >= n + 3;
const direction = (v: Direction[]): Direction =>
  v.every((x) => x === '多') ? '多' : v.every((x) => x === '空') ? '空' : '震荡';
export function confirmStates(raw: Direction[], count: number) {
  return raw.map((d, i) =>
    d === '多' || d === '空'
      ? i >= count - 1 && raw.slice(i - count + 1, i + 1).every((x) => x === d)
        ? d
        : '震荡'
      : d,
  );
}
export function classify(data: Computed, config: RuleConfig = DEFAULT_RULE) {
  const volatility = atr(data.bars, 20),
    raw = Object.fromEntries(SYSTEMS.map((s) => [s, [] as SystemState[]])) as Record<
      System,
      SystemState[]
    >;
  for (let i = 0; i < data.bars.length; i++) {
    const close = data.bars[i].c,
      scale = Math.max(volatility[i] || 0, close * 0.0001),
      v = (key: string, offset = 0) => data.lines[key][i - offset]!,
      evidence = (label: string, value: number, band = config.buffer): Evidence => ({
        label,
        value: value / scale,
        side: side(value / scale, band),
      });
    for (const system of SYSTEMS) {
      let ready = false,
        reason = '',
        items: Evidence[] = [],
        d: Direction = '不足';
      if (system === 'zlma') {
        ready = i >= 59;
        reason = '至少60根；零滞后线与EMA15的差值及零滞后线3根斜率同向';
        items =
          i >= 3
            ? [
                evidence('零滞后线 − EMA15', v('ZLMA') - v('E15')),
                evidence('零滞后线3根变化', v('ZLMA') - v('ZLMA', 3), 0),
              ]
            : [];
        d = direction(items.map((e) => e.side));
      } else if (system === 'pma') {
        ready = eligibleEma(676, i + 1);
        reason = '三条通道144/169、288/338、576/676同向；EMA676种子残余须≤1%';
        if (i >= 3)
          for (const [fast, slow] of [
            [144, 169],
            [288, 338],
            [576, 676],
          ]) {
            const a = v(`PMA${fast}`),
              b = v(`PMA${slow}`),
              mid = (a + b) / 2,
              previous = (v(`PMA${fast}`, 3) + v(`PMA${slow}`, 3)) / 2,
              gap =
                close > Math.max(a, b)
                  ? close - Math.max(a, b)
                  : close < Math.min(a, b)
                  ? close - Math.min(a, b)
                  : 0;
            items.push({
              label: `通道 ${fast}/${slow}`,
              value: gap / scale,
              side: direction([
                side(gap / scale, config.buffer),
                side((a - b) / scale, 0),
                side((mid - previous) / scale, 0),
              ]),
            });
          }
        d = direction(items.map((e) => e.side));
      } else {
        const prefix = system === 'sma' ? 'MA' : 'EMA';
        ready = system === 'sma' ? i >= 202 : eligibleEma(200, i + 1);
        reason =
          system === 'sma'
            ? '至少203根；4项中至少3项同向，且价格/200与20线斜率同向'
            : 'EMA200种子残余≤1%；4项中至少3项同向，且价格/200与20线斜率同向';
        if (i >= 202) {
          items = [
            evidence('价格 − 20均线', close - v(`${prefix}20`)),
            evidence('20 − 60均线', v(`${prefix}20`) - v(`${prefix}60`)),
            evidence('60 − 100均线', v(`${prefix}60`) - v(`${prefix}100`)),
            evidence('价格 − 200均线', close - v(`${prefix}200`)),
          ];
          const slope = evidence('20均线3根变化', v(`${prefix}20`) - v(`${prefix}20`, 3), 0);
          d =
            (['多', '空'].find(
              (s) =>
                items.filter((e) => e.side === s).length >= 3 &&
                items[3].side === s &&
                slope.side === s,
            ) as Direction) || '震荡';
          items.push(slope);
        }
      }
      raw[system].push({
        direction: ready ? d : '不足',
        raw: ready ? d : '不足',
        ready,
        reason,
        evidence: items,
      });
    }
  }
  for (const system of SYSTEMS) {
    const confirmed = confirmStates(
      raw[system].map((s) => s.raw),
      config.confirmation,
    );
    raw[system].forEach((s, i) => (s.direction = confirmed[i]));
  }
  let since = 0,
    transitions = 0;
  const history: Assessment[] = data.bars.map((b, i) => {
    const systems = Object.fromEntries(SYSTEMS.map((s) => [s, raw[s][i]])) as Assessment['systems'],
      available = Object.values(systems).filter((s) => s.ready),
      eligible = available.length,
      bulls = available.filter((s) => s.direction === '多').length,
      bears = available.filter((s) => s.direction === '空').length,
      d = systems.zlma.direction,
      previous = i ? raw.zlma[i - 1].direction : '不足';
    if (!i || d !== previous) {
      since = b.t;
      if (i && previous !== '不足' && d !== '不足') transitions++;
    }
    return { systems, direction: d, eligible, bulls, bears, since, transitions };
  });
  const current = history.at(-1) || {
    systems: Object.fromEntries(
      SYSTEMS.map((s) => [
        s,
        { direction: '不足', raw: '不足', ready: false, evidence: [], reason: '尚无已完成K线' },
      ]),
    ) as Assessment['systems'],
    direction: '不足',
    eligible: 0,
    bulls: 0,
    bears: 0,
    since: 0,
    transitions: 0,
  };
  return { history, current };
}
export const directionLabel = (d: Direction) =>
  ({ 多: '偏多', 空: '偏空', 震荡: '中性', 不足: '待验证' }[d]);

export interface BacktestMetric {
  start: string;
  end: string;
  sessions: number;
  return: number;
  maxDrawdown: number;
  trades: number;
  orders: number;
  exposure: number;
  fees: number;
  rejectedOrders: number;
}
export interface BacktestRow {
  symbol: string;
  frame: string;
  group: string;
  excluded: boolean;
  system: string;
  train: BacktestMetric;
  test: BacktestMetric;
  baseline: BacktestMetric;
  benchmark: BacktestMetric;
  stress: BacktestMetric;
}
export interface ResearchReport {
  rulesVersion: string;
  generatedAt: string;
  snapshotGeneratedAt: string;
  hashes: string[];
  selected: RuleConfig;
  selection: { buffer: number; confirmation: number; score: number; assets: number }[];
  rows: BacktestRow[];
  splitDate: string;
  evaluationStart: string;
  engine: string;
  costs: { feeBps: number; slippageBps: number };
  limitations: string[];
  coverage: { symbol: string; frame: string; ready: Record<System, number> }[];
}
