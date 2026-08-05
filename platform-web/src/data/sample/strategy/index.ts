export type StrategyDeskKey = 'funding' | 'crossSpread' | 'trend';

export interface StrategyKpiItem {
  label: string;
  value: string;
  note: string;
  tone?: 'positive' | 'warning' | 'neutral';
}

export interface StrategyCardItem {
  title: string;
  value: string;
  note: string;
  tone?: 'positive' | 'warning' | 'neutral';
}

export interface StrategyTableSection {
  columns: Array<{ key: string; label: string }>;
  rows: Array<Record<string, string>>;
}

export const strategySampleMeta = Object.freeze({
  state: 'sample' as const,
  source: 'sample:strategy-management-restoration',
  asOf: '非实时 · 参考提交 bbdff039',
  actionable: false,
});

export const strategyDeskOrder: StrategyDeskKey[] = ['funding', 'crossSpread', 'trend'];

export const strategyDeskLabels: Record<StrategyDeskKey, string> = {
  funding: '资金费率套利',
  crossSpread: '跨所价差',
  trend: '趋势跟踪',
};

const commonCurves = [
  { title: '策略净值', points: [20, 28, 26, 38, 46, 43, 58, 64, 70] },
  { title: '风险预算', points: [48, 44, 50, 47, 42, 38, 41, 36, 34] },
];

export const strategyProfiles: Record<
  StrategyDeskKey,
  {
    overview: StrategyKpiItem[];
    pnl: StrategyCardItem[];
    riskCards: StrategyCardItem[];
    structureCards: StrategyCardItem[];
    rulePanel: { title: string; rules: string[] };
    riskOverview: StrategyCardItem[];
    runtimeCards: StrategyCardItem[];
    curve: { title: string; points: number[] };
    metricCurves: Array<{ title: string; points: number[] }>;
    records: Record<string, StrategyTableSection>;
  }
> = {
  funding: {
    overview: [
      { label: '账户权益', value: '--', note: '示例组合口径' },
      { label: '资金占用', value: '28%', note: '非实时' },
      { label: '近30日', value: '+1.42%', note: '非真实业绩', tone: 'positive' },
      { label: '风险状态', value: '观察', note: '不可执行', tone: 'warning' },
    ],
    pnl: [
      { title: '累计价差收益', value: '--', note: '示例损益拆分' },
      { title: '累计资金费', value: '--', note: '示例口径' },
      { title: '累计手续费', value: '--', note: '示例口径' },
      { title: '净收益', value: '--', note: '不构成业绩披露' },
    ],
    riskCards: [
      { title: '保证金率', value: '--', note: '未连接正式 Owner' },
      { title: '最大单腿敞口', value: '--', note: '样例风控' },
    ],
    structureCards: [
      { title: '现货腿', value: 'Bybit', note: '示例账户' },
      { title: '永续腿', value: 'Bybit', note: '示例账户' },
    ],
    rulePanel: {
      title: '资金费率策略规则',
      rules: ['样例状态禁止下单', 'Live Write 双门禁保持关闭', '费率、基差和流动性需同时满足'],
    },
    riskOverview: [
      { title: '方向敞口', value: '中性', note: '样例' },
      { title: '流动性', value: '待复核', note: '样例' },
    ],
    runtimeCards: [
      { title: '行情订阅', value: '未配置', note: 'sample' },
      { title: '执行状态', value: '禁用', note: 'actionable=false' },
    ],
    curve: { title: '账户净值（示例）', points: commonCurves[0].points },
    metricCurves: commonCurves,
    records: {
      positions: {
        columns: [
          { key: 'symbol', label: '标的' },
          { key: 'side', label: '方向' },
          { key: 'quantity', label: '数量' },
          { key: 'status', label: '状态' },
        ],
        rows: [{ symbol: 'BTCUSDT', side: '对冲', quantity: '--', status: '样例' }],
      },
      orders: {
        columns: [
          { key: 'orderId', label: '订单号' },
          { key: 'venue', label: '场所' },
          { key: 'status', label: '状态' },
        ],
        rows: [{ orderId: 'SAMPLE-FUNDING-01', venue: 'Bybit', status: '不可执行' }],
      },
    },
  },
  crossSpread: {
    overview: [
      { label: 'Bybit 权益', value: '--', note: '真实接口可用时读取' },
      { label: 'MT5 权益', value: '--', note: '真实接口可用时读取' },
      { label: '组合价差', value: '--', note: '研究样例' },
      { label: '执行状态', value: '关闭', note: 'Live Write关闭', tone: 'warning' },
    ],
    pnl: [
      { title: '价差变动总损益', value: '--', note: '研究样例' },
      { title: '累计资金费', value: '--', note: '研究样例' },
      { title: '累计手续费', value: '--', note: '研究样例' },
      { title: '滑点成本', value: '--', note: '单独披露' },
    ],
    riskCards: [
      { title: 'Bybit 保证金率', value: '--', note: '真实接口读取失败时不回退假值' },
      { title: 'MT5 Margin Level', value: '--', note: '真实接口读取失败时不回退假值' },
    ],
    structureCards: [
      { title: '左腿', value: 'XAUUSDT.P', note: 'Bybit' },
      { title: '右腿', value: 'XAUUSD+', note: 'MT5' },
    ],
    rulePanel: {
      title: '跨所价差运行规则',
      rules: ['ACK 不等于 Fill', 'result_unknown 必须查询确认', '双腿处置继续由正式执行工作区负责'],
    },
    riskOverview: [
      { title: '单腿风险', value: '独立门禁', note: '保持现有安全语义' },
      { title: '执行权限', value: '后端校验', note: '前端隐藏不等于授权' },
    ],
    runtimeCards: [
      { title: '观测接口', value: '读取中', note: 'CrossSpreadObservability' },
      { title: '执行区', value: '正式工作区', note: 'CrossVenueExecutionWorkspace' },
    ],
    curve: { title: '价差净值（示例）', points: [32, 38, 35, 44, 42, 53, 58, 54, 63] },
    metricCurves: commonCurves,
    records: {
      positions: {
        columns: [
          { key: 'venue', label: '场所' },
          { key: 'symbol', label: '标的' },
          { key: 'side', label: '方向' },
          { key: 'status', label: '状态' },
        ],
        rows: [
          { venue: 'Bybit', symbol: 'XAUUSDT.P', side: '左腿', status: '样例' },
          { venue: 'MT5', symbol: 'XAUUSD+', side: '右腿', status: '样例' },
        ],
      },
      orders: {
        columns: [
          { key: 'batch', label: '批次' },
          { key: 'leg', label: '腿' },
          { key: 'status', label: '状态' },
        ],
        rows: [{ batch: 'SAMPLE-XVENUE-01', leg: '双腿', status: '不可执行' }],
      },
    },
  },
  trend: {
    overview: [
      { label: '策略净值', value: '--', note: '示例' },
      { label: '资本占用', value: '22%', note: '示例' },
      { label: '近30日', value: '+0.44%', note: '非真实业绩', tone: 'positive' },
      { label: '风险状态', value: '研究', note: '不可部署' },
    ],
    pnl: [
      { title: '趋势收益', value: '--', note: '示例' },
      { title: '换手成本', value: '--', note: '示例' },
      { title: '滑点', value: '--', note: '示例' },
      { title: '净收益', value: '--', note: '非真实业绩' },
    ],
    riskCards: [
      { title: '最大回撤', value: '--', note: '样例' },
      { title: '波动率', value: '--', note: '样例' },
    ],
    structureCards: [
      { title: '标的池', value: '股指', note: '研究样例' },
      { title: '周期', value: '日频', note: '研究样例' },
    ],
    rulePanel: {
      title: '趋势策略规则',
      rules: ['仅用于研究展示', '不自动部署', '正式参数 Owner 尚未配置'],
    },
    riskOverview: [
      { title: '趋势暴露', value: '动态', note: '样例' },
      { title: '杠杆', value: '禁用', note: '不可执行' },
    ],
    runtimeCards: [
      { title: '信号引擎', value: '样例', note: '非实时' },
      { title: '执行引擎', value: '禁用', note: 'Live Write关闭' },
    ],
    curve: { title: '趋势净值（示例）', points: [18, 24, 29, 27, 36, 45, 49, 57, 62] },
    metricCurves: commonCurves,
    records: {
      positions: {
        columns: [
          { key: 'symbol', label: '标的' },
          { key: 'signal', label: '信号' },
          { key: 'status', label: '状态' },
        ],
        rows: [{ symbol: '中证1000', signal: '观察', status: '样例' }],
      },
      orders: {
        columns: [
          { key: 'orderId', label: '订单号' },
          { key: 'status', label: '状态' },
        ],
        rows: [{ orderId: 'SAMPLE-TREND-01', status: '不可执行' }],
      },
    },
  },
};
