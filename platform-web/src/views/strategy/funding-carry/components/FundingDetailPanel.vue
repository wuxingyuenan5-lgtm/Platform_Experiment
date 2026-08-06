<template>
  <section class="funding-detail-panel" data-testid="funding-detail-panel">
    <header
      ><div
        ><span>研究详情</span><h2>{{ exchange }} · {{ symbol }}</h2></div
      ><em>不可执行</em></header
    >
    <div class="summary-grid">
      <article v-for="item in research.summary" :key="item.label">
        <span>{{ item.label }}</span
        ><strong>{{ item.value }}</strong
        ><small>{{ item.note }}</small>
      </article>
    </div>
    <dl>
      <div v-for="item in research.details" :key="item.label"
        ><dt>{{ item.label }}</dt
        ><dd>{{ item.value }}</dd></div
      >
    </dl>
    <footer>{{ selectedRange }} · {{ resolution }} · {{ startDate }} 至 {{ endDate }}</footer>
  </section>
</template>

<script setup lang="ts">
  defineProps<{
    exchange: string;
    symbol: string;
    selectedRange: string;
    resolution: string;
    startDate: string;
    endDate: string;
    research: {
      summary: Array<{ label: string; value: string; note: string }>;
      details: Array<{ label: string; value: string }>;
    };
  }>();
</script>

<style scoped lang="less">
  .funding-detail-panel {
    display: grid;
    gap: 14px;
    padding: 18px;
    border: 1px solid #e1e7ef;
    border-radius: 14px;
    background: #fff;
  }
  header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
  }
  header div {
    display: grid;
    gap: 4px;
  }
  header span,
  small,
  footer {
    color: #738094;
  }
  h2 {
    margin: 0;
    font-size: 18px;
  }
  em {
    padding: 4px 8px;
    border-radius: 999px;
    background: #fff5d6;
    color: #8a6210;
    font-size: 11px;
    font-style: normal;
  }
  .summary-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
  }
  article {
    display: grid;
    gap: 5px;
    padding: 14px;
    border-radius: 11px;
    background: #f7f9fc;
  }
  article strong {
    font-size: 20px;
  }
  dl {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    margin: 0;
  }
  dl div {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding: 12px;
    border-bottom: 1px solid #edf1f5;
  }
  dt {
    color: #738094;
  }
  dd {
    margin: 0;
    font-weight: 700;
    text-align: right;
  }
  footer {
    font-size: 12px;
    text-align: right;
  }
  @media (max-width: 900px) {
    .summary-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }
  @media (max-width: 560px) {
    .summary-grid,
    dl {
      grid-template-columns: 1fr;
    }
  }
</style>
