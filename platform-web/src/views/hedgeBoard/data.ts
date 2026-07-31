export type MetricSignal = 'bullish' | 'neutral' | 'watch' | 'risk';

export interface BoardMetric {
  label: string;
  value: string;
  change: string;
  signal: MetricSignal;
  signalLabel: string;
  detail: string;
  sparkline: number[];
}

export interface BoardModule {
  title: string;
  summary: string;
  items: string[];
}

export interface HedgeBoardDefinition {
  id: 'gold' | 'macro' | 'crypto';
  shortTitle: string;
  title: string;
  headline: string;
  biasLabel: string;
  biasSignal: MetricSignal;
  summary: string;
  driver: string;
  cadence: string;
  note: string;
  modules: BoardModule[];
  metrics: BoardMetric[];
  checklist: string[];
}

export const hedgeBoardData: HedgeBoardDefinition[] = [
  {
    id: 'macro',
    shortTitle: '宏观',
    title: '宏观看板',
    headline: '等待更清晰的宏观定价主线',
    biasLabel: '中性观察',
    biasSignal: 'neutral',
    summary: '旧版 hedgeBoard 占位数据，保留为合法模块，避免历史无效文本继续阻塞 TypeScript 检查。',
    driver: '长端利率、美元方向与流动性预期仍在拉扯',
    cadence: '周更框架 / 日更观察',
    note: '当前正式页面已改由 nativeData 终端与研究模块驱动。',
    modules: [
      {
        title: '流动性',
        summary: '观察政策与融资层面的流动性约束。',
        items: ['DLI', 'TGA', 'RRP'],
      },
    ],
    metrics: [
      {
        label: 'Macro Placeholder',
        value: 'Neutral',
        change: '0.0',
        signal: 'neutral',
        signalLabel: '占位',
        detail: '仅用于保留历史类型导出，不承载实际页面数据。',
        sparkline: [42, 43, 44, 45, 44, 43, 42],
      },
    ],
    checklist: ['保留类型兼容', '不再作为页面主数据源'],
  },
  {
    id: 'gold',
    shortTitle: '商品',
    title: '商品看板',
    headline: '保留为旧版占位数据',
    biasLabel: '结构保留',
    biasSignal: 'watch',
    summary: '当前商品页面数据改由 dashboardClean 与本地图表组件驱动。',
    driver: '实际利率、美元与避险情绪',
    cadence: '日更观察',
    note: '此文件仅做历史兼容。',
    modules: [
      {
        title: '价格',
        summary: '黄金主图与驱动拆解。',
        items: ['XAUUSD', 'Real Yield', 'DXY'],
      },
    ],
    metrics: [
      {
        label: 'Gold Placeholder',
        value: 'Watch',
        change: '+0.0',
        signal: 'watch',
        signalLabel: '占位',
        detail: '兼容旧数据结构。',
        sparkline: [55, 56, 57, 58, 57, 56, 55],
      },
    ],
    checklist: ['保留类型兼容', '不再作为页面主数据源'],
  },
  {
    id: 'crypto',
    shortTitle: '加密',
    title: '加密看板',
    headline: '保留为旧版占位数据',
    biasLabel: '风险观察',
    biasSignal: 'bullish',
    summary: '当前加密页面数据改由 dashboardClean 与 TradingView 组件驱动。',
    driver: 'BTC 趋势、稳定币流量与宏观风险偏好',
    cadence: '日更观察',
    note: '此文件仅做历史兼容。',
    modules: [
      {
        title: '核心资产',
        summary: '围绕 BTC 与高 beta 扩散。',
        items: ['BTC', 'ETH', 'TOTAL3'],
      },
    ],
    metrics: [
      {
        label: 'Crypto Placeholder',
        value: 'Risk On',
        change: '+0.0',
        signal: 'bullish',
        signalLabel: '占位',
        detail: '兼容旧数据结构。',
        sparkline: [48, 50, 52, 54, 53, 52, 51],
      },
    ],
    checklist: ['保留类型兼容', '不再作为页面主数据源'],
  },
];
