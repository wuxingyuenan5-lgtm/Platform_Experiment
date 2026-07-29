<template>
  <section class="cross-card cross-card--market-quotes">
    <div class="card-head">
      <div>
        <h3>市场报价</h3>
        <span>实时</span>
      </div>
    </div>

    <div class="quote-grid">
      <article class="quote-card">
        <div class="quote-card__head">
          <strong>BYBIT: {{ leftLegSymbol }}</strong>
          <span class="live-tag"><i class="online-dot"></i>在线</span>
        </div>
        <div class="quote-stats">
          <div class="quote-stat">
            <span>Bid</span>
            <strong class="green">{{ formatNullablePrice(bybitQuote?.bid) }}</strong>
            <small>USDT</small>
          </div>
          <div class="quote-stat">
            <span>Mid</span>
            <strong>{{ formatNullablePrice(bybitQuote?.mid) }}</strong>
            <small>USDT</small>
          </div>
          <div class="quote-stat">
            <span class="red-text">Ask</span>
            <strong class="red">{{ formatNullablePrice(bybitQuote?.ask) }}</strong>
            <small>USDT</small>
          </div>
          <div class="quote-stat">
            <span>延迟</span>
            <strong>{{ venueStatusLabel(bybitStatus) }}</strong>
            <small>&nbsp;</small>
          </div>
        </div>
      </article>

      <article class="quote-card">
        <div class="quote-card__head">
          <strong>MT5: {{ rightLegSymbol }}</strong>
          <span class="live-tag"><i class="online-dot"></i>在线</span>
        </div>
        <div class="quote-stats">
          <div class="quote-stat">
            <span>Bid</span>
            <strong class="green">{{ formatNullablePrice(mt5Quote?.bid) }}</strong>
            <small>USD</small>
          </div>
          <div class="quote-stat">
            <span>Mid</span>
            <strong>{{ formatNullablePrice(mt5Quote?.mid) }}</strong>
            <small>USD</small>
          </div>
          <div class="quote-stat">
            <span class="red-text">Ask</span>
            <strong class="red">{{ formatNullablePrice(mt5Quote?.ask) }}</strong>
            <small>USD</small>
          </div>
          <div class="quote-stat">
            <span>延迟</span>
            <strong>{{ venueStatusLabel(mt5Status) }}</strong>
            <small>&nbsp;</small>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
  import type { MarketQuoteResult } from '@/api/platform/trading.types';

  defineProps<{
    leftLegSymbol: string;
    rightLegSymbol: string;
    bybitQuote: MarketQuoteResult | null;
    mt5Quote: MarketQuoteResult | null;
    bybitStatus?: string | null;
    mt5Status?: string | null;
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

  function formatNullablePrice(value: string | number | null | undefined, digits = 2) {
    const parsed = parseOptionalNumber(value);
    return parsed === null ? '--' : formatNumber(parsed, digits);
  }

  function venueStatusLabel(status: string | null | undefined) {
    if (status === 'available') return '可用';
    if (status === 'timeout') return '超时';
    if (status === 'unavailable') return '不可用';
    return '等待';
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
    letter-spacing: -0.012em;
    color: #162845;
  }

  .card-head span {
    display: none;
  }

  .quote-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .quote-card {
    display: flex;
    flex-direction: column;
    min-height: 208px;
    padding: 18px 18px 14px;
    border: 1px solid #e9edf2;
    border-radius: 16px;
    background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
  }

  .quote-card__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px 14px;
    flex-wrap: wrap;
    margin-bottom: 14px;
    color: #1a2b4a;
  }

  .quote-card__head strong {
    font-size: 18px;
    font-weight: 800;
  }

  .live-tag {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    color: #19a04d;
    font-size: 12px;
    font-weight: 700;
  }

  .online-dot {
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: #1db954;
    box-shadow: 0 0 0 3px rgba(29, 185, 84, 0.12);
  }

  .quote-stats {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 8px;
    flex: 1;
    align-items: stretch;
  }

  .quote-stat {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 8px;
    min-width: 0;
    min-height: 92px;
  }

  .quote-stat span {
    color: #2f3640;
    font-size: 13px;
    font-weight: 800;
  }

  .quote-stat strong {
    font-family: var(--strategy-font-data);
    font-size: clamp(14px, 0.82vw, 18px);
    line-height: 1.08;
    font-weight: 600;
    letter-spacing: -0.02em;
    white-space: nowrap;
  }

  .quote-stat small {
    color: #2f3640;
    font-size: 12px;
    font-weight: 600;
  }

  .green {
    color: var(--strategy-success, #168a4a);
  }

  .red,
  .red-text {
    color: var(--strategy-danger, #c94848);
  }

  @media (max-width: 1480px) {
    .quote-grid {
      grid-template-columns: 1fr;
    }

    .quote-stats {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
</style>
