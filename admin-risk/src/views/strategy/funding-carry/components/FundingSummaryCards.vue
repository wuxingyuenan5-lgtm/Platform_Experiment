<template>
  <article class="summary-shell">
    <div class="summary-time">{{ updatedAt }}</div>

    <div class="summary-grid">
      <div v-for="item in metrics" :key="item.label" class="summary-item">
        <label>{{ item.label }}</label>
        <small>{{ item.unit || 'Value' }}</small>
        <strong :class="item.tone ? `is-${item.tone}` : ''">{{ item.value }}</strong>
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
  import type { FundingSummaryMetric } from '../types';

  defineProps<{
    updatedAt: string;
    metrics: FundingSummaryMetric[];
  }>();
</script>

<style scoped lang="less">
  .summary-shell {
    overflow: hidden;
    border: 1px solid var(--strategy-border);
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.9);
    box-shadow: var(--strategy-shadow);
  }

  .summary-time {
    padding: 12px 18px;
    color: var(--strategy-text-3);
    font-size: 12px;
    text-align: right;
    border-bottom: 1px solid var(--strategy-border);
    background: var(--strategy-surface-muted);
  }

  .summary-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .summary-item {
    min-height: 108px;
    padding: 18px;
    border-right: 1px solid var(--strategy-border);
    border-bottom: 1px solid var(--strategy-border);
  }

  .summary-item:nth-child(4n) {
    border-right: none;
  }

  .summary-item label,
  .summary-item small,
  .summary-item strong {
    display: block;
  }

  .summary-item label {
    color: var(--strategy-text-2);
    font-size: 12px;
    font-weight: 700;
  }

  .summary-item small {
    margin-top: 4px;
    color: var(--strategy-text-3);
    font-size: 11px;
  }

  .summary-item strong {
    margin-top: 10px;
    color: var(--strategy-text-1);
    font-size: 28px;
    font-weight: 900;
    line-height: 1.1;
  }

  .summary-item .is-positive {
    color: #1ea15e;
  }

  .summary-item .is-negative {
    color: #db3a34;
  }

  @media (max-width: 1200px) {
    .summary-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .summary-item:nth-child(2n) {
      border-right: none;
    }
  }

  @media (max-width: 640px) {
    .summary-grid {
      grid-template-columns: 1fr;
    }

    .summary-item {
      border-right: none;
    }
  }
</style>
