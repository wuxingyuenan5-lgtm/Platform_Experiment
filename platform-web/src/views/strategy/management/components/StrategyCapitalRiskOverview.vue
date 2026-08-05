<template>
  <section class="risk-overview" data-testid="strategy-capital-risk-overview">
    <header><h2>风险概览</h2><span>只读</span></header>
    <div>
      <article v-for="item in overview" :key="item.title" :class="`tone-${item.tone || 'neutral'}`">
        <span>{{ item.title }}</span>
        <strong>{{ item.value }}</strong>
        <small>{{ item.note }}</small>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
  import type { StrategyCardItem } from '@/data/sample/strategy';

  defineProps<{ overview: StrategyCardItem[] }>();
</script>

<style scoped lang="less">
  .risk-overview {
    display: grid;
    gap: 14px;
    padding: 18px;
    border: 1px solid var(--strategy-border, #e4e9ef);
    border-radius: var(--strategy-radius-card, 14px);
    background: var(--strategy-surface, #fff);
  }

  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  h2 {
    margin: 0;
    font-size: 17px;
  }

  header span,
  article span,
  small {
    color: var(--strategy-text-3, #778396);
  }

  .risk-overview > div {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }

  article {
    display: grid;
    gap: 5px;
    padding: 14px;
    border-radius: 11px;
    background: #f7f9fc;
  }

  strong {
    font-size: 19px;
  }

  .tone-positive strong {
    color: #087a55;
  }

  .tone-warning strong {
    color: #a06400;
  }

  @media (max-width: 520px) {
    .risk-overview > div {
      grid-template-columns: 1fr;
    }
  }
</style>
