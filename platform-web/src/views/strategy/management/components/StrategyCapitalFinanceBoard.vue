<template>
  <section class="capital-insight-board">
    <article class="insight-card">
      <header class="insight-card__header">
        <div>
          <h3>风控栏</h3>
        </div>
      </header>

      <div class="risk-grid">
        <article v-for="item in visibleRiskCards" :key="item.label" class="risk-item">
          <label>{{ item.label }}</label>
          <strong :class="item.tone ? `is-${item.tone}` : 'is-neutral'">{{ item.value }}</strong>
        </article>
      </div>
    </article>

    <article class="insight-card">
      <header class="insight-card__header">
        <div>
          <h3>资金结构观察</h3>
        </div>
      </header>

      <div class="structure-grid">
        <article v-for="item in structureCards" :key="item.label" class="structure-item">
          <label>{{ item.label }}</label>
          <strong :class="item.tone ? `is-${item.tone}` : 'is-neutral'">{{ item.value }}</strong>
        </article>
      </div>

      <slot name="position-distribution" />
    </article>
  </section>
</template>

<script setup lang="ts">
  import { computed } from 'vue';
  import type { StrategyAccountBreakdown, StrategyCapitalRiskCard } from '@/data/sample/strategy';

  const props = defineProps<{
    riskCards: StrategyCapitalRiskCard[];
    structureCards: StrategyAccountBreakdown[];
  }>();

  const visibleRiskCards = computed(() =>
    props.riskCards.filter((item) => !item.label.includes('持仓价值')),
  );
</script>

<style scoped lang="less">
  .capital-insight-board {
    display: grid;
    grid-template-columns: 1.05fr 1fr;
    gap: var(--strategy-space-2);
  }

  .insight-card {
    padding: 18px 20px;
    border-radius: var(--strategy-radius-panel);
    background: var(--strategy-surface);
    border: 1px solid var(--strategy-border);
    box-shadow: var(--strategy-shadow-card);
  }

  .insight-card__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 18px;
  }

  .insight-card__header h3 {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    margin: 0;
    font-size: 20px;
    line-height: 1.2;
    font-weight: 900;
    letter-spacing: 0.02em;
    color: var(--strategy-text-1);
  }

  .insight-card__header h3::before {
    width: 4px;
    height: 18px;
    border-radius: 999px;
    background: linear-gradient(180deg, var(--strategy-accent), var(--strategy-accent-strong));
    content: '';
  }

  .risk-grid,
  .structure-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .risk-item,
  .structure-item {
    padding: 14px 16px;
    border-radius: var(--strategy-radius-card);
    background: var(--strategy-surface);
    border: 1px solid var(--strategy-border-strong);
    box-shadow: var(--strategy-shadow-soft);
  }

  .risk-item label,
  .structure-item label {
    display: block;
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-xs);
    font-weight: 700;
  }

  .risk-item strong,
  .structure-item strong {
    display: block;
    margin-top: 10px;
    font-size: 22px;
    line-height: 1.12;
    font-weight: 800;
    color: var(--strategy-text-1);
  }

  .is-positive {
    color: var(--strategy-success) !important;
  }

  .is-negative {
    color: var(--strategy-danger) !important;
  }

  .is-neutral {
    color: var(--strategy-text-1) !important;
  }

  @media (max-width: 1180px) {
    .capital-insight-board {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 860px) {
    .risk-grid,
    .structure-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
