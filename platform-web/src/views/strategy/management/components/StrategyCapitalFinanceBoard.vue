<template>
  <section class="capital-finance-board" data-testid="strategy-capital-finance-board">
    <article>
      <header><h2>账户风险</h2><span>只读</span></header>
      <div class="card-grid">
        <div v-for="item in riskCards" :key="item.title" :class="`tone-${item.tone || 'neutral'}`">
          <span>{{ item.title }}</span>
          <strong>{{ item.value }}</strong>
          <small>{{ item.note }}</small>
        </div>
      </div>
    </article>

    <article>
      <header><h2>资金结构</h2><span>只读</span></header>
      <div class="card-grid">
        <div
          v-for="item in structureCards"
          :key="item.title"
          :class="`tone-${item.tone || 'neutral'}`"
        >
          <span>{{ item.title }}</span>
          <strong>{{ item.value }}</strong>
          <small>{{ item.note }}</small>
        </div>
      </div>
    </article>
  </section>
</template>

<script setup lang="ts">
  import type { StrategyCardItem } from '@/data/sample/strategy';

  defineProps<{
    riskCards: StrategyCardItem[];
    structureCards: StrategyCardItem[];
  }>();
</script>

<style scoped lang="less">
  .capital-finance-board {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  article {
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
  small,
  .card-grid span {
    color: var(--strategy-text-3, #778396);
  }

  .card-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }

  .card-grid > div {
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

  @media (max-width: 900px) {
    .capital-finance-board {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 520px) {
    .card-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
