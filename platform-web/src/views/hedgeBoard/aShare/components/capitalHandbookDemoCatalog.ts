export const demoCategories = [
  { key: 'overview', label: '资金总览' },
  { key: 'funds', label: '公募基金' },
  { key: 'insurance', label: '保险资金' },
  { key: 'foreign', label: '外资' },
  { key: 'pension', label: '养老资金' },
  { key: 'resident', label: '居民资金' },
  { key: 'corporate', label: '产业资本' },
  { key: 'demand', label: '融资需求' },
] as const;
export type DemoCategory = (typeof demoCategories)[number]['key'];
export type DemoRecipe =
  | 'series'
  | 'flows'
  | 'bridge'
  | 'allocation'
  | 'companyMatrix'
  | 'holdings'
  | 'rankHistory'
  | 'attribution'
  | 'subscription'
  | 'histogram'
  | 'holderMix'
  | 'industry'
  | 'accounting'
  | 'stockStyle'
  | 'events'
  | 'supply';
export interface DemoMetric {
  name: string;
  unit: string;
  base: number;
  amplitude?: number;
  trend?: number;
  right?: boolean;
  bar?: boolean;
}
export interface DemoSpec {
  id: string;
  category: DemoCategory;
  page: string;
  title: string;
  recipe: DemoRecipe;
  definition: string;
  metrics?: DemoMetric[];
}
const metric = (
  name: string,
  unit: string,
  base: number,
  right = false,
  amplitude = base * 0.15,
  trend = 0,
  bar = false,
): DemoMetric => ({ name, unit, base, right, amplitude, trend, bar });
const specs: DemoSpec[] = [];
function add(
  category: DemoCategory,
  id: string,
  page: string,
  title: string,
  recipe: DemoRecipe,
  definition: string,
  metrics?: DemoMetric[],
) {
  specs.push({ category, id, page, title, recipe, definition, metrics });
}

add(
  'overview',
  'funding-balance',
  '4、6—7',
  '资金流入流出与供需差额',
  'flows',
  '各渠道按同一期间展示；供需差额为示例流入减流出，不与机构存量相加。',
);
add(
  'funds',
  'fund-sector-allocation',
  '10—11',
  '行业配置、环比与历史分位',
  'allocation',
  '配置比例采用组合内股票资产权重；环比为本期减上期，超低配为本期减基准。',
);
add(
  'funds',
  'fund-heavy-a',
  '12',
  'A股前二十大重仓股与季度变化',
  'holdings',
  '示例证券均为虚构名称；持仓权重、季度变化、持有基金数和收益率并列比较。',
);
add(
  'insurance',
  'insurance-sector-change',
  '17—18',
  '险资行业配置与估值剔除',
  'attribution',
  '配置残差为实际权重减价格自然变化后权重，不全等于真实交易。',
);
add(
  'insurance',
  'insurance-premium',
  '17',
  '新增保费与潜在权益配置',
  'series',
  '示例情景中的保费和潜在配置独立展示，潜在配置不是实际入市资金。',
  [
    metric('新增保费', '亿元', 2100, false, 800, 800),
    metric('情景权益配置', '亿元', 550, false, 200, 150),
  ],
);

add(
  'foreign',
  'foreign-sector-rank',
  '21',
  '外资前十大行业持仓变迁',
  'rankHistory',
  '展示独立模拟的外资样本；不将QFII披露直接扩称全部外资。',
);
add(
  'foreign',
  'foreign-value-share',
  '19',
  '外资股票市值及A股市值占比',
  'series',
  '持股占比＝外资持有A股市值 / 同期A股总市值。',
  [metric('持股市值', '亿元', 30000, false, 4500, 7000), metric('占A股市值', '%', 3.1, true, 0.5)],
);
add(
  'foreign',
  'foreign-quarter-flow',
  '19',
  '外资季度净买入',
  'series',
  '完全模拟的净买入；2024年后不冒充交易所每日北向净流入。',
  [metric('季度净买入', '亿元', 0, false, 1100, 0, true)],
);
add(
  'foreign',
  'foreign-pmi',
  '20',
  '外资流量与PMI',
  'series',
  '两侧均为模拟序列，用于展示配对研究结构。',
  [metric('净流入', '亿元', 0, false, 500, 0, true), metric('PMI', '点', 50, true, 2)],
);
add(
  'foreign',
  'foreign-yield',
  '20',
  '外资流量与美债利率',
  'series',
  '同月模拟观测，不将同期关联解释为资金流因果。',
  [metric('净流入', '亿元', 0, false, 500, 0, true), metric('10年美债利率', '%', 3.6, true, 0.7)],
);
add(
  'foreign',
  'foreign-fx',
  '20—21',
  '外资流量与人民币汇率',
  'series',
  '汇率单位为人民币元/美元；净流量用独立金额轴。',
  [
    metric('净流入', '亿元', 0, false, 500, 0, true),
    metric('美元兑人民币', '元/美元', 7, true, 0.25),
  ],
);
add(
  'foreign',
  'foreign-relative',
  '21',
  '外资流量与中国资产相对收益',
  'series',
  '相对收益为模拟中国股票组合与模拟全球股票组合的同期收益率之差。',
  [metric('净流入', '亿元', 0, false, 500, 0, true), metric('中国资产相对收益', '%', 0, true, 15)],
);

add(
  'pension',
  'pension-enterprise',
  '26—27',
  '企业年金积累规模与收益',
  'series',
  '模拟企业年金积累基金，不与社保、职业年金规模混合。',
  [metric('积累基金', '亿元', 26000, false, 1800, 9000), metric('投资收益率', '%', 4, true, 3)],
);
add(
  'pension',
  'pension-occupation',
  '27',
  '职业年金投资运营规模',
  'series',
  '独立职业年金模拟序列，不使用企业年金或社保规模替代。',
  [metric('投资运营规模', '亿元', 20000, false, 700, 11000)],
);
add(
  'pension',
  'pension-stock-change',
  '26',
  '社保持股市值与估值剔除变化',
  'bridge',
  '期末持股市值＝期初市值＋新增持仓＋存量持仓净增减＋估值变动。',
);
add(
  'resident',
  'resident-market',
  '27',
  '新开户与市场表现',
  'series',
  '开户以账户而非去重人数计数；两侧为模拟月度观测。',
  [metric('新开户', '万户', 180, false, 90, 0, true), metric('市场区间收益', '%', 0, true, 13)],
);
add(
  'corporate',
  'corporate-net',
  '28',
  '产业资本增持、减持与净额',
  'supply',
  '按实际实施期模拟汇总增持、减持与净额，不按重复公告累加。',
);
add(
  'demand',
  'supply-annual',
  '29',
  'IPO、再融资、回购与分红',
  'supply',
  '现金募集为资金需求，实施回购与现金分红单列；示例净额不称全市场净流入。',
);

export const DEMO_CATALOG: readonly DemoSpec[] = specs;
export const FOREIGN_COMPARISON_IDS: readonly string[] = [
  'foreign-pmi',
  'foreign-yield',
  'foreign-fx',
  'foreign-relative',
];
