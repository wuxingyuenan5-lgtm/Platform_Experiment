// Deterministic, synthetic research scenarios. No venue or account data is read.
export interface Pair {
  id: string;
  symbol: string;
  venue: string;
  asset: '加密' | '金属' | '股票';
  mapping: string;
  eligible: boolean;
  reason: string;
  state: string;
  price: number;
  hours: number;
  nextBp: number;
  basisBp: number;
  spotIndexBp: number;
  exitMoveBp: number;
  feeBp: number;
  depth: [number, number];
  oi: number;
  priceChange: number;
  taker: number;
  event: string;
}

export const pairs: Pair[] = [
  {
    id: 'btc-bn',
    symbol: 'BTC',
    venue: 'Binance',
    asset: '加密',
    mapping: '同资产配对',
    eligible: true,
    reason: '',
    state: '稳定 Carry',
    price: 80000,
    hours: 8,
    nextBp: 1.4,
    basisBp: -2,
    spotIndexBp: 1,
    exitMoveBp: 3,
    feeBp: 12,
    depth: [1800000, 2400000],
    oi: 2.4,
    priceChange: 1.2,
    taker: 52,
    event: '无额外事件冲击情景',
  },
  {
    id: 'eth-bb',
    symbol: 'ETH',
    venue: 'Bybit',
    asset: '加密',
    mapping: '同资产配对',
    eligible: true,
    reason: '',
    state: '稳定 Carry',
    price: 2800,
    hours: 8,
    nextBp: 1.8,
    basisBp: 1.5,
    spotIndexBp: -0.5,
    exitMoveBp: 5,
    feeBp: 14,
    depth: [900000, 1300000],
    oi: 4.8,
    priceChange: 2.1,
    taker: 54,
    event: '无额外事件冲击情景',
  },
  {
    id: 'btc-bb',
    symbol: 'BTC',
    venue: 'Bybit',
    asset: '加密',
    mapping: '同资产配对',
    eligible: true,
    reason: '',
    state: 'Carry 衰减',
    price: 80010,
    hours: 8,
    nextBp: 0.55,
    basisBp: -3,
    spotIndexBp: 2,
    exitMoveBp: 2,
    feeBp: 12,
    depth: [1100000, 1600000],
    oi: -3.6,
    priceChange: 0.5,
    taker: 48,
    event: '下一期资费低于历史均值',
  },
  {
    id: 'sol-bg',
    symbol: 'SOL',
    venue: 'Bitget',
    asset: '加密',
    mapping: '同资产配对',
    eligible: true,
    reason: '',
    state: '杠杆拥挤',
    price: 150,
    hours: 4,
    nextBp: 2.1,
    basisBp: 12,
    spotIndexBp: 3,
    exitMoveBp: 18,
    feeBp: 18,
    depth: [280000, 420000],
    oi: 19.2,
    priceChange: 8.5,
    taker: 66,
    event: 'OI 与主动买入同步扩张',
  },
  {
    id: 'doge-bn',
    symbol: 'DOGE',
    venue: 'Binance',
    asset: '加密',
    mapping: '同资产配对',
    eligible: true,
    reason: '',
    state: '去杠杆',
    price: 0.18,
    hours: 4,
    nextBp: -0.6,
    basisBp: -8,
    spotIndexBp: 4,
    exitMoveBp: 15,
    feeBp: 18,
    depth: [160000, 250000],
    oi: -16.8,
    priceChange: -11.3,
    taker: 33,
    event: '负资费与退出深度下降',
  },
  {
    id: 'xaut-bb',
    symbol: 'XAUT',
    venue: 'Bybit',
    asset: '金属',
    mapping: '同代币配对待核验',
    eligible: false,
    reason: '同所产品与指数映射待核验',
    state: '映射待核验',
    price: 3000,
    hours: 8,
    nextBp: 1.2,
    basisBp: 6,
    spotIndexBp: 9,
    exitMoveBp: 8,
    feeBp: 20,
    depth: [120000, 180000],
    oi: 1.2,
    priceChange: 0.4,
    taker: 50,
    event: '底层金属休市情景：代币与指数偏离扩大',
  },
  {
    id: 'crcl-bg',
    symbol: 'CRCL',
    venue: 'Bitget',
    asset: '股票',
    mapping: '股票代币／股票永续',
    eligible: false,
    reason: '权利、乘数与分红处理待核验',
    state: '事件观察',
    price: 100,
    hours: 8,
    nextBp: 5.2,
    basisBp: 28,
    spotIndexBp: 15,
    exitMoveBp: 35,
    feeBp: 24,
    depth: [45000, 90000],
    oi: 12.6,
    priceChange: 5.5,
    taker: 62,
    event: '财报与分红情景：公司行动现金流尚未确认',
  },
  {
    id: 'xau-bg',
    symbol: 'XAU',
    venue: 'Bitget',
    asset: '金属',
    mapping: '黄金代币／XAU 代理',
    eligible: false,
    reason: '代理对冲不具备同资产资格',
    state: '基差失真',
    price: 3000,
    hours: 4,
    nextBp: 3.6,
    basisBp: 45,
    spotIndexBp: 30,
    exitMoveBp: 40,
    feeBp: 22,
    depth: [70000, 140000],
    oi: 8.4,
    priceChange: 1.8,
    taker: 59,
    event: '代币赎回与指数休市价格不可互换',
  },
];

export const snapshot = Date.parse('2026-11-06T00:00:00+08:00');
export function history(pair: Pair) {
  const count = (30 * 24) / pair.hours;
  return Array.from({ length: count }, (_, i) => {
    const fade = pair.state === 'Carry 衰减' ? (count - i) / count : 0;
    const spike = pair.state === '杠杆拥挤' && i > count - 8 ? 2.3 : 0;
    const rate =
      pair.nextBp * 0.8 + Math.sin(i * 0.73) * 0.7 + Math.cos(i * 0.27) * 0.32 + fade + spike;
    return {
      time: snapshot - (count - i - 1) * pair.hours * 3600000,
      value: Number(rate.toFixed(3)),
    };
  });
}
export function statistics(pair: Pair) {
  const values = history(pair).map((p) => p.value);
  const sum = (v: number[]) => v.reduce((s, n) => s + n, 0);
  const positives = values.filter((v) => v > 0);
  const top = [...positives].sort((a, b) => b - a).slice(0, Math.ceil(values.length * 0.1));
  let streak = 0;
  for (let i = values.length - 1; i >= 0 && values[i] > 0; i--) streak++;
  return {
    day: sum(values.slice(-24 / pair.hours)),
    week: sum(values.slice((-7 * 24) / pair.hours)),
    month: sum(values),
    positive: (positives.length / values.length) * 100,
    concentration: positives.length ? (sum(top) / sum(positives)) * 100 : 0,
    streak,
    count: values.length,
  };
}
export interface Assumptions {
  notional: number;
  days: number;
  fundingScale: number;
  basisMove: number;
  depthLoss: number;
  priceShock: number;
  reservePct: number;
}
export function evaluate(pair: Pair, a: Assumptions) {
  const settlements = Math.floor((a.days * 24) / pair.hours);
  const quantity = a.notional / pair.price;
  const capacity = Math.min(...pair.depth) * (1 - a.depthLoss / 100);
  const covered = a.notional <= capacity;
  // Simplified depth-cost curve, in bp of the entry spot notional, not a venue VWAP.
  const impactBp = 2 + (8 * a.notional) / Math.max(capacity, 1);
  const funding = (((a.notional * pair.nextBp * a.fundingScale) / 100) * settlements) / 10000;
  const basis = (-a.notional * a.basisMove) / 10000;
  const fees = (a.notional * pair.feeBp) / 10000;
  const impact = (a.notional * impactBp) / 10000;
  const net = funding + basis - fees - impact;
  const reserve = (a.notional * a.reservePct) / 100;
  const capital = a.notional + reserve;
  const cashNeed =
    (a.notional * Math.max(0, a.priceShock)) / 100 +
    (a.notional * Math.max(0, a.basisMove)) / 10000 +
    a.notional * (1 + Math.max(0, a.priceShock) / 100) * 0.005 +
    fees / 2 +
    impact / 2;
  const cashLeft = reserve - cashNeed;
  const basisBudget = a.notional * 0.005;
  const gates = [
    {
      name: '产品配对',
      pass: pair.eligible,
      detail: pair.eligible ? '同资产、等经济数量情景' : pair.reason,
    },
    {
      name: '持有收益',
      pass: net > 0 && pair.nextBp * a.fundingScale > 0,
      detail:
        pair.nextBp * a.fundingScale <= 0
          ? '正资费条件不满足'
          : net > 0
          ? '情景净收益为正'
          : '资费未覆盖基差与成本',
    },
    {
      name: '基差风险',
      pass: Math.max(0, -basis) <= basisBudget,
      detail: '不利基差损失预算：名义金额的 0.5%（假设）',
    },
    {
      name: '退出容量',
      pass: covered,
      detail: covered ? '25bp 内双腿深度覆盖目标规模' : '25bp 内较薄一腿深度不足',
    },
    {
      name: '现金压力',
      pass: cashLeft >= 0,
      detail: cashLeft >= 0 ? '假设储备覆盖空头现金需求' : '假设储备不足，现货浮盈未计入',
    },
  ];
  const status: '待核验' | '可研究' | '暂缓' = !pair.eligible
    ? '待核验'
    : gates.every((g) => g.pass)
    ? '可研究'
    : '暂缓';
  const dailyIncome =
    (((a.notional * pair.nextBp * a.fundingScale) / 100) * (24 / pair.hours)) / 10000;
  return {
    quantity,
    settlements,
    capacity,
    covered,
    impactBp,
    funding,
    basis,
    fees,
    impact,
    net,
    reserve,
    capital,
    cashNeed,
    cashLeft,
    gates,
    status,
    returnPct: (net / capital) * 100,
    breakEven: dailyIncome > 0 ? Math.max(0, fees + impact - basis) / dailyIncome : null,
  };
}
export const money = (n: number, signed = false) =>
  `${signed && n > 0 ? '+' : ''}${n.toLocaleString('en-US', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })}`;
export const bp = (n: number) => `${n > 0 ? '+' : ''}${n.toFixed(2)}`;
