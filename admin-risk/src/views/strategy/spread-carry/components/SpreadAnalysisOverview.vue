<template>
  <section class="spread-overview">
    <article class="spread-card spread-card--table">
      <header>期限结构</header>
      <table>
        <thead>
          <tr>
            <th>合约</th>
            <th>价格</th>
            <th>升贴水</th>
            <th>当前年化</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in termRows" :key="item.contract">
            <td>{{ item.contract }}</td>
            <td>{{ item.price }}</td>
            <td>{{ item.premium }}</td>
            <td>{{ item.annualized }}</td>
          </tr>
        </tbody>
      </table>
    </article>

    <article class="spread-card">
      <header>
        <span>机会分析</span>
        <button type="button" @click="$emit('refresh')">刷新</button>
      </header>
      <div class="analysis-grid">
        <div class="analysis-head">
          <span></span>
          <span>当前</span>
          <span>10%</span>
          <span>50%</span>
          <span>90%</span>
        </div>
        <div v-for="item in premiumRows" :key="item.label" class="analysis-row">
          <strong>{{ item.label }}</strong>
          <span>{{ item.current }}</span>
          <span>{{ item.p10 }}</span>
          <span>{{ item.p50 }}</span>
          <span>{{ item.p90 }}</span>
        </div>
      </div>
    </article>
  </section>
</template>

<script setup lang="ts">
  defineEmits<{
    (event: 'refresh'): void;
  }>();

  const termRows = [
    { contract: 'COMEX GCQ6', price: '2,353.6', premium: '18.7', annualized: '8.42%' },
    { contract: 'COMEX GCV6', price: '2,360.1', premium: '21.4', annualized: '9.10%' },
    { contract: 'LBMA Spot', price: '2,334.9', premium: '--', annualized: '--' },
  ] as const;

  const premiumRows = [
    { label: '近一月', current: '18.7', p10: '6.8', p50: '13.2', p90: '22.4' },
    { label: '近一季度', current: '16.4', p10: '4.5', p50: '11.8', p90: '21.1' },
    { label: '近一年', current: '14.9', p10: '-2.3', p50: '9.7', p90: '20.2' },
  ] as const;
</script>

<style scoped lang="less">
  .spread-overview {
    display: grid;
    grid-template-columns: 1.1fr 1fr;
    gap: 12px;
  }

  .spread-card {
    padding: var(--strategy-space-3);
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-panel);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-card);
  }

  .spread-card header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-card-title);
    font-weight: 800;
  }

  .spread-card header button {
    height: var(--strategy-control-height);
    padding: 0 var(--strategy-space-2);
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
    font-size: var(--strategy-font-base);
    font-weight: 700;
    box-shadow: var(--strategy-shadow-soft);
    cursor: pointer;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th,
  td {
    padding: 10px 0;
    border-bottom: 1px solid var(--strategy-border-soft);
    text-align: left;
    font-size: var(--strategy-font-sm);
  }

  th {
    color: var(--strategy-text-3);
    font-weight: 700;
  }

  td {
    color: var(--strategy-text-2);
    font-weight: 700;
  }

  .analysis-grid {
    display: grid;
    gap: 10px;
  }

  .analysis-head,
  .analysis-row {
    display: grid;
    grid-template-columns: 1.2fr repeat(4, 1fr);
    gap: 8px;
    align-items: center;
  }

  .analysis-head {
    color: var(--strategy-text-faint);
    font-size: var(--strategy-font-sm);
    font-weight: 800;
  }

  .analysis-row {
    padding: 10px 0;
    border-bottom: 1px solid var(--strategy-border-soft);
    color: var(--strategy-text-2);
    font-weight: 700;
  }

  @media (max-width: 1320px) {
    .spread-overview {
      grid-template-columns: 1fr;
    }
  }
</style>
