<template>
  <span v-if="isPrimitive" class="data-primitive">{{ formatPrimitive(value) }}</span>
  <div v-else-if="isArray" class="data-array">
    <div v-if="!arrayValue.length" class="data-empty">暂无数据</div>
    <article v-for="(item, index) in arrayValue" :key="index" class="data-array__item">
      <span class="data-array__index">{{ index + 1 }}</span>
      <ResearchDataRenderer :value="item" />
    </article>
  </div>
  <dl v-else class="data-object">
    <template v-for="entry in objectEntries" :key="entry[0]">
      <dt>{{ label(entry[0]) }}</dt>
      <dd><ResearchDataRenderer :value="entry[1]" /></dd>
    </template>
  </dl>
</template>

<script setup lang="ts">
  import { computed } from 'vue';

  defineOptions({ name: 'ResearchDataRenderer' });
  const props = defineProps<{ value: unknown }>();

  const isArray = computed(() => Array.isArray(props.value));
  const arrayValue = computed(() => (Array.isArray(props.value) ? props.value : []));
  const isPrimitive = computed(
    () => props.value == null || ['string', 'number', 'boolean'].includes(typeof props.value),
  );
  const objectEntries = computed<[string, unknown][]>(() => {
    if (!props.value || typeof props.value !== 'object' || Array.isArray(props.value)) return [];
    return Object.entries(props.value as Record<string, unknown>);
  });

  const labels: Record<string, string> = {
    name: '名称', code: '代码', price: '价格', lastClose: '昨收', open: '开盘', high: '最高', low: '最低',
    changeAmount: '涨跌额', changePct: '涨跌幅', turnoverYuan: '成交额', turnoverPct: '换手率',
    peTtm: 'PE-TTM', peStatic: '静态PE', pb: 'PB', marketCapYuan: '总市值', floatMarketCapYuan: '流通市值',
    volumeRatio: '量比', amplitudePct: '振幅', limitUp: '涨停价', limitDown: '跌停价', period: '报告期',
    revenue: '营业收入', revenueYoy: '营收同比', netProfit: '净利润', netProfitYoy: '净利同比', eps: '每股收益',
    bvps: '每股净资产', roe: 'ROE', grossMargin: '毛利率', netMargin: '净利率',
    operatingCashFlowPerShare: '每股经营现金流', year: '年度', meanEps: '一致预期EPS', institutionCount: '预测机构数',
    forwardPe: '前向PE', growthPct: '增长率', peg: 'PEG', digestYears: '估值消化年数', analystCount: '分析师覆盖',
    current: '当前值', percentile: '历史分位', min: '最小值', max: '最大值', p20: '20%分位', p50: '中位数',
    p80: '80%分位', observations: '样本数', title: '标题', organization: '机构', author: '作者', rating: '评级',
    publishedAt: '发布时间', pdfUrl: '原文', url: '链接', date: '日期', type: '类型', source: '来源', content: '内容',
    financingBalance: '融资余额', financingBuy: '融资买入', financingRepay: '融资偿还', securitiesBalance: '融券余额',
    securitiesSell: '融券卖出', totalBalance: '两融合计', holderCount: '股东户数', averageFreeShares: '户均持股',
    history: '历史记录', mainNet20d: '近20日主力净流入', mainNet: '主力净流入', smallNet: '小单净流入',
    mediumNet: '中单净流入', largeNet: '大单净流入', superNet: '超大单净流入', progress: '进度',
    pretaxBonusRmb: '税前派息', transferRatio: '转增比例', bonusRatio: '送股比例', premiumPct: '折溢价率',
    volume: '成交量', amount: '成交额', buyer: '买方营业部', seller: '卖方营业部', reason: '上榜原因',
    netBuyYuan: '净买入', turnoverPct: '换手率', buy: '买入席位', sell: '卖出席位', buyYuan: '买入额',
    sellYuan: '卖出额', netYuan: '净额', upcoming: '未来90日', shares: '解禁股数', availableShares: '实际可流通股数',
    ratioPct: '解禁比例', company: '公司', question: '问题', answer: '回复', answerer: '回复人', askedAt: '提问时间',
    swL1Name: '申万一级', swL1Code: '申万一级代码', swL2Name: '申万二级', swL2Code: '申万二级代码',
    classificationVersion: '分类版本', effectiveFrom: '生效日期', forecasts: '一致预期明细', metrics: '估值指标',
    records: '上榜记录', seats: '席位明细', pdfURL: '原文', securityCode: '股票代码', securityName: '股票名称',
  };

  function label(key: string) {
    return labels[key] || key.replace(/([A-Z])/g, ' $1').trim();
  }

  function formatPrimitive(value: unknown) {
    if (value == null || value === '') return '—';
    if (typeof value === 'boolean') return value ? '是' : '否';
    return String(value);
  }
</script>

<style scoped lang="less">
  .data-primitive { color: var(--strategy-text-2); word-break: break-word; }
  .data-empty { padding: 10px; color: var(--strategy-text-4); text-align: center; }
  .data-array { display: grid; gap: 8px; }
  .data-array__item { display: grid; grid-template-columns: 28px minmax(0, 1fr); gap: 8px; padding: 9px; border: 1px solid var(--strategy-border); border-radius: 9px; background: var(--strategy-surface); }
  .data-array__index { display: grid; place-items: center; width: 24px; height: 24px; border-radius: 999px; background: var(--strategy-surface-2); color: var(--strategy-text-4); font-size: 11px; }
  .data-object { display: grid; grid-template-columns: minmax(110px, .32fr) minmax(0, 1fr); margin: 0; }
  .data-object dt, .data-object dd { margin: 0; padding: 8px 10px; border-bottom: 1px solid var(--strategy-border); }
  .data-object dt { color: var(--strategy-text-3); font-size: 12px; }
  .data-object dd { min-width: 0; color: var(--strategy-text-2); }
  .data-object dt:last-of-type, .data-object dd:last-of-type { border-bottom: 0; }
  @media (max-width: 640px) { .data-object { grid-template-columns: 1fr; } .data-object dt { padding-bottom: 2px; border-bottom: 0; } .data-object dd { padding-top: 2px; } }
</style>
