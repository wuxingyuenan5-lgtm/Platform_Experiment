<template>
  <section class="cross-card cross-card--summary">
    <div class="card-head">
      <div>
        <h3>价差汇总</h3>
      </div>
    </div>

    <div class="summary-grid">
      <article class="summary-item">
        <label>做多价差 <small>(BY Ask - MT5 Bid)</small></label>
        <strong :class="spreadTone(longSpread)">{{ formatNullableSigned(longSpread) }} <em>USDT</em></strong>
      </article>
      <article class="summary-item">
        <label>做空价差 <small>(BY Bid - MT5 Ask)</small></label>
        <strong :class="spreadTone(shortSpread)">{{ formatNullableSigned(shortSpread) }} <em>USDT</em></strong>
      </article>
      <article class="summary-item summary-item--compact">
        <label>资费 | 买方库存费 | 卖方库存费</label>
        <strong class="summary-inline">{{ fundingInventoryText }}</strong>
      </article>
      <article class="summary-item">
        <label>USDT/USD</label>
        <strong>{{ usdtUsdText }}</strong>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
  defineProps<{
    longSpread: string | number | null | undefined;
    shortSpread: string | number | null | undefined;
    fundingInventoryText: string;
    usdtUsdText: string;
  }>();

  function parseOptionalNumber(value: string | number | null | undefined) {
    if (value === null || value === undefined || value === '') return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function formatNumber(value: number, digits = 2) {
    return value.toLocaleString('en-US', {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  }

  function formatSigned(value: number) {
    return `${value > 0 ? '+' : ''}${formatNumber(value)}`;
  }

  function formatNullableSigned(value: string | number | null | undefined) {
    const parsed = parseOptionalNumber(value);
    if (parsed === null) return '--';
    return formatSigned(parsed);
  }

  function spreadTone(value: string | number | null | undefined) {
    const parsed = parseOptionalNumber(value);
    if (parsed === null) return '';
    return parsed <= 0 ? 'green' : 'red';
  }
</script>

<style scoped lang="less">
  .cross-card {
    padding: 16px 18px 18px;
    border: 1px solid #e7ebf0;
    border-radius: 18px;
    background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
    box-shadow: 0 10px 22px rgba(94, 109, 133, 0.04);
  }

  .card-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 12px;
  }

  .card-head h3 {
    margin: 0;
    font-family: var(--strategy-font-heading);
    font-size: 21px;
    font-weight: 800;
    letter-spacing: 0;
    color: #162845;
  }

  .summary-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
    overflow: hidden;
    border: 1px solid #e9edf2;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.9);
  }

  .summary-item {
    min-height: 106px;
    padding: 14px 16px;
    border-right: 1px solid #e9edf2;
    border-bottom: 1px solid #e9edf2;
  }

  .summary-item:nth-child(2n) {
    border-right: none;
  }

  .summary-item:nth-last-child(-n + 2) {
    border-bottom: none;
  }

  .summary-item label {
    display: flex;
    align-items: baseline;
    gap: 6px;
    flex-wrap: wrap;
    margin-bottom: 7px;
    color: #1d2e4d;
    font-family: var(--strategy-font-heading);
    font-size: 16px;
    font-weight: 800;
  }

  .summary-item label small {
    color: #2f3640;
    font-size: 13px;
    font-weight: 600;
  }

  .summary-item strong {
    display: inline-flex;
    align-items: baseline;
    gap: 6px;
    margin-top: 18px;
    color: #10203f;
    font-family: var(--strategy-font-data);
    font-size: 16px;
    font-weight: 700;
    line-height: 1.2;
  }

  .summary-item--compact label {
    font-size: 14px;
  }

  .summary-item--compact strong {
    margin-top: 14px;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.01em;
    line-height: 1.3;
  }

  .summary-inline {
    white-space: nowrap;
  }

  .summary-item strong em {
    font-size: 14px;
    font-weight: 700;
    font-style: normal;
  }

  .green,
  .red {
    color: var(--strategy-text-1) !important;
  }
</style>
