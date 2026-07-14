<template>
  <section class="capital-insight-board">
    <article class="insight-card">
      <header class="insight-card__header">
        <div>
          <h3>风控栏</h3>
        </div>
      </header>

      <div class="risk-grid">
        <article v-for="item in riskCards" :key="item.label" class="risk-item">
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
    </article>
  </section>
</template>

<script setup lang="ts">
  import type { StrategyAccountBreakdown, StrategyCapitalRiskCard } from '../types';

  defineProps<{
    riskCards: StrategyCapitalRiskCard[];
    structureCards: StrategyAccountBreakdown[];
  }>();
</script>

<style scoped lang="less">
  .capital-insight-board {
    display: grid;
    grid-template-columns: 1.05fr 1fr;
    gap: 12px;
  }

  .insight-card {
    padding: 18px 20px;
    border-radius: 20px;
    background: linear-gradient(180deg, var(--strategy-surface) 0%, var(--strategy-surface-soft) 100%);
    border: 1px solid var(--strategy-border);
    box-shadow: var(--strategy-shadow);
  }

  .insight-card__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 14px;
  }

  .insight-card__header h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 700;
    color: var(--strategy-text-1);
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
    border-radius: 16px;
    background: var(--strategy-surface);
    border: 1px solid var(--strategy-border);
  }

  .risk-item label,
  .structure-item label {
    display: block;
    color: var(--strategy-text-3);
    font-size: 12px;
    font-weight: 700;
  }

  .risk-item strong,
  .structure-item strong {
    display: block;
    margin-top: 10px;
    font-size: 22px;
    line-height: 1.12;
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
