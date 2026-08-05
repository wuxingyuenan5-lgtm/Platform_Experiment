export type NewsAssetKey = 'macro' | 'equity' | 'commodity' | 'crypto';

export const newsSampleMeta = Object.freeze({
  state: 'sample' as const,
  source: 'sample:news-digest',
  asOf: '非实时 · 编辑样例',
  actionable: false,
});

export const wealthSampleMeta = Object.freeze({
  state: 'sample' as const,
  source: 'sample:wealth-campaigns',
  asOf: '非实时 · 产品结构样例',
  actionable: false,
});

export const newsDigestSections: Array<{
  key: NewsAssetKey;
  index: string;
  label: string;
  eyebrow: string;
  items: Array<{ id: string; title: string; summary: string; publishedAt: string; source: string; importance: number; bias: 'positive' | 'neutral' | 'negative' }>;
}> = [
  {
    key: 'macro', index: '01', label: '宏观', eyebrow: 'MACRO SAMPLE',
    items: [
      { id: 'm1', title: '美元、利率与风险资产联动观察', summary: '样例摘要仅用于恢复原新闻整理结构，不代表当前市场事实。', publishedAt: '非实时', source: 'sample:editorial', importance: 1, bias: 'neutral' },
      { id: 'm2', title: '流动性变量检查清单', summary: '观察美元指数、实际利率与波动率是否同向变化。', publishedAt: '非实时', source: 'sample:editorial', importance: 2, bias: 'neutral' },
      { id: 'm3', title: '经济数据日历影响路径', summary: '展示事件、预期差和资产传导的产品信息层级。', publishedAt: '非实时', source: 'sample:editorial', importance: 2, bias: 'neutral' },
    ],
  },
  {
    key: 'equity', index: '02', label: '权益', eyebrow: 'EQUITY SAMPLE',
    items: [
      { id: 'e1', title: '成交扩散与风格切换观察', summary: '关注宽基、行业广度和成交额的结构关系。', publishedAt: '非实时', source: 'sample:editorial', importance: 1, bias: 'positive' },
      { id: 'e2', title: '小盘与核心资产相对强弱', summary: '样例内容不构成板块推荐。', publishedAt: '非实时', source: 'sample:editorial', importance: 2, bias: 'neutral' },
      { id: 'e3', title: '进攻与防守风格核对', summary: '仅展示新闻卡片和影响标签结构。', publishedAt: '非实时', source: 'sample:editorial', importance: 2, bias: 'neutral' },
    ],
  },
  {
    key: 'commodity', index: '03', label: '商品', eyebrow: 'COMMODITY SAMPLE',
    items: [
      { id: 'c1', title: '有色与贵金属相对强弱', summary: '比较铜、金与美元利率变量的方向一致性。', publishedAt: '非实时', source: 'sample:editorial', importance: 1, bias: 'positive' },
      { id: 'c2', title: '库存与基差观察', summary: '样例摘要不代表当前库存事实。', publishedAt: '非实时', source: 'sample:editorial', importance: 2, bias: 'neutral' },
      { id: 'c3', title: '供给扰动检查', summary: '仅用于恢复原产品结构。', publishedAt: '非实时', source: 'sample:editorial', importance: 2, bias: 'neutral' },
    ],
  },
  {
    key: 'crypto', index: '04', label: '加密', eyebrow: 'CRYPTO SAMPLE',
    items: [
      { id: 'k1', title: '资金费与跨所价差状态', summary: '观察永续资金费、现货深度和稳定币换汇因子。', publishedAt: '非实时', source: 'sample:editorial', importance: 1, bias: 'neutral' },
      { id: 'k2', title: '交易所流动性结构', summary: '样例内容不可作为下单依据。', publishedAt: '非实时', source: 'sample:editorial', importance: 2, bias: 'neutral' },
      { id: 'k3', title: '稳定币换汇因子', summary: '展示新闻整理字段结构。', publishedAt: '非实时', source: 'sample:editorial', importance: 2, bias: 'neutral' },
    ],
  },
];

export const wealthCampaigns = [
  { id: 'cash-01', name: '短久期流动性方案', platform: '外部参考结构', exchange: 'all', frequency: 'daily', lock: 'short', apy: '示例 3.2%', apyValue: 3.2, apyNote: '非实时、不构成收益承诺', tags: ['现金管理', '不可申购'], expiryLabel: '非实时', expiryNote: '无正式 Owner' },
  { id: 'arb-02', name: '低波动套利组合', platform: '外部参考结构', exchange: 'all', frequency: 'floating', lock: 'mid', apy: '示例 4.8%', apyValue: 4.8, apyNote: '非真实产品或收益', tags: ['套利工具', '不可执行'], expiryLabel: '非实时', expiryNote: '无正式 Owner' },
  { id: 'gold-03', name: '黄金区间研究票据', platform: '外部参考结构', exchange: 'all', frequency: 'fixed', lock: 'long', apy: '示例 6.0%', apyValue: 6, apyNote: '仅展示产品信息结构', tags: ['结构观察', '不可申购'], expiryLabel: '非实时', expiryNote: '无正式 Owner' },
];
