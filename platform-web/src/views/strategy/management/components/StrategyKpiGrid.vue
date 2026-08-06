<template>
  <section class="strategy-kpi-grid" data-testid="strategy-kpi-grid">
    <article v-for="item in items" :key="item.label" :class="`tone-${item.tone || 'neutral'}`">
      <span>{{ item.label }}</span>
      <strong>{{ item.value }}</strong>
      <small>{{ item.note }}</small>
    </article>
  </section>
</template>

<script setup lang="ts">
  import type { StrategyKpiItem } from '@/data/sample/strategy';

  defineProps<{ items: StrategyKpiItem[] }>();
</script>

<style scoped lang="less">
  .strategy-kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
  }

  article {
    display: grid;
    gap: 6px;
    padding: 18px;
    border: 1px solid var(--strategy-border, #e4e9ef);
    border-radius: var(--strategy-radius-card, 14px);
    background: var(--strategy-surface, #fff);
    box-shadow: var(--strategy-shadow, 0 8px 24px rgba(23, 35, 57, 0.05));
  }

  span,
  small {
    color: var(--strategy-text-3, #778396);
  }

  strong {
    color: var(--strategy-text-1, #1d2b3a);
    font-size: 25px;
  }

  .tone-positive strong {
    color: #087a55;
  }

  .tone-warning strong {
    color: #a06400;
  }

  @media (max-width: 900px) {
    .strategy-kpi-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 520px) {
    .strategy-kpi-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
