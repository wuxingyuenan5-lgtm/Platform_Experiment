export type NewsAssetKey =
  | 'macro'
  | 'us-equities'
  | 'a-shares'
  | 'metals'
  | 'crypto'
  | 'energy'
  | 'ai';

export interface NewsDigestItem {
  id: string;
  title: string;
  summary: string;
  source: string;
  publishedAt: string;
  importance: 1 | 2 | 3 | 4 | 5;
  bias: 'bull' | 'neutral' | 'bear';
}

export interface NewsDigestSection {
  key: NewsAssetKey;
  index: string;
  label: string;
  eyebrow: string;
  description: string;
  items: NewsDigestItem[];
}

export const newsDigestSections: NewsDigestSection[] = [
  {
    key: 'macro',
    index: '01',
    label: '宏观',
    eyebrow: 'MACRO',
    description: '优先识别利率、美元、流动性与通胀预期的变化，再决定是否向下映射到单一资产。',
    items: [
      {
        id: 'macro-1',
        title: '长端利率再度抬升，风险资产估值端承压',
        summary: '如果长端利率继续高位运行，黄金、成长股与高久期资产都会同步面临折现压力。',
        source: 'Bloomberg',
        publishedAt: '2026-06-26 08:40',
        importance: 5,
        bias: 'bear',
      },
      {
        id: 'macro-2',
        title: '美元指数维持偏强，全球风险偏好仍受约束',
        summary: '美元并未进入趋势性走弱阶段，跨市场风险资产仍运行在同一流动性约束框架里。',
        source: 'Reuters',
        publishedAt: '2026-06-26 10:15',
        importance: 4,
        bias: 'bear',
      },
      {
        id: 'macro-3',
        title: '市场等待下一组通胀数据，宏观交易进入观察期',
        summary: '数据空窗期意味着定价会更依赖已有主线，短期更适合验证而不是追价。',
        source: 'WSJ',
        publishedAt: '2026-06-26 13:20',
        importance: 3,
        bias: 'neutral',
      },
    ],
  },
  {
    key: 'us-equities',
    index: '02',
    label: '美股',
    eyebrow: 'US EQUITIES',
    description: '重点看龙头盈利预期、指数宽度、回购与再定价节奏，而不是单日情绪噪音。',
    items: [
      {
        id: 'us-1',
        title: 'AI 龙头高位分化加剧，市场容错率下降',
        summary: '市场开始只给最强兑现者溢价，这会直接改写板块内部强弱排序。',
        source: 'Bloomberg',
        publishedAt: '2026-06-26 09:30',
        importance: 5,
        bias: 'bear',
      },
      {
        id: 'us-2',
        title: '企业回购重新开启，为指数高位震荡提供承接',
        summary: '回购不是情绪变量，而是微观流动性变量，会直接影响回撤速度。',
        source: 'Reuters',
        publishedAt: '2026-06-26 11:10',
        importance: 4,
        bias: 'bull',
      },
      {
        id: 'us-3',
        title: '防御板块获得边际增配，市场并非全面 risk-on',
        summary: '当前更像结构性再平衡，而不是无差别追逐风险资产。',
        source: 'WSJ',
        publishedAt: '2026-06-26 14:00',
        importance: 3,
        bias: 'neutral',
      },
    ],
  },
  {
    key: 'a-shares',
    index: '03',
    label: 'A股',
    eyebrow: 'A SHARES',
    description: '把北向资金、政策预期与风格轮动放在一起，判断行情是短反弹还是趋势切换。',
    items: [
      {
        id: 'ashare-1',
        title: '北向资金回流，市场重新交易政策托底预期',
        summary: '这类信号往往同时影响风格、情绪与成交结构，是 A 股最值得优先看的增量变量。',
        source: '财联社',
        publishedAt: '2026-06-26 09:05',
        importance: 4,
        bias: 'bull',
      },
      {
        id: 'ashare-2',
        title: '高股息板块继续获配，成长风格仍待新催化',
        summary: '当前仍偏防守配置，成长风格要真正启动还需要看到盈利预期改善。',
        source: '证券时报',
        publishedAt: '2026-06-26 10:50',
        importance: 3,
        bias: 'neutral',
      },
      {
        id: 'ashare-3',
        title: '顺周期链条修复偏慢，地产与工业仍缺持续放量',
        summary: '这意味着顺周期更像交易型修复，而不是中期主升浪的起点。',
        source: '第一财经',
        publishedAt: '2026-06-26 13:45',
        importance: 4,
        bias: 'bear',
      },
    ],
  },
  {
    key: 'metals',
    index: '04',
    label: '黄金',
    eyebrow: 'PRECIOUS METALS',
    description: '把黄金价格、ETF 资金面、央行购金与实际利率放到同一张图里理解。',
    items: [
      {
        id: 'metals-1',
        title: '黄金高位震荡，但 ETF 流量尚未形成持续共振',
        summary: '价格韧性仍在，但资金面确认度不够，说明趋势尚未完全扩散。',
        source: 'World Gold Council',
        publishedAt: '2026-06-26 08:55',
        importance: 4,
        bias: 'neutral',
      },
      {
        id: 'metals-2',
        title: '实际利率回落放缓，黄金上行斜率受到压制',
        summary: '若实际利率不能继续下台阶，黄金更可能进入高位盘整而非单边拔高。',
        source: 'Bloomberg',
        publishedAt: '2026-06-26 11:20',
        importance: 5,
        bias: 'bear',
      },
      {
        id: 'metals-3',
        title: '央行购金保持中枢偏高，长期配置力量未变',
        summary: '长期支撑仍在，只是短线驱动权更多落在美元和利率手里。',
        source: 'Reuters',
        publishedAt: '2026-06-26 15:10',
        importance: 3,
        bias: 'bull',
      },
    ],
  },
  {
    key: 'crypto',
    index: '05',
    label: '加密',
    eyebrow: 'CRYPTO',
    description: '先分清宏观流动性驱动、ETF 资金面驱动，还是链上主题驱动。',
    items: [
      {
        id: 'crypto-1',
        title: 'BTC ETF 净流入恢复，但价格弹性弱于资金增量',
        summary: '这说明市场结构还没有回到全面追价阶段，更像资金稳定回补。',
        source: 'SoSoValue',
        publishedAt: '2026-06-26 09:20',
        importance: 4,
        bias: 'bull',
      },
      {
        id: 'crypto-2',
        title: '山寨轮动扩散不足，主线仍集中在 BTC 与高流动性代理',
        summary: '如果扩散不起来，行情更像主资产修复而非广谱 beta 行情。',
        source: 'TradingView',
        publishedAt: '2026-06-26 12:05',
        importance: 4,
        bias: 'neutral',
      },
      {
        id: 'crypto-3',
        title: '链上稳定币供应继续抬升，风险偏好底层变量仍偏正面',
        summary: '稳定币供应扩张是中层流动性信号，但真正定价仍取决于宏观环境配合度。',
        source: 'DefiLlama',
        publishedAt: '2026-06-26 16:00',
        importance: 3,
        bias: 'bull',
      },
    ],
  },
  {
    key: 'energy',
    index: '06',
    label: '能源',
    eyebrow: 'ENERGY',
    description: '供给扰动、库存拐点与期限结构，决定原油交易更偏趋势还是偏震荡。',
    items: [
      {
        id: 'energy-1',
        title: '原油供给扰动仍停留在 headline 阶段',
        summary: '真正能推动趋势的不是标题强弱，而是库存与出口流向是否同步收紧。',
        source: 'Reuters',
        publishedAt: '2026-06-26 08:30',
        importance: 4,
        bias: 'neutral',
      },
      {
        id: 'energy-2',
        title: '裂解价差保持韧性，需求端尚未明显掉队',
        summary: '需求没有显著恶化，使油价在高位依然具备支撑。',
        source: 'Bloomberg',
        publishedAt: '2026-06-26 11:40',
        importance: 4,
        bias: 'bull',
      },
      {
        id: 'energy-3',
        title: '期限结构回归平缓，趋势交易拥挤度有所下降',
        summary: '从结构看更适合等待新的供需证据，而不是在中段追涨杀跌。',
        source: 'WSJ',
        publishedAt: '2026-06-26 14:55',
        importance: 3,
        bias: 'neutral',
      },
    ],
  },
  {
    key: 'ai',
    index: '07',
    label: 'AI',
    eyebrow: 'AI THEMES',
    description: '观察资本开支、算力供需与产业链瓶颈，判断主题是延续还是退潮。',
    items: [
      {
        id: 'ai-1',
        title: '算力资本开支预期维持高位，但订单兑现节奏更受关注',
        summary: '主题没有结束，只是市场从讲故事切换到看兑现，这会抬高分化程度。',
        source: 'Bloomberg',
        publishedAt: '2026-06-26 09:55',
        importance: 5,
        bias: 'neutral',
      },
      {
        id: 'ai-2',
        title: '上游器件紧缺边际缓和，估值从稀缺溢价转向业绩溢价',
        summary: '这意味着配置重点会从最稀缺环节，转向真正能兑现利润的公司。',
        source: 'WSJ',
        publishedAt: '2026-06-26 13:35',
        importance: 4,
        bias: 'neutral',
      },
      {
        id: 'ai-3',
        title: '下游应用融资回暖，主题从基础设施向应用侧扩散',
        summary: '如果扩散继续成立，AI 主线会进入第二阶段，而不仅仅是算力单线叙事。',
        source: 'Reuters',
        publishedAt: '2026-06-26 15:45',
        importance: 3,
        bias: 'bull',
      },
    ],
  },
];

export type WealthFrequency = 'daily' | 'fixed' | 'floating';
export type WealthLock = 'short' | 'mid' | 'long';

export interface WealthCampaign {
  id: string;
  name: string;
  platform: string;
  exchange: string;
  coin: string;
  frequency: WealthFrequency;
  lock: WealthLock;
  apy: string;
  apyValue: number;
  apyNote: string;
  tags: string[];
  expiryLabel: string;
  expiryNote: string;
  daysLeft: number;
  description: string;
}

export const wealthCampaigns: WealthCampaign[] = [
  {
    id: 'usd1-gate',
    name: 'USD1 持仓活动',
    platform: 'Gate 主站 / 活动',
    exchange: 'gate',
    coin: 'USD1',
    frequency: 'daily',
    lock: 'long',
    apy: '15.00%',
    apyValue: 15,
    apyNote: '$10,000 本金到期预估收益 $123.29',
    tags: ['每日派息', '持有即计息', '长期活动'],
    expiryLabel: '长期',
    expiryNote: '持续关注活动规则',
    daysLeft: 99,
    description: '以稳定币持仓为基础的活动信息，仅用于展示活动结构，不提供申购入口。',
  },
  {
    id: 'gho-aave',
    name: 'GHO 链上收益活动',
    platform: 'Aave / 链上',
    exchange: 'aave',
    coin: 'GHO',
    frequency: 'daily',
    lock: 'mid',
    apy: '13.36%',
    apyValue: 13.36,
    apyNote: '$5,000 本金到期预估收益 $58.56',
    tags: ['额度 $5,000', '每日 08:00 派息', '赎回 2 天'],
    expiryLabel: '长期',
    expiryNote: '额度 $5,000',
    daysLeft: 99,
    description: '展示链上稳定币活动的币种、平台、期限和收益指标。',
  },
  {
    id: 'lorenzo-binance',
    name: 'Lorenzo USD1',
    platform: 'Binance 主站 / 链上',
    exchange: 'binance',
    coin: 'USD1',
    frequency: 'fixed',
    lock: 'short',
    apy: '13.05%',
    apyValue: 13.05,
    apyNote: '$10,000 本金到期预估收益 $3.57',
    tags: ['固定期限', '派息 BANK 代币', '短期活动'],
    expiryLabel: '还剩 1 天',
    expiryNote: '截止 2026-06-19 07:59',
    daysLeft: 1,
    description: '固定期限活动，适合在列表中观察锁仓和到期时间字段。',
  },
  {
    id: 'usdgo-bitget',
    name: 'USDGO 活期赚币',
    platform: 'Bitget 主站 / 活期赚币',
    exchange: 'bitget',
    coin: 'USDGO',
    frequency: 'floating',
    lock: 'mid',
    apy: '12.00%',
    apyValue: 12,
    apyNote: '$10,000 本金到期预估收益 $65.75',
    tags: ['额度 $300,000', '每小时派息', '利率浮动'],
    expiryLabel: '还剩 20 天',
    expiryNote: '截止 2026-07-08 23:59',
    daysLeft: 20,
    description: '浮动收益活动，用于验证利率排序和条件筛选。',
  },
  {
    id: 'pharos-okx',
    name: 'Pharos USDC',
    platform: 'OKX 主站 / 锁定',
    exchange: 'okx',
    coin: 'USDC',
    frequency: 'fixed',
    lock: 'long',
    apy: '11.49%',
    apyValue: 11.49,
    apyNote: '$10,000 本金到期预估收益 $122.74',
    tags: ['锁仓 91 天', '赎回 7 天', '长期'],
    expiryLabel: '还剩 32 天',
    expiryNote: '截止 2026-07-20 19:00',
    daysLeft: 32,
    description: '锁定期较长的 USDC 活动，展示期限和到期字段。',
  },
  {
    id: 'usd1-bybit',
    name: 'USD1 持仓赚币',
    platform: 'Bybit 主站 / 持仓赚币',
    exchange: 'bybit',
    coin: 'USD1',
    frequency: 'daily',
    lock: 'mid',
    apy: '11.43%',
    apyValue: 11.43,
    apyNote: '$10,000 本金到期预估收益 $93.93',
    tags: ['每日派息', '派息 WLFI 代币', '中期活动'],
    expiryLabel: '还剩 30 天',
    expiryNote: '截止 2026-07-18 08:00',
    daysLeft: 30,
    description: '展示持仓类活动的信息密度和标签结构。',
  },
];
