<template>
  <section class="history-risk" aria-label="历史收益与回撤">
    <header
      ><div
        ><h2>历史收益与回撤</h2
        ><p
          >{{ data?.start || '—' }} — {{ data?.asOf || '—' }} · {{ data?.samples || 0 }}个收盘观测 ·
          价格收益，不含现金分红再投资</p
        ></div
      ><label
        >分析标的
        <select v-model="instrument"
          ><option value="spy">标普500 ETF · SPY</option
          ><option value="ndx">纳斯达克100指数</option
          ><option value="dow">道琼斯工业指数</option
          ><option value="soxx">半导体 ETF · SOXX</option
          ><option value="xlk">信息技术 ETF · XLK</option></select
        ></label
      ></header
    >
    <p v-if="loading" role="status">正在读取所选标的历史…</p>
    <p v-if="error" role="alert">{{ error }} <button @click="load">重试</button></p>
    <template v-if="data?.samples">
      <div class="cards"
        ><article
          ><span>最新收盘</span><strong>{{ fmt(data.summary.price) }} {{ data.unit }}</strong
          ><small>{{ data.asOf }}</small></article
        ><article
          ><span>距样本历史高点</span><strong>{{ fmt(data.summary.drawdown) }}%</strong
          ><small>按观测收盘价</small></article
        ><article
          ><span>样本最大回撤</span><strong>{{ fmt(data.summary.maxDrawdown) }}%</strong
          ><small>{{ data.start }}以来</small></article
        ><article
          ><span>区间价格年化</span><strong>{{ fmt(data.summary.cagr) }}%</strong
          ><small>按实际日历持有长度</small></article
        ></div
      >
      <nav aria-label="历史分析分类"
        ><button v-for="t in tabs" :key="t.id" :aria-pressed="view === t.id" @click="view = t.id">{{
          t.name
        }}</button></nav
      >
      <template v-if="view === 'drawdown'">
        <FinancingChart
          :key="instrument + view"
          :title="`${data.name} · 回撤与价格`"
          :rows="data.history"
          :lines="[
            { key: 'drawdown', name: '距样本高点回撤', color: '#2864ec', unit: '%' },
            { key: 'close', name: data.name, color: '#171717', unit: data.unit, right: true },
          ]"
        />
        <div class="controls"
          ><h3>回撤登记</h3
          ><label
            >最低回撤
            <select v-model="threshold"
              ><option :value="5">5%</option
              ><option :value="10">10%</option
              ><option :value="20">20%</option></select
            ></label
          ></div
        >
        <div class="table-scroll"
          ><table
            ><thead
              ><tr
                ><th>峰值日期</th><th>低点日期</th><th>最大跌幅</th><th>观测恢复日期</th
                ><th>水下日历天数</th></tr
              ></thead
            ><tbody
              ><tr v-for="e in episodes" :key="e.peakDate"
                ><td>{{ e.peakDate }}</td
                ><td>{{ e.troughDate }}</td
                ><td class="negative">{{ fmt(e.depth) }}%</td
                ><td>{{ e.recoveryDate || '尚未恢复' }}</td
                ><td>{{ e.daysUnderwater }}</td></tr
              ><tr v-if="!episodes.length"
                ><td colspan="5">该样本内没有符合阈值的回撤</td></tr
              ></tbody
            ></table
          ></div
        >
      </template>
      <template v-else-if="view === 'annual'">
        <FinancingChart
          :key="instrument + view"
          :title="`${data.name} · 年度收益与年内回撤`"
          :rows="data.annual"
          :lines="[
            { key: 'return', name: '年度 / YTD价格收益', color: '#d84f5a', unit: '%', bar: true },
            { key: 'drawdown', name: '年内最大回撤', color: '#00976f', unit: '%', bar: true },
          ]"
        />
        <div class="table-scroll"
          ><table
            ><thead
              ><tr><th>年度</th><th>价格收益</th><th>年内最大回撤</th><th>收盘样本</th></tr></thead
            ><tbody
              ><tr v-for="r in [...data.annual].reverse()" :key="r.year"
                ><th>{{ r.year }}{{ r.partial ? ' · 区间 / YTD' : '' }}</th
                ><td :class="tone(r.return)">{{ fmt(r.return) }}%</td
                ><td class="negative">{{ fmt(r.drawdown) }}%</td><td>{{ r.samples }}</td></tr
              ></tbody
            ></table
          ></div
        >
      </template>
      <template v-else>
        <FinancingChart
          :key="instrument + view"
          :title="`${data.name} · 五年滚动价格年化`"
          :rows="data.history"
          :lines="[{ key: 'rolling5y', name: '五年滚动年化', color: '#2864ec', unit: '%' }]"
        />
        <FinancingChart
          :key="instrument + 'vol'"
          :title="`${data.name} · 已实现波动率`"
          :rows="data.history"
          :lines="[
            { key: 'vol20', name: '20个收盘收益观测', color: '#2864ec', unit: '%' },
            { key: 'vol60', name: '60个收盘收益观测', color: '#d09a14', unit: '%' },
          ]"
        />
      </template>
      <p v-if="data.invalid || data.gaps" class="notice"
        >存在 {{ data.invalid }}个无效收盘、{{
          data.gaps
        }}段超过7个日历日的间隔；日收益和波动率不跨这些缺口计算。</p
      >
      <details
        ><summary>计算口径</summary
        ><p
          >回撤以样本内已观测最高收盘价计算，登记表按跌幅排序；恢复日期为首次观测到收盘价重回原峰值的日期。年内回撤包含上年末收盘作为年初起点，首年缺少上年末价格时年度收益留空。五年年化按接近五周年的前一有效收盘及实际日历长度计算；20/60期波动率使用有效收盘收益的样本标准差
          × √252。历史交易日完整性尚未全量核验。</p
        ></details
      >
      <footer
        ><a :href="data.sourceUrl" target="_blank" rel="noopener noreferrer">价格来源 ↗</a
        ><a :href="data.referenceUrl" target="_blank" rel="noopener noreferrer">分析参考 ↗</a
        ><button @click="load">刷新</button></footer
      >
    </template>
    <p v-else-if="data && !loading">所选标的暂无可用历史，其他模块可继续查看。</p>
  </section>
</template>
<script setup lang="ts">
  import { computed, onBeforeUnmount, ref, shallowRef, watch } from 'vue';
  import { getHistoryRisk, type HistoryRisk } from '@/api/marketAnalytics';
  import FinancingChart from '../aShare/components/FinancingChart.vue';

  const instrument = ref('spy'),
    view = ref('drawdown'),
    threshold = ref(10),
    loading = ref(false),
    error = ref('');
  const data = shallowRef<HistoryRisk>();
  const tabs = [
    { id: 'drawdown', name: '回撤与恢复' },
    { id: 'annual', name: '年度收益与回撤' },
    { id: 'holding', name: '长期持有与波动' },
  ];
  const fmt = (v: unknown) =>
    v == null || v === '' || !Number.isFinite(Number(v))
      ? '—'
      : Number(v).toLocaleString('zh-CN', { maximumFractionDigits: 2, minimumFractionDigits: 2 });
  const tone = (v: unknown) =>
    v == null ? '' : Number(v) > 0 ? 'positive' : Number(v) < 0 ? 'negative' : '';
  const episodes = computed(
    () =>
      data.value?.episodes.filter((e) => e.depth != null && Number(e.depth) <= -threshold.value) ||
      [],
  );
  let controller: AbortController | undefined;
  async function load() {
    controller?.abort();
    const current = new AbortController();
    controller = current;
    loading.value = true;
    error.value = '';
    data.value = undefined;
    try {
      const result = await getHistoryRisk(instrument.value, current.signal);
      if (!current.signal.aborted) data.value = result;
    } catch {
      if (!current.signal.aborted) error.value = '历史分析读取失败';
    } finally {
      if (!current.signal.aborted) loading.value = false;
    }
  }
  watch(instrument, load, { immediate: true });
  onBeforeUnmount(() => controller?.abort());
</script>
<style scoped>
  .history-risk {
    min-width: 0;
    margin-top: 24px;
    padding: 20px;
    border: 1px solid #dce5ef;
    border-radius: 14px;
    background: #fff;
    color: #17324d;
  }

  h2 {
    margin: 0;
    font-size: 20px;
  }

  h3 {
    font-size: 15px;
  }

  header,
  .controls,
  nav,
  footer {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    gap: 12px;
  }

  nav,
  footer {
    justify-content: flex-start;
  }

  header p,
  small,
  details {
    color: #71869d;
    font-size: 12px;
  }

  select,
  button {
    padding: 6px 10px;
    border: 1px solid #dce5ef;
    border-radius: 6px;
    background: white;
    color: inherit;
    font: inherit;
  }

  button {
    cursor: pointer;
  }

  button[aria-pressed='true'] {
    border-color: #abc3ff;
    background: #edf3ff;
    color: #2864ec;
  }

  .cards {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin: 16px 0;
  }

  .cards article {
    display: flex;
    flex-direction: column;
    padding: 14px;
    border: 1px solid #e0e8f2;
    border-radius: 9px;
    background: #f8fafd;
    gap: 8px;
  }

  .cards span {
    font-size: 12px;
  }

  .cards strong {
    font-size: 21px;
  }

  .table-scroll {
    max-height: 500px;
    margin: 16px 0;
    overflow: auto;
    border: 1px solid #e0e8f2;
    border-radius: 9px;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    white-space: nowrap;
  }

  th,
  td {
    padding: 10px;
    border-bottom: 1px solid #edf1f5;
    text-align: right;
  }

  th:first-child,
  td:first-child {
    text-align: left;
  }

  thead {
    position: sticky;
    top: 0;
    background: #f4f7fb;
  }

  details {
    margin: 16px 0;
  }

  summary {
    cursor: pointer;
  }

  .positive {
    color: #d84f5a;
  }

  .negative {
    color: #00976f;
  }

  .notice {
    color: #967025;
    font-size: 12px;
  }

  footer a {
    color: #2864ec;
  }

  @media (max-width: 700px) {
    .cards {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .history-risk {
      padding: 12px;
    }
  }
</style>
