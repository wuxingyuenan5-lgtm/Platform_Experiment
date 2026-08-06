<template>
  <section class="strategy-pnl-panel" data-testid="strategy-pnl-panel">
    <header>
      <div>
        <span>策略损益</span>
        <h2>{{ title }}</h2>
      </div>
      <em>Sample · Non-actionable</em>
    </header>

    <div class="pnl-grid">
      <article v-for="item in items" :key="item.title" :class="`tone-${item.tone || 'neutral'}`">
        <span>{{ item.title }}</span>
        <strong>{{ item.value }}</strong>
        <small>{{ item.note }}</small>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
  import type { StrategyCardItem } from '@/data/sample/strategy';

  defineProps<{
    title: string;
    items: StrategyCardItem[];
  }>();
</script>

<style scoped lang="less">
  .strategy-pnl-panel {
    display: grid;
    gap: 16px;
    padding: 20px;
    border: 1px solid var(--strategy-border, #e4e9ef);
    border-radius: var(--strategy-radius-card, 14px);
    background: var(--strategy-surface, #fff);
    box-shadow: var(--strategy-shadow, 0 8px 24px rgba(23, 35, 57, 0.05));
  }

  header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
  }

  header span,
  small {
    color: var(--strategy-text-3, #778396);
  }

  h2 {
    margin: 4px 0 0;
    font-size: 20px;
  }

  em {
    padding: 5px 9px;
    border-radius: 999px;
    background: #fff5d6;
    color: #8a6210;
    font-size: 11px;
    font-style: normal;
  }

  .pnl-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
  }

  article {
    display: grid;
    gap: 6px;
    padding: 16px;
    border-radius: 12px;
    background: #f7f9fc;
  }

  article strong {
    color: #1e2c3b;
    font-size: 22px;
  }

  .tone-positive strong {
    color: #087a55;
  }

  .tone-warning strong {
    color: #a06400;
  }

  @media (max-width: 900px) {
    .pnl-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 520px) {
    header {
      flex-direction: column;
    }

    .pnl-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
