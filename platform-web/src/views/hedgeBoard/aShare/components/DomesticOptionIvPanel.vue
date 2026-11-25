<template>
  <article class="derivative-card">
    <header><h3>国内股票期权 IV</h3></header>
    <div class="controls">
      <label
        >标的
        <select v-model="underlying" aria-label="期权标的"
          ><option value="IO">沪深300股指期权（IO）</option
          ><option value="HO">上证50股指期权（HO）</option
          ><option value="MO">中证1000股指期权（MO）</option
          ><option value="510050">50ETF</option
          ><option value="510300">沪深300ETF（510300）</option
          ><option value="159919">沪深300ETF（159919）</option
          ><option value="510500">中证500ETF（510500）</option
          ><option value="159922">中证500ETF（159922）</option
          ><option value="588000">科创50ETF（588000）</option
          ><option value="588080">科创50ETF（588080）</option
          ><option value="159915">创业板ETF（159915）</option
          ><option value="159901">深证100ETF（159901）</option></select
        ></label
      ></div
    >
    <p v-if="!ivRows.length" role="status">暂无该标的的连续 IV 数据。</p>
    <FinancingChart
      v-else
      class="option-iv-chart"
      :title="isIndexOption ? '主力连续 IV' : '近月连续 IV'"
      :rows="ivRows"
      :lines="ivLines"
      embedded
      allow-table
      :note="
        isIndexOption
          ? '每日按到期月份合计成交量选主力，成交量相同取较近月份。'
          : isSzseOption
          ? '取近月最接近50 Delta的标准认购和认沽。IV 按深交所公布的 Gamma、Vega 反推后取均值。'
          : '取近月最接近50 Delta的标准认购、认沽合约IV均值。'
      "
    />
    <p v-if="ivRows.length" class="source"
      >来源：<a
        :href="
          isIndexOption
            ? 'https://www.cffex.com.cn/rtj/'
            : isSzseOption
            ? 'https://www.szse.cn/option/quotation/delay/risk/'
            : 'https://www.sse.com.cn/assortment/options/risk/'
        "
        target="_blank"
        rel="noreferrer"
        >{{
          isIndexOption
            ? '中金所日行情'
            : isSzseOption
            ? '深交所合约风险指标'
            : '上交所期权风险指标'
        }}
        ↗</a
      >
      · {{ ivRows.at(-1)?.date || '—' }}
      <template v-if="ivIndex?.sourceUrl">
        ·
        <a :href="ivIndex.sourceUrl" target="_blank" rel="noreferrer">{{ ivIndex.name }}收盘 ↗</a>
      </template>
      <template v-if="ivIndex?.historySourceUrl">
        ·
        <a :href="ivIndex.historySourceUrl" target="_blank" rel="noreferrer">指数历史 ↗</a>
      </template></p
    >
  </article>
</template>
<script setup lang="ts">
  import { useDomesticOptionIv } from './useDomesticFinancing';
  import FinancingChart from './FinancingChart.vue';

  const { underlying, isIndexOption, isSzseOption, ivRows, ivIndex, ivLines } =
    useDomesticOptionIv();
</script>
<style scoped>
  .derivative-card {
    min-width: 0;
    height: 100%;
    padding: 18px;
    border: 1px solid var(--strategy-border);
    border-radius: 14px;
    background: var(--strategy-surface);
  }

  header {
    padding-right: 38px;
  }

  h3 {
    margin: 0;
    font-size: 15px;
  }

  .controls {
    display: flex;
    margin: 16px 0;
    font-size: 12px;
  }

  .controls label {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
  }

  select {
    max-width: 100%;
    padding: 6px 10px;
    border: 1px solid #d7e3ee;
    border-radius: 7px;
    background: #fff;
    color: #294d68;
    font: inherit;
  }

  select:focus-visible {
    outline: 2px solid var(--strategy-accent);
    outline-offset: 2px;
  }

  .source {
    overflow-wrap: anywhere;
    line-height: 1.7;
  }

  :deep(.financing-chart.is-embedded) {
    margin: 0;
    padding: 0;
  }
</style>
