<template>
  <section class="context" :aria-label="titles[section]">
    <p v-if="loading" role="status">正在读取{{ titles[section] }}…</p>
    <p v-if="error" role="alert">{{ error }} <button @click="load">重试</button></p>
    <template v-if="document">
      <template v-if="section === 'risk'">
        <div class="controls"
          ><label
            >指数
            <select v-model="riskIndex"
              ><option value="000300">沪深300</option
              ><option value="000016">上证50</option
              ><option value="000905">中证500</option></select
            ></label
          ><label
            >盈利口径
            <select v-model="earningsMethod"
              ><option value="Lyr">静态 PE LYR</option
              ><option value="Ttm">滚动 PE TTM</option></select
            ></label
          ></div
        >
        <div class="cards"
          ><article
            ><span>盈利收益率 − 国债收益率</span
            ><strong>{{ fmt(latestRisk?.['erp' + earningsMethod]) }} pp</strong
            ><small>{{ latestRisk?.date || '—' }}</small></article
          ><article
            ><span>盈利收益率</span
            ><strong>{{ fmt(latestRisk?.['earnings' + earningsMethod]) }}%</strong
            ><small
              >{{ earningsMethod === 'Lyr' ? '静态 PE LYR' : '滚动 PE TTM' }} 倒数</small
            ></article
          ><article
            ><span>10年期国债收益率</span><strong>{{ fmt(latestRisk?.bond) }}%</strong
            ><small>与指数估值同日匹配</small></article
          ></div
        >
        <p class="definition"
          >盈利收益率 = 100 ÷
          PE；股债差为盈利收益率减同日10年国债收益率。静态和滚动口径分别计算。</p
        >
        <FinancingChart
          v-if="riskRows.length"
          :key="riskIndex + earningsMethod"
          :title="`${riskNames[riskIndex]} · 股债性价比`"
          :rows="riskRows"
          :lines="[
            {
              key: 'erp' + earningsMethod,
              name: '盈利收益率−国债收益率',
              color: '#2864ec',
              unit: 'pp',
            },
            { key: 'close', name: riskNames[riskIndex], color: '#171717', unit: '点', right: true },
          ]"
        />
        <FinancingChart
          v-if="riskRows.length"
          :key="'inputs' + riskIndex + earningsMethod"
          title="盈利收益率与国债收益率"
          :rows="riskRows"
          :lines="[
            { key: 'earnings' + earningsMethod, name: '盈利收益率', color: '#2864ec', unit: '%' },
            { key: 'bond', name: '10年国债收益率', color: '#d09a14', unit: '%' },
          ]"
        />
        <p class="definition"
          >指数估值：Choice · 国债：中债 / 财政部收益率曲线。<a
            href="https://yield.chinabond.com.cn/cbweb-czb-web/czb/historyQuery"
            target="_blank"
            rel="noopener noreferrer"
            >国债来源 ↗</a
          >
          <a
            href="https://legulegu.com/stockdata/a-risk-premium"
            target="_blank"
            rel="noopener noreferrer"
            >公式参考 ↗</a
          ></p
        >
        <p v-if="!latestRisk" class="notice">缺少同日有效PE和国债收益率，暂不能计算股债差。</p>
        <p v-else-if="lagged(riskIndex, 'erp' + earningsMethod)" class="notice"
          >最近可计算日期为 {{ latestRisk.date }}，后续缺少同日配对数据。</p
        >
        <SourceState :source="document.sources[riskIndex]" :rows="riskRows" />
      </template>
      <template v-else-if="section === 'breadth'">
        <h3>破净比例</h3>
        <div class="cards cards-four"
          ><button
            v-for="(name, key) in markets"
            :key="key"
            :class="{ active: market === key }"
            @click="market = key"
            ><span>{{ name }}</span
            ><strong>{{ fmt(latest('below_' + key, 'value')?.value) }}%</strong
            ><small>{{ latest('below_' + key, 'value')?.date || '暂无有效日期' }}</small></button
          ></div
        >
        <p class="definition"
          >{{ markets[market] }}：{{ fmt(latest('below_' + market, 'value')?.count, 0) }}只破净 /
          {{ fmt(latest('below_' + market, 'value')?.total, 0) }}只统计样本；0 &lt; PB &lt;
          1，净资产为负的公司不计入破净数量。</p
        >
        <FinancingChart
          v-if="rows('below_' + market).length"
          :key="market"
          :title="`${markets[market]} · 破净比例`"
          :rows="rows('below_' + market)"
          :lines="[
            { key: 'value', name: '破净比例', color: '#2864ec', unit: '%' },
            {
              key: 'close',
              name: market === 'all' ? '参考指数' : markets[market],
              color: '#171717',
              unit: '点',
              right: true,
            },
          ]"
        />
        <SourceState
          :source="document.sources['below_' + market]"
          :rows="rows('below_' + market)"
        />
        <h3>全A · 均线宽度</h3>
        <div class="cards"
          ><article v-for="period in [5, 20, 60]" :key="period"
            ><span>收盘价高于{{ period }}日均线</span
            ><strong>{{ fmt(latest('ma', 'ma' + period)?.['ma' + period], 0) }}%</strong
            ><small>{{ latest('ma', 'ma' + period)?.date || '暂无有效日期' }}</small></article
          ></div
        >
        <p class="notice" v-if="lagged('ma', 'ma20')"
          >公开来源均线统计截至 {{ latest('ma', 'ma20')?.date }}，其后暂无公开统计值。</p
        >
        <FinancingChart
          v-if="rows('ma').length"
          title="全A · 站上均线的股票比例"
          :rows="rows('ma')"
          :lines="[
            { key: 'ma5', name: '高于5日均线', color: '#2864ec', unit: '%' },
            { key: 'ma20', name: '高于20日均线', color: '#00976f', unit: '%' },
            { key: 'ma60', name: '高于60日均线', color: '#d09a14', unit: '%' },
          ]"
        />
        <SourceState :source="document.sources.ma" :rows="rows('ma')" />
        <div class="controls"
          ><h3>全A · 创新高 / 新低</h3
          ><label
            >观察窗口
            <select v-model="highLowPeriod"
              ><option :value="20">20日</option
              ><option :value="60">60日</option
              ><option :value="120">120日</option></select
            ></label
          ></div
        >
        <div class="cards"
          ><article
            ><span>{{ highLowPeriod }}日新高</span
            ><strong
              >{{
                fmt(latest('highlow', 'high' + highLowPeriod)?.['high' + highLowPeriod], 0)
              }}只</strong
            ><small>{{ latest('highlow', 'high' + highLowPeriod)?.date }}</small></article
          ><article
            ><span>{{ highLowPeriod }}日新低</span
            ><strong
              >{{
                fmt(latest('highlow', 'low' + highLowPeriod)?.['low' + highLowPeriod], 0)
              }}只</strong
            ><small>{{ latest('highlow', 'low' + highLowPeriod)?.date }}</small></article
          ><article
            ><span>新高 − 新低</span
            ><strong
              >{{
                fmt(latest('highlow', 'net' + highLowPeriod)?.['net' + highLowPeriod], 0)
              }}只</strong
            ><small>同日数量差</small></article
          ></div
        >
        <p v-if="lagged('highlow', 'high20')" class="notice"
          >公开来源新高新低统计截至 {{ latest('highlow', 'high20')?.date }}，其后暂无公开统计值。</p
        >
        <FinancingChart
          v-if="rows('highlow').length"
          :key="highLowPeriod"
          title="全A · 创新高与创新低数量"
          :rows="rows('highlow')"
          :lines="[
            {
              key: 'high' + highLowPeriod,
              name: '创新高',
              color: '#d84f5a',
              unit: '只',
              bar: true,
            },
            { key: 'low' + highLowPeriod, name: '创新低', color: '#00976f', unit: '只', bar: true },
          ]"
        />
        <SourceState :source="document.sources.highlow" :rows="rows('highlow')" />
        <p class="definition"
          >均线和新高新低均为来源的全A统计、剔除停牌股，区别于股票池样本广度。</p
        >
      </template>
      <template v-else>
        <h3>总市值 / GDP</h3>
        <div class="cards"
          ><article
            ><span>总市值 / GDP</span><strong>{{ fmt(latest('buffett', 'value')?.value) }}%</strong
            ><small>{{ latest('buffett', 'value')?.date }}</small></article
          ><article
            ><span>A股总市值</span
            ><strong>{{ trillions(latest('buffett', 'value')?.marketCap) }}万亿元</strong
            ><small>沪、深、北交易所上市股票</small></article
          ><article
            ><span>年度GDP（来源口径）</span
            ><strong>{{ trillions(latest('buffett', 'value')?.gdp) }}万亿元</strong
            ><small>按来源年度值计算</small></article
          ></div
        >
        <FinancingChart
          v-if="rows('buffett').length"
          title="巴菲特指标 · 总市值 / GDP"
          :rows="rows('buffett')"
          :lines="[
            { key: 'value', name: '总市值 / GDP', color: '#2864ec', unit: '%' },
            { key: 'close', name: '沪深300', color: '#171717', unit: '点', right: true },
          ]"
        />
        <SourceState :source="document.sources.buffett" :rows="rows('buffett')" />
        <p class="definition"
          >分子为来源汇总的A股总市值，分母为来源提供的年度GDP；上市公司收入与国内GDP覆盖范围不同。</p
        >
      </template>
    </template>
  </section>
</template>
<script setup lang="ts">
  import {
    computed,
    defineComponent,
    h,
    onBeforeUnmount,
    ref,
    shallowRef,
    watch,
    type PropType,
  } from 'vue';
  import {
    getMarketContext,
    type MarketContextSection,
    type MarketMonitor,
    type MonitorRow,
    type MonitorSource,
    type MonitorValue,
  } from '@/api/cnMarketMonitor';
  import FinancingChart from './FinancingChart.vue';

  const props = defineProps<{ section: MarketContextSection; refreshKey?: number }>();
  const titles = { risk: '股债性价比', breadth: '市场宽度', macroValue: '总市值与GDP' };
  const document = shallowRef<MarketMonitor>(),
    loading = ref(false),
    error = ref('');
  const riskIndex = ref('000300'),
    earningsMethod = ref('Lyr'),
    market = ref('all'),
    highLowPeriod = ref(20);
  const riskNames: Record<string, string> = {
    '000300': '沪深300',
    '000016': '上证50',
    '000905': '中证500',
  };
  const markets: Record<string, string> = {
    all: '全部A股',
    hs300: '沪深300',
    sz50: '上证50',
    zz500: '中证500',
  };
  const rows = (key: string) => (document.value?.sources[key]?.data || []) as MonitorRow[];
  const latest = (key: string, field: string) => {
    const history = rows(key);
    for (let i = history.length - 1; i >= 0; i--) {
      if (history[i][field] != null) return history[i];
    }
    return undefined;
  };
  const riskRows = computed(() => rows(riskIndex.value));
  const latestRisk = computed(() => latest(riskIndex.value, 'erp' + earningsMethod.value));
  const fmt = (v: MonitorValue | undefined, digits = 2) =>
    v == null || v === '' || !Number.isFinite(Number(v))
      ? '—'
      : Number(v).toLocaleString('zh-CN', {
          minimumFractionDigits: digits,
          maximumFractionDigits: digits,
        });
  const trillions = (v: MonitorValue | undefined) => (v == null ? '—' : fmt(Number(v) / 10000));
  const lagged = (key: string, field: string) =>
    !!latest(key, field)?.date && latest(key, field)!.date < (rows(key).at(-1)?.date || '');
  const SourceState = defineComponent({
    props: {
      source: Object as PropType<MonitorSource>,
      rows: { type: Array as PropType<MonitorRow[]>, required: true },
    },
    setup(p) {
      return () => {
        const conflicts = p.rows.filter((r) => r.conflictFields).map((r) => r.date);
        return h('div', { class: 'source-state' }, [
          p.source?.status === 'error'
            ? h('p', { class: 'notice' }, '本轮来源更新失败，保留已有有效历史。')
            : null,
          !p.rows.length ? h('p', { class: 'notice' }, '暂无有效历史，其他图表可继续查看。') : null,
          conflicts.length
            ? h(
                'p',
                { class: 'notice' },
                `历史同日记录存在冲突，相关字段留空：${conflicts.slice(0, 5).join('、')}${
                  conflicts.length > 5 ? ' 等' : ''
                }。`,
              )
            : null,
          p.source?.sourceUrl && /^https?:\/\//.test(p.source.sourceUrl)
            ? h(
                'a',
                { href: p.source.sourceUrl, target: '_blank', rel: 'noopener noreferrer' },
                '来源 ↗',
              )
            : null,
        ]);
      };
    },
  });
  let controller: AbortController | undefined;
  async function load() {
    controller?.abort();
    const current = new AbortController();
    controller = current;
    loading.value = true;
    error.value = '';
    document.value = undefined;
    try {
      const d = await getMarketContext(props.section, current.signal);
      if (!current.signal.aborted) document.value = d;
    } catch {
      if (!current.signal.aborted) error.value = `${titles[props.section]}读取失败`;
    } finally {
      if (!current.signal.aborted) loading.value = false;
    }
  }
  watch(() => [props.section, props.refreshKey], load, { immediate: true });
  onBeforeUnmount(() => controller?.abort());
</script>
<style scoped>
  .context {
    min-width: 0;
    color: #17324d;
  }

  h3 {
    margin: 24px 0 12px;
    font-size: 16px;
  }

  .controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    margin: 16px 0;
    gap: 18px;
  }

  button,
  select {
    padding: 6px 12px;
    border: 1px solid #dce5ef;
    border-radius: 6px;
    background: white;
    color: inherit;
    font: inherit;
  }

  button {
    cursor: pointer;
  }

  button.active {
    border-color: #a7c0ff;
    background: #edf3ff;
    color: #2864ec;
  }

  .cards {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    margin: 16px 0;
  }

  .cards-four {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .cards article,
  .cards button {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    padding: 16px;
    border: 1px solid #dce5ef;
    border-radius: 10px;
    background: #f8fafd;
    gap: 8px;
  }

  .cards strong {
    font-size: 22px;
  }

  .cards small,
  .definition {
    color: #71869d;
    font-size: 12px;
  }

  .notice,
  .context :deep(.notice) {
    color: #967025;
    font-size: 12px;
  }

  a,
  .context :deep(a) {
    color: #2864ec;
  }

  .context :deep(.source-state) {
    margin: 10px 0 22px;
  }

  @media (max-width: 700px) {
    .cards,
    .cards-four {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
</style>
