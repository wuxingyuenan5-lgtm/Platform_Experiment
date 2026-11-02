<template>
  <section class="lens" aria-label="美元流动性透镜">
    <header
      ><div
        ><h3>量 · 价 · 结构</h3><p>共同观测日 {{ data?.asOf || '—' }} · 单位：十亿美元</p></div
      ><button @click="load">刷新</button></header
    >
    <p v-if="loading" role="status">正在读取流动性分项…</p
    ><p v-if="error" role="alert">{{ error }}</p>
    <template v-if="data">
      <div class="summary"
        ><article
          ><span>美元净流动性</span><strong>{{ fmt(data.latest?.net) }}</strong
          ><small>{{ data.asOf || '暂无有效日期' }}</small></article
        ><article
          ><span>过去4周变化</span
          ><strong :class="tone(data.change4w.net)">{{ signed(data.change4w.net) }}</strong
          ><small
            >{{ data.change4w.previousDate || '缺少同日基期' }} → {{ data.change4w.date }}</small
          ></article
        ><article
          ><span>Fed资产变动贡献</span
          ><strong :class="tone(data.change4w.fed)">{{ signed(data.change4w.fed) }}</strong
          ><small>过去4周</small></article
        ><article
          ><span>TGA余额变动贡献</span
          ><strong :class="tone(data.change4w.tga)">{{ signed(data.change4w.tga) }}</strong
          ><small>过去4周 · 减余额变动</small></article
        ></div
      >
      <nav aria-label="流动性视角"
        ><button v-for="t in tabs" :key="t.id" :aria-pressed="tab === t.id" @click="tab = t.id">{{
          t.name
        }}</button></nav
      >
      <div class="metric-grid"
        ><article v-for="card in visibleCards" :key="card.id"
          ><div class="metric-head"
            ><span>{{ card.name }}</span
            ><a
              v-if="card.sourceUrl"
              :href="card.sourceUrl"
              target="_blank"
              rel="noopener noreferrer"
              >来源 ↗</a
            ></div
          ><strong
            >{{ fmt(card.value) }} <small>{{ card.unit }}</small></strong
          ><small
            >{{ card.date || '暂无有效日期' }} · 较前次 {{ signed(card.change) }}
            {{ card.unit }}</small
          ><svg
            v-if="card.spark.length"
            viewBox="0 0 100 22"
            role="img"
            :aria-label="`${card.name}最近30次有效观测`"
          >
            <polyline
              :points="spark(card.spark)"
              fill="none"
              stroke="#2864ec"
              stroke-width="1.2"
            /></svg
          ><div class="rank-text">近5年内历史分位 {{ fmt(card.rank, 0) }}% · n={{ card.count }}</div
          ><div v-if="card.rank != null" class="rank-track" :aria-label="`${card.name}历史分位`"
            ><i :style="{ width: `${Number(card.rank)}%` }"></i></div
          ><small v-if="['error', 'stale', 'no_data'].includes(card.status)" class="notice">{{
            card.status === 'error'
              ? '来源更新或数据结构异常'
              : card.status === 'stale'
              ? '待更新'
              : '暂无有效数据'
          }}</small></article
        ></div
      >
      <template v-if="tab === 'quantity'">
        <FinancingChart
          v-if="data.history.length"
          title="净流动性变动 · 分项贡献"
          :rows="data.history"
          :lines="[
            {
              key: 'fedChange',
              name: 'Fed资产变动',
              color: '#2864ec',
              unit: '十亿美元',
              bar: true,
              stack: 'changes',
            },
            {
              key: 'tgaEffect',
              name: '−TGA变动',
              color: '#d09a14',
              unit: '十亿美元',
              bar: true,
              stack: 'changes',
            },
            {
              key: 'rrpEffect',
              name: '−ON RRP变动',
              color: '#00976f',
              unit: '十亿美元',
              bar: true,
              stack: 'changes',
            },
            { key: 'netChange', name: '净变动', color: '#171717', unit: '十亿美元' },
          ]"
        />
        <p class="definition"
          >4周贡献：Fed {{ fmt(data.change4w.fed, 3) }}，TGA {{ fmt(data.change4w.tga, 3) }}，ON RRP
          {{ fmt(data.change4w.rrp, 3) }}；净变动 {{ fmt(data.change4w.net, 3) }}（十亿美元）。</p
        >
      </template>
      <FinancingChart
        v-else-if="tab === 'structure' && data.structure.length"
        title="部分负债 / Fed总资产"
        :rows="data.structure"
        :lines="[
          { key: 'reserves', name: '银行准备金', color: '#2864ec', unit: '%' },
          { key: 'tga', name: 'TGA', color: '#d09a14', unit: '%' },
          { key: 'rrp', name: 'ON RRP', color: '#00976f', unit: '%' },
        ]"
      />
      <details
        ><summary>计算口径</summary
        ><p
          >净流动性 = Fed总资产 − TGA − ON
          RRP，三项严格按同一观测日匹配；总量卡片也取该共同日期。贡献图为相邻共同观测日的差分，4周变化要求28天前有共同观测。其他指标保留各自日期与发布频率。历史分位只使用观测日前5年内有效值，按数值排序，不是综合松紧评分。小图为最近30次有效观测。</p
        ></details
      >
      <a :href="data.referenceUrl" target="_blank" rel="noopener noreferrer">分析方法参考 ↗</a>
    </template>
  </section>
</template>
<script setup lang="ts">
  import { computed, onBeforeUnmount, ref, shallowRef } from 'vue';
  import { getLiquidityLens, type LiquidityLens, type LensCard } from '@/api/marketAnalytics';
  import FinancingChart from '../aShare/components/FinancingChart.vue';

  const data = shallowRef<LiquidityLens>(),
    loading = ref(false),
    error = ref(''),
    tab = ref('quantity');
  const tabs = [
    { id: 'quantity', name: '量与驱动' },
    { id: 'price', name: '融资价格' },
    { id: 'structure', name: '结构与市场反馈' },
  ];
  const visibleCards = computed(
    () =>
      data.value?.cards.filter((c) =>
        tab.value === 'quantity'
          ? c.category === '量'
          : tab.value === 'price'
          ? c.category === '价'
          : ['结构', '市场反馈'].includes(c.category),
      ) || [],
  );
  const fmt = (v: unknown, d = 2) =>
    v == null || v === '' || !Number.isFinite(Number(v))
      ? '—'
      : Number(v).toLocaleString('zh-CN', { minimumFractionDigits: d, maximumFractionDigits: d });
  const signed = (v: unknown) => (v == null ? '—' : `${Number(v) > 0 ? '+' : ''}${fmt(v)}`);
  const tone = (v: unknown) =>
    v == null ? '' : Number(v) > 0 ? 'positive' : Number(v) < 0 ? 'negative' : '';
  function spark(points: LensCard['spark']) {
    const values = points.map((p) => Number(p.value)),
      lo = Math.min(...values),
      hi = Math.max(...values);
    return values
      .map(
        (v, i) =>
          `${values.length > 1 ? (i / (values.length - 1)) * 100 : 50},${
            hi > lo ? 20 - ((v - lo) / (hi - lo)) * 18 : 11
          }`,
      )
      .join(' ');
  }
  let controller: AbortController | undefined;
  async function load() {
    controller?.abort();
    const current = new AbortController();
    controller = current;
    loading.value = true;
    error.value = '';
    try {
      const result = await getLiquidityLens(current.signal);
      if (!current.signal.aborted) data.value = result;
    } catch {
      if (!current.signal.aborted) error.value = '流动性透镜读取失败，其他图表可继续查看。';
    } finally {
      if (!current.signal.aborted) loading.value = false;
    }
  }
  void load();
  onBeforeUnmount(() => controller?.abort());
</script>
<style scoped>
  .lens {
    min-width: 0;
    padding: 4px;
    color: #17324d;
  }

  h3 {
    margin: 0;
    font-size: 18px;
  }

  header,
  nav,
  .metric-head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  header p,
  small,
  .definition,
  details {
    color: #71869d;
    font-size: 11px;
  }

  button {
    padding: 6px 10px;
    border: 1px solid #dce5ef;
    border-radius: 6px;
    background: white;
    color: inherit;
    font: inherit;
    cursor: pointer;
  }

  nav {
    justify-content: flex-start;
    margin: 16px 0;
  }

  button[aria-pressed='true'] {
    border-color: #abc3ff;
    background: #edf3ff;
    color: #2864ec;
  }

  .summary,
  .metric-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin: 16px 0;
  }

  .metric-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .summary article,
  .metric-grid article {
    display: flex;
    flex-direction: column;
    padding: 14px;
    border: 1px solid #e0e8f2;
    border-radius: 9px;
    background: #f8fafd;
    gap: 8px;
  }

  .summary span,
  .metric-head {
    font-size: 12px;
  }

  .summary strong {
    font-size: 23px;
  }

  .metric-grid strong {
    font-size: 20px;
  }

  .metric-grid svg {
    width: 100%;
    height: 32px;
  }

  .metric-head a,
  .lens > a {
    color: #2864ec;
    font-size: 11px;
  }

  .rank-text {
    color: #71869d;
    font-size: 11px;
  }

  .rank-track {
    height: 4px;
    overflow: hidden;
    border-radius: 4px;
    background: #e5ebf6;
  }

  .rank-track i {
    display: block;
    height: 100%;
    background: #7c9bd7;
  }

  .positive {
    color: #d84f5a;
  }

  .negative {
    color: #00976f;
  }

  .notice {
    color: #967025;
  }

  details {
    margin: 16px 0;
  }

  summary {
    cursor: pointer;
  }

  @media (max-width: 700px) {
    .summary,
    .metric-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
</style>
